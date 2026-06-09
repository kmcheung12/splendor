import tempfile
import os
import torch
import numpy as np
import pytest
from pokemon_splendor.agents.alpha_net import AlphaNet, OBS_SIZE, TOTAL_ACTIONS


def test_default_constructor_is_256x3():
    net = AlphaNet()
    # shared has 3 Linear layers → indices 0, 2, 4 in Sequential (interleaved with ReLU)
    linear_layers = [m for m in net.shared if isinstance(m, torch.nn.Linear)]
    assert len(linear_layers) == 3
    assert linear_layers[0].out_features == 256


def test_custom_hidden_size():
    net = AlphaNet(hidden_size=512, num_layers=2)
    linear_layers = [m for m in net.shared if isinstance(m, torch.nn.Linear)]
    assert len(linear_layers) == 2
    assert all(layer.out_features == 512 for layer in linear_layers)


def test_forward_shape_default():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)
    assert value.shape == ()
    assert abs(policy.sum().item() - 1.0) < 1e-5
    assert 0.0 <= value.item() <= 1.0


def test_forward_shape_custom():
    net = AlphaNet(hidden_size=512, num_layers=4)
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)
    assert value.shape == ()
    assert abs(policy.sum().item() - 1.0) < 1e-5
    assert 0.0 <= value.item() <= 1.0


def test_save_embeds_architecture():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "net.pt")
        net = AlphaNet(hidden_size=512, num_layers=3)
        net.save(path)
        data = torch.load(path, map_location="cpu", weights_only=True)
        assert isinstance(data, dict)
        assert data["hidden_size"] == 512
        assert data["num_layers"] == 3
        assert "state_dict" in data


def test_load_new_format_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "net.pt")
        net = AlphaNet(hidden_size=512, num_layers=3)
        obs = torch.randn(OBS_SIZE)
        mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
        policy_orig, value_orig = net(obs, mask)
        net.save(path)
        net2 = AlphaNet.load(path)
        policy_loaded, value_loaded = net2(obs, mask)
        assert torch.allclose(policy_orig, policy_loaded)
        assert torch.allclose(value_orig, value_loaded)


def test_load_legacy_format():
    """Simulate a pre-migration .pt file: raw state_dict, no metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy.pt")
        net = AlphaNet(hidden_size=256, num_layers=2)
        # Save legacy format (raw state dict, no metadata)
        torch.save(net.state_dict(), path)
        # Load should infer architecture and succeed
        net2 = AlphaNet.load(path)
        linear_layers = [m for m in net2.shared if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) == 2
        assert linear_layers[0].out_features == 256


def test_load_legacy_format_output_matches():
    """Legacy load produces identical output to original network."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy.pt")
        net = AlphaNet(hidden_size=256, num_layers=2)
        obs = torch.randn(OBS_SIZE)
        mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
        policy_orig, value_orig = net(obs, mask)
        torch.save(net.state_dict(), path)
        net2 = AlphaNet.load(path)
        policy_loaded, value_loaded = net2(obs, mask)
        assert torch.allclose(policy_orig, policy_loaded)
        assert torch.allclose(value_orig, value_loaded)


def test_load_legacy_format_256x3():
    """Legacy 256x3 network (current default before migration) loads correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy_3layer.pt")
        net = AlphaNet(hidden_size=256, num_layers=3)
        torch.save(net.state_dict(), path)
        net2 = AlphaNet.load(path)
        linear_layers = [m for m in net2.shared if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) == 3
