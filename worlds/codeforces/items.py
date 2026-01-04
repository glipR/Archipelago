from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification

if TYPE_CHECKING:
    from .world import CodeforcesWorld

# Item Bank 1 - 100: Possible problem locations
# Item Bank 1001-1010: Upgrades
class Upgrades(Enum):
    memory = "Memory Upgrade"
    time_limit = "Time Limit Upgrade"
    hint = "Problem Hint"
# Item Bank 1101-1200: Filler
class Fillers(Enum):
    words = "Words of Encouragement"
# Item Bank 1201-1300: Trap
class Traps(Enum):
    reading = "Reading Time"

ITEM_NAME_TO_ID = {
    "Bank Key": 500,
    Upgrades.memory.value: 1001,
    Upgrades.time_limit.value: 1002,
    Upgrades.hint.value: 1003,

    Fillers.words.value: 1101,

    Traps.reading.value: 1201,
}
DEFAULT_ITEM_CLASSIFICATIONS = {
    "Bank Key": ItemClassification.progression,
    Upgrades.memory.value: ItemClassification.progression_deprioritized,
    Upgrades.time_limit.value: ItemClassification.progression_deprioritized,
    Upgrades.hint.value: ItemClassification.useful,

    Fillers.words.value: ItemClassification.filler,

    Traps.reading.value: ItemClassification.trap,
}
for problem_index in range(1, 101):
    name = f"Bank Key {problem_index}"
    ITEM_NAME_TO_ID[name] = problem_index
    DEFAULT_ITEM_CLASSIFICATIONS[name] = ItemClassification.progression


ID_TO_ITEM_NAME = {
    v: k
    for k, v in ITEM_NAME_TO_ID.items()
}


class CodeforcesItem(Item):
    game = "Codeforces"


def get_random_filler_item_name(world: CodeforcesWorld) -> str:
    if world.random.randint(0, 99) < world.options.hint_chance:
        return Upgrades.hint.value
    if world.random.randint(0, 99) < world.options.trap_chance:
        return Traps.reading.value
    return Fillers.words.value


def create_item_with_correct_classification(world: CodeforcesWorld, name: str) -> CodeforcesItem:
    classification = DEFAULT_ITEM_CLASSIFICATIONS[name]

    return CodeforcesItem(name, classification, ITEM_NAME_TO_ID[name], world.player)


def create_all_items(world: CodeforcesWorld) -> None:
    problems = world.get_problems()
    mapping = world.get_problem_to_key_mapping()

    number_of_unfilled_locations = len(world.multiworld.get_unfilled_locations(world.player))

    itempool: list[Item] = [
        world.create_item("Bank Key" if world.options.progressive_keys else f"Bank Key {v}")
        for v in set(mapping.values())
        if v != 1 # We ignore the first Bank key, since this will be given to the player on start.
    ]

    memory_upgrades = [
        world.create_item(Upgrades.memory.value)
        for _ in range(len(world.options.memory_upgrades.value) - 1)
    ]
    time_upgrades = [
        world.create_item(Upgrades.time_limit.value)
        for _ in range(len(world.options.time_limit_upgrades.value) - 1)
    ]

    memory_initial = 0
    time_initial = 0
    expected_items = len(itempool) + len(memory_upgrades) + len(time_upgrades)

    if expected_items > number_of_unfilled_locations:
        # We need to give some memory/time upgrades to the player from the get-go.
        iters = 0
        while (
            memory_initial < len(world.options.memory_upgrades.value) - 1 or
            time_initial < len(world.options.time_limit_upgrades.value) - 1
        ) and expected_items > number_of_unfilled_locations and iters < 100:
            if world.random.randint(0, 1) == 0 and memory_initial < len(world.options.memory_upgrades.value) - 1:
                memory_initial += 1
                expected_items -= 1
            elif time_initial < len(world.options.time_limit_upgrades.value) - 1:
                time_initial += 1
                expected_items -= 1
            iters += 1
        if expected_items > number_of_unfilled_locations:
            raise ValueError("Failed to allocate Time and Memory upgrades during generation.")

    itempool.extend(memory_upgrades[memory_initial:])
    itempool.extend(time_upgrades[time_initial:])

    number_of_items = len(itempool)

    needed_number_of_filler_items = number_of_unfilled_locations - number_of_items

    itempool += [world.create_filler() for _ in range(needed_number_of_filler_items)]

    world.multiworld.itempool += itempool

    # The first bank of problems is always available
    world.push_precollected(world.create_item("Bank Key" if world.options.progressive_keys else "Bank Key 1"))
    # Additionally, we may have needed to give the player some memory and time upgrades
    for _ in range(memory_initial):
        world.push_precollected(world.create_item(Upgrades.memory.value))
    for _ in range(time_initial):
        world.push_precollected(world.create_item(Upgrades.time_limit.value))
