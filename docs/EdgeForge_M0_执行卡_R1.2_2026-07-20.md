# EdgeForge · M0 执行卡 · 评测底座 + 数据管线 + 板端转换 smoke（三线并行）【R1.2】

> 出卡日期：2026-07-16；**R1 修订：2026-07-17**。依据：《EdgeForge 蓝图终稿（v4-R2）》M0 行 + §5 评测协议 + §9 数据七门 + §12 雷区索引；《W0 环境准备说明（事实版）2026-07-14》（执行事实层，**仅供参考、非强制约束——缺失的环境条件可顺延 M1 补齐**）；《对话结论补遗》；2026-07-17 公网核实（harbor / terminus-2 / BFCL / lm-eval / llama.cpp，条目标〔网核〕并附来源）。
> **卡制度**（蓝图头部）：本卡 = 已核实事实 + 操作建议，非命令。真实机器前判断优先，可自由偏离。标注读法：**〔事实/雷区〕** 偏离需留一句理由；**〔网核〕** 2026-07-17 公网文档核实的事实，同〔事实〕级；**〔建议〕** 操作起点随意改；**`[未复核]`** 用前自行判断。
> M0 目标一句话：**把"跑一次评测"变成一条挂快照的可重复命令，产出官方 E4B 基线数字（主表第一行，含系统指标列），同时清掉数据七门和板端转换单点风险。**

## R1 修订记录（对照 2026-07-16 初版）

| # | 类别 | 修订 |
|---|---|---|
| A1 | 命令错误 | TB 探测与基线命令补任务过滤；**20 题清单改用 harbor job.yaml + lock.json 作冻结载体**（§2/§3.2） |
| A2 | 命令错误 | 断点续跑 `--reuse` → `harbor jobs resume -p`（§3.2） |
| A3 | 命令错误 | lm-eval：MMLU 只能走 `local-completions`；补 `--confirm_run_unsafe_code`、max_length 冻结（§3.3） |
| A4 | 协议漏洞 | 采样冻结补 agent 侧 temperature（harbor 新版不再默认发送）（§1/§2） |
| B5 | 协议决定 | terminus-2 摘要开关 + LiteLLM `model_info` 注册升格为冻结项（§2） |
| B6 | 补事实 | BFCL 补 `BFCL_PROJECT_ROOT`、dummy key、handler 映射核对（§3.3） |
| B7 | 补事实 | `KV self size` 读法防呆（前缀随版本变、iSWA 双 cache 求和）（§1） |
| B8 | 补事实 | trajectory 配置与磁带保真度的依赖显式化（§3.4） |
| C9 | 一致性 | 主表第一行补系统指标列：M0 新增**最小 replayer**（§3.4/§4） |
| C10 | 一致性 | MMLU 抽样清单提前冻结，解门⑤时序矛盾（§3.3/§5） |
| C11 | 一致性 | 门①加 checksum manifest（W0 明言未做，语料不可再生）（§5） |
| C12 | 一致性 | 门⑦加 GGUF 内嵌模板 vs HF 模板 diff（§5） |
| C13 | 指标定义 | metrics.py 拆分 terminus parser 错误率 vs BFCL tools-API 准确率；`max_format_errors` 护栏（§2/§4） |
| D14–D19 | 小项 | `--alias`；hello-world 路径来源；数据集名统一全名；选题判据加运行期外网下载排除；基线 GGUF 来源/imatrix 入 config；聚簇 SE 注释 |
| W0 | 合入 | 新增 §0.5 前置（git init + W0 事实引用表 + 审计口径）；门①对账表以 W0 实测清单为起点 |
| R1.1 | 对齐 v4-R2（07-19） | 项目更名 EdgeForge；§7 结束状态声明的 M1 管线对齐决策 16（merge=S → OPD polish=S.O=M1 → PTQ）；**深层审计结论：其余三线内容零改动**——OPD 支线按决策 16 设计不触任何 M0 冻结件（基线/eval_config/磁带/七门/板端均正交；OPD prompt 池 = 七道门产出池的 M1 时引用，无 M0 新工作；OPD 训练配置属 §10 candidate 快照层非冻结评测层） |
| R1.2 | 谱系纪律 + 官方锚快档（07-20） | 外部评审（双基线提案）部分吸收：① W0 Q4_0 谱系核验**已完成**——确认为官方 `qat-q4_0-gguf`，即 §4.3 官方 QAT 锚本尊已在盘，非"我的 PTQ Q4_0"（后者 M6 自转生成）；② training_lineage 与 quantization_format 分列登记，普通 PTQ Q4_0 与官方 QAT Q4_0 禁止混写；③ 题单 sanity 仅由 B0-PTQ-Q4KM 驱动，锁定后不因任何其他模型分数换题；④ 官方 QAT 锚在 M0 过快档四件（零下载，文件已在盘），慢档定于 M6 三点对照同场；⑤ 磁带唯一来源 = B0-PTQ 轨迹，同批磁带回放所有模型。**拒绝项留档**：严格双基线（M0 第二条慢档）不做——该数字 M6 前无消费者，冻结协议使延后执行零损失，M6 同场测更新鲜；蓝图不动（决策 3 已覆盖官方锚，DAG 是工序图非锚点登记处） |
| R1.3 | 摘要方案定案（07-24） | `enable_summarize=false`；上下文溢出计为失败；`model_info=null`。原二选一的 16K 溢出前提已被 131072 实测端点取代；轨迹保持线性，轮数/token 指标不含摘要子代理调用。 |
| R1.4 | boot log 对账与待办插入（07-24） | 16K/32K 残留按实测边界修正；补入基线轨迹上下文分布、metrics token 分类、板端上下文档位及 thinking 模板链的待办，不改变既有结论。 |
| E1 | 锚点修正（07-17 补） | 官方发布图 E4B @TB2 全集 ≈2.2%（前代 0.0%）——"小模型 ~15%"预期下修；选题加"官方基线落在可测区间"显式目标带（§3.1/§3.2） |
| E2 | 校准锚（07-17 补） | 官方 BFCL ≈66.6% 入快档校准锚 + `external_anchors` 段；四个高功效指标升格为主要测量手段（§3.3/§4） |
| E3 | 选型记录（07-17 补） | tau2-bench 已考虑未选 + 理由入卡（§3.3 附注），建议同步蓝图决策表 |

