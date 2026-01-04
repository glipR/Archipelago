from dataclasses import dataclass

from Options import Choice, OptionGroup, PerGameCommonOptions, Range, Toggle, DefaultOnToggle, OptionDict, OptionList

# For further reading on options, you can also read the Options API Document:
# https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/options%20api.md


class MemoryUpgrades(OptionList):
    """
    What progressive memory upgrades to include as limitations on submission.
    Enabling this limits your ability to solve problems by requiring that your submission be under a certain file size.

    This list specifies the stages that this upgrade will progress through in gameplay.

    The first value will be the default ability of the player, so a list of size N memory limits
    will spawn N-1 items in game.

    Specify memory limits in bytes. Use "inf" to represent an unbounded memory limit.

    By default, the logic will assume that if problems are ordered by rating,
    you can only complete a problem once you've collected a proportionate amount of memory upgrades,
    from halfway through on difficulty.

    So for example, if you had 8 problems, and 4 values in this list, then:
    * 5 problems would require no upgrades in logic
    * 1 problems would require 1 upgrade in logic
    * 1 problems would require 2 upgrades in logic
    * 1 problems would require 3 upgrades in logic

    To support generation, some of these upgrades may be given to you immediately.
    """

    display_name = "Memory Upgrades"
    default = [500, 1000, 2000, "inf"]


class TimeLimitUpgrades(OptionList):
    """
    What progressive time limit upgrades to include as limitations on submission.
    Enabling this limits your ability to solve problems by requiring that your submission
    run in under a factor of the expected run-time.
    So if the original time limit for a problem was 3 seconds,
    but your current time limit requirement was 0.5, you need to solve the problem with a max of 1.5 seconds run-time.

    This list specifies the stages that this upgrade will progress through in gameplay.

    The first value will be the default ability of the player, so a list of size N time limits
    will spawn N-1 items in game.

    Specify time limits in multipliers of the original time limit.

    By default, the logic will assume that if problems are ordered by rating,
    you can only complete a problem once you've collected a proportionate amount of time limit upgrades,
    from halfway through on difficulty.

    So for example, if you had 8 problems, and 4 values in this list, then:
    * 5 problems would require no upgrades in logic
    * 1 problems would require 1 upgrade in logic
    * 1 problems would require 2 upgrades in logic
    * 1 problems would require 3 upgrades in logic

    To support generation, some of these upgrades may be given to you immediately.
    """

    display_name = "Time Limit Upgrades"
    default = [1]


class HintChance(Range):
    """
    Percentage chance that any given filler item is replaced with a Hint.

    This chance is global to all filler items
    """

    display_name = "Hint Chance"

    range_start = 0
    range_end = 100

    default = 50


class TrapChance(Range):
    """
    Percentage chance that any given filler item is replaced with a Trap!
    This percentage is applied after the hint chance,
    so this just determines the percentage that replaces true filler items, not hints.

    For example Hint Chance = 40, Trap Chance = 50 would actually result in
    40% Hint Items, 20% Filler items, and 20% Trap Items.
    """

    display_name = "Trap Chance"

    range_start = 0
    range_end = 100
    default = 0


class NumberOfProblems(Range):
    """
    The number of problems to generate.
    """

    display_name = "Number of Problems"

    range_start = 1
    range_end = 100
    default = "random-range-6-10"


class NumberOfKeys(Range):
    """
    The number of progression keys to generate that will unlock collections of problems.
    Note that you get 1 key for free at the start of the game.

    Recommended this is set to around about 40% of the number of problems, to clear up space for additional items.

    Set to 1 to have access to all problems at once.
    """

    display_name = "Number of Keys"
    range_start = 1
    range_end = 100
    default = "random-range-3-4"


class BankSizeVariance(Range):
    """
    The variance in the size of problem banks.

    0 variance: Problems are evenly distributed to banks
    100 variance: Problems are assigned completely randomly.
        Only guarantee is that every bank has at least a single problem.
    """

    display_name = "Bank Size Variance"
    range_start = 0
    range_end = 100
    default = 50


class ProgressiveKeys(Toggle):
    """
    Makes keys progressive, and problems ordered by rating
    (The first key you get will definitely unlock easier problems than the next key you get, and so on.)
    """

    display_name = "Progressive Keys"


class RatingFloor(Range):
    """
    The floor under which no problems with less than this rating will be considered for selection.
    """

    display_name = "Rating Floor"

    range_start = 0
    range_end = 5000
    default = 800


class RatingCeiling(Range):
    """
    The ceiling above which no problems with more than this rating will be considered for selection.
    """

    display_name = "Rating Ceiling"

    range_start = 0
    range_end = 5000
    default = 2000


class RatingSource(Choice):
    """
    Where to source ratings from.
    """

    display_name = "Rating Source"

    option_codeforces = 0
    option_clist = 1

    default = option_codeforces


class TagPreferenceMapping(OptionDict):
    """
    If you want particular tags to appear with higher or lower likely-hood,
    then you can use this setting to influence this.

    By default, all tags have a value of 1.

    Set a tag value to 0 to ban it from selection as a problem.

    Example:
      # Problems containing math are more likely to be selected
      math: 3.5
      # Problems containing geometry are banned
      geometry: -1
    """

    display_name = "Tag Preference Mapping"


class GoalSolves(Range):
    """
    The percentage of problems full solved to reach the goal for this game.
    """

    display_name = "Goal Solves"

    range_start = 1
    range_end = 100
    default = 80


@dataclass
class CodeforcesOptions(PerGameCommonOptions):
    memory_upgrades: MemoryUpgrades
    time_limit_upgrades: TimeLimitUpgrades
    hint_chance: HintChance
    trap_chance: TrapChance
    number_of_problems: NumberOfProblems
    number_of_keys: NumberOfKeys
    progressive_keys: ProgressiveKeys
    rating_floor: RatingFloor
    rating_ceiling: RatingCeiling
    rating_source: RatingSource
    tag_preference_mapping: TagPreferenceMapping
    goal_solves: GoalSolves
    bank_size_variance: BankSizeVariance


option_groups = [
    OptionGroup(
        "Problem Selection Options",
        [NumberOfProblems, RatingFloor, RatingCeiling, RatingSource, TagPreferenceMapping, BankSizeVariance],
    ),
    OptionGroup(
        "Gameplay Options",
        [GoalSolves, NumberOfKeys, ProgressiveKeys, MemoryUpgrades, TimeLimitUpgrades, HintChance, TrapChance],
    ),
]
