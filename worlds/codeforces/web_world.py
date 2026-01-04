from BaseClasses import Tutorial
from worlds.AutoWorld import WebWorld

from .options import option_groups


class CodeforcesWebWorld(WebWorld):
    game = "Codeforces"

    theme = "partyTime"

    setup_en = Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up Codeforces for MultiWorld.",
        "English",
        "setup_en.md",
        "setup/en",
        ["glipR"],
    )

    tutorials = [setup_en]

    option_groups = option_groups
