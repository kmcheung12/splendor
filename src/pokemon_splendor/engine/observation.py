# src/pokemon_splendor/engine/observation.py
from collections import Counter
import numpy as np
from pokemon_splendor.models import Game, PokeballType, Tier, GamePhase
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, get_evolvable_cards
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
    MAX_OWNED_CARDS,
)

_OBS_SIZE = 6 + 14 * 20 + 4 * 13 + 4 + 3  # = 345


def compute_observation(game: Game, player_name: str) -> np.ndarray:
    obs = np.zeros(_OBS_SIZE, dtype=np.float32)
    offset = 0
    for i, ptype in enumerate(PokeballType):
        obs[offset + i] = game.tokens.get(ptype, 0) / 10.0
    offset += 6
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for slot in all_slots:
        if slot:
            obs[offset:offset+6] = [
                Counter(t.name for t in slot.cost).get(pt, 0) / 5.0
                for pt in PokeballType
            ]
            obs[offset+6:offset+12] = [
                sum(1 for b in slot.bonus if b.name == pt) / 3.0
                for pt in PokeballType
            ]
            obs[offset+12:offset+18] = [
                sum(1 for b in slot.evolve if b.name == pt) / 3.0
                for pt in PokeballType
            ]
            obs[offset+18] = slot.point / 15.0
            obs[offset+19] = list(Tier).index(slot.tier) / 4.0
        offset += 20
    player_map = {p.name: p for p in game.players}
    for i in range(4):
        a = f"player_{i}"
        if a in player_map:
            p = player_map[a]
            tc = Counter(t.name for t in p.tokens)
            for j, pt in enumerate(PokeballType):
                obs[offset + j] = tc.get(pt, 0) / 10.0
            offset += 6
            tier_counts = Counter(c.tier for c in p.cards if not c.evolved)
            for t in Tier:
                obs[offset] = tier_counts.get(t, 0) / 5.0
                offset += 1
            obs[offset] = p.points / 18.0
            obs[offset+1] = len(p.reserved_cards) / 3.0
            offset += 2
        else:
            offset += 13
    for i in range(4):
        obs[offset + i] = 1.0 if f"player_{i}" == game.turn.name else 0.0
    offset += 4
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
        effective = calculate_effective_cost(pokemon, player_bonuses)
        master_req = effective.get(PokeballType.Master, 0)
        if pokemon.tier in (Tier.Epic, Tier.Legendary):
            master_req = max(master_req, 1)
        master_have = ptokens.get(PokeballType.Master, 0)
        if master_have < master_req:
            catch_ok = False
        else:
            shortfall = sum(
                max(0, needed - ptokens.get(pt, 0))
                for pt, needed in effective.items()
                if pt != PokeballType.Master
            )
            catch_ok = (master_have - master_req) >= shortfall
        if catch_ok:
            mask[CATCH_BOARD_START + slot_idx] = True

    for i, pokemon in enumerate(player.reserved_cards):
        effective = calculate_effective_cost(pokemon, player_bonuses)
        master_req = effective.get(PokeballType.Master, 0)
        if pokemon.tier in (Tier.Epic, Tier.Legendary):
            master_req = max(master_req, 1)
        master_have = ptokens.get(PokeballType.Master, 0)
        if master_have >= master_req:
            shortfall = sum(
                max(0, needed - ptokens.get(pt, 0))
                for pt, needed in effective.items()
                if pt != PokeballType.Master
            )
            if (master_have - master_req) >= shortfall:
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