---

## 0. 继承审查（本卡的 `[未复核]` 清单，开工先扫这几个）

| 项 | 值 | 状态 | 处置 |
|---|---|---|---|
| TB 子集题数 × k | 20 × 5 | `[未复核]` 决策 7 拍板值 | 先按 20×5 锁；若本地单题墙钟过长，M0 可先跑 10 题×3 出基线，题清单锁定后不再改 |
| 晋级阈值 | 掉分 ≤3pp | `[未复核]` 决策 2 模板值 | 基线阶段用不到（无父 candidate），M1 首次晋级前复议 |
| MMLU 抽样规模 | 500–1000 题起步 | `[未复核]`〔建议〕 | **R1：抽样清单提前到 D2 冻结**（C10，见 §3.3），锁定即冻结 |
| PC 基线上下文 / KV | `n_ctx=131072`；K/V `q8_0` | 〔事实〕已由 boot log 实测与冻结协议取代 | 见仓库根目录 `eval_config.yaml`（全项目 candidate 协议） |
| 板端 W8A8 校准集 | agent 域样本替换官方 21 条 | 〔建议〕 | §6 给最小可行版 |
| BFCL category 清单 + handler/模型名映射 | 未定 | `[未复核]`（R1 新增 handler 项） | §3.3 锁版时一并定案 |
| terminus trajectory kwargs 的 CLI 透传性 | raw_content / linear_history 能否经 `--agent-kwarg` 传入 | **已因关摘要而消解** | `enable_summarize=false` 时轨迹天然线性；保留本行作可审计痕迹 |
| harbor CLI 旗标名 | `--jobs-dir` / `--n-attempts` 长名等 | 以当日 `harbor run --help` 为准（R1 新增） | 核心语义已网核（§2），旗标拼写开工扫一眼 |

---

## 0.5 前置 · W0 状态引用与 M0 开工件（R1 新增）〔事实〕

**W0 定位声明**：下表为 2026-07-14 板上/机上实测事实，作为 M0 的起点参考，**不构成强制约束**——若某项与开工当日实况不符，以当日实测为准；缺失的环境条件（如 Q4_K_M 模型文件、独立 venv、checksum/第二介质）**默认在 M0 内准备补齐**；仅当进度崩溃触发 §7 最小可交付原则时才顺延 M1，顺延项记入待办。

| W0 事实 | 内容 | M0 用法 |
|---|---|---|
| llama.cpp commit | `ad8d8219915df8e423768d082d1dccfccb6e8437`（**不是 b9553**，报告一律用实际 commit） | §1 冻结 |
| 本地模型 | 已下载 **Q4_0**；`/v1/models` 曾验证；**谱系已核验（2026-07-20）：官方 `qat-q4_0-gguf`** | §1 基线需另备 Q4_K_M；在盘 Q4_0 = **官方 QAT 锚本尊（B0-OFFICIAL-QAT-Q4_0）**，M0 过快档四件（§3.3），慢档 M6 同场；"我的 PTQ Q4_0"点 M6 时从 bf16 自转另生成 |
| TB 2.1 | 本地已解析 + Oracle/verifier 闭环（五题样本三题 reward=1；两题失败源于网络抖动） | §2 起点：2.1 可用性已证，降 2.0 仅作兜底；**"terminus-2 + 自家端点"链路仍未验证** |
| Pi | 0.80.6 / Node 22.21.0，`use_pi = conditional` | M0 不用（benchmark 运行取代 live loop） |
| RK3588 | RKLLM runtime 1.3.0 + RKNPU driver 0.9.8；旧 v1.2.x 已移除；官方 `llm_demo` 板上原生构建、init 既有 .rkllm 成功 | §6 前提；≠ Gemma4 转换验收 |
| 数据 | 9 数据集在 `data/archive/`（清单见 §5 门①）；**checksum / manifest / 第二介质均未做** | §5 门①补齐（C11） |
| 审计口径 | W0 原始日志/trace 已按清理原则删除，仅剩事实摘要 + `logs/w0/` 少量记录 | 引用 W0 结论时注明"依 W0 事实版摘要，原始证据已清理，需审计则重跑对应 smoke" |

**M0 开工两件事〔建议，半小时〕**：
1. **git init + 首提交**（W0 遗留事项，明言应在进入需版本追踪的实验前完成）：提交 W0 事实版、本卡、`eval_config.yaml` 骨架、`logs/w0/` 残留记录。此后 eval_config / job.yaml / lock.json / metrics.py 全部入库，每次冻结项变更一次 commit。
2. 建 `eval_config.yaml` 骨架文件（字段占位），后续各节实测值逐项填入——避免"数字散落终端历史"。

---

## 1. 线 A · 本地推理端点钉参（半天）〔事实/雷区〕

**状态：已完成端点钉参；TB/terminus-2 链路尚未在本节完成。** 本节以本地构建、启动和请求日志为准，替换原先未实测的上下文起点。冻结值见仓库根目录 `eval_config.yaml`。

### 1.1 已冻结的主基线〔事实〕

