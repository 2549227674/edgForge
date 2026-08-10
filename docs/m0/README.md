# EdgeForge M0 · 最终执行卡（R2.0 冻结事实版）

- 结案日期：2026-08-11
- 里程碑：M0（评测底座、数据七门、RK3588 转换 smoke）
- 当前状态：**已冻结，无 M0 活动待办，不再继续实验**
- 机器可读合同：`eval_config.yaml`
- 跨里程碑机制事实：`docs/facts.md`

## 1. 结案结论

M0 已建立合同、题单和流程可重放的 E4B 评测底座，冻结 B0 PTQ Q4_K_M 的 Terminal-Bench、BFCL、MMLU、GSM8K、HumanEval smoke 和系统指标；官方 QAT-Q4_0 快档作为独立部署锚也已登记。数据线的 9 个来源已经过完整性、结构、退化、去重、安全、去污染和渲染/掩码审查，得到 154,097 条规范训练池。这里的“可重放”不承诺逐 token 确定性：seed 没有被可证地固定。

板端线只实现了 16K / 1-core W8A8 的诊断运行；2/3-core 初始化受单 IOMMU domain 4 GiB IOVA 窗口限制，3-core 缺 44,933,120 B。S2b 的 H2/H3 没有完成归因，准确状态是「门禁未放行/未完成判定」。owner 接受该未知并冻结；这是管理性结案，不是 3-core 交付成功，也不是 S2b 技术通过。

## 2. §1–§6 实际状态

| 节 | 实际状态 | 冻结输出 | 详细事实卡 |
|---|---|---|---|
| §1 本地端点 | **完成** | B0 Q4_K_M、131K 上下文、Q8 K/V、单 slot 与采样协议 | [01_endpoint.md](01_endpoint.md) |
| §2 TB 2.1 链路 | **完成** | endpoint → terminus-2 → 容器命令 → verifier 四段闭环 | [02_tb_link.md](02_tb_link.md) |
| §3 锁题与基线 | **完成，声明 HumanEval 缺口** | 20 题×5、B0 主表、QAT 锚快档、5 盘磁带 | [03_baseline.md](03_baseline.md) |
| §4 Agent 指标 | **完成** | schema B、v2 runner、token sidecar、任务聚簇统计 | [04_agent_metrics.md](04_agent_metrics.md) |
| §5 数据七门 | **完成** | 154,097 条规范池、manifest、审计报告与 `mix.yaml` | [05_data_pipeline.md](05_data_pipeline.md) |
| §6 板端 smoke | **部分通过后冻结** | 1-core 诊断工件、3-core IOVA 根因、X0–X5 证据 | [06_board_smoke.md](06_board_smoke.md) |

## 3. 冻结评测合同

| 项 | 冻结值 |
|---|---|
| B0 | Gemma 4 E4B IT，`google_bf16_instruct` → PTQ `Q4_K_M` |
| B0 SHA-256 | `953b94c6a89960ab9363720d14bf3ed266058dff31f3d35d2f91e68efdf8989a` |
| llama.cpp | build 9987，commit `ad8d8219915df8e423768d082d1dccfccb6e8437` |
| 端点 | alias `gemma4-e4b`；`n_ctx=131072`；单 slot；Q8 K/V；`n_predict=32768` |
| 采样 | temperature 1.0，top-p 0.95，top-k 64，min-p 0，seed 未可证地固定 |
| 模板 | Jinja + `reasoning_format=auto`，thinking 开，不摘要 |
| TB | Terminal-Bench 2.1，锁定 20 题，k=5，串行，terminus-2 JSON parser，`max_turns=30` |
| cache 口径 | prompt cache 开；系统指标每盘连续两遍，只统计第二遍 cache-warm |

`eval_config.yaml` 是字段级权威。本卡只给读者结论，不重复全部机器可读字段。

## 4. 基线与锚点

### 4.1 B0 主表

| 指标 | 冻结值 |
|---|---:|
| TB 2.1（20 题×5） | 0/100 |
| Terminus hard parser error | 149/836（17.823%） |
| Terminus soft format warning | 498/836（59.569%） |
| BFCL v4 `simple_python` | 363/400（90.75%） |
| MMLU fast-500，5-shot | 0.598 ± 0.0200 |
| GSM8K fast-200 strict / flexible | 0.840 / 0.845 |
| HumanEval | 5 题均完成评分，0 题通过（pass@1=0）；**仅 smoke，无正式全量基线** |
| cache-warm TTFT p50 / p95 | 349.459 / 1762.491 ms |
| cache-warm TPOT p50 | 19.220 ms/token |
| cache-warm 吞吐 p50 | 52.029 tok/s |

TB 失败四分类 F1/F2/F3/F4 = 92/7/1/0；`finish_reason=length` 为 0。parser 分母 836 是 100 条 trajectory 中被检查的 assistant 消息数。0/100 的任务聚簇 rule-of-three 95% 上界为 15%，不使用失真的 Wald SE=0。完整 agent/token 列见 [evaluation_baseline.md](evaluation_baseline.md)。

### 4.2 官方 QAT-Q4_0 部署锚

它是 `google_official_qat` 的独立锚，不是 B0 before 行：

