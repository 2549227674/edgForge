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
    "data/archive_parquet",
    "data/eval",
    "data/pipeline/gate3_scan_payloads",
    "data/pipeline/gate7_render_samples",
    "data/pipeline/ir",
    "data/pipeline/ir_dedup",
    "data/pipeline/ir_gate5",
    "data/pipeline/ir_l2",
    "data/pipeline/mix_records",
    "data/eval/mmlu/cais_mmlu",
    "data/eval/mmlu/fast_500",
    "models",
    "results/baseline_e4b_q4km",
    "results/lmeval",
    "results/anchor_official_qat_q4_0/bfcl",
    "tasks/edgeforge_mmlu_fast",
}

PURPOSES = {
    ".gitignore": "大型可再生产物与本地环境的忽略规则。",
    "README.md": "新会话入口、权威文档与证据优先级说明。",
    "docs": "蓝图、执行卡、实际执行记录和 M0 基线摘要。",
    "docs/research": "2026-07 历史事实台账、分轮调研与面经资料；只读溯源层。",
    "eval_config.yaml": "M0 冻结的机器可读评测契约与证据哈希。",
    "configs": "按里程碑分类的 job 与环境检查配置。",
    "metrics.py": "从 B0 ATIF trajectory 计算 parser 与 agent 指标。",
    "docker": "TB agent 预热镜像的 Dockerfile。",
    "scripts": "冻结 manifest/磁带、评测和回放的可执行源码。",
    "tasks": "lm-eval 自定义 GSM8K、HumanEval、MMLU task 定义。",
    "manifests": "固定抽样题单及其 SHA-256 清单。",
    "traces": "已入库的 5 盘 B0 磁带与 100 条 trajectory 哈希清单。",
    "logs/m0": "M0 启动、选题、评测、QAT 和 replayer 的运行证据。",
    "logs/w0": "W0 环境准备阶段的本地日志。",
    "results": "评测结果、100 条 B0 原始 trajectory 与选定的小型复现快照。",
    "data/eval": "已入库的 MMLU/GSM8K/HumanEval 冻结评测输入；下载缓存元数据不入库。",
    "data/archive": "原始/历史下载树；完整性边界见 data/SOURCES.md，不入 Git。",
    "data": "线 C 的可审计数据卡、mix 元数据与各门报告；原始语料和可再生产物保持本地。",
    "models": "配置、模板、tokenizer 已入库；HF/GGUF 权重仅本地保留。",
    "third_party": "Harbor 与 llama.cpp 的固定提交子模块；构建物与本地补丁不混入 gitlink。",
    "vm": "原生 Ubuntu allowlist 核验 VM、启动介质和 SSH 文件；不入 Git。",
    ".venv-bfcl": "BFCL 专用 Python 虚拟环境。",
    ".venv-data": "线 C 数据管线专用 Python 虚拟环境。",
    ".venv-lmeval": "lm-eval 专用 Python 虚拟环境。",
}


# The first table records what a remote-only reader receives immediately. The
# second records the corresponding workstation-only paths and available file
# granularity. Keep paths stable so a remote reader can identify separately
# supplied resources without this index deciding whether they should be read.
LOCAL_ASSETS = (
    (
        "LOCAL-MODEL-HF-WEIGHT",
        "models/gemma-4-E4B-it/model.safetensors",
        "Gemma 4 E4B HF 权重；RKLLM 转换输入。",
        "单文件；模型配置和 tokenizer 已在仓库。",
        "manifests/gemma4_e4b_rkllm_frozen_input_sha256.json",
    ),
    (
        "LOCAL-MODEL-B0-GGUF",
        "models/gguf/gemma4-e4b-it-Q4_K_M.gguf",
        "B0 PTQ Q4_K_M 推理与评测权重。",
        "单文件。",
        "eval_config.yaml",
    ),
    (
        "LOCAL-MODEL-QAT-GGUF",
        "models/gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B_q4_0-it.gguf",
        "官方 QAT-Q4_0 部署锚权重。",
        "单文件；README 已在仓库。",
        "eval_config.yaml",
    ),
    (
        "LOCAL-MODEL-QAT-MMPROJ",
        "models/gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B-it-mmproj.gguf",
        "官方 QAT 锚的多模态 projector。",
        "单文件；与 QAT GGUF 分开保存。",
        "models/gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/README.md",
    ),
    (
        "LOCAL-DATA-RAW",
        "data/archive",
        "九个来源的原始/历史下载树；不同来源完整度不同。",
        "整目录或单个来源子目录；该树不是统一规范输入。",
        "manifests/data_archive_sha256.json；data/SOURCES.md",
    ),
    (
        "LOCAL-DATA-PARQUET",
        "data/archive_parquet",
        "六个来源的完整冻结 parquet export。",
        "整目录或单个来源子目录。",
        "manifests/data_archive_sha256.json；data/SOURCES.md",
    ),
    (
        "LOCAL-DATA-MIX",
        "data/pipeline/mix_records",
        "154,097 条门后规范训练池，按来源拆成 5 个 JSONL。",
        "整目录或单个来源 JSONL。",
        "data/mix.yaml；data/data_card.md",
    ),
    (
        "LOCAL-RKNN-SDK",
        "rknn-llm-release-v1.3.0.zip",
        "RKLLM 1.3.0 SDK 原始压缩包。",
        "单个 ZIP 文件。",
        "docs/m0/06_board_smoke.md",
    ),
)

