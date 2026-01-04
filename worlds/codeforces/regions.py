from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Region, CollectionState

if TYPE_CHECKING:
    from .world import CodeforcesWorld


def create_and_connect_regions(world: CodeforcesWorld) -> None:
    create_all_regions(world)
    connect_regions(world)


def _bank_regions(world: CodeforcesWorld) -> list[Region]:
    key_regions = []
    for key_val in range(1, world.options.number_of_keys.value + 1):
        key_regions.append(Region(f"Problem Bank {key_val}", world.player, world.multiworld))
    return key_regions


def bank_regions(world: CodeforcesWorld) -> list[Region]:
    return [world.get_region(f"Problem Bank {key_val}") for key_val in range(1, world.options.number_of_keys.value + 1)]


def create_all_regions(world: CodeforcesWorld) -> None:
    menu = Region("Menu", world.player, world.multiworld)

    regions = [menu]
    regions.extend(_bank_regions(world))

    world.multiworld.regions += regions


def create_progressive_key_rule(world: CodeforcesWorld, index: int):
    def rule(state: CollectionState):
        return state.has("Bank Key", world.player, count=index)

    return rule


def create_key_rule(world: CodeforcesWorld, index: int):
    def rule(state: CollectionState):
        return state.has(f"Bank Key {index}", world.player)

    return rule


def connect_regions(world: CodeforcesWorld) -> None:
    menu = world.get_region("Menu")
    banks = bank_regions(world)

    for key_index, bank in enumerate(banks, start=1):
        if world.options.progressive_keys:
            rule = create_progressive_key_rule(world, key_index)
        else:
            rule = create_key_rule(world, key_index)

        menu.connect(bank, f"{menu.name} to {bank.name}", rule)
