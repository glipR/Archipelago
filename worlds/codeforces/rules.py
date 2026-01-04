from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from worlds.generic.Rules import set_rule
from .items import Upgrades

if TYPE_CHECKING:
    from .world import CodeforcesWorld

logger = logging.getLogger("Codeforces")


def set_all_rules(world: CodeforcesWorld) -> None:
    # Entrance rules are handled by the location definition, since this rule is rather simple (Banks -> Keys)
    # set_all_entrance_rules(world)
    set_all_location_rules(world)
    set_completion_condition(world)


def create_requirements_rule(world: CodeforcesWorld, reqs: list[tuple[str, int]]):
    return lambda state: all(state.has(v[0], world.player, v[1]) for v in reqs)


def set_all_location_rules(world: CodeforcesWorld) -> None:
    problems = [(idx, prob) for idx, prob in enumerate(world.get_problems(), start=1)]
    problems.sort(key=lambda v: v[1].rating)

    for idx, prob in problems:
        # solve_pct is 0 for the first 50%, then ramps from 0 to 1 for the second half.
        solve_pct = ((idx - 1) / len(problems) - 0.5) * 2
        mem_upgrades = len(world.options.memory_upgrades.value) - 1
        expected_mem_upgrades = max(0, math.floor(solve_pct * mem_upgrades))
        time_upgrades = len(world.options.time_limit_upgrades.value) - 1
        expected_time_upgrades = max(0, math.floor(solve_pct * time_upgrades))

        logger.info(
            f"Location Problem {idx} Full Solve requires "
            f"{expected_mem_upgrades} Memory Upgrades and "
            f"{expected_time_upgrades} Time Limit Upgrades."
        )

        loc = world.get_location(f"Problem {idx} Full Solve")
        event = world.get_location(f"Problem {idx} Full Solve Event")
        reqs = []
        if expected_mem_upgrades > 0:
            reqs.append((Upgrades.memory.value, expected_mem_upgrades))
        if expected_time_upgrades > 0:
            reqs.append((Upgrades.time_limit.value, expected_time_upgrades))
        set_rule(loc, create_requirements_rule(world, reqs))
        set_rule(event, create_requirements_rule(world, reqs))


def set_completion_condition(world: CodeforcesWorld) -> None:
    n_problems = len(world.get_problems())
    expected_solves = math.floor(n_problems / 100 * world.options.goal_solves.value)
    world.multiworld.completion_condition[world.player] = lambda state: state.has(
        "Problem Solve Key", world.player, expected_solves
    )