- endpoint/tools smoke 通过。
- BFCL `simple_python` 364/400（91.00%）。
- GSM8K strict/flexible 0.850/0.865。
- cache-warm TTFT p50/p95 377.423/848.977 ms，TPOT p50 19.161 ms/token。
- TB 20×5 慢档留给 M6 三点同测，不是 M0 未完成项。

## 5. 数据交付

- 9 个来源完整对账，冻结 export revision 与 SHA-256 在 `manifests/data_archive_sha256.json`。
- 规范池 154,097 条：Crownelius 150,919、Hermes 2,907、GLM-5.2 232、Qwen 38、Glint 1。
- Mythos 因最高频前缀 100%、精确重复率 99.14% 整集剔除。
- 冻结测试集 canary 为 0；13-gram 去污染删除 448 条。
- 最终训练载荷安全复扫为 0；20/20 渲染和掩码人工审核通过。
- 第二介质备份未做，是显式接受的保留风险，不伪称完成。
- 规范池含 1 条 AGPL-3.0 Glint 记录；不得发布训练后权重。

## 6. 板端冻结边界

- W8A8 / RK3588 / 16K 可转换。
- 1-core 可初始化、贪心生成合法 UTF-8；手动模板的 `thought` / `tool_call` 标记能成对出现。
- 1-core 是唯一保留的诊断工件，不是交付物。
- 2/3-core 因 IOVA 失败；3-core 精确缺口 44,933,120 B。
- X0 aperture、X1 W4A16、X2 domain 改写三条 3-core 路线均关闭。
- X4 的 N=128 成功，N=256 CUDA OOM 无工件，所以 H2/H3 未归因。
- X5 已把 U6 收缩为 RKLLM 1.3.0 parser 不支持 `raise_exception()` 实参中的相邻字符串字面量隐式拼接。

不再继续 X4、X5、H2 粒度阶梯、S3、driver/DT 改写或 3-core 试错。重开条件见 [06_board_smoke.md](06_board_smoke.md) §5.3。

## 7. 证据与资产分层

| 层 | 保留内容 | 处置 |
|---|---|---|
| 合同 | `eval_config.yaml`、job/task YAML、manifest | 版本化保留 |
| 结论 | 本卡、六张事实卡、`docs/facts.md`、数据卡 | 版本化保留 |
| 可复核小证据 | 锁题 lock/result、聚合评测 JSON、静态日志、5 盘磁带 | 版本化保留 |
| 本地冻结输入 | 两条 GGUF、HF 权重、冻结 parquet export、`mix_records/` | 保留，不入 Git |
| 原始 TB trajectory | 100 条 `trajectory.json` + `traces/trajectories_sha256.txt` | 本地保留，删除 cast/pane/容器附件 |
| 板端证据 | `exports/m0/board/` 七个 ZIP + `.sha256` | 本地冻结保留 |
| 可再生中间层 | 数据 IR 各阶段、安全投影、渲染样本、allowlist VM、smoke/sanity 运行目录 | 本次删除 |

维护删除只是资产管理记录，不改写实验结论。

本次收敛的实际结果：

- 本地删除一次性 allowlist VM、线 C 的 IR/dedup/gate5/安全投影/渲染中间层、旧 smoke/sanity 目录、lm-eval samples 与 trajectory cast/pane 附件，约释放 20 GiB。
- 云端删除 `/root/autodl-tmp/gemma-4-E4B-it.zip` 重复模型包；复核时 `/root/autodl-tmp` 约 692 KiB，只剩平台自己的 `.autodl/autopanel.*.db`，无 M0 资产。
- 板端上一轮已收敛为 `/home/orangepi/edgeforge_m0_frozen_r2/` 下的工件、`SHA256SUMS` 和 `FROZEN.txt`；本轮无可再删项。

## 8. 顺延与重开

以下是下游里程碑边界，不是 M0 待办：

- M1：在等 optimizer-step/等 token 预算下选数据采样配方，再做全量渲染。
- M2：若另行授权，定义正式板端校准集与新的硬件合同。
- M5：SWE-bench Pro 去污染。
- M6：官方 QAT、项目 QAT 与项目 PTQ 三点同场慢档。

任何 M0 技术结论的重开，必须由 owner 明确撤销冻结，新建执行卡、artifact 身份、manifest、预注册判据和独立证据包。不得继续在本卡追加补丁。

## 9. 结案验收

以下勾选表示对应事项已经形成可审计结论或显式缺口，不表示 HumanEval 全量、第二介质、3-core 或 S2b 已技术完成。

- [x] B0 模型身份、端点与采样协议冻结
- [x] TB 2.1 自家端点链路闭环
- [x] 20 题×5 基线、快档和 cache-warm 系统列冻结
- [x] Agent v2 指标和统计边界冻结
- [x] 数据七门与 154,097 条规范池闭环
- [x] 板端 1/2/3-core、S2b、agent 模板和 parser 边界留结论
- [x] HumanEval 全量缺口、数据第二介质缺口、板端 S2b 未归因均显式标注
- [x] M0 资产已分层，可再生中间物不再冒充冻结证据

**R2.0 是 M0 的唯一当前执行卡；旧 R1.x 混合卡可从 Git 历史追溯，不再作为当前操作说明。**
