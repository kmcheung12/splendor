import torch
import torch.nn as nn
import torch.nn.functional as F

OBS_SIZE = 345
TOTAL_ACTIONS = 108


class AlphaNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(OBS_SIZE, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(256, TOTAL_ACTIONS)
        self.value_head = nn.Linear(256, 1)

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
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path: str) -> "AlphaNet":
        net = cls()
        net.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        net.eval()
        return net
