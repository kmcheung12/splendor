from pathlib import Path
from scripts.article_export.models import BatchResult


def load_narratives(yaml_path: Path) -> dict[str, str]:
    import yaml
    data = yaml.safe_load(yaml_path.read_text())
    return {k: v.strip() for k, v in (data or {}).items()}


def apply_narratives(batches: list[BatchResult], narrs: dict[str, str]) -> None:
    for b in batches:
        if b.id in narrs:
            b.narrative = narrs[b.id]
