import re
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, BenchmarkResult, TrainingMetrics
)

_BATCH_RE = re.compile(r"^=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ===$", re.M)
_OPP_RE = re.compile(r"--opponents (\S+)")
_EPISODES_RE = re.compile(r"--episodes (\d+)")
_SAVE_RE = re.compile(r"--save (\S+)")
_STAGE_RE = re.compile(r"Stage: (\d+)")
_METRIC_RE = re.compile(r"(\w+):\s*([\-\d\.]+)")
_PLAYERS_RE = re.compile(r"--players (\S+)")
_WIN_RATE_RE = re.compile(r"([\w\-/\.]+):\s*([\d\.]+)%")


def _block_iter(text: str):
    matches = list(_BATCH_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield text[start:end]


def _batch_id_from_save(save_path: str) -> str:
    name = Path(save_path).stem
    return name.split("-")[0]


def parse_training_log(path: Path) -> list[BatchResult]:
    text = path.read_text()
    out: list[BatchResult] = []
    for block in _block_iter(text):
        cmd_line = next(
            (ln for ln in block.splitlines() if ln.startswith("Command:")), None
        )
        if not cmd_line:
            continue
        save_match = _SAVE_RE.search(cmd_line)
        if not save_match:
            continue
        batch_id = _batch_id_from_save(save_match.group(1))
        stage_match = _STAGE_RE.search(block)
        stage = int(stage_match.group(1)) if stage_match else 0
        opp_match = _OPP_RE.search(cmd_line)
        opponents = opp_match.group(1).split(",") if opp_match else []
        eps_match = _EPISODES_RE.search(cmd_line)
        episodes = int(eps_match.group(1)) if eps_match else 0
        lr_match = re.search(r"--lr (\S+)", cmd_line)
        lr = float(lr_match.group(1)) if lr_match else 1e-4

        result_section = _section(block, "Result:")
        metrics = _parse_metrics(result_section)
        benchmarks = _parse_benchmarks(block)
        narrative = _parse_assessment(block)

        out.append(BatchResult(
            id=batch_id,
            stage=stage,
            opponents=opponents,
            episodes=episodes,
            lr=lr,
            result=metrics,
            benchmarks=benchmarks,
            narrative=narrative,
        ))
    return out


def _section(block: str, header: str) -> str:
    lines = block.splitlines()
    out: list[str] = []
    in_section = False
    for ln in lines:
        if ln.strip() == header.strip():
            in_section = True
            continue
        if in_section:
            if ln.startswith(("Benchmark", "Assessment", "Command", "Stage")):
                break
            out.append(ln)
    return "\n".join(out)


def _parse_metrics(section: str) -> TrainingMetrics:
    found = {k: float(v) for k, v in _METRIC_RE.findall(section)}
    return TrainingMetrics(
        total_timesteps=int(found.get("total_timesteps", 0)),
        explained_variance=found.get("explained_variance", 0.0),
        entropy_loss=found.get("entropy_loss", 0.0),
        value_loss=found.get("value_loss", 0.0),
        clip_fraction=found.get("clip_fraction", 0.0),
    )


def _parse_benchmarks(block: str) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("Benchmark:"):
            players_match = _PLAYERS_RE.search(ln)
            games_match = re.search(r"--games (\d+)", ln)
            if not (players_match and games_match):
                continue
            opp_strs = players_match.group(1).split(",")
            opponents = [Path(s).name for s in opp_strs]
            games = int(games_match.group(1))
            result_line = next(
                (lines[j] for j in range(i + 1, min(i + 5, len(lines)))
                 if "%" in lines[j]),
                "",
            )
            win_rates: list[float] = []
            for _name, pct in _WIN_RATE_RE.findall(result_line):
                win_rates.append(float(pct) / 100.0)
            if len(win_rates) == len(opponents):
                results.append(BenchmarkResult(
                    opponents=opponents,
                    win_rates=win_rates,
                    games=games,
                ))
    return results


def _parse_assessment(block: str) -> str:
    for ln in block.splitlines():
        if ln.startswith("Assessment:"):
            return ln[len("Assessment:"):].strip()
    return ""
