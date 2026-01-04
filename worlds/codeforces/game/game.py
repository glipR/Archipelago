from collections import Counter
from enum import Enum
from random import Random

from typing import Any, TYPE_CHECKING

from .events import Event, LocationClearedEvent, ConfettiFired, ProblemSolveEvent
from .items import RemotelyReceivedItem, ITEM_NAME_TO_ID
from ..locations import LOCATION_NAME_TO_ID

if TYPE_CHECKING:
    from ..client.game_manager import CodeforcesManager
    from ..client.codeforces_client import CodeforcesContext


class ProblemStatus(Enum):
    HIDDEN = 1
    AVAILABLE = 2
    FULL_SOLVED = 3
    CLEARED = 4
    CLEARED_HIDDEN = 5

class Game:
    random: Random

    queued_events: list[Event]

    remotely_received_items: set[tuple[int, int, int]]

    problem_status: list[ProblemStatus]

    has_won: bool

    context: "CodeforcesContext"

    def __init__(
        self,
        progressive_keys: bool,
        memory_upgrades: list[int | str],
        time_limit_upgrades: list[float],
        goal_solves: int,
        problem_data: list[dict[str, Any]]
    ) -> None:
        self.inventory = Counter()
        self.queued_events = []
        self.remotely_received_items = set()
        self.progressive_keys = progressive_keys
        self.memory_upgrades = memory_upgrades
        self.time_limit_upgrades = time_limit_upgrades
        self.goal_solves = goal_solves
        self.problem_data = problem_data
        self.problem_status = [ProblemStatus.HIDDEN] * len(problem_data)
        self.has_won = False

    def receive_item(self, remote_item_id: int, remote_location_id: int, remote_location_player: int) -> None:
        remotely_received_item = RemotelyReceivedItem(remote_item_id, remote_location_id, remote_location_player)
        if remotely_received_item in self.remotely_received_items:
            return
        self.remotely_received_items.add(remotely_received_item)

        self.inventory[remote_item_id] += 1

        self.hydrate_problem_status()

    def hydrate_problem_status(self):
        for i in range(len(self.problem_data)):
            bank = self.problem_data[i]["bank_mapping"]
            if self.progressive_keys:
                available = self.inventory[ITEM_NAME_TO_ID["Bank Key"]] >= bank
            else:
                available = self.inventory[ITEM_NAME_TO_ID[f"Bank Key {bank}"]] > 0
            location_track = LOCATION_NAME_TO_ID[f"Problem {i+1} Full Solve"]
            checked = location_track in self.context.locations_checked
            solved = self.context.stored_data.get(self.context.solved_key(i+1), False)
            if not available:
                if checked:
                    self.problem_status[i] = ProblemStatus.CLEARED_HIDDEN
                else:
                    self.problem_status[i] = ProblemStatus.HIDDEN
            elif checked and not solved:
                self.problem_status[i] = ProblemStatus.CLEARED
            elif not checked:
                self.problem_status[i] = ProblemStatus.AVAILABLE
            elif solved:
                self.problem_status[i] = ProblemStatus.FULL_SOLVED
        self.check_goal_state()

    @property
    def current_memory_limit(self):
        return self.memory_upgrades[min(
            len(self.memory_upgrades)-1,
            self.inventory[ITEM_NAME_TO_ID["Memory Upgrade"]]
        )]

    @property
    def current_time_limit(self):
        return self.time_limit_upgrades[min(
            len(self.time_limit_upgrades)-1,
            self.inventory[ITEM_NAME_TO_ID["Time Limit Upgrade"]]
        )]

    def render(self, manager: "CodeforcesManager"):
        self.hydrate_problem_status()
        manager.set_problem_status(self.problem_status, self.problem_data)
        manager.set_memory_limit(self.current_memory_limit)
        manager.set_time_limit(self.current_time_limit)

    def get_problem_index(self, contestId: str, index: str):
        for i, prob in enumerate(self.problem_data, start=1):
            if prob["contest_id"] == contestId and prob["problem_index"] == index:
                return i
        return -1

    def validate_within_constraints(self, idx: int, submission):
        """
        Determines whether a solution to a problem was within the bounds
        specified by current upgrade state.
        """
        # Checking memory constraints
        submission_bytes = len(submission["sourceCode"].encode("utf-8"))
        if self.current_memory_limit != "inf" and submission_bytes > self.current_memory_limit:
            return f"Your submission is too large ({submission_bytes} Bytes)"

        # Checking time constraints
        time_limit = self.problem_data[idx-1]["time_limit"]
        seconds_ratio = submission["timeConsumedMillis"] / 1000 / time_limit
        if seconds_ratio > self.current_time_limit:
            return f"Your submission took too long ({seconds_ratio * 100:.1f}% of {time_limit} seconds)"


    def problem_solved(self, idx: int):
        problem_solve = ProblemSolveEvent(idx)
        full_solve = LocationClearedEvent(LOCATION_NAME_TO_ID[f"Problem {idx} Full Solve"])
        self.queued_events.append(full_solve)
        self.queued_events.append(ConfettiFired(0.5, 0.5))
        self.queued_events.append(problem_solve)


    def check_goal_state(self):
        count_solved = 0
        for i in range(len(self.problem_data)):
            solved = self.context.stored_data.get(self.context.solved_key(i+1), False)
            count_solved += bool(solved)
        if len(self.problem_data) > 0 and count_solved * 100 > len(self.problem_data) * self.goal_solves:
            self.has_won = True

    def force_clear_location(self, idx: int):
        self.hydrate_problem_status()