| 项 | 实测值 | 证据 |
|---|---|---|
| 基线 ID / 谱系 | `B0-PTQ-Q4KM`；`google_bf16_instruct`；PTQ `Q4_K_M` | `eval_config.yaml`；`logs/m0/quantize_gemma4_e4b_q4_k_m.log` |
| 模型文件 | `models/gguf/gemma4-e4b-it-Q4_K_M.gguf`；SHA256 `953b94c6a89960ab9363720d14bf3ed266058dff31f3d35d2f91e68efdf8989a` | `eval_config.yaml` |
| 量化配方 | 官方 BF16 转 GGUF 后由本地 `llama-quantize` 量化；**未使用 imatrix** | `logs/m0/convert_gemma4_e4b_bf16_gguf.log`；`logs/m0/quantize_gemma4_e4b_q4_k_m.log` |
| llama.cpp | build `9987`，commit `ad8d8219915df8e423768d082d1dccfccb6e8437` | `logs/m0/llama_server_pi_c131072_q8_reasoning_unrestricted.log` |
| 主端点 | `n_ctx = 131072`、单 slot、43/43 层已 offload 至 CUDA0、q8_0 K/V KV；监听 `127.0.0.1:8080` | 同上 |
| 采样 | `temperature=1.0`、`top_p=0.95`、`top_k=64` | 同上；启动 seed 未在留存日志中出现，记为 `null` |
| 推理模式 | chat template 已启用，`thinking = 1`；本次 131K 日志为 `unrestricted` reasoning | 同上 |

**量化与谱系纪律**：在盘 `gemma-4-E4B_q4_0-it.gguf` 是官方 `google_official_qat` / QAT `Q4_0` 锚，不能写成“我的 PTQ Q4_0”；它与上表的 BF16→PTQ `Q4_K_M` 是两条独立谱系。两者的本地 SHA256、`training_lineage`、`quantization_method` 和 `quantization_format` 已分列记录在 `eval_config.yaml`。

### 1.2 131K 显存与请求证据〔事实〕

目标机器为 RTX 4060 Laptop GPU（8187 MiB；启动时可用 7096 MiB）。131072 上下文在 q8_0 KV 下成功分配并启动，日志预测 GPU 使用 4688 MiB（模型 2868 + 上下文 1109 + compute 711 MiB），加载后实际尚余 2364 MiB。

Gemma4 为 iSWA 拓扑，KV 必须将两段相加，而不是只记其中一条：

| KV cache | cells / layers | K / V 格式 | 大小 |
|---|---:|---|---:|
| non-SWA | 131072 / 4 | q8_0 / q8_0 | 1088.00 MiB |
| SWA | 1024 / 20 | q8_0 / q8_0 | 21.25 MiB |
| **合计** | — | — | **1109.25 MiB** |

服务完成了两次 5121-token 提示请求，最长一次结束于 7206 tokens，二者均为 `truncated = 0`。这证明了 **131K 端点的分配、加载和中等长度请求闭环**；它**不等于**已完成接近 131072 tokens 的满窗压力测试。若后续需要以“131K 可用”宣称满窗能力，须另补一条接近上限的输入日志及响应结果。

### 1.3 alias 与 tools-API〔已完成，范围受限〕

实际 TB 探测服务的 `logs/m0/v1_models_tb_probe_c131072.json` 返回 alias `gemma4-e4b`，故 alias 已以本线冻结的 131072 / `-n 4096` 服务复核。此前 32768 的 `/v1/models` 与 tools smoke 为未入库临时文件，已按清理决定删除，不再作为证据，也不应被引用。

OpenAI tools-API 不是本线过门条件：terminus-2 从纯文本解析 JSON/XML，不走 OpenAI `tools` 字段；它由 §2 的 harbor 单题探测验证。当前未保留 131K 的独立 tools 响应，因此不能声称该路径已在本线协议下验证。

### 1.4 §2 已钉死的协议项〔事实/雷区〕

1. Harbor agent 侧 `temperature=1.0` 已实传验证；不要把 server 采样日志误作该结论的唯一证据。
2. `enable_summarize=false`、上下文溢出计失败、`model_info=null` 均保持冻结。TB probe 已反推并冻结 `max_turns=30`；Harbor 0.18.0 terminus-2 不支持 `max_format_errors`，配置必须保持 `null`，由轮数与任务 timeout 共同限住重试。

**本节产出**：`eval_config.yaml` 已回填；审计证据包括转换/量化日志、`logs/m0/llama_server_tb_probe_c131072_q8.log`、端点自检日志及 §2 的 lock.json。Pi 历史日志仅作 131K KV/显存背景证据。

---

## 2. 线 A · TB 2.1 接自家端点跑通（半天，全卡风险最高一步）〔事实/雷区〕

**完成状态（2026-08-02）**：已完成“端点 → terminus-2 → 容器 tmux → verifier”的单题闭环。端点随后按要求停止；下列实测结论均对应实际执行的 `-n 4096`。当前配置已恢复为 32768 的待重启目标，但尚未以该值启动或测量，不能把它与下列 4096 证据混用。

| 冻结项 | 实测定案 | 证据 / 说明 |
|---|---|---|
| 模型接入 | `openai/gemma4-e4b`，`api_base=http://localhost:8080/v1`，`OPENAI_API_KEY=not-needed` | Harbor 0.18 的 `hosted_vllm` 与 `model_info=null` 不兼容；provider 选择器改为 `openai`，推理后端仍是 llama.cpp。 |
| 服务协议 | `-c 131072`、q8_0 K/V、`--jinja`、`--reasoning-format auto`、`-n 4096`、temperature 1.0 / top-p 0.95 / top-k 64 / min-p 0 | `logs/m0/llama_server_tb_probe_c131072_q8.log`；模型 alias 为 `gemma4-e4b`。 |
| reasoning 分离 | `reasoning_content` 非空，`content` 为可解析 JSON | `logs/m0/reasoning_format_check.json`。 |
| parser | `json` | 本地 hello-world：JSON reward=1；XML reward=0 的直接原因是模型命令缺换行，不是端点不可达。故在任何 TB 真题之前定案为 JSON。 |
| 轮数 / 超时 | `max_turns=30`；任务定义的 900 秒 agent timeout 不放大；`agent_setup_timeout_multiplier=3.0` | 见下方实测反推；轮数耗尽与任务超时均计失败。 |
| 格式错误护栏 | `max_format_errors: null` / unsupported | Harbor 0.18.0 的 terminus-2 未实现该参数；曾传入的 `64` 为 no-op，重试边界只能由 `max_turns` 与 task timeout 提供。 |

