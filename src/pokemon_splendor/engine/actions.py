from itertools import combinations
from pokemon_splendor.models import PokeballType, Tier

NORMAL_TYPES = [
    PokeballType.Red,
    PokeballType.Yellow,
    PokeballType.Blue,
    PokeballType.Pink,
    PokeballType.Black,
]

# Precompute all take-different combos (size 1, 2, 3)
TAKE_DIFF_COMBOS: list[tuple[PokeballType, ...]] = [
    combo
    for size in range(1, 4)
    for combo in combinations(NORMAL_TYPES, size)
]
assert len(TAKE_DIFF_COMBOS) == 25

# Action index ranges
TAKE_DIFF_START = 0          # 0–24  (25 actions)
TAKE_SAME_START = 25         # 25–29 (5 actions)
CATCH_BOARD_START = 30       # 30–43 (14 actions)
CATCH_RESERVED_START = 44    # 44–46 (3 actions)
RESERVE_MASTER_START = 47    # 47–58 (12 actions)
RESERVE_NO_MASTER_START = 59 # 59–70 (12 actions)
DISCARD_START = 71           # 71–76 (6 actions, one per PokeballType)
EVOLVE_START = 77            # 77–106 (30 slots)
EVOLVE_PASS = 107            # pass evolution

TOTAL_ACTIONS = 108
MAX_OWNED_CARDS = 30  # upper bound for evolve action slots

# Board slot layout for CATCH_BOARD and RESERVE actions
# Slots 0–3: common, 4–7: uncommon, 8–11: rare, 12: epic, 13: legendary
BOARD_SLOT_TIERS = (
    [Tier.Common] * 4
    + [Tier.Uncommon] * 4
    + [Tier.Rare] * 4
    + [Tier.Epic]
    + [Tier.Legendary]
)

RESERVABLE_TIERS = {Tier.Common, Tier.Uncommon, Tier.Rare}

# Maps PokeballType to its DISCARD action index
DISCARD_ACTION = {ptype: DISCARD_START + i for i, ptype in enumerate(PokeballType)}
# Maps PokeballType to its TAKE_SAME action index
TAKE_SAME_ACTION = {ptype: TAKE_SAME_START + i for i, ptype in enumerate(NORMAL_TYPES)}
