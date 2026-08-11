#!/usr/bin/env python3
"""Stream M1 records through the frozen M0 renderer contract.

The stats pass records untrimmed lengths.  The render pass applies the M1
deterministic trimming policy and writes compact Parquet shards suitable for
training without materializing the full corpus in memory.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[2]
HISTOGRAM_BOUNDS = (512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072)
_WORKER_TOKENIZER: Any = None
_WORKER_RENDERER: Any = None


def load_renderer() -> Any:
    path = ROOT / "scripts/m0/data/render_linec_samples.py"
    spec = importlib.util.spec_from_file_location("edgeforge_m0_renderer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import renderer from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iter_records(directory: Path) -> Iterator[tuple[str, int, dict[str, Any]]]:
    for path in sorted(directory.glob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    yield path.name, line_number, json.loads(line)


def init_worker(model: str, need_renderer: bool) -> None:
    global _WORKER_TOKENIZER, _WORKER_RENDERER
    _WORKER_TOKENIZER = AutoTokenizer.from_pretrained(model, local_files_only=True)
    _WORKER_RENDERER = load_renderer() if need_renderer else None


def render_text(tokenizer: Any, record: dict[str, Any]) -> str:
    return tokenizer.apply_chat_template(
        record["messages"],
        tools=record.get("tools") or None,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=True,
        preserve_thinking=True,
    )


def compact_render(tokenizer: Any, renderer: Any, record: dict[str, Any]) -> tuple[list[int], list[int]]:
    text = render_text(tokenizer, record)
    tagged_messages, marker_pairs = renderer.add_content_markers(record["messages"])
    marked = tokenizer.apply_chat_template(
        tagged_messages,
        tools=record.get("tools") or None,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=True,
        preserve_thinking=True,
    )
    # A tool-call-only assistant turn has no text field to mark.  The frozen
    # renderer still supervises its <|tool_call> span, so an empty marker set
    # is valid and must not be passed to re.compile("").
    if marker_pairs:
        stripped, content_ranges = renderer.remove_markers_and_ranges(marked, marker_pairs)
    else:
        stripped, content_ranges = marked, []
    if stripped != text:
        raise AssertionError("marker removal did not reproduce native rendered text")
    ranges = renderer.ranges_for_rendered_text(text, content_ranges)
    encoded = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    input_ids = [int(token_id) for token_id in encoded["input_ids"]]
    offsets = encoded["offset_mapping"]
    labels: list[int] = []
    range_index = 0
    for token_id, (start, end) in zip(input_ids, offsets, strict=True):
        while range_index < len(ranges) and ranges[range_index][1] <= start:
            range_index += 1
        supervised = (
            end > start
            and range_index < len(ranges)
            and start < ranges[range_index][1]
            and end > ranges[range_index][0]
        )
        labels.append(token_id if supervised else -100)
    return input_ids, labels


def trim_record(
    tokenizer: Any,
    renderer: Any,
    record: dict[str, Any],
    max_length: int,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    working = copy.deepcopy(record)
    input_ids, labels = compact_render(tokenizer, renderer, working)
    original_tokens = len(input_ids)
    deleted_messages = 0
    modes: list[str] = []

    while len(input_ids) > max_length:
        user_indices = [
            index for index, message in enumerate(working["messages"])
            if message.get("role") == "user"
        ]
        if len(user_indices) < 2:
            break
        cut_at = user_indices[-1]
        prefix = working["messages"][:cut_at]
        if not any(message.get("role") == "assistant" for message in prefix):
            break
        deleted_messages += len(working["messages"]) - len(prefix)
        working["messages"] = prefix
        input_ids, labels = compact_render(tokenizer, renderer, working)
        if "drop_tail_turns" not in modes:
            modes.append("drop_tail_turns")

    if len(input_ids) > max_length:
        input_ids = input_ids[:max_length]
        labels = labels[:max_length]
        modes.append("prefix_tokens")

    supervised_tokens = sum(label != -100 for label in labels)
    dropped = supervised_tokens == 0
    audit = {
        "uid": record["uid"],
        "original_tokens": original_tokens,
        "kept_tokens": len(input_ids),
        "supervised_tokens": supervised_tokens,
        "deleted_messages": deleted_messages,
        "trim_mode": "+".join(modes) if modes else "none",
        "drop_reason": "no_supervised_tokens_after_trim" if dropped else None,
    }
    if dropped:
        return None, audit
    return {
        "uid": record["uid"],
        "dataset": record["dataset"],
        "family": record.get("_family"),
        "task_type": record.get("_task_type"),
        "is_subagent": bool(record.get("is_subagent", False)),
        "input_ids": input_ids,
        "labels": labels,
        "original_tokens": original_tokens,
        "kept_tokens": len(input_ids),
        "deleted_messages": deleted_messages,
        "trim_mode": audit["trim_mode"],
    }, audit


def stat_one(tokenizer: Any, task: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    source_file, line_number, record = task
    try:
        text = render_text(tokenizer, record)
        token_count = len(tokenizer.encode(text, add_special_tokens=False))
    except Exception as error:
        return {
            "failure": {
                "source_file": source_file,
                "line_number": line_number,
                "uid": record.get("uid"),
                "error": f"{type(error).__name__}: {error}",
            }
        }
    return {
        "row": {
            "uid": record["uid"],
            "dataset": record["dataset"],
            "family": str(record.get("_family") or "unknown"),
            "task_type": str(record.get("_task_type") or "unknown"),
            "is_subagent": bool(record.get("is_subagent", False)),
            "token_count": token_count,
        }
    }


def stats_worker(task: tuple[str, int, dict[str, Any]]) -> dict[str, Any]:
    return stat_one(_WORKER_TOKENIZER, task)


def render_one_worker(task: tuple[str, int, dict[str, Any]], max_length: int) -> dict[str, Any]:
    source_file, line_number, record = task
    try:
        rendered, audit = trim_record(_WORKER_TOKENIZER, _WORKER_RENDERER, record, max_length)
    except Exception as error:
        return {
            "failure": {
                "source_file": source_file,
                "line_number": line_number,
                "uid": record.get("uid"),
                "error": f"{type(error).__name__}: {error}",
            }
        }
    return {"rendered": rendered, "audit": audit}


def render_worker(task_and_length: tuple[tuple[str, int, dict[str, Any]], int]) -> dict[str, Any]:
    task, max_length = task_and_length
    return render_one_worker(task, max_length)


def percentile(values: list[int], probability: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def histogram(values: list[int]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for value in values:
        lower = 0
        placed = False
        for bound in HISTOGRAM_BOUNDS:
            if value <= bound:
                counts[f"{lower + 1}-{bound}"] += 1
                placed = True
                break
            lower = bound
        if not placed:
            counts[f">{HISTOGRAM_BOUNDS[-1]}"] += 1
    return dict(counts)


def length_summary(values: list[int]) -> dict[str, Any]:
    return {
        "records": len(values),
        "tokens": sum(values),
        "min": min(values) if values else 0,
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values) if values else 0,
        "over_8192": sum(value > 8192 for value in values),
        "over_16384": sum(value > 16384 for value in values),
        "histogram": histogram(values),
    }


def run_stats(args: argparse.Namespace, tokenizer: Any) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lengths: list[int] = []
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    source_counts: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []
    metadata_path = args.output_dir / "lengths.jsonl.gz"
    started = time.perf_counter()
    pool = None
    try:
        if args.workers > 1:
            pool = mp.get_context("spawn").Pool(
                args.workers,
                initializer=init_worker,
                initargs=(str(args.model), False),
            )
            results = pool.imap(stats_worker, iter_records(args.records), chunksize=args.worker_chunksize)
        else:
            results = (stat_one(tokenizer, task) for task in iter_records(args.records))
        with gzip.open(metadata_path, "wt", encoding="utf-8") as output:
            for index, result in enumerate(results, 1):
                if "failure" in result:
                    failures.append(result["failure"])
                    continue
                row = result["row"]
                token_count = row["token_count"]
                family = row["family"]
                task_type = row["task_type"]
                output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                lengths.append(token_count)
                groups[(family, task_type)].append(token_count)
                source_counts[row["dataset"]] += 1
                if index % args.progress_every == 0:
                    elapsed = time.perf_counter() - started
                    print(f"stats rows={index} rendered={len(lengths)} failures={len(failures)} elapsed={elapsed:.1f}s", file=sys.stderr)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    report = {
        "mode": "stats",
        "renderer": "scripts/m0/data/render_linec_samples.py",
        "template_sha256": hashlib.sha256((args.model / "chat_template.jinja").read_bytes()).hexdigest(),
        "records_seen": len(lengths) + len(failures),
        "records_rendered": len(lengths),
        "render_failures": failures,
        "overall": length_summary(lengths),
        "by_family_task_type": {
            f"{family}|{task_type}": length_summary(values)
            for (family, task_type), values in sorted(groups.items())
        },
        "by_dataset_records": dict(sorted(source_counts.items())),
        "elapsed_seconds": time.perf_counter() - started,
        "lengths_file": metadata_path.name,
    }
    report_path = args.output_dir / "stats.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures and report["records_rendered"] == args.expected_records else 1


def run_render(args: argparse.Namespace, tokenizer: Any, renderer: Any) -> int:
    if not args.max_length or args.max_length <= 0:
        raise ValueError("--max-length must be positive in render mode")
    import pyarrow as pa
    import pyarrow.parquet as pq

    args.output_dir.mkdir(parents=True, exist_ok=True)
    schema = pa.schema(
        [
            ("uid", pa.string()),
            ("dataset", pa.string()),
            ("family", pa.string()),
            ("task_type", pa.string()),
            ("is_subagent", pa.bool_()),
            ("input_ids", pa.list_(pa.int32())),
            ("labels", pa.list_(pa.int32())),
            ("original_tokens", pa.int32()),
            ("kept_tokens", pa.int32()),
            ("deleted_messages", pa.int32()),
            ("trim_mode", pa.string()),
        ]
    )
    batch: list[dict[str, Any]] = []
    shard_paths: list[Path] = []
    failures: list[dict[str, Any]] = []
    trim_counts: Counter[str] = Counter()
    written = 0
    seen = 0
    total_kept_tokens = 0
    total_supervised_tokens = 0
    started = time.perf_counter()
    audit_path = args.output_dir / "trim_audit.jsonl.gz"

    def flush() -> None:
        nonlocal batch
        if not batch:
            return
        path = args.output_dir / f"train-{len(shard_paths):05d}.parquet"
        pq.write_table(pa.Table.from_pylist(batch, schema=schema), path, compression="zstd")
        shard_paths.append(path)
        batch = []

    pool = None
    try:
        if args.workers > 1:
            pool = mp.get_context("spawn").Pool(
                args.workers,
                initializer=init_worker,
                initargs=(str(args.model), True),
            )
            tasks = ((task, args.max_length) for task in iter_records(args.records))
            results = pool.imap(render_worker, tasks, chunksize=args.worker_chunksize)
        else:
            def single_results() -> Iterator[dict[str, Any]]:
                global _WORKER_TOKENIZER, _WORKER_RENDERER
                _WORKER_TOKENIZER = tokenizer
                _WORKER_RENDERER = renderer
                for task in iter_records(args.records):
                    yield render_one_worker(task, args.max_length)
            results = single_results()
        with gzip.open(audit_path, "wt", encoding="utf-8") as audit_output:
            for result in results:
                seen += 1
                if "failure" in result:
                    failures.append(result["failure"])
                    continue
                rendered = result["rendered"]
                audit = result["audit"]
                audit_output.write(json.dumps(audit, ensure_ascii=False, separators=(",", ":")) + "\n")
                trim_counts[audit["trim_mode"]] += 1
                if rendered is not None:
                    total_kept_tokens += rendered["kept_tokens"]
                    total_supervised_tokens += audit["supervised_tokens"]
                    batch.append(rendered)
                    written += 1
                    if len(batch) >= args.shard_rows:
                        flush()
                if seen % args.progress_every == 0:
                    elapsed = time.perf_counter() - started
                    print(f"render rows={seen} written={written} failures={len(failures)} elapsed={elapsed:.1f}s", file=sys.stderr)
            flush()
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    shards = []
    for path in shard_paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        shards.append({"file": path.name, "bytes": path.stat().st_size, "sha256": digest})
    report = {
        "mode": "render",
        "renderer": "scripts/m0/data/render_linec_samples.py",
        "max_length": args.max_length,
        "records_seen": seen,
        "records_written": written,
        "records_dropped": seen - written - len(failures),
        "render_failures": failures,
        "trim_counts": dict(sorted(trim_counts.items())),
        "kept_tokens": total_kept_tokens,
        "supervised_tokens": total_supervised_tokens,
        "elapsed_seconds": time.perf_counter() - started,
        "audit_file": audit_path.name,
        "shards": shards,
    }
    report_path = args.output_dir / "render_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures and seen == args.expected_records else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stats", "render"), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-length", type=int)
    parser.add_argument("--shard-rows", type=int, default=1000)
    parser.add_argument("--progress-every", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--worker-chunksize", type=int, default=8)
    parser.add_argument("--expected-records", type=int, default=154097)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    renderer = load_renderer()
    if args.mode == "stats":
        return run_stats(args, tokenizer)
    return run_render(args, tokenizer, renderer)


if __name__ == "__main__":
    raise SystemExit(main())