**正式单题探测**：数据集 `terminal-bench/terminal-bench-2-1`，完整 task ID 为 `terminal-bench/kv-store-grpc`，`k=1`、串行。最终 trial 目录为 `results/m0_tb_probe/2026-08-02__16-31-43/kv-store-grpc__7FvkxNN/`：agent 完成 7 轮、7 次命令调用，verifier 运行 7 项检查，reward=0.0 但无异常，因而“模型在环”的链路过门。reward=0 的实现原因是提交代码使用 `Server` 类名且 proto `value` 字段不匹配，不是 endpoint、harness 或 parser 故障。早先 agent 安装超时只用于确定 `--agent-setup-timeout-multiplier 3`，不计入正式结果。

**实测反推**（正式 trial，分位数按线性口径 `q=(n-1)p`）：completion tokens 为 `[690, 465, 378, 761, 952, 195, 229]`，p50=465、p95=894.7（配置取 895），4096 触顶 0/7；完整 agent 响应周期 p50=9.43 s、p95=19.07 s，agent 合计 81.65 s，trial 总时长 110.90 s，API 请求耗时合计 74.38 s，峰值上下文为 5,770 tokens。以 900 / 19.07 = 47.2 轮估算，30 轮约占 572.1 秒，保留约 327.9 秒尾部余量，故冻结上述轮数与超时政策。

**关键排障事实更正**：`-lv 4` 中的 `logit bias = -inf` 候选 token 行会在未启用 `--ignore-eos` 时同样出现，不能据此推断 EOG 被抑制。实际重起端点的 `/props` 显示 `ignore_eos=false`，启动命令也未带该旗标；以后只以 `/props` 与实际命令行判定该状态，旧 Pi log 仅保留作 KV/显存历史证据。

**归档与后续**：`results/` 已整体忽略，仅强制提交本 probe 的 lock.json；结论已写入 `docs/m0_eval_base.md`，相关配置、日志与快照已在提交 `8d0e903` 入库。本段是 §2 当时的阶段性结论；后续 32768 重起、锁题与基线的实际完成状态以下方 §3 的 2026-08-05 回填为准。

---

## 3. 线 A · 锁题 + 镜像预拉 + 官方基线（1–2 天，主要是等）〔建议+事实〕

**实际执行回填（2026-08-05，本块优先于下方保留的原计划）**：详细命令、排障过程和哈希见 `docs/EdgeForge_M0_§3_锁题与官方基线_R1.4_实际执行版.md`；本节只保留可供后续里程碑直接引用的冻结结论。

| 环节 | 实际结果 | 冻结件 / 说明 |
|---|---|---|
| 端点与协议 | B0 `gemma4-e4b` 已按 `-c 131072`、单 slot、q8_0 K/V、`-n 32768`、`--jinja`、`--reasoning-format auto` 实际启动；`finish_reason=length` **0** | `eval_config.yaml`；`logs/m0/llama_server_baseline_c131072_q8_n32768.log` |
| 镜像与外网纪律 | 20 题候选镜像 digest 已预拉并登记；2 题预热映射已留证；WSL 的 nftables 限制改在原生 Ubuntu VM 执行 allowlist 检查 | `logs/m0/m0_sanity_candidate_base_image_digests.tsv`、`m0_prewarm_two_task_image_map.tsv`、`m0_allowlist_check_vm_r3.tsv` |
| 锁题 | 最终 20 题、`k=5`、串行；sanity 最终 **0/5**，仅换题 **1 轮**后按预声明上限锁定，不再追分换题 | `m0_baseline_job.yaml`；`results/baseline_e4b_q4km/lock.json` |
| TB 2.1 慢档 | **0/100**；F1 verifier-zero=92、F2 30-turn 耗尽=7、F3 agent timeout=1、F4 基础设施重跑=0 | 子集未达 15–30% 目标，但按防选择偏差纪律如实冻结；不得与官方 TB2 全集 2.2% 横向比较 |
| 上下文与 parser | 单 trial 峰值上下文 p50/p95 = **6292.5 / 22340.55 tokens**；硬解析错误 **149/836 = 17.823%**；软格式警告 **498/836 = 59.569%** | `metrics.py`；`results/baseline_e4b_q4km/parser_metrics.json` |
| B0 快档 | BFCL `simple_python` **363/400 = 90.75%**；MMLU 固定 500 题 **0.598±0.0200**；GSM8K 固定 200 题 strict **0.840±0.0260** / flexible **0.845±0.0257**；HumanEval 官方执行器只完成 **5 题 smoke，0/5** | HumanEval 不得写成正式全量基线；MMLU 因端点缺 prompt `token_logprobs`，改用同 GGUF/同 llama.cpp 的 continuation-loglikelihood 兼容层，仍是 MCQ loglikelihood，不是生成式判题 |
| B0 系统列 | 完整重放 **22/22** 成功，warm 第二遍 **11/11**；TTFT p50/p95 **349.459/1762.491 ms**，TPOT p50 **19.220 ms/token**，吞吐 p50 **52.029 tok/s** | 5 盘、11 请求/遍，每盘连续两遍，仅统计第二遍 cache-warm；一次中断的 17/22 记录未混入正式值 |
| 官方 QAT-Q4_0 锚快档 | endpoint/tools smoke 通过；BFCL **364/400 = 91.00%**；GSM8K strict **0.850** / flexible **0.865**；warm TTFT p50/p95 **377.423/848.977 ms**，TPOT p50 **19.161 ms/token**，吞吐 p50 **52.188 tok/s** | 只进锚区，不冒充 B0 before 行；TB 20×5 慢档按原决策延后到 M6 三点同测 |
| 磁带与交接 | 从 B0 冻结 **5 盘 / 11 请求/遍**；100 条原始 ATIF trajectory 本地保留，全量 SHA-256 manifest 入库 | `traces/tapes/`、`traces/trajectories_sha256.txt`；原始 trajectory 仍在被 Git 忽略的 `results/baseline_e4b_q4km/`，不再复制进 `traces/` |
| 入库边界 | 源码、配置、task/manifest、磁带、静态日志和小型结果快照入 Git；大型 samples、数据缓存、GGUF 和原始 trajectory 不入库 | 小型 `/results/` 冻结件需 `git add -f`；实际清单见 R1.4 实际执行版 §10 |

