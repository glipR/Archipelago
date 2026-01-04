from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, ClassVar
from math import ceil

import settings
from worlds.AutoWorld import World

from . import items, locations, regions, rules, web_world
from . import options as codeforces_options
from .api import generate_problems, Problem


class CodeforcesSettings(settings.Group):
    class CodeforcesInfo(settings.OptionalUserFilePath):
        pass

    codeforces_info: CodeforcesInfo = CodeforcesInfo("codeforces.yaml")


class CodeforcesWorld(World):
    """
    Codeforces is an online judge serving 1000s of competitive programming problems.

    Checks are few! Most of the location requirements are within your brain :)
    """

    game = "Codeforces"

    web = web_world.CodeforcesWebWorld()

    options_dataclass = codeforces_options.CodeforcesOptions
    options: codeforces_options.CodeforcesOptions

    # Populate host.yaml with codeforce settings path
    settings_key = "codeforces_options"
    settings: ClassVar[CodeforcesSettings] = CodeforcesSettings()

    location_name_to_id = locations.LOCATION_NAME_TO_ID
    item_name_to_id = items.ITEM_NAME_TO_ID

    origin_region_name = "Menu"

    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
        self.slot_problems = {}
        self.slot_mapping = {}

    def get_problems(self) -> list[Problem]:
        if not hasattr(self, "problems"):
            self.problems = generate_problems(self)
        return self.problems

    def get_problem_to_key_mapping(self) -> dict[int, int]:
        if not hasattr(self, "problem_to_key_mapping"):
            problems = self.get_problems()
            generated_keys = self.options.number_of_keys.value
            if generated_keys > len(problems):
                raise ValueError(
                    "Failed to generate problem to key mapping. "
                    "Please ensure that number of keys is at most problem count - 1."
                )
            prob_tuple_with_rating = [(p.rating, p.id) for p in problems]
            self.random.shuffle(prob_tuple_with_rating)
            if self.options.progressive_keys:
                prob_tuple_with_rating.sort()

            # saved_problems will be manually distributed instead.
            saved_problems = ceil((100 - self.options.bank_size_variance) / 100 * (len(problems) - generated_keys))
            remaining_problems = len(problems) - generated_keys - saved_problems

            # Now, assume that every key opens at least 1 problem, and find the breakpoints between key boundaries.
            breakpoints = [
                b
                + i
                + i * (saved_problems // generated_keys)
                + min(i + 1, saved_problems % generated_keys)  # Final problem for key i.
                for i, b in enumerate(
                    sorted([self.random.randint(0, remaining_problems) for _ in range(generated_keys - 1)])
                )
            ]
            mapping = {}
            cur_index = 0
            for i in range(len(problems)):
                while cur_index < len(breakpoints) and breakpoints[cur_index] < i:
                    cur_index += 1
                mapping[problems[i].id] = cur_index + 1
            self.problem_to_key_mapping = mapping
        return self.problem_to_key_mapping

    def create_regions(self) -> None:
        regions.create_and_connect_regions(self)
        locations.create_all_locations(self)

    def set_rules(self) -> None:
        rules.set_all_rules(self)

    def create_items(self) -> None:
        items.create_all_items(self)

    def create_item(self, name: str) -> items.CodeforcesItem:
        return items.create_item_with_correct_classification(self, name)

    def get_filler_item_name(self) -> str:
        return items.get_random_filler_item_name(self)

    def fill_slot_data(self) -> Mapping[str, Any]:
        problems = self.get_problems()
        mapping = self.get_problem_to_key_mapping()
        obj_dict = self.options.as_dict(
            "memory_upgrades",
            "time_limit_upgrades",
            "hint_chance",
            "trap_chance",
            "number_of_problems",
            "number_of_keys",
            "progressive_keys",
            "rating_floor",
            "rating_ceiling",
            "rating_source",
            "tag_preference_mapping",
            "goal_solves",
        )
        obj_dict["problems"] = [{k: v for k, v in asdict(p).items()} for p in problems]
        for i, prob in enumerate(obj_dict["problems"]):
            prob["id"] = problems[i].id
            prob["url"] = problems[i].url
            prob["bank_mapping"] = mapping[problems[i].id]
        return obj_dict
