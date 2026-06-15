import torch
import torch.nn as nn
import torch.nn.functional as F

from pokemon_splendor.engine.observation import OBS_SIZE
TOTAL_ACTIONS = 108


class AlphaNet(nn.Module):
    def __init__(self, hidden_size: int = 256, num_layers: int = 3):
        super().__init__()
        self._hidden_size = hidden_size
        self._num_layers = num_layers
        layers = []
        in_size = OBS_SIZE
        for _ in range(num_layers):
            layers += [nn.Linear(in_size, hidden_size), nn.ReLU()]
            in_size = hidden_size
        self.shared = nn.Sequential(*layers)
        self.policy_head = nn.Linear(hidden_size, TOTAL_ACTIONS)
        self.value_head = nn.Linear(hidden_size, 1)

    def forward(self, obs: torch.Tensor, mask: torch.Tensor):
        x = self.shared(obs)
        logits = self.policy_head(x)
        logits = logits.masked_fill(~mask, float("-inf"))

        # Check for all-masked input (would produce NaN in softmax)
        if mask.dim() == 1:
            # Single-sample case
            if mask.sum() == 0:
                raise ValueError("Cannot compute policy: all actions are masked")
        else:
            # Batched case
            if not mask.any(dim=-1).all():
                raise ValueError("Cannot compute policy: batch contains samples with all actions masked")

        policy = F.softmax(logits, dim=-1)
        value = torch.sigmoid(self.value_head(x)).squeeze(-1)
        return policy, value

    def save(self, path: str) -> None:
        torch.save({
            "state_dict": self.state_dict(),
            "hidden_size": self._hidden_size,
            "num_layers": self._num_layers,
        }, path)

    @classmethod
    def load(cls, path: str) -> "AlphaNet":
        data = torch.load(path, map_location="cpu", weights_only=True)
        if isinstance(data, dict) and "state_dict" in data:
            net = cls(hidden_size=data["hidden_size"], num_layers=data["num_layers"])
            net.load_state_dict(data["state_dict"])
        else:
            # Legacy: raw state_dict — infer architecture from weight shapes
            hidden_size = data["shared.0.weight"].shape[0]
            layer_indices = {
                int(k.split(".")[1])
                for k in data
                if k.startswith("shared.") and k.endswith(".weight")
            }
            num_layers = len(layer_indices)
            net = cls(hidden_size=hidden_size, num_layers=num_layers)
            net.load_state_dict(data)
        net.eval()
        return net