**统计口径提醒**：TB 成功率已贴地板，后续主要看 parser、轮数/token 和系统列；BFCL `simple_python` 与官方 overall 66.6% 不是同一 scope；HumanEval 0/5 虽是有效 smoke 分数，但样本量不足以作正式基线。

**以下 3.1–3.4 保留为原计划和决策来源；若与上述实际回填冲突，以回填和 R1.4 实际执行版为准。**

**3.1 选题〔建议〕**：列 TB 2.1 全部 89 任务，手筛 20 个（`[未复核]` 20 这个数）——判据：不需要 GPU、单容器不过大、本地几分钟级可完成、**（R1/D17）运行期不依赖外网下载，或其 pip/apt 依赖可并入预拉**（"镜像预拉"只覆盖容器镜像，task 内下载是网络纪律的另一个漏点）。参考 TB 官方 empirical difficulty 优先 Easy/Medium；**（E1）选题显式目标 = 让官方 E4B 基线落在可测区间（子集成功率 15–30% 一带）**——官方发布图 E4B 在 TB2 全集仅 ≈2.2%（前代 0.0%），随机取题会让成功率贴地板、before/after 在该列失效。因此锁定动作分两步：手筛 20 题后，**仅由 B0-PTQ-Q4KM（基线本尊）**对其中 3–5 题各跑 1 次做量级 sanity（半小时级），基线明显 <10% 则回换更容易的题；**sanity 通过后清单锁定、从此不改，且不因官方 QAT 锚或任何其他模型的分数回头换题**（防选择偏差污染，R1.2）。选完：① `docker pull` 全部镜像预拉；② **20 个 task 写进 `m0_baseline_job.yaml`**（见 3.2，取代"手抄 ID 进 eval_config"）；③ 挑 2 个最快的标为烟测对。

**3.2 官方 E4B 基线（before 列，主表第一行）〔事实，R1/A1 重写〕**：

冻结载体改用 harbor 原生机制：job 是一个 YAML 文件（dataset/agent/model/task/`n_attempts` 全字段），`harbor run -c <yaml>` 运行；**解析后的 JobConfig 持久化为 job 目录内 lock.json**——它就是"一条可重复命令挂快照"的官方实现，`eval_config.yaml` 挂其指针即可。

```yaml
# m0_baseline_job.yaml（骨架，字段名以当日 harbor 文档为准）
job_name: baseline_e4b_q4km
jobs_dir: results/
n_attempts: 5
# dataset: terminal-bench/terminal-bench-2-1 + 20 个 task 的显式清单
# agent: terminus-2 + §2 冻结的全部 agent_kwargs（api_base/temperature/max_turns/
#        parser_name/max_format_errors/enable_summarize[/model_info]）
# n_concurrent: 1（串行，网络纪律）
```

```bash
harbor run -c m0_baseline_job.yaml          # 20 题 × k=5 × 串行
# 中断后续跑：
harbor jobs resume -p results/baseline_e4b_q4km/
```

**待办（基线完成后）**：从 trajectory 记录每题峰值上下文占用（零额外成本）。该分布同时决定 M2 板端 `max_context_len` 与 §3.4 的磁带上下文档位。

预期量级（E1 修正）：台账"小模型 TB ~15%"是通用小模型锚；官方发布图给出 E4B @TB2 全集 ≈2.2%（前代 0.0%）——不做 §3.1 的可测区间控制，100 试验可能只有 0–2 个成功、成功率列贴地板。目标：子集基线落在 15–30%（对应 100 试验 15–30 个成功，SE≈3.5–4.6pp；聚簇修正见 §4）——这就是 before。若 sanity 后基线仍偏低，成功率列如实记录、不硬拗，测量重心按 §4 移到四个高功效指标。**所有 session/trajectory 文件保留进 `traces/`，不删**（快档指标来源 + 磁带素材 + kernel shape 采样源）。

**3.3 快档基线（R1/A3、B6、C10 修订）**：
- **BFCL 工具调用准确率**〔网核〕：`pip install bfcl-eval`（勿混淆 PyPI 上无关的 `bfcl` 包；CalVer 锁版记进 config）。**PyPI 安装必须设 `BFCL_PROJECT_ROOT`**（结果/配置存放位置，.env 在 `$BFCL_PROJECT_ROOT/.env` 下查找）——不设则结果埋进 site-packages。本地端点：`--skip-server-setup` + .env 里 `VLLM_ENDPOINT`/`VLLM_PORT` 或 `REMOTE_OPENAI_BASE_URL=http://localhost:8080/v1`（+ `REMOTE_OPENAI_API_KEY` 给 dummy key，社区有 401 先例）；**模型名按 BFCL 支持列表对好 handler**（`[未复核]`，与 category 清单一并锁定）。`--test-category` 选非 live 子集起步（单轮 AST 评分，分钟级，量化退化金丝雀）。**（E2）校准锚：官方发布图 E4B @BFCL ≈66.6%（+0.5）**——M0 快档基线与其量级严重偏离时（非 live 子集与配置差异会带来偏差，但量级应对得上），先怀疑 handler/模板配置而非模型。该数与 TB2 ≈2.2% 一并记入 `eval_config.yaml` 新增 `external_anchors:` 段（值+出处=官方发布图+采录日期）。
- **lm-eval**〔网核〕：钉版本（commit + task 版本）。**任务→端点映射不可自由选**：
  - **MMLU（loglikelihood/MCQ）只能走 `local-completions`**——官方文档明确 chat-completion 端点不支持 loglikelihood 类任务；base_url 写全路径 `http://localhost:8080/v1/completions`，指定 tokenizer（loglikelihood 必需），instruct 模型加 `--apply_chat_template`。
  - GSM8K / HumanEval（生成式）：`local-chat-completions` 指 `.../v1/chat/completions` 即可。
  - **HumanEval 需显式 `--confirm_run_unsafe_code`**（代码执行任务强制开关）。
  - **API 模式 max_length 默认仅 2048**——GSM8K CoT + thinking 模板下必炸，显式调大并与 `-c` 实测值对齐后记入 config；`num_concurrent=1` 与 server `--parallel 1` 匹配。
  - **（R1/C10）MMLU 抽样清单在 D2 冻结**（起步 500–1000 题〔建议〕），门⑤去污染按该清单扫；若不愿提前定，门⑤改扫 MMLU 全量。GPQA-Diamond 不跑（4B 贴地板）。

