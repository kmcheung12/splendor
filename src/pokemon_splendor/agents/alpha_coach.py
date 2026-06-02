from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import random
import torch
import torch.nn.functional as F
from pokemon_splendor.models import Game


def compute_outcomes(game: Game) -> dict[str, float]:
    winner = game.winner
    winner_score = winner.points
    winner_cards = len([c for c in winner.cards if not c.evolved])
    outcomes = {}
    for player in game.players:
        active_cards = len([c for c in player.cards if not c.evolved])
        card_delta = (active_cards - winner_cards) * 0.001
        outcome = player.points / winner_score + card_delta
        outcomes[player.name] = max(0.0, min(1.0, outcome))
    return outcomes
