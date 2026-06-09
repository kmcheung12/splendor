# Configurable Network Size Design

## Goal

Make hidden layer width and depth configurable for both the PPO (`MlpPolicy`) and `AlphaNet` networks, while preserving full backward compatibility with existing `.zip` and `.pt` checkpoints.

## Architecture

### AlphaNet (`src/pokemon_splendor/agents/alpha_net.py`)

**Constructor** gains two parameters:
- `hidden_size: int = 256` — width of each hidden layer
- `num_layers: int = 3` — number of hidden layers in the shared trunk

The shared trunk becomes a loop:
```python
layers = []
in_size = OBS_SIZE
for _ in range(num_layers):
    layers += [nn.Linear(in_size, hidden_size), nn.ReLU()]
    in_size = hidden_size
self.shared = nn.Sequential(*layers)
self.policy_head = nn.Linear(hidden_size, TOTAL_ACTIONS)
self.value_head = nn.Linear(hidden_size, 1)
```

**Save format** changes to embed architecture:
```python
def save(self, path: str) -> None:
    torch.save({
        "state_dict": self.state_dict(),
        "hidden_size": self._hidden_size,
        "num_layers": self._num_layers,
    }, path)
```

**Load** handles both legacy (raw state dict) and new (dict with metadata) formats:
```python
@classmethod
def load(cls, path: str) -> "AlphaNet":
    data = torch.load(path, map_location="cpu", weights_only=True)
    if isinstance(data, dict) and "state_dict" in data:
        net = cls(hidden_size=data["hidden_size"], num_layers=data["num_layers"])
        net.load_state_dict(data["state_dict"])
    else:
        # Legacy: raw state_dict, infer architecture from weight shapes
        hidden_size = data["shared.0.weight"].shape[0]
        layer_indices = {int(k.split(".")[1]) for k in data if k.startswith("shared.") and k.endswith(".weight")}
        num_layers = len(layer_indices)
        net = cls(hidden_size=hidden_size, num_layers=num_layers)
        net.load_state_dict(data)
    net.eval()
    return net
```

**Defaults: 256×3** — safe after running the migration script which rewrites all existing 256×2 checkpoints to embed their architecture. Legacy `.pt` files loaded before migration are still handled by shape inference.

### PPO / RL (`src/pokemon_splendor/__main__.py`)

`_run_train` builds `net_arch` dynamically from CLI flags:
```python
layers = [args.hidden_size] * args.hidden_layers
policy_kwargs = {"net_arch": dict(pi=layers, vf=layers)}
```

On `--resume`, SB3 reads `policy_kwargs` from the zip and raises a warning if the caller passes different `policy_kwargs` — so CLI flags are safely ignored when resuming. No special handling needed.

### New CLI flags

| Flag | Default | Applies to |
|------|---------|------------|
| `--hidden-size` | 256 | `--mode train` (PPO) |
| `--hidden-layers` | 3 | `--mode train` (PPO) |
| `--alpha-hidden-size` | 256 | `--mode alpha-train` |
| `--alpha-hidden-layers` | 3 | `--mode alpha-train` |

## Backward Compatibility

| Checkpoint type | Behaviour |
|----------------|-----------|
| Old `.zip` (128×2) | SB3 restores 128×2 from zip; `--hidden-size`/`--hidden-layers` ignored on `--resume` |
| Old `.zip` (any arch) | Same — architecture always read from zip |
| Old `.pt` before migration | `load()` infers architecture from weight shapes |
| Old `.pt` after migration | `load()` reads architecture from embedded metadata |
| New `.pt` (any arch) | `load()` reads architecture from embedded metadata |

## Migration Script

`scripts/migrate_alpha_checkpoints.py` — one-time script, run manually after alpha training completes:

```bash
uv run python scripts/migrate_alpha_checkpoints.py --dry-run  # preview
uv run python scripts/migrate_alpha_checkpoints.py            # apply
```

Infers `hidden_size` and `num_layers` from weight tensor shapes. Idempotent — skips already-migrated files.

## Files Changed

- Modify: `src/pokemon_splendor/agents/alpha_net.py` — constructor, save, load
- Modify: `src/pokemon_splendor/__main__.py` — 4 new CLI flags, dynamic `net_arch`
- Modify: `src/pokemon_splendor/agents/alpha_coach.py` — pass `hidden_size`/`num_layers` through to `AlphaNet()` construction and `_run_alpha_train`
- Create: `tests/test_network_compat.py` — backward compatibility tests

## Backward Compatibility Tests (`tests/test_network_compat.py`)

- **Legacy `.pt` loads correctly** — create a raw state dict (256×2), save with `torch.save(state_dict, path)`, load with `AlphaNet.load()`, verify output shape
- **New `.pt` round-trips** — `AlphaNet(hidden_size=512, num_layers=3)`, save, load, verify output identical
- **Shape mismatch raises** — save 256×2, attempt `cls(hidden_size=512)` + `load_state_dict`, verify error
- **Default constructor matches existing checkpoints** — `AlphaNet(hidden_size=256, num_layers=2)` produces same shapes as legacy checkpoints
- **Non-default architecture forward pass** — `AlphaNet(hidden_size=512, num_layers=4)` produces correct output shape `(TOTAL_ACTIONS,)` and scalar value
- **PPO net_arch built correctly** — `layers = [256] * 3` produces `dict(pi=[256,256,256], vf=[256,256,256])`
