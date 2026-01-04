import asyncio
import os
import sys
from argparse import Namespace
from enum import Enum
from typing import TYPE_CHECKING, Any

import Utils
from CommonClient import CommonContext, gui_enabled, logger, server_loop, ClientCommandProcessor
from NetUtils import ClientStatus
from settings import get_settings
from Utils import parse_yaml

from kvui import KivyJSONtoTextParser

from ..api import (
    set_user_info,
    new_submissions,
    CFAPIError,
    set_last_checked_submission,
    get_last_checked_ts,
    default_last_checked_ts,
)
from ..game.events import ConfettiFired, LocationClearedEvent, VictoryEvent, ProblemSolveEvent
from ..game.game import Game
from .game_manager import CodeforcesManager

if TYPE_CHECKING:
    import kvui


class ConnectionStatus(Enum):
    NOT_CONNECTED = 0
    SCOUTS_NOT_SENT = 1
    SCOUTS_SENT = 2
    GAME_RUNNING = 3


class CodeforcesCommands(ClientCommandProcessor):
    ctx: "CodeforcesContext"

    def _cmd_clear_cf(self) -> bool:
        """Clears the codeforces check window so it can check your submissions again."""
        self.ctx.queue_clear = True
        self.output("Cleared!")
        return True


class CodeforcesContext(CommonContext):
    game = "Codeforces"
    items_handling = 0b111  # full remote

    client_loop: asyncio.Task[None]

    last_connected_slot: int | None = None

    slot_data: dict[str, Any]

    codeforces_game: Game | None = None

    progressive_keys: bool = False
    memory_upgrades: list[int | str]
    time_limit_upgrades: list[int | str]
    problem_data: list[dict[str, Any]]

    connection_status: ConnectionStatus = ConnectionStatus.NOT_CONNECTED

    command_processor = CodeforcesCommands

    highest_processed_item_index: int = 0
    queued_locations: list[int]
    queued_solves: list[int]

    ui: CodeforcesManager

    def __init__(self, server_address: str | None = None, password: str | None = None) -> None:
        super().__init__(server_address, password)

        self.queued_locations = []
        self.queued_solves = []
        self.queue_clear = False
        self.slot_data = {}
        self.kivy_parser = KivyJSONtoTextParser(self)

        settings = get_settings()
        cf_settings = settings.codeforces_options

        cf_yaml = os.path.expanduser(str(cf_settings.codeforces_info))
        if not os.path.exists(cf_yaml):
            # Touch based on template
            with open(Utils.local_path("worlds/codeforces/client/template_settings.yaml"), "r") as f:
                content = f.read()
            with open(cf_yaml, "w") as f:
                f.write(content)
        self.collect_cf_info()

    def solved_key(self, index: int):
        return f"_problem_solves_{self.team}_{self.slot}_{index}"

    def last_checked_key(self):
        return f"_last_checked_ts_{self.team}_{self.slot}"

    async def solve_problem(self, index: int):
        self.stored_data[self.solved_key(index)] = True
        await self.send_msgs(
            [
                {
                    "cmd": "Set",
                    "key": self.solved_key(index),
                    "default": False,
                    "want_reply": False,
                    "operations": [{"operation": "replace", "value": True}],
                }
            ]
        )

    async def set_last_checked(self, ts: int):
        self.stored_data[self.last_checked_key()] = ts
        await self.send_msgs(
            [
                {
                    "cmd": "Set",
                    "key": self.last_checked_key(),
                    "default": False,
                    "want_reply": False,
                    "operations": [{"operation": "replace", "value": ts}],
                }
            ]
        )

    async def clear_check(self):
        set_last_checked_submission(default_last_checked_ts())
        self.stored_data[self.last_checked_key()] = get_last_checked_ts()
        await self.send_msgs(
            [
                {
                    "cmd": "Set",
                    "key": self.last_checked_key(),
                    "default": False,
                    "want_reply": False,
                    "operations": [{"operation": "replace", "value": None}],
                }
            ]
        )

    def get_yaml_path(self):
        settings = get_settings()
        cf_settings = settings.codeforces_options
        return os.path.expanduser(str(cf_settings.codeforces_info))

    def collect_cf_info(self):
        last_checked = self.stored_data.get(self.last_checked_key(), None)
        if last_checked:
            set_last_checked_submission(last_checked)
        else:
            set_last_checked_submission(default_last_checked_ts())

        cf_yaml = self.get_yaml_path()

        if not os.path.exists(cf_yaml):
            self.gui_error(
                "Configuration Error", f"The path you've specified for codeforces settings ({cf_yaml}) does not exist."
            )
            return

        with open(cf_yaml, "r") as f:
            data = parse_yaml(f)

        set_user_info(data.get("cf_username"), data.get("cf_api_key"), data.get("cf_api_secret"))
        if self.ui and self.ui.config_button:
            self.ui.config_button.handle_present = bool(data.get("cf_username"))
            self.ui.config_button.api_present = bool(data.get("cf_api_key") and data.get("cf_api_secret"))

    async def poll_for_submissions(self):
        logger.debug("Polling Codeforces for new submissions...")
        try:
            async for submission in new_submissions():
                self.handle_submission(submission)
                await asyncio.sleep(0.05)
            await self.set_last_checked(get_last_checked_ts())
        except CFAPIError:
            self.gui_error(
                "Configuration error",
                "Please press the icon in the top-right to specify your codeforces handle "
                "[and api token, if you want automatic submission size detection]",
            )

    def handle_submission(self, submission):
        name = submission["problem"]["name"]
        verdict = submission["verdict"]
        logger.debug(f"Checking submission for {name} with status {verdict}")
        if verdict != "OK":
            # For now, nothing to do.
            return
        problem = submission["problem"]
        contestId = problem["contestId"]
        index = problem["index"]
        problem_index = self.codeforces_game.get_problem_index(contestId, index)
        logger.debug(f"Submission matches problem index {problem_index}")
        if problem_index == -1:
            # Not in this archipelago slot.
            return

        error = self.codeforces_game.validate_within_constraints(problem_index, submission)
        if not error:
            self.codeforces_game.problem_solved(problem_index)
        else:
            self.ui.add_notif_anim(f"Your submission failed: {error}", duration=2)

    def on_return_intro(self):
        pass

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            self.on_return_intro()
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect(game=self.game)

    def handle_connection_loss(self, msg: str) -> None:
        self.on_return_intro()
        super().handle_connection_loss(msg)

    async def connect(self, address: str | None = None) -> None:
        self.ui.switch_to_regular_tab()
        await super().connect(address)

    async def submission_loop(self) -> None:
        try:
            while not self.exit_event.is_set():
                if self.connection_status != ConnectionStatus.GAME_RUNNING:
                    await asyncio.sleep(0.1)
                    continue
                if not self.codeforces_game:
                    await asyncio.sleep(0.1)
                    continue
                # Don't lag immediately.
                self.collect_cf_info()
                self.ui.set_refreshing(True)
                await asyncio.sleep(0.5)
                await self.poll_for_submissions()
                self.ui.set_refreshing(False)
                await asyncio.sleep(9.5)

        except Exception as e:
            import traceback

            logger.exception(traceback.format_exc())
            raise e

    async def codeforces_loop(self) -> None:
        try:
            while not self.exit_event.is_set():
                if self.connection_status != ConnectionStatus.GAME_RUNNING:
                    if self.connection_status == ConnectionStatus.SCOUTS_NOT_SENT:
                        await self.send_msgs([{"cmd": "LocationScouts", "locations": self.server_locations}])
                        self.connection_status = ConnectionStatus.SCOUTS_SENT

                    await asyncio.sleep(0.1)
                    continue

                if not self.codeforces_game:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    self.handle_game_events()

                    rerender = False

                    if self.queue_clear:
                        self.queue_clear = False
                        await self.clear_check()

                    while self.queued_locations:
                        location = self.queued_locations.pop(0)
                        self.location_checked_side_effects(location)
                        self.locations_checked.add(location)
                        rerender = True
                        await self.check_locations({location})

                    while self.queued_solves:
                        solve = self.queued_solves.pop(0)
                        rerender = True
                        await self.solve_problem(solve)

                    new_items = self.items_received[self.highest_processed_item_index :]
                    for item in new_items:
                        self.highest_processed_item_index += 1
                        self.codeforces_game.receive_item(item.item, item.location, item.player)
                        rerender = True

                    for new_remotely_cleared_location in self.checked_locations - self.locations_checked:
                        self.locations_checked.add(new_remotely_cleared_location)
                        self.codeforces_game.force_clear_location(new_remotely_cleared_location)
                        rerender = True

                    if rerender:
                        self.render()

                    if self.codeforces_game.has_won and not self.finished_game:
                        await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
                        self.finished_game = True
                except Exception as e:
                    logger.exception(e)

                await asyncio.sleep(0.1)
        except Exception as e:
            import traceback

            logger.exception(traceback.format_exc())
            raise e

    def on_package(self, cmd: str, args: dict[str, Any]) -> None:
        if cmd == "ConnectionRefused":
            self.on_return_intro()

        if cmd == "Connected":
            if self.connection_status == ConnectionStatus.GAME_RUNNING:
                # In a connection loss -> auto reconnect scenario, we can seamlessly keep going
                return

            self.last_connected_slot = self.slot

            self.connection_status = ConnectionStatus.NOT_CONNECTED  # for safety, it will get set again later

            self.slot_data = args["slot_data"]
            logger.debug(f"Received slot data: {self.slot_data}")
            self.progressive_keys = self.slot_data["progressive_keys"]
            self.memory_upgrades = self.slot_data["memory_upgrades"]
            self.time_limit_upgrades = self.slot_data["time_limit_upgrades"]
            self.goal_solves = self.slot_data["goal_solves"]
            self.problem_data = self.slot_data["problems"]

            self.codeforces_game = Game(
                self.progressive_keys,
                self.memory_upgrades,
                self.time_limit_upgrades,
                self.goal_solves,
                self.problem_data,
            )
            self.codeforces_game.context = self
            self.highest_processed_item_index = 0
            self.set_notify(
                *(self.solved_key(i) for i in range(1, len(self.problem_data) + 1)), self.last_checked_key()
            )
            self.render()

            self.connection_status = ConnectionStatus.SCOUTS_NOT_SENT
        if cmd == "LocationInfo":
            # This is telling you what type of network item is appearing within each location slot.
            # remote_item_graphic_overrides = {
            #     Location(location): Item(network_item.item)
            #     for location, network_item in self.locations_info.items()
            #     if self.slot_info[network_item.player].game == self.game
            # }

            assert self.codeforces_game is not None
            # self.codeforces_game.gameboard.fill_remote_location_content(remote_item_graphic_overrides)
            self.render()
            self.ui.game_view.bind_keyboard()

            self.connection_status = ConnectionStatus.GAME_RUNNING
            self.ui.game_started()
        if cmd == "PrintJSON" and args["type"] == "ItemSend":
            text = self.kivy_parser(args["data"])
            self.ui.add_notif_anim(text)

    async def disconnect(self, *args: Any, **kwargs: Any) -> None:
        self.finished_game = False
        self.locations_checked = set()
        self.connection_status = ConnectionStatus.NOT_CONNECTED
        self.ui.unbuild()
        await super().disconnect(*args, **kwargs)

    def render(self) -> None:
        if self.codeforces_game is None:
            raise RuntimeError("Tried to render before self.codeforces_game was initialized.")

        self.ui.render(self.codeforces_game)

    def location_checked_side_effects(self, location: int) -> None:
        network_item = self.locations_info[location]

        # A network item has been released. What shall we do with the location/item?

        # item_quality = get_quality_for_network_item(network_item)
        # self.play_jingle(ITEM_JINGLES[item_quality])

    def handle_game_events(self) -> None:
        if self.codeforces_game is None:
            return

        while self.codeforces_game.queued_events:
            event = self.codeforces_game.queued_events.pop(0)

            if isinstance(event, LocationClearedEvent):
                self.queued_locations.append(event.location_id)
                continue

            if isinstance(event, ProblemSolveEvent):
                self.queued_solves.append(event.index)
                continue

            if isinstance(event, VictoryEvent):
                # self.play_jingle(VICTORY_JINGLE)
                continue

            if isinstance(event, ConfettiFired):
                self.ui.add_confetti((event.x, event.y), 15)
                continue

    def make_gui(self) -> "type[kvui.GameManager]":
        self.load_kv()
        return CodeforcesManager

    def load_kv(self) -> None:
        import pkgutil

        from kivy.lang import Builder

        data = pkgutil.get_data(__name__, "codeforces_client.kv")
        if data is None:
            raise RuntimeError("codeforces_client.kv could not be loaded.")

        Builder.load_string(data.decode())


async def main(args: Namespace) -> None:
    if not gui_enabled:
        raise RuntimeError("Codeforces cannot be played without gui.")

    ctx = CodeforcesContext(args.connect, args.password)
    ctx.auth = args.name
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")

    ctx.run_gui()
    ctx.run_cli()

    ctx.client_loop = asyncio.create_task(ctx.codeforces_loop(), name="Client Loop")

    ctx.submission_loop = asyncio.create_task(ctx.submission_loop(), name="Submission Loop")

    await ctx.exit_event.wait()
    await ctx.shutdown()


def launch(*args: str) -> None:
    from .launch import launch_codeforces_client

    launch_codeforces_client(*args)


if __name__ == "__main__":
    launch(*sys.argv[1:])
