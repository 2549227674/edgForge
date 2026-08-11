#!/usr/bin/env python3
"""Train one frozen M1 QLoRA recipe to its 1/8-token race checkpoint."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import time
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pyarrow.parquet as pq
import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForImageTextToText,
    BitsAndBytesConfig,
    get_cosine_schedule_with_warmup,
)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def iter_rows(path: Path, batch_size: int = 16) -> Iterator[dict[str, Any]]:
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=batch_size):
        yield from batch.to_pylist()


def tensorize(row: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    input_ids = torch.tensor([row["input_ids"]], dtype=torch.long, device="cuda")
    labels = torch.tensor([row["labels"]], dtype=torch.long, device="cuda")
    return input_ids, labels, torch.ones_like(input_ids)


@torch.no_grad()
def evaluate(model: Any, path: Path, use_cache: bool) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    token_weighted_sum = 0.0
    supervised_tokens = 0
    input_tokens = 0
    started = time.perf_counter()
    for row in iter_rows(path):
        count = sum(label != -100 for label in row["labels"][1:])
        if not count:
            continue
        input_ids, labels, attention_mask = tensorize(row)
        output = model(
            input_ids=input_ids,
            labels=labels,
            attention_mask=attention_mask,
            use_cache=use_cache,
        )
        value = float(output.loss.detach().cpu())
        losses.append(value)
        token_weighted_sum += value * count
        supervised_tokens += count
        input_tokens += input_ids.numel()
        del output, input_ids, labels, attention_mask
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    sample_mean = statistics.fmean(losses)
    standard_error = statistics.stdev(losses) / math.sqrt(len(losses)) if len(losses) > 1 else 0.0
    return {
        "records": len(losses),
        "input_tokens": input_tokens,
        "supervised_tokens": supervised_tokens,
        "sample_mean_loss": sample_mean,
        "sample_loss_standard_error": standard_error,
        "token_weighted_loss": token_weighted_sum / supervised_tokens,
        "elapsed_seconds": elapsed,
    }


def save_checkpoint(
    model: Any,
    optimizer: torch.optim.Optimizer,
    scheduler: Any,
    output_dir: Path,
    state: dict[str, Any],
) -> None:
    adapter_dir = output_dir / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir, safe_serialization=True)
    torch.save(
        {
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "torch_rng_state": torch.get_rng_state(),
            "cuda_rng_state": torch.cuda.get_rng_state_all(),
            "state": state,
        },
        output_dir / "continuation_state.pt",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--holdout", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--race-steps", type=int, default=1024)
    parser.add_argument("--full-steps", type=int, default=8192)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--eval-every", type=int, default=64)
    parser.add_argument("--use-cache", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    seed_everything(args.seed)
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        args.model,
        local_files_only=True,
        dtype=torch.bfloat16,
        quantization_config=quantization,
        device_map={"": 0},
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=False)
    model = get_peft_model(
        model,
        LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            target_modules="all-linear",
            task_type="CAUSAL_LM",
        ),
    )
    model.config.use_cache = args.use_cache
    if hasattr(model.config, "text_config"):
        model.config.text_config.use_cache = args.use_cache
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=args.learning_rate)
    warmup_steps = round(args.full_steps * args.warmup_ratio)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, args.full_steps)

    log_path = args.output_dir / "train_log.jsonl"
    evaluations: list[dict[str, Any]] = []
    initial_eval = evaluate(model, args.holdout, args.use_cache)
    initial_eval["optimizer_step"] = 0
    evaluations.append(initial_eval)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"event": "validation", **initial_eval}, ensure_ascii=False) + "\n")
        log.flush()
        model.train()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        current_step = 0
        step_loss = 0.0
        seen_records = 0
        input_tokens = 0
        supervised_tokens = 0
        optimizer.zero_grad(set_to_none=True)

        def finish_step(step: int) -> None:
            nonlocal step_loss
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
            payload = {
                "event": "train_step",
                "optimizer_step": step + 1,
                "weighted_loss": step_loss,
                "learning_rate": scheduler.get_last_lr()[0],
                "seen_records": seen_records,
                "input_tokens": input_tokens,
                "elapsed_seconds": time.perf_counter() - started,
            }
            log.write(json.dumps(payload, ensure_ascii=False) + "\n")
            log.flush()
            step_loss = 0.0

        for row in iter_rows(args.plan):
            row_step = int(row["optimizer_step"])
            if row_step != current_step:
                if row_step != current_step + 1:
                    raise RuntimeError(f"non-contiguous optimizer step {current_step} -> {row_step}")
                finish_step(current_step)
                current_step = row_step
                if current_step % args.eval_every == 0:
                    result = evaluate(model, args.holdout, args.use_cache)
                    result["optimizer_step"] = current_step
                    evaluations.append(result)
                    log.write(json.dumps({"event": "validation", **result}, ensure_ascii=False) + "\n")
                    log.flush()
                    model.train()

            count = int(row["shifted_supervised_tokens"])
            seen_records += 1
            input_tokens += int(row["scheduled_tokens"])
            supervised_tokens += count
            if not count:
                continue
            group_count = int(row["optimizer_step_supervised_tokens"])
            input_ids, labels, attention_mask = tensorize(row)
            output = model(
                input_ids=input_ids,
                labels=labels,
                attention_mask=attention_mask,
                use_cache=args.use_cache,
            )
            weighted_loss = output.loss * (count / group_count)
            value = float(weighted_loss.detach().cpu())
            if not math.isfinite(value):
                raise FloatingPointError(f"non-finite loss at optimizer step {current_step}")
            weighted_loss.backward()
            step_loss += value
            del output, weighted_loss, input_ids, labels, attention_mask

        finish_step(current_step)
        completed_steps = current_step + 1
        if completed_steps != args.race_steps:
            raise RuntimeError(f"completed {completed_steps} optimizer steps, expected {args.race_steps}")
        final_eval = evaluate(model, args.holdout, args.use_cache)
        final_eval["optimizer_step"] = completed_steps
        evaluations.append(final_eval)
        log.write(json.dumps({"event": "validation", **final_eval}, ensure_ascii=False) + "\n")
        log.flush()

    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    state = {
        "recipe": args.recipe,
        "seed": args.seed,
        "race_steps": args.race_steps,
        "full_schedule_steps": args.full_steps,
        "warmup_steps": warmup_steps,
        "learning_rate": args.learning_rate,
        "use_cache": args.use_cache,
        "attention_implementation": "sdpa",
        "records": seen_records,
        "input_tokens": input_tokens,
        "supervised_tokens": supervised_tokens,
        "elapsed_seconds": elapsed,
        "input_tokens_per_second": input_tokens / elapsed,
        "peak_allocated_gib": torch.cuda.max_memory_allocated() / 2**30,
        "peak_reserved_gib": torch.cuda.max_memory_reserved() / 2**30,
        "trainable_parameters": sum(parameter.numel() for parameter in parameters),
        "evaluations": evaluations,
        "final_validation": final_eval,
    }
    save_checkpoint(model, optimizer, scheduler, args.output_dir, state)
    report_path = args.output_dir / "report.json"
    report_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