**（E3）选型附注——tau2-bench 已考虑未选**：官方发布图另一半（Tau2 Retail/Airline/Telecom 三域，测"模拟用户对话 + 工具使用 + 政策遵循"中间层）不入本项目：① 需要模拟用户 LLM 在环，引入 API 成本 + 一个**无法冻结的评测组件**（模拟器换版本分数即漂，与"全程冻结协议"直接冲突）；② 客服对话域与终端 agent 部署叙事不贴。此结论建议同步进蓝图 §1 决策表（作"为何不跑官方 benchmark 组合"的面试现成答案）。另注：发布图 "TB2 (Agents)" 的括号是能力类别标注，非官方子集——TB 2.1 无 agents 子集，只有任务级难度/类别元数据（即 §3.1 选题所用维度）。

**官方 QAT-Q4_0 锚快档（R1.2 新增，约 1–2h，零下载）**：在盘官方 `qat-q4_0-gguf` 以独立 alias（`gemma4-e4b-qat-q4_0`）起服务，过四件：① endpoint smoke（`/v1/models` + tools 请求）；② BFCL 同 category 子集；③ GSM8K 快抽样；④ §3.4 磁带回放取系统指标。结果入 `results/anchor_official_qat_q4_0/`，登记进 eval_config `external_anchors` 区（非主表 before 行）。**慢档（TB 20×5）明确不在 M0 跑**——定于 M6 三点对照时与"我的 QAT Q4_0""我的 PTQ Q4_0"同场同鲜落成。协议参数（题单/采样/上下文/模板/agent kwargs）与基线完全一致，仅 alias 与模型文件不同。

**产出**：`results/baseline_e4b_q4km/`（lock.json + 逐 trial 结果）；`results/baseline_bfcl.json`、`results/baseline_lmeval.json`；`results/anchor_official_qat_q4_0/` 快档四件；主表第一行（官方 Q4_K_M @PC）+ 锚区一行（官方 QAT-Q4_0，标注 training_lineage）。

**3.4 磁带首批固化 + 最小 replayer（R1/B8、C9 重写）〔建议，加半天〕**：
- 从 3.2 的 trajectory 里挑 5–10 条固化成 replay 磁带（含 repeated-prefix 场景；上下文档位由基线跑出的真实任务上下文分布确定），存 `traces/tapes/`。**磁带唯一来源 = B0-PTQ-Q4KM 的轨迹（R1.2）**：固化一次后，同一批磁带回放所有模型（含官方 QAT 锚与后续全部 candidate），不得按各模型自己的成功轨迹分别选带——负载定死，模型文件才是唯一变量。
- **保真度（B8，R1.3 已消解）**：`enable_summarize=false`，轨迹天然线性，不再依赖 `linear_history` / `raw_content` 经 `--agent-kwarg` 透传，也无需因此改走 server 侧请求日志录制。
- **最小 replayer（C9）**：蓝图主表列含 TTFT/TPOT/吞吐，快档第①项就是磁带回放——初版卡"只固化不扫描"导致基线行系统指标列无产出路径。**R1 决定：M0 加半天写最小 replayer**（读磁带逐条重发请求、记 TTFT/TPOT/总吞吐；不做扫描矩阵，只对官方 E4B 跑一遍补齐第一行）。若进度崩，退回初版方案：第一行系统列留空 + 主表脚注"M1 补测"，但该决定要写进 m0_summary。

---

## 4. 线 A · 指标脚本（半天）〔建议，R1/C13、D19 修订〕

写 `metrics.py` 从 `traces/` 的 session 文件算四个数：成功率、**terminus 解析格式错误率**、平均修复轮数、每任务 token 消耗。

- **待办**：将“每任务 token”拆为 thinking / answer / tool 三列。thinking 模式开启后 thinking token 会主导总量；不拆列则无法测出工具调用效率的前后变化。
- **（C13）指标命名必须拆分**：TB 轨迹里测到的是 **terminus parser 格式错误率**（模型吐的 JSON/XML 结构坏，被 terminus 计为 format error——单工具 tmux 机制，不走 tools 字段）；**BFCL 测的才是 tools-API 调用准确率**。两者是不同机制的两列，M1 归因时不得混用。若 §2 走方案 (a)，轮数/token 统计需标注是否含摘要子代理调用。
- 理由（补遗 §4.1）：100 次二值试验统计功效弱，但里面有上千次结构化调用，后三个指标功效高一个量级，是 M1 之后真正测得出训练前后差异的地方。**（E2）鉴于官方 TB2 锚 ≈2.2%，这四个指标从"归因辅助"升格为主要测量手段**：成功率列保留但预期低信噪（除非 §3.1 可测区间达成），报告叙事以高功效指标为主线。
- **统计纪律写进脚本注释**：TB 成功率差 <7pp 一律输出"未分辨"。**（D19）加一句：SE≈3.5pp 按 100 次独立试验估，20 题×k=5 为聚簇结构，真实 SE 略大，故 7pp 是下界而非精确线。**

**产出**：`metrics.py` + 基线四指标表（+ replayer 输出的系统指标三列）。

---

## 5. 线 C · 数据管线七门（与线 A 并行，零租卡，独立 venv）〔事实/建议〕

**〔雷区〕环境隔离**：独立 venv，`datasets` 锁 <4.0 或与 harbor 分离（§2 警告）。