AUXILIARY_LOCAL = (
    ("`.venv-bfcl/`、`.venv-data/`、`.venv-lmeval/`", "Python 环境", "依赖版本另见 lock/requirements 文件。"),
    ("`third_party/llama.cpp/build/`、`.venv-convert/`", "编译与转换产物", "源码身份由固定子模块提交记录。"),
    ("`results/m0_tb_probe/`", "旧 probe 运行目录", "未列入冻结证据；相关执行脚本仍在仓库。"),
    ("`logs/w0/`、`tasks/worktrees/`、`tmp/`", "空目录或瞬态工作区", "生成时为空或包含过程性文件。"),
)


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


def tracked_files(*prefixes: str) -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--", *prefixes], cwd=ROOT
    )
    paths: list[Path] = []
    for raw in output.split(b"\0"):
        if not raw:
            continue
        path = ROOT / os.fsdecode(raw)
        if path.is_file():
            paths.append(path)
    return paths


def file_set_summary(paths: list[Path]) -> tuple[int, int]:
    existing = [path for path in paths if path.is_file()]
    return len(existing), sum(path.stat().st_size for path in existing)


def render_remote_bundle_table() -> list[str]:
    bundles = (
        (
            "REMOTE-MODEL-METADATA",
            tracked_files("models"),
            "Gemma 配置、Jinja、tokenizer 与模型卡；不含任何权重。",
            "manifests/remote_clone_assets.sha256",
        ),
        (
            "REMOTE-EVAL-INPUTS",
            tracked_files("data/eval"),
            "MMLU、GSM8K、HumanEval 冻结 parquet 输入。",
            "manifests/remote_clone_assets.sha256",
        ),
        (
            "REMOTE-TB-TRAJECTORIES",
            [
                path
                for path in tracked_files("results/baseline_e4b_q4km")
                if path.name == "trajectory.json"
            ],
            "20 题 × 5 的 100 条 B0 原始 ATIF trajectory。",
            "traces/trajectories_sha256.txt",
        ),
        (
            "REMOTE-BOARD-EVIDENCE",
            tracked_files("exports/m0/board"),
            "板端 S6 与 X0–X5 的七个证据包及校验文件。",
            "exports/m0/board/README.md",
        ),
    )
    rows: list[str] = []
    for asset_id, paths, purpose, identity in bundles:
        count, size = file_set_summary(paths)
        rows.append(
            f"| `{asset_id}` | {count} | {human_size(size)} | {purpose} | `{identity}` |"
        )
    return rows


def render_local_asset_table() -> list[str]:
    rows: list[str] = []
    for asset_id, relative, purpose, handoff, identity in LOCAL_ASSETS:
        path = ROOT / relative
        if path.is_file():
            count, size, state = 1, path.stat().st_size, "本机存在"
        elif path.is_dir():
            count, size = dir_summary(path)
            state = "本机存在"
        else:
            count, size, state = 0, 0, "本机缺失"
        rows.append(
            f"| `{asset_id}` | `{relative}` | {state}；{count} 文件，{human_size(size)} | "
            f"{purpose} | {handoff} | `{identity}` |"
        )
    return rows


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
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z", "--", relative], cwd=ROOT
        )
        tracked_count = len([entry for entry in tracked.split(b"\0") if entry])
        return [
            f"{prefix}{label}/  … 本机 {count} files, {human_size(size)}；"
            f"Git {tracked_count} entries (summarized)"
        ]

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
    print(f"> 生成基准提交（不含生成时尚未提交的工作区变更）：`{head}`")
    print("> 目的：记录普通 clone 可见资产、仅本机资产、路径、体积、可用粒度与身份入口。"
    )
    print()
    print("## 状态说明")
    print()
    print("- `REMOTE-*`：文件已包含在普通 clone 中。")
    print("- `LOCAL-*`：生成本索引时文件存在于本机，但普通 clone 不包含。")
    print("- 规范路径用于把单独提供的文件关联回项目结构；manifest 或哈希用于确认文件身份。")
    print("- `I` 仅表示路径受 Git 忽略规则约束，不附带删除、证据充分性或任务状态判断。")
    print("- 本索引不规定读取、提供或重建顺序；具体范围由读者及当前任务决定。")
    print()
    print("## 普通 clone 已包含的复现资产")
    print()
    print("| 资产 ID | 文件数 | 体积 | 内容 | 完整性入口 |")
    print("|---|---:|---:|---|---|")
    for row in render_remote_bundle_table():
        print(row)
    print()
    print("## 仅本机保留的资产")
    print()
    print("体积和文件数是本索引生成时的本机快照。目录型资产同时记录整目录与子目录/单文件粒度。")
    print()
    print("| 资产 ID | 规范本机路径 | 当前快照 | 用途 | 可用粒度 | 身份/解释入口 |")
    print("|---|---|---|---|---|---|")
    for row in render_local_asset_table():
        print(row)
    print()
    print("## 本机可再生或过程性目录")
    print()
    print("| 路径 | 类型 | 已记录的来源或状态 |")
    print("|---|---|---|")
    for path, kind, handling in AUXILIARY_LOCAL:
        print(f"| {path} | {kind} | {handling} |")
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
