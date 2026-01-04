from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Location

from . import items
from . import regions

if TYPE_CHECKING:
    from .world import CodeforcesWorld

LOCATION_NAME_TO_ID = {}
# Location Bank 1 - 500: Possible problem locations
for problem_index in range(100):
    LOCATION_NAME_TO_ID[f"Problem {problem_index} Full Solve"] = problem_index * 5 + 1
    LOCATION_NAME_TO_ID[f"Problem {problem_index} Pretest Pass"] = problem_index * 5 + 2


ID_TO_LOCATION_NAMES = {v: k for k, v in LOCATION_NAME_TO_ID.items()}


class CodeforcesLocation(Location):
    game = "Codeforces"


def get_location_names_with_ids(location_names: list[str]) -> dict[str, int | None]:
    return {location_name: LOCATION_NAME_TO_ID[location_name] for location_name in location_names}


def create_all_locations(world: CodeforcesWorld) -> None:
    create_regular_locations(world)
    create_events(world)


def create_regular_locations(world: CodeforcesWorld) -> None:
    bank_regions = regions.bank_regions(world)

    problems = world.get_problems()
    region_mapping = world.get_problem_to_key_mapping()

    for problem_index, problem in enumerate(problems, start=1):
        r = region_mapping[problem.id]
        bank_regions[r - 1].add_locations(
            get_location_names_with_ids([f"Problem {problem_index} Full Solve"]), CodeforcesLocation
        )


def create_events(world: CodeforcesWorld) -> None:
    bank_regions = regions.bank_regions(world)
    problems = world.get_problems()
    region_mapping = world.get_problem_to_key_mapping()

    for problem_index, problem in enumerate(problems, start=1):
        r = region_mapping[problem.id]
        loc_name = f"Problem {problem_index} Full Solve Event"
        bank_regions[r - 1].add_event(
            loc_name, "Problem Solve Key", location_type=CodeforcesLocation, item_type=items.CodeforcesItem
        )
