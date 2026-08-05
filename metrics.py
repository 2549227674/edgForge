#!/usr/bin/env python3
"""Compute EdgeForge's two Terminus parser-format metrics from ATIF traces.

The metrics deliberately use parser feedback recorded in each agent step's
``observation.results[].content``.  They never inspect arbitrary terminal
output, because task commands may legitimately emit the word ``ERROR``.

* ``parser_hard_error_rate`` is the fraction of agent responses rejected by
  the Terminus JSON parser.
* ``parser_soft_warning_rate`` is the fraction of all agent responses that
  were accepted but had text before and/or after the JSON object.

The two rates are distinct columns.  A rejected response can also contain the
extra-text warning, but it is not counted as a soft-warning response because
the parser did not accept it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "edgeforge-parser-metrics/v1"
HARD_ERROR_PREFIX = "Previous response had parsing errors:"
SOFT_WARNING_PREFIX = "Previous response had warnings:"
BEFORE_JSON_WARNING = "Extra text detected before JSON object"
AFTER_JSON_WARNING = "Extra text detected after JSON object"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        action="append",
        type=Path,
        help="Trajectory JSON file or directory to scan; repeat for multiple inputs.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write JSON to this path. Defaults to stdout.",
    )
    return parser.parse_args()


def trajectory_paths(inputs: Iterable[Path]) -> list[Path]:
    """Return unique, sorted trajectory files from files and directories."""

    paths: set[Path] = set()
    for input_path in inputs:
        if input_path.is_file():
            paths.add(input_path)
        elif input_path.is_dir():
            paths.update(input_path.rglob("trajectory.json"))
        else:
            raise FileNotFoundError(f"Input does not exist: {input_path}")
    return sorted(paths, key=lambda path: str(path))


def relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def observation_contents(step: Mapping[str, Any]) -> list[str]:
    observation = step.get("observation")
    if not isinstance(observation, Mapping):
        return []
    results = observation.get("results")
    if not isinstance(results, list):
        return []

    contents: list[str] = []
    for result in results:
        if isinstance(result, Mapping) and isinstance(result.get("content"), str):
            contents.append(result["content"])
    return contents


def parser_feedback(contents: Iterable[str]) -> list[str]:
    """Keep only Terminus parser feedback, excluding terminal-output text."""

    return [
        content
        for content in contents
        if content.startswith(HARD_ERROR_PREFIX)
        or content.startswith(SOFT_WARNING_PREFIX)
    ]


def classify_step(step: Mapping[str, Any]) -> dict[str, int] | None:
    """Classify one agent response, or return None for non-agent steps."""

    if step.get("source") != "agent":
        return None

    feedback = parser_feedback(observation_contents(step))
    hard = any(content.startswith(HARD_ERROR_PREFIX) for content in feedback)
    before = any(BEFORE_JSON_WARNING in content for content in feedback)
    after = any(AFTER_JSON_WARNING in content for content in feedback)
    has_extra_text_warning = before or after

    # A hard rejection may carry warnings too.  The soft metric explicitly
    # measures accepted-but-untidy replies, so keep the columns disjoint.
    soft = has_extra_text_warning and not hard
    return {
        "agent_response_attempts": 1,
        "hard_error_responses": int(hard),
        "soft_warning_accepted_responses": int(soft),
        "hard_error_responses_with_extra_text_warning": int(
            hard and has_extra_text_warning
        ),
        "extra_text_warning_responses": int(has_extra_text_warning),
        "before_json_marker_responses": int(before),
        "after_json_marker_responses": int(after),
    }


def empty_counts() -> dict[str, int]:
    return {
        "agent_response_attempts": 0,
        "hard_error_responses": 0,
        "soft_warning_accepted_responses": 0,
        "hard_error_responses_with_extra_text_warning": 0,
        "extra_text_warning_responses": 0,
        "before_json_marker_responses": 0,
        "after_json_marker_responses": 0,
    }


def add_counts(target: dict[str, int], increment: Mapping[str, int]) -> None:
    for key in target:
        target[key] += increment[key]


def load_trajectory(path: Path) -> Mapping[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ValueError(f"Trajectory root must be an object: {path}")
    steps = parsed.get("steps")
    if not isinstance(steps, list):
        raise ValueError(f"Trajectory has no list-valued steps field: {path}")
    return parsed


def summarize(paths: Iterable[Path], input_paths: Iterable[Path]) -> dict[str, Any]:
    totals = empty_counts()
    trajectories: list[dict[str, Any]] = []

    for path in paths:
        trajectory = load_trajectory(path)
        counts = empty_counts()
        for step in trajectory["steps"]:
            if not isinstance(step, Mapping):
                raise ValueError(f"Step is not an object in {path}")
            step_counts = classify_step(step)
            if step_counts is not None:
                add_counts(counts, step_counts)
        add_counts(totals, counts)
        trajectories.append(
            {
                "path": relative_path(path),
                "session_id": trajectory.get("session_id"),
                **counts,
            }
        )

    denominator = totals["agent_response_attempts"]
    if denominator == 0:
        raise ValueError("No agent response attempts found in input trajectories")

    return {
        "schema_version": SCHEMA_VERSION,
        "input_roots": [relative_path(path) for path in input_paths],
        "trajectory_file_count": len(trajectories),
        "denominator": {
            "name": "agent_response_attempts",
            "value": denominator,
            "definition": "Every ATIF step with source == 'agent'.",
        },
        "metrics": {
            "parser_hard_error_rate": totals["hard_error_responses"] / denominator,
            "parser_soft_warning_rate": totals["soft_warning_accepted_responses"]
            / denominator,
            "hard_error_definition": (
                "The parser feedback begins with "
                "'Previous response had parsing errors:'."
            ),
            "soft_warning_definition": (
                "The parser accepted the response and its feedback reports text "
                "before and/or after the JSON object."
            ),
            "rate_relationship": (
                "Both rates use all agent response attempts as their denominator "
                "and must not be merged."
            ),
        },
        "counts": totals,
        "trajectories": trajectories,
    }


def write_json(payload: Mapping[str, Any], output: Path | None) -> None:
    encoded = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(encoded)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        paths = trajectory_paths(args.input)
        if not paths:
            raise ValueError("No trajectory.json files found")
        payload = summarize(paths, args.input)
        write_json(payload, args.output)
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"metrics.py: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
