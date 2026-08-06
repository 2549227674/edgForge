#!/usr/bin/env python3
"""Print a concise, versionable index of this workspace's local layout.

The output intentionally records names, hierarchy, Git state, file counts, and
sizes only.  It never reads the contents of model files, logs, keys, datasets,
or benchmark results.  Large generated/vendor trees are summarized so the
index remains useful as a handoff document instead of becoming a raw `tree`
dump of virtual environments and trial artifacts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Directories whose descendants add noise rather than navigational value.  The
# directory itself is still displayed with an on-disk summary.
SUMMARY_TREES = {
    ".git",
    ".venv-bfcl",
    ".venv-data",
    ".venv-lmeval",
    "__pycache__",
    "third_party",
    "data/archive",
    "data/pipeline/gate3_scan_payloads",
    "data/pipeline/gate7_render_samples",
    "data/pipeline/ir",
    "data/pipeline/ir_dedup",
    "data/pipeline/ir_gate5",
    "data/pipeline/ir_l2",
    "data/pipeline/mix_records",
    "data/eval/mmlu/cais_mmlu",
    "data/eval/mmlu/fast_500",
    "results/baseline_e4b_q4km",
    "results/lmeval",
    "results/anchor_official_qat_q4_0/bfcl",
}

PURPOSES = {
    ".gitignore": "大型可再生产物与本地环境的忽略规则。",
    "README.md": "新会话入口、权威文档与证据优先级说明。",
    "docs": "蓝图、执行卡、实际执行记录和 M0 基线摘要。",
    "eval_config.yaml": "M0 冻结的机器可读评测契约与证据哈希。",
    "m0_baseline_job.yaml": "B0 TB 20 题 × 5 的 Harbor job 定义。",
    "m0_allowlist_check.yaml": "WSL allowlist 检查配置。",
    "m0_allowlist_check_vm.yaml": "原生 Ubuntu VM allowlist 检查配置。",
    "metrics.py": "从 B0 ATIF trajectory 计算 parser 与 agent 指标。",
    "docker": "TB agent 预热镜像的 Dockerfile。",
    "scripts": "冻结 manifest/磁带、评测和回放的可执行源码。",
    "tasks": "lm-eval 自定义 GSM8K、HumanEval、MMLU task 定义。",
    "manifests": "固定抽样题单及其 SHA-256 清单。",
    "traces": "已入库的 5 盘 B0 磁带与 100 条 trajectory 哈希清单。",
    "logs/m0": "M0 启动、选题、评测、QAT 和 replayer 的运行证据。",
    "logs/w0": "W0 环境准备阶段的本地日志。",
    "results": "评测原始结果；仅选定的小型快照强制加入 Git，其余为本地证据。",
    "data/eval": "MMLU/GSM8K/HumanEval 的本地评测缓存；可按 pinned revision 重取。",
    "data/archive": "后续数据管线的本地归档数据集，不入 Git。",
    "data": "线 C 的可审计数据卡、mix 元数据与各门报告；原始语料和可再生产物保持本地。",
    "models": "HF 模型配置、tokenizer、GGUF 和 QAT 锚模型，本地保留不入 Git。",
    "third_party": "Harbor 与 llama.cpp 的 vendor 源码/构建目录，本地维护。",
    "vm": "原生 Ubuntu allowlist 核验 VM、启动介质和 SSH 文件；不入 Git。",
    ".venv-bfcl": "BFCL 专用 Python 虚拟环境。",
    ".venv-data": "线 C 数据管线专用 Python 虚拟环境。",
    ".venv-lmeval": "lm-eval 专用 Python 虚拟环境。",
}


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def git_state(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if path.is_dir():
        descendants = subprocess.check_output(
            ["git", "ls-files", "-z", "--", relative], cwd=ROOT
        )
        if descendants:
            return "G*"
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", "--", relative], cwd=ROOT
        ).returncode == 0
        return "I" if ignored else "U"
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "G"
    except subprocess.CalledProcessError:
        pass
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative], cwd=ROOT
    ).returncode == 0
    return "I" if ignored else "U"


def dir_summary(path: Path) -> tuple[int, int]:
    files = 0
    size = 0
    for current, _, names in os.walk(path):
        for name in names:
            candidate = Path(current) / name
            try:
                if candidate.is_symlink():
                    continue
                files += 1
                size += candidate.stat().st_size
            except OSError:
                continue
    return files, size


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    raise AssertionError("unreachable")


def purpose_for(relative: str) -> str | None:
    return PURPOSES.get(relative)


def should_summarize(relative: str) -> bool:
    if relative in SUMMARY_TREES:
        return True
    # Hugging Face cache metadata and Harbor trial payloads are local evidence,
    # but listing every file hides the project-level structure.
    if "/.cache" in relative:
        return True
    if relative == "results/bfcl" or relative.startswith("results/m0_"):
        return True
    return False


def render_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    if relative == ".":
        return []
    state = git_state(path)
    label = f"[{state}] {path.name}"
    if path.is_dir() and should_summarize(relative):
        count, size = dir_summary(path)
        return [f"{prefix}{label}/  … {count} files, {human_size(size)} (summarized)"]

    line = f"{prefix}{label}{'/' if path.is_dir() else ''}"
    if path.is_dir():
        children = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        lines = [line]
        for child in children:
            if child.name in {".git", "__pycache__"}:
                continue
            lines.extend(render_tree(child, prefix + "  ", depth + 1))
        return lines
    return [line]


def render_purpose_table() -> list[str]:
    rows: list[str] = []
    for relative, purpose in PURPOSES.items():
        path = ROOT / relative
        if path.exists():
            state = git_state(path)
            rows.append(f"| `{relative}` | `{state}` | {purpose} |")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-vendor",
        action="store_true",
        help="expand third_party/ instead of summarizing it",
    )
    args = parser.parse_args()
    if args.include_vendor:
        SUMMARY_TREES.remove("third_party")

    head = git(["rev-parse", "--short", "HEAD"])
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    state_counts: defaultdict[str, int] = defaultdict(int)
    for path in ROOT.iterdir():
        if path.name == ".git":
            continue
        state_counts[git_state(path)] += 1

    print("# 本地项目目录索引")
    print()
    print(f"> 生成时间：`{now}`")
    print(f"> 基准提交：`{head}`")
    print("> 目的：让远程仓库读者了解此工作区的目录结构、用途以及哪些对象只保留在本地。"
    )
    print()
    print("## 读取约定")
    print()
    print("- `G`：已被 Git 跟踪（含被 `git add -f` 冻结的小型结果快照）。")
    print("- `G*`：目录内至少有一个 Git 跟踪文件；目录仍可能同时含本地生成物。")
    print("- `U`：本地未跟踪。")
    print("- `I`：被 `.gitignore` 忽略的本地生成物。")
    print("- 索引只读取路径、层级、文件数和文件大小，不读取文件内容。")
    print("- 虚拟环境、第三方源码、大型数据集和高扇出 trial 目录折叠为汇总行。")
    print()
    print("## 关键目录与用途")
    print()
    print("| 路径 | Git 状态 | 用途 |")
    print("|---|---|---|")
    for row in render_purpose_table():
        print(row)
    print()
    print("## 目录树")
    print()
    print("```text")
    print(f"[G] {ROOT.name}/")
    for child in sorted(ROOT.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        if child.name == ".git":
            continue
        for line in render_tree(child, "  "):
            print(line)
    print("```")
    print()
    print("## 更新方式")
    print()
    print("目录布局、模型、数据、结果或 VM 有显著变化后，运行：")
    print()
    print("```bash")
    print("python3 scripts/generate_local_project_index.py > docs/本地项目目录索引.md")
    print("```")
    print()
    print(
        "提交前应审阅输出：它会记录本地文件名和层级，但不会把被索引文件的内容带入 Git。"
    )


if __name__ == "__main__":
    main()
