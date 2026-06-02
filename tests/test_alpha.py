import torch
import numpy as np
import pytest
from pokemon_splendor.agents.alpha_net import AlphaNet

OBS_SIZE = 345
TOTAL_ACTIONS = 108


def test_alpha_net_policy_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)


def test_alpha_net_value_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert value.shape == ()


def test_alpha_net_policy_sums_to_one():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, _ = net(obs, mask)
    assert abs(policy.sum().item() - 1.0) < 1e-5


def test_alpha_net_policy_respects_mask():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.zeros(TOTAL_ACTIONS, dtype=torch.bool)
    mask[0] = True
    mask[1] = True
    policy, _ = net(obs, mask)
    assert policy[2:].sum().item() < 1e-6
    assert abs(policy[:2].sum().item() - 1.0) < 1e-5


def test_alpha_net_value_in_range():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    _, value = net(obs, mask)
    assert 0.0 <= value.item() <= 1.0


def test_alpha_net_batch_forward():
    net = AlphaNet()
    obs = torch.randn(4, OBS_SIZE)
    mask = torch.ones(4, TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (4, TOTAL_ACTIONS)
    assert value.shape == (4,)
