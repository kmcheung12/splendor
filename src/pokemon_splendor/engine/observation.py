# src/pokemon_splendor/engine/observation.py
from collections import Counter
import numpy as np
from pokemon_splendor.models import Game, PokeballType, Tier, GamePhase
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, get_evolvable_cards, can_afford
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
    MAX_OWNED_CARDS,
)

# Normalization constants — upper bounds for each feature type
MAX_TOKENS_PER_TYPE      = 10.0  # token supply per type (board or player hand)
MAX_COST_PER_TYPE        = 7.0   # max single-type cost on any card (e.g. Alakazam)
MAX_BONUS_PER_CARD       = 2.0   # max bonuses of one type on a single card
MAX_EVOLVE_COST_PER_TYPE = 4.0   # max single-type evolve cost on any card
MAX_POINT_PER_CARD       = 5.0   # max VP on a single card
MAX_OWNED_BONUS_PER_TYPE = 10.0  # practical ceiling for accumulated same-type discounts
WINNING_THRESHOLD        = 18.0  # points at which the game can end
MAX_RESERVED_CARDS       = 3     # maximum reserved cards per player

# v1 layout (345-dim): used by old trained models
_DEPRECATED_OBS_SIZE = 345

# v2 layout:
#   global tokens:    6
#   board slots:     14 × 19  = 266  (cost/6, bonus/6, evolve/6, point/1; tier dropped)
#   players:          4 × 52  = 208  (tokens/6, owned_bonus/6, points/1,
#                                     3 reserved slots × 13 = presence/1 + cost/6 + bonus_type/6)
#   turn indicator:   4
#   phase:            3
OBS_SIZE = 6 + 14 * 19 + 4 * 52 + 4 + 3  # = 487

_POKE_TYPES = list(PokeballType)


def compute_observation(game: Game, player_name: str) -> np.ndarray:
    obs = np.zeros(OBS_SIZE, dtype=np.float32)
    offset = 0

    # Global token supply
    for i, ptype in enumerate(_POKE_TYPES):
        obs[offset + i] = game.tokens.get(ptype, 0) / MAX_TOKENS_PER_TYPE
    offset += 6

    # Board slots (14 total: 4+4+4+1+1)
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for slot in all_slots:
        if slot:
            cost_counter = Counter(t.name for t in slot.cost)
            for i, pt in enumerate(_POKE_TYPES):
                obs[offset + i]      = cost_counter.get(pt, 0) / MAX_COST_PER_TYPE
                obs[offset + 6 + i]  = sum(1 for b in slot.bonus  if b.name == pt) / MAX_BONUS_PER_CARD
                obs[offset + 12 + i] = sum(1 for b in slot.evolve if b.name == pt) / MAX_EVOLVE_COST_PER_TYPE
            obs[offset + 18] = slot.point / MAX_POINT_PER_CARD
        offset += 19

    # Player states — self-relative: requesting player always in slot 0,
    # then other present players in turn order, then None-padded to 4 slots.
    present = [p.name for p in game.players]  # ordered as the game sees them
    self_pos = present.index(player_name)
    ordered = present[self_pos:] + present[:self_pos]  # rotate so self is first
    slots = ordered + [None] * (4 - len(ordered))       # pad absent slots with None

    player_map = {p.name: p for p in game.players}

    for slot_name in slots:
        if slot_name is not None:
            p = player_map[slot_name]

            # Tokens held
            tc = Counter(t.name for t in p.tokens)
            for j, pt in enumerate(_POKE_TYPES):
                obs[offset + j] = tc.get(pt, 0) / MAX_TOKENS_PER_TYPE
            offset += 6

            # Total discount bonuses from owned cards (engine state)
            bonus_counter: Counter = Counter()
            for card in p.cards:
                for b in card.bonus:
                    bonus_counter[b.name] += 1
            for j, pt in enumerate(_POKE_TYPES):
                obs[offset + j] = bonus_counter.get(pt, 0) / MAX_OWNED_BONUS_PER_TYPE
            offset += 6

            # Victory points
            obs[offset] = p.points / WINNING_THRESHOLD
            offset += 1

            # Reserved card slots (3 slots × 13 features)
            for slot_idx in range(MAX_RESERVED_CARDS):
                if slot_idx < len(p.reserved_cards):
                    rc = p.reserved_cards[slot_idx]
                    obs[offset] = 1.0  # presence
                    cost_counter = Counter(t.name for t in rc.cost)
                    for j, pt in enumerate(_POKE_TYPES):
                        obs[offset + 1 + j] = cost_counter.get(pt, 0) / MAX_COST_PER_TYPE
                    # Reserved cards always have exactly 1 bonus; one-hot over 6 types
                    for j, pt in enumerate(_POKE_TYPES):
                        obs[offset + 7 + j] = 1.0 if (rc.bonus and rc.bonus[0].name == pt) else 0.0
                offset += 13
        else:
            offset += 52

    # Turn indicator — self-relative to match player slot ordering above
    for slot_name in slots:
        obs[offset] = 1.0 if slot_name == game.turn.name else 0.0
        offset += 1

    # Game phase
    for i, ph in enumerate(GamePhase):
        obs[offset + i] = 1.0 if game.phase == ph else 0.0

    return obs


