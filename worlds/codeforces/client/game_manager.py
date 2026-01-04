from __future__ import annotations


from typing import TYPE_CHECKING, Any

from kvui import GameManager, MDNavigationItemBase
from kivy.animation import Animation
from kivy.uix.layout import Layout

from CommonClient import logger

from ..game.game import Game, ProblemStatus
from .custom_views import (
    CodeforcesGameView,
    CodeforcesProblemHeader,
    CodeforcesUpgradeList,
    CodeforcesProblemBox,
    CodeforcesProblemTopBoxes,
    CodeforcesConfigButton,
)

if TYPE_CHECKING:
    from .codeforces_client import CodeforcesContext


def make_notif_animation(message, duration=0.5):
    anim = Animation(notif_pos=1, t="in_out_back", duration=duration)

    def on_start(animation, widget):
        widget.notif_text = message

    anim.bind(on_start=on_start)
    anim += Animation(duration=1.5) + Animation(notif_pos=0, t="in_out_back", duration=duration)
    return anim


class CodeforcesManager(GameManager):
    base_title = "Codeforces for AP version"
    ctx: CodeforcesContext

    game_view: CodeforcesGameView
    game_view_tab: MDNavigationItemBase

    codeforces_header: CodeforcesProblemHeader
    codeforces_upgrades: CodeforcesUpgradeList
    codeforces_problem_box: CodeforcesProblemBox

    config_button: CodeforcesConfigButton

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.queued_anims = []
        self.playing_anim = None

    def add_confetti(self, position: tuple[float, float], amount: int) -> None:
        # Do nothing
        pass

    def switch_to_tab(self, desired_tab: MDNavigationItemBase) -> None:
        if self.screens.current_tab == desired_tab:
            return
        self.screens.current_tab.active = False
        self.screens.switch_screens(desired_tab)
        desired_tab.active = True

    def switch_to_game_tab(self) -> None:
        self.switch_to_tab(self.game_view_tab)

    def switch_to_regular_tab(self) -> None:
        self.switch_to_tab(self.tabs.children[-1])

    def game_started(self) -> None:
        self.switch_to_game_tab()

    def render(self, game: Game) -> None:
        game.render(self)
        if self.codeforces_problem_box.game_reference is None:
            self.codeforces_problem_box.game_reference = game

    def build(self) -> Layout:
        try:
            container = super().build()

            self.game_view = CodeforcesGameView()

            self.game_view_tab = self.add_client_tab("Codeforces", self.game_view)

            float_container = self.game_view.ids["float_container"]
            game_container = self.game_view.ids["game_container"]
            self.codeforces_header = CodeforcesProblemHeader()
            self.codeforces_upgrades = CodeforcesUpgradeList()
            self.codeforces_problem_box = CodeforcesProblemBox()
            game_container.add_widget(self.codeforces_header)
            game_container.add_widget(self.codeforces_upgrades)
            game_container.add_widget(self.codeforces_problem_box)

            game_container.bind(size=self.codeforces_problem_box.check_resize)

            self.top_boxes = CodeforcesProblemTopBoxes()
            self.codeforces_header.add_widget(self.top_boxes)
            self.config_button = CodeforcesConfigButton()
            self.codeforces_header.add_widget(self.config_button)
            self.config_button.context_reference = self.ctx

            self.ctx.collect_cf_info()

        except Exception as e:
            import traceback

            logger.exception(traceback.format_exc())
            raise e
        return container

    def unbuild(self):
        self.codeforces_problem_box.game_reference = None
        self.switch_to_regular_tab()

    def set_problem_status(self, statuses: list[ProblemStatus], problem_data: list[dict[str, Any]]):
        self.top_boxes.set_problem_info(problem_data, statuses)
        self.codeforces_problem_box.set_problem_info(problem_data, statuses)

    def set_memory_limit(self, mem_limit: int | str):
        self.codeforces_upgrades.memory_val = str(mem_limit)

    def set_time_limit(self, time_limit: float):
        self.codeforces_upgrades.time_mult = time_limit

    def check_for_notif(self):
        if self.playing_anim is not None:
            return
        elif len(self.queued_anims) > 0:
            self.play_notif_anim(*self.queued_anims.pop(0))

    def add_notif_anim(self, message: str, duration=0.5):
        self.queued_anims.append((message, duration))
        self.check_for_notif()

    def play_notif_anim(self, message: str, duration: float):
        anim = make_notif_animation(message, duration)

        def on_complete(animation, widget):
            self.playing_anim = None
            self.check_for_notif()

        anim.bind(on_complete=on_complete)
        self.playing_anim = anim
        self.playing_anim.start(self.game_view)

    def set_refreshing(self, refreshing: bool):
        self.config_button.refreshing = refreshing