| 门 | 动作 | 本卡要点 |
|---|---|---|
| ① 完整性〔事实，R1/C11 扩充〕 | 行数/文件核验 + **checksum manifest** | 对账起点 = W0 实测清单：Glint 44M(88/73)、**Crownelius 293M(3/0，vs 台账 981.5MB/2.0M 行——parquet 点行数定案，别假设）**、Hermes 1.6G(5/0，点 parquet 行数)、GLM-5.2 3.3M(16/15)、qwen3.7-max-pi 9.8M(49/47)、Mythos-25k 53M(3/1)、opus-4.8-pi 640K(5/3)、kernelbench hard/mega（永不进训练，仅案例库）。**W0 明言 checksum/manifest/第二介质未做，而台账对语料冻结的处置是"立即存档+checksum"（源模型下线、语料不可再生）——本门给 `data/archive/` 出 sha256 manifest 进数据卡，第二介质备份一并在本门完成**（拷贝 + 用 manifest 复验第二份，半小时级；语料不可再生，这是唯一兜底） |
| ② 跨集去重〔事实/雷区〕 | session 指纹 + MinHash | 高危：Glint × Crownelius × opus-4.8-pi 同为 Fable 家族极可能重叠（补遗 §5.3），不去重=隐形上调 Fable 权重。首轮 user 内容 hash 精确去重 + MinHash 近重 |
| ③ 安全〔事实〕 | TruffleHog + PII 脱敏 + 抽样50 | 公开 trace 内容未知，密钥/真实路径/用户名脱敏，人工抽 50 条 |
| ④ 结构有效〔事实〕 | 多 harness 解析归一 | Pi session / Claude Code / parquet 三格式统一；坏 JSON、截断 session 剔除；每数据集记解析失败率（进数据卡） |
| ⑤ 去污染〔事实/雷区，R1/C10〕 | n-gram 重叠扫描 | 对 **HumanEval（最高危）** / TB 2.1 任务描述 / GSM8K / **MMLU（按 D2 冻结的抽样清单扫；清单未定则扫全量）** 逐一扫；kernelbench 两集已排除不用扫。产出去污染声明表（面试素材） |
| ⑥ 配平〔事实，1k–10k 已废〕 | 数量=质量门输出 | 四道硬过滤后原则上全保留；只做类别/源配比封顶防 Fable 偏科（参考 Mythos-25k 六类结构）；Mythos-25k 整包按其配平用（无工具 schema 部分仅防遗忘掺料）；含失败轨迹保留；总量不预设，过拟合靠留出验证集 early stopping（蓝图 §9 门⑥修订）。mix yaml 带 provenance 标签 |
| ⑦ 渲染掩码〔事实/雷区，R1/C12 扩充〕 | Gemma4 template + loss mask | 统一渲染 Gemma4 chat template（thinking 模板决定入冻结项）；loss 只落 assistant token、工具返回掩除（teich mask_data）；tokenizer 往返校验 + 人眼抽 20 条看掩码边界。**加一步：GGUF 内嵌模板（线 A `--jinja` 实际使用的）vs HF 侧模板（本门渲染训练数据用的）显式 diff**——两侧漂移是雷区"chat template 不一致→静默崩坏"的另一种触发形态，评测侧与训练侧必须同源。**待办**：thinking 模式已定为开启，训练侧渲染必须与评测端点同模式；`template_diff_ok` 目前为 `null`，此链未闭。 |

**产出**：七门漏斗表 → `data/data_card.md`；`data/mix.yaml`（带 provenance）；去污染声明表；**sha256 manifest**。M0 只要求管线跑通 + 漏斗表齐，正式训练 mix 在 M1 开工前定稿即可。

---

## 6. 线 B · 板端 E4B W8A8 转换 smoke（与线 A/C 并行，拆单点风险）〔事实/雷区〕

**目的**：蓝图把这步从 M2 提到 M0，唯一理由是拆单点风险——Gemma4→RKLLM 有 `[PAD]` 乱码先例（Issue #424，补遗 §7.1）。本步用官方权重转，不涉及微调模型，只验证"E4B 能不能干净转成 W8A8 并输出正常文本"。成败都记录，失败不阻塞线 A/C。

**〔事实〕前提（W0 已就位）**：板端旧 v1.2.x 已移除；RKLLM runtime 1.3.0 + RKNPU driver 0.9.8（未升内核）；官方 `llm_demo` 板上原生构建并成功 init 既有 .rkllm 模型——**这证明用户态升级可用，不等于 Gemma4 转换验收**（W0 事实版原文口径）。

**待办（M0/M2 边界）**：RKLLM 的 `max_context_len` 是转换时参数，写进 `.rkllm` 文件后运行时不可改。M0 smoke 用保守 8K–16K 跑通即可；正式板端档位由 M2 依 prefill 实测与任务上下文分布确定，不照抄 PC 的 131072。

**步骤〔建议〕**：
1. 用 RKLLM toolkit v1.3.0（Gemma4 支持在 v1.3.0 CHANGELOG 明文）转官方 `gemma-4-e4b-it` → W8A8 `.rkllm`。
2. 校准集〔建议，`[未复核]`〕：最小可行版先用官方通用样本跑通格式；agent 域样本替换（补遗 §7.2）留到 M2 正式量化时做——M0 只验"转得出、不乱码"。
3. 板上加载 + 发一条 prompt，确认输出不是 `[PAD]`/乱码；chat/thinking 模板与 PC 侧核对（与门⑦的模板 diff 同源）。
4. 版本记录一律以板上 `rkllm init` 打印为准（补遗 §7.4，网页缓存误导有先例；W0 审计口径同——原始 smoke 日志已清理，本步产出即新证据基线）。

**〔雷区〕**：若 `[PAD]` 复现——记录 toolkit 版本/转换参数/报错入 `docs/09_failures.md`，评估对 M2/M4 影响；不在 M0 死磕（探测项，可顺延但结论必须留档）。

**产出**：转换 smoke 结论（成/败 + 证据）入 `docs/m0_board_smoke.md`；`.rkllm` 文件（若成功）+ 板上 init 版本打印。

---

## 7. M0 验收（对照蓝图 M0 行，R1 更新）

**必须齐**：
- [ ] git 仓库初始化 + 冻结件全部入库（§0.5）
- [ ] `eval_config.yaml` 冻结（模型SHA/来源+imatrix/commit/参数/KV 实测/双端采样/seed/**摘要方案与 model_info**/**max_format_errors**/烟测对/lm-eval 版本+max_length/BFCL 版本+PROJECT_ROOT+category+handler/**MMLU 抽样清单**/template 决定/**m0_baseline_job.yaml 与 lock.json 指针**）
- [ ] TB 链路跑通 ≥1 题（terminus-2 + 自家端点，非 oracle）
- [ ] 官方 E4B 基线入主表第一行（TB 20×5 慢档 + BFCL/GSM8K/MMLU/HumanEval 快档 + **replayer 系统指标三列**）
- [ ] 官方 QAT-Q4_0 锚快档四件入锚区（含 training_lineage/sha 登记；慢档=M6，R1.2）
- [ ] `metrics.py` + 基线四指标表（parser 错误率与 tools-API 准确率分列）
- [ ] 磁带首批 5–10 盘固化 + 最小 replayer 脚本
- [ ] 数据七门漏斗表齐 + 去污染声明表 + mix.yaml（带 provenance）+ **sha256 manifest**
- [ ] 板端转换 smoke 有结论（成败皆记录）

**最小可交付**（进度崩了保什么）：`eval_config.yaml` + 官方基线一行（系统列可留空+脚注） + 数据漏斗表。TB 链路/BFCL/replayer/板端 smoke 可顺延到 M1 头两天，但**基线数字和评测配置冻结没有顺延选项**——没有 before 就没有整个项目的 after。W0 缺口（checksum/第二介质等）默认已在 M0 内补齐（§0.5/门①）；仅进度崩溃时随本原则顺延并记入待办。

**M0 结束状态声明**（写进 `docs/m0_summary.md`）：
> 评测已可复现（`harbor run -c m0_baseline_job.yaml`，lock.json + eval_config 双快照）；官方 gemma-4-e4b-it @Q4_K_M 的 TB2.1 子集成功率/parser 格式错误率/BFCL 工具调用准确率/GSM8K/MMLU/HumanEval/TTFT/TPOT 已入主表 before 行；官方 QAT-Q4_0 锚快档四件已入锚区（谱系分列登记，慢档定于 M6 三点对照同场）；摘要方案=___、上下文协议=___；数据池七门跑通、去污染声明齐、sha256 manifest 齐、Fable 偏科已配平封顶；板端 E4B W8A8 转换 smoke 结论=___。M1 开工无未决分叉：`teich→E4B QLoRA(vGPU-32)→merge=S → OPD polish(teacher=gemma-4-31b-it FP8 @Pro 6000 96GB)=S.O=M1 → PTQ 谱系 → 同一 job.yaml 重跑 → A/C 对照表 v1`。

---

## 8. 三线并行排布建议〔建议，R1 更新〕

| 日 | 线 A（评测） | 线 C（数据，独立 venv） | 线 B（板端） |
|---|---|---|---|
| D1 | **git init + config 骨架** + 端点钉参 + 读 KV 实测行 | 门①完整性 + **sha256 manifest + 第二介质备份** + 门②去重启动 | 转换 toolkit 装 + 官方权重转 |
| D2 | TB hello-world→1题探测 + **摘要方案定案** + **MMLU 抽样清单冻结** | 门③安全 + 门④结构 | 板上加载 + 乱码判定 |
| D3 | 选题20 + **job.yaml 成稿** + 镜像预拉 | 门⑤去污染（HumanEval 优先，MMLU 按清单） | （smoke 结论留档）|
| D4–5 | 官方基线慢档（`harbor run -c`，挂后台；中断用 `jobs resume`） | 门⑥配平 + 门⑦渲染掩码（含**模板 diff**） | — |
| D6 | 快档 BFCL/lm-eval + **官方 QAT-Q4_0 锚快档四件** + metrics.py | 漏斗表 + 数据卡 + mix.yaml | — |
| D7 | 磁带固化 + **最小 replayer + 基线系统指标** + 主表第一行 + 验收 | — | — |

冲突处理：线 A 的基线（D4–5）和线 C 的漏斗表不可挪（最小可交付）；TB 探测（D2）、板端 smoke（D1–2）、replayer（D7）属探测/增补项，可顺延但结论留档。

---

## 附 · R1 网核来源索引（〔网核〕条目出处，面试拷打备查）

| 事实 | 来源 |
|---|---|
| harbor 2.1 数据集全名、`--include-task-name`、`-l`、oracle 探测命令 | tbench.ai/docs/run-terminal-bench-2-1 |
| terminus-2 kwargs 全表（api_base/parser_name/max_turns/enable_summarize/阈值/temperature/model_info）、摘要三级回退、trajectory linear_history/raw_content 语义 | harborframework.com/docs/agents/terminus-2 |
| "不再默认发送 temperature" | github.com/harbor-framework/harbor releases |
| job.yaml 字段（n_attempts/jobs_dir）、`harbor jobs resume -p`、lock.json 持久化 | harbor PyPI 文档 + DeepWiki（Job & Trial Configuration / Job Resumption） |
| `hosted_vllm/` 前缀 + api_base 接本地端点先例、`max_format_errors` 护栏先例 | AISBench harbor_bench 文档；hamishivi/tmax README |
| BFCL：bfcl-eval 包名、BFCL_PROJECT_ROOT 必设、VLLM_ENDPOINT/REMOTE_OPENAI_BASE_URL、`--skip-server-setup`、401 先例 | PyPI bfcl-eval / gorilla README / gorilla issue #1305 |
| lm-eval：MCQ/loglikelihood 仅 completion 端点、base_url 全路径、tokenizer 必需、max_length 默认 2048 | EleutherAI lm-evaluation-harness README + docs/API_guide.md |
| llama.cpp `KV self size` 行现存格式与 iSWA 双 cache 日志 | ggml-org/llama.cpp issues（#12436 等）+ 源码日志串 |