def compute_mask(game: Game, player_name: str) -> np.ndarray:
    mask = np.zeros(TOTAL_ACTIONS, dtype=bool)
    player = next(p for p in game.players if p.name == player_name)

    if game.phase == GamePhase.DISCARD:
        tc = Counter(t.name for t in player.tokens)
        for ptype, idx in DISCARD_ACTION.items():
            if tc.get(ptype, 0) > 0:
                mask[idx] = True
        return mask

    if game.phase == GamePhase.EVOLVE:
        mask[EVOLVE_PASS] = True
        evolvable = get_evolvable_cards(game, player)
        for card, _ in evolvable:
            idx = player.cards.index(card)
            if idx < MAX_OWNED_CARDS:
                mask[EVOLVE_START + idx] = True
        return mask

    available_types = {pt for pt in NORMAL_TYPES if game.tokens.get(pt, 0) > 0}
    for i, combo in enumerate(TAKE_DIFF_COMBOS):
        if all(pt in available_types for pt in combo):
            mask[TAKE_DIFF_START + i] = True

    for pt in NORMAL_TYPES:
        if game.tokens.get(pt, 0) >= 4:
            mask[TAKE_SAME_ACTION[pt]] = True

    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    player_bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)

    for slot_idx, pokemon in enumerate(all_slots):
        if pokemon is None:
            continue
        if can_afford(pokemon, player_bonuses, ptokens):
            mask[CATCH_BOARD_START + slot_idx] = True

    for i, pokemon in enumerate(player.reserved_cards):
        if can_afford(pokemon, player_bonuses, ptokens):
            mask[CATCH_RESERVED_START + i] = True

    if len(player.reserved_cards) < 3:
        reservable_slots = [i for i, p in enumerate(all_slots[:12]) if p is not None]
        for slot_idx in reservable_slots:
            if game.tokens.get(PokeballType.Master, 0) > 0:
                mask[RESERVE_MASTER_START + slot_idx] = True
            mask[RESERVE_NO_MASTER_START + slot_idx] = True

    if not mask.any():
        tc = Counter(t.name for t in player.tokens)
        for ptype, idx in DISCARD_ACTION.items():
            if tc.get(ptype, 0) > 0:
                mask[idx] = True
        if not mask.any():
            mask[EVOLVE_PASS] = True

    return mask


def get_obs_fn(model):
    """Return the compute_observation function matching the model's expected input size."""
    size = model.observation_space.shape[0]
    if size == _DEPRECATED_OBS_SIZE:
        from pokemon_splendor.engine.deprecated_observation import compute_observation as _old
        return _old
    return compute_observation
