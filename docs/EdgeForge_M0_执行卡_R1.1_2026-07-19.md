# EdgeForge · M0 执行卡 · 评测底座 + 数据管线 + 板端转换 smoke（三线并行）【R1.1】

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
| 16k 上下文 | `-c 16384` | 〔事实〕待实测校正 | §1 读 KV 相关日志行定案，不照抄 |
| 板端 W8A8 校准集 | agent 域样本替换官方 21 条 | 〔建议〕 | §6 给最小可行版 |
| BFCL category 清单 + handler/模型名映射 | 未定 | `[未复核]`（R1 新增 handler 项） | §3.3 锁版时一并定案 |
| terminus trajectory kwargs 的 CLI 透传性 | raw_content / linear_history 能否经 `--agent-kwarg` 传入 | 待开工验证（R1 新增） | §3.4；传不进则磁带改走 server 侧录制 |
| harbor CLI 旗标名 | `--jobs-dir` / `--n-attempts` 长名等 | 以当日 `harbor run --help` 为准（R1 新增） | 核心语义已网核（§2），旗标拼写开工扫一眼 |

---

## 0.5 前置 · W0 状态引用与 M0 开工件（R1 新增）〔事实〕

**W0 定位声明**：下表为 2026-07-14 板上/机上实测事实，作为 M0 的起点参考，**不构成强制约束**——若某项与开工当日实况不符，以当日实测为准；缺失的环境条件（如 Q4_K_M 模型文件、独立 venv、checksum/第二介质）**默认在 M0 内准备补齐**；仅当进度崩溃触发 §7 最小可交付原则时才顺延 M1，顺延项记入待办。

| W0 事实 | 内容 | M0 用法 |
|---|---|---|
| llama.cpp commit | `ad8d8219915df8e423768d082d1dccfccb6e8437`（**不是 b9553**，报告一律用实际 commit） | §1 冻结 |
| 本地模型 | 已下载 **Q4_0**；`/v1/models` 曾验证 | §1 基线需另备 Q4_K_M（Q4_0 留作官方 QAT-Q4_0 对照线伴生资产） |
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

**目的**：把 llama-server 起来、把启动参数冻结进 `eval_config.yaml`、用实测校正 `-c`。W0 的 `llama_direct_tool_call.json`（仍保留在 `logs/w0/`）已验证工具调用可用，本步是把它固化。

```bash
LLAMA_COMMIT=ad8d8219915df8e423768d082d1dccfccb6e8437   # W0 实测，非 b9553
./build/bin/llama-server \
  -m models/gemma4-e4b-it-Q4_K_M.gguf \
  --alias gemma4-e4b \
  -ngl 99 -c 16384 --parallel 1 --jinja --port 8080 \
  2>&1 | tee logs/m0/llama_server_boot.log
```

**〔事实/雷区〕五条**：
1. **量化格式先定案**：W0 下的是 `Q4_0`（补遗 §2.1），基线与后续自量化必须同格式可比。**决定：基线用 `Q4_K_M`**（k-quant，"Q4≈92%FP16"质量锚即指它；自量化社区标准同）。文件来源二选一：换下官方 Q4_K_M GGUF，或 `llama-quantize` 从 bf16 自转。**（R1/D18）来源与 imatrix 使用与否必须记入 `eval_config.yaml`**——蓝图 §4.2 把 imatrix 列为校准轴，M1 做"我的 PTQ vs 官方"对照时，基线格的可比性取决于此。Q4_0 那份留作官方 QAT-Q4_0 对照线伴生资产，别删。
2. **读 KV 大小实测行（R1/B7 防呆）**：启动日志中 `KV self size = XXX MiB, K (...): ..., V (...): ...` 行是补遗 §1.5 的精确显存答案。两点注意：① 行前缀随版本变过（旧 `llama_new_context_with_model:`、新 `llama_context:`），**grep 关键字用 `KV self size` 而非整行**；② 若 E4B 属交错滑窗（iSWA）架构，日志会出现 `creating non-SWA KV cache` 与 `creating SWA KV cache` 两个 cache，**显存账按全部 KV 相关行求和**记录（E4B 的宽 KV + 18 层跨层共享落到哪种拓扑，以 boot 日志为准）。若 +激活+CUDA 缓冲逼近 8GB 上限，降 `-c 12288` 或加 `--cache-type-k/v q8_0`（KV 量化是实验轴，基线要么全程 f16、要么明确标注）。
3. **`--jinja` 必开**：chat template 不一致会让工具调用静默崩坏（补遗 §6.2 / 雷区表）。**（R1/D14）加 `--alias gemma4-e4b`** 使 `/v1/models` 返回名与 harbor 的 `-m hosted_vllm/gemma4-e4b` 对齐。启动后 `curl :8080/v1/models` 确认，再发一条带 `tools` 字段的 `/v1/chat/completions` 确认工具调用格式回得来——**注意（R1/C13）：这一步验证的是 BFCL 所需的 tools-API 路径；TB 的 terminus-2 不走 tools 字段（见 §2），TB 链路由 §2 探测本身验证**。
4. **采样钉死是双端问题（R1/A4）**：server 端 temperature/top-p 取 Gemma4 模型卡推荐值；**agent 端 terminus-2 的 temperature 必须在 §2 用 `--agent-kwarg temperature=<同值>` 显式设置**——harbor 新版明确"Terminus 2 与 LiteLLM 不再发送默认 temperature"，不显式设则行为随 harbor 版本漂移，且请求级参数会覆盖 server 默认。`eval_config.yaml` 采样栏分 server / agent 两行记。k=5 要求 temp>0（否则五次全同白跑）；seed 记录（server 端 `--seed` 若设则记，agent 不消除不确定性但留痕）。
5. **产出**：`eval_config.yaml`（模型 SHA256 / 模型文件来源+imatrix / LLAMA_COMMIT / 启动参数 / KV 实测行 / 双端采样值 / seed）；`logs/m0/llama_server_boot.log`。

---

## 2. 线 A · TB 2.1 接自家端点跑通（半天，全卡风险最高一步）〔事实/雷区〕

**目的**：W0 跑的是 oracle（不经过模型），"terminus-2 + 自家端点 + Gemma 模板"这条链**从未验证过**（补遗 §4.4）。本步先跑通 1 题，不论成败，只要 agent 正常发请求→收回复→执行命令→verifier 出结果即算过门。W0 已证 TB 2.1 本地可解析、容器闭环可用——本步只补"模型在环"这一段。

**〔网核〕harbor / terminus-2 机制（2026-07-17，来源：harborframework.com/docs、tbench.ai/docs、harbor releases）**：
- 数据集名：2.1 官方运行文档用全名 `-d terminal-bench/terminal-bench-2-1`（与 04 台账/R 报告一致）；`terminal-bench@2.1` 简写亦有官方先例（论文用 `@2.0`）。**统一用全名**，简写作备注；实际解析结果以 lock.json 为准（R1/D16）。
- 子集/单题：`--include-task-name "<task>"`（单题）、`-t "<glob>"` + `-l <n>`（模式+限量）；**成套子集走 job.yaml**（§3.2）。
- k 值 `-k`（attempts），并发 `--n-concurrent`；job 配置字段名 `n_attempts`。断点续跑 = **`harbor jobs resume -p jobs/<目录>`**（按 trial 配置识别已完成试验、只补未完成的）——不是初版误写的 `--reuse`（R1/A2）。
- terminus-2 kwargs（官方文档全部证实）：`api_base`、`parser_name`（json/xml，默认 json；官方注明 xml 对部分模型更稳）、`max_turns`（即 max_episodes，**默认 1,000,000，务必显式设小**）、`enable_summarize`（默认 true）、`proactive_summarization_threshold`（默认 8000 free tokens）、`temperature`、`model_info`、`session_id`。
- **terminus-2 是单工具（tmux）设计**：从纯文本回复里解析 JSON/XML 结构化命令，**不使用 OpenAI tools/function-calling 字段**（R1/C13）。社区跑本地小模型有 `--agent-kwarg max_format_errors=64` 护栏先例——小模型吐坏 JSON 是常态，**显式设置并记录**（它是影响成功率的协议参数）。

**〔事实/雷区，R1/B5 升格为冻结项〕摘要与上下文核算——开工必须二选一并写进 `eval_config.yaml`**：
LiteLLM 不认识 `hosted_vllm/gemma4-e4b` 这类自定义模型；官方文档明确 metrics 统计与上下文摘要要正常工作需通过 `model_info` 注册 `max_input_tokens` 等（proactive 摘要的触发量 free tokens = max_input_tokens − 当前上下文，不注册无从计算）。且 `enable_summarize=false` 同时关掉 passive 摘要（上下文溢出时的三级回退恢复）——16k 跑 TB，溢出即硬失败。两个方案都站得住，但**不能悬置**：
- **方案 (a)**：开摘要 + `model_info.max_input_tokens` ≈（`-c` 实测值 − 生成余量）+ 阈值调低（如 2000–4000）。任务更可能跑完，但轮数/token 指标含摘要子代理调用，磁带保真度需 §3.4 处理。
- **方案 (b)（起步建议）**：关摘要，**声明"上下文溢出计为失败"是评测协议的一部分**。轨迹天然线性（利好磁带与指标），代价是长任务折损——这本身也是 16k 端侧模型的真实约束，作为协议成立。

```bash
# 先 hello-world 验证 harness 自身
# （R1/D15）examples/tasks 是 harbor 仓库内路径，pip 安装环境不存在——
#  要么 clone harbor 仓库取该路径，要么 `harbor tasks init` 造一个本地最小任务
harbor run -a terminus-2 -m hosted_vllm/gemma4-e4b \
  --path <harbor仓库>/examples/tasks/ --task-name hello-world \
  --agent-kwarg api_base=http://localhost:8080/v1 \
  --agent-kwarg temperature=<模型卡值> \
  --agent-kwarg max_turns=30 \
  --agent-kwarg parser_name=json \
  --agent-kwarg max_format_errors=<定值并记录> \
  --agent-kwarg enable_summarize=false \        # 或方案(a)：true + model_info + 阈值
  --jobs-dir outputs/m0_hello

# 通过后跑 1 题 TB 2.1（R1/A1：必须带任务过滤，否则跑满全部 89 题）
harbor run -d terminal-bench/terminal-bench-2-1 -a terminus-2 -m hosted_vllm/gemma4-e4b \
  --include-task-name "<从 89 题里挑一个轻量题>" \
  --agent-kwarg api_base=http://localhost:8080/v1 \
  --agent-kwarg temperature=<同上> --agent-kwarg max_turns=30 \
  --agent-kwarg max_format_errors=<同上> --agent-kwarg enable_summarize=false \
  -k 1 --n-concurrent 1 \
  --jobs-dir outputs/m0_tb_probe
```

**〔雷区〕排障顺序（补遗 §4.4 + R1 扩一条）**：agent 发不出/解析不了 → ① chat template（`--jinja` + parser_name json↔xml 换一下）；② 上下文不够（`-c` 加到实测上限；若走方案(a)查 `model_info` 是否注册、阈值是否过高）；③ 输出格式 terminus 解析不了（看 `outputs/m0_tb_probe/**/trial_*` 原始交互；format error 计数是否触顶 `max_format_errors`）；④ LiteLLM 对未知模型的 token 核算异常（unknown model 警告行）。
**〔雷区〕环境**：安装 harbor 会把 `datasets` 升到 ≥4.0——**数据管线（线 C）用独立 venv**。Docker ≥20.10、Compose ≥2.0、Python 3.12。
**〔雷区〕TB 版本**：W0 已证 2.1 本地可用；仅当当日拉取失败才降 `terminal-bench-2`（89→2.0 小模型分差 ~3pp，降锚不伤主线），记录探测日期。网络抖动不解释为模型失败（补遗 §4.5，W0 同口径）。

**产出**：`outputs/m0_tb_probe` 一题闭环证据；**摘要方案 (a)/(b) 决定 + model_info（若用）+ max_format_errors 值**入 `eval_config.yaml`；链路结论一行入 `docs/m0_eval_base.md`。

---

## 3. 线 A · 锁题 + 镜像预拉 + 官方基线（1–2 天，主要是等）〔建议+事实〕

**3.1 选题〔建议〕**：列 TB 2.1 全部 89 任务，手筛 20 个（`[未复核]` 20 这个数）——判据：不需要 GPU、单容器不过大、本地几分钟级可完成、**（R1/D17）运行期不依赖外网下载，或其 pip/apt 依赖可并入预拉**（"镜像预拉"只覆盖容器镜像，task 内下载是网络纪律的另一个漏点）。参考 TB 官方 empirical difficulty 优先 Easy/Medium；**（E1）选题显式目标 = 让官方 E4B 基线落在可测区间（子集成功率 15–30% 一带）**——官方发布图 E4B 在 TB2 全集仅 ≈2.2%（前代 0.0%），随机取题会让成功率贴地板、before/after 在该列失效。因此锁定动作分两步：手筛 20 题后先用官方模型对其中 3–5 题各跑 1 次做量级 sanity（半小时级），基线明显 <10% 则回换更容易的题；**sanity 通过后清单才锁定、从此不改**。选完：① `docker pull` 全部镜像预拉；② **20 个 task 写进 `m0_baseline_job.yaml`**（见 3.2，取代"手抄 ID 进 eval_config"）；③ 挑 2 个最快的标为烟测对。

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
harbor jobs resume -p results/baseline_e4b_q4km-<ts>/
```

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

**产出**：`results/baseline_e4b_q4km/`（lock.json + 逐 trial 结果）；`results/baseline_bfcl.json`、`results/baseline_lmeval.json`；主表第一行（官方 Q4_K_M @PC）。

**3.4 磁带首批固化 + 最小 replayer（R1/B8、C9 重写）〔建议，加半天〕**：
- 从 3.2 的 trajectory 里挑 5–10 条固化成 replay 磁带（含 repeated-prefix 场景 + 一条 16k 长上下文场景），存 `traces/tapes/`。
- **保真度依赖（B8）**：terminus-2 默认 trajectory 配置下，一旦发生摘要就无法从主文件还原真实发给 LLM 的请求序列（`linear_history=true` + `raw_content=true` 才行）。若 §2 选了方案 (b)（关摘要），轨迹天然线性、无此问题；若选方案 (a)，开工验证这两个开关能否经 `--agent-kwarg` 透传（继承审查表项），传不进则磁带改从 server 侧请求日志录制。
- **最小 replayer（C9）**：蓝图主表列含 TTFT/TPOT/吞吐，快档第①项就是磁带回放——初版卡"只固化不扫描"导致基线行系统指标列无产出路径。**R1 决定：M0 加半天写最小 replayer**（读磁带逐条重发请求、记 TTFT/TPOT/总吞吐；不做扫描矩阵，只对官方 E4B 跑一遍补齐第一行）。若进度崩，退回初版方案：第一行系统列留空 + 主表脚注"M1 补测"，但该决定要写进 m0_summary。

---

## 4. 线 A · 指标脚本（半天）〔建议，R1/C13、D19 修订〕

写 `metrics.py` 从 `traces/` 的 session 文件算四个数：成功率、**terminus 解析格式错误率**、平均修复轮数、每任务 token 消耗。

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
| ⑦ 渲染掩码〔事实/雷区，R1/C12 扩充〕 | Gemma4 template + loss mask | 统一渲染 Gemma4 chat template（thinking 模板决定入冻结项）；loss 只落 assistant token、工具返回掩除（teich mask_data）；tokenizer 往返校验 + 人眼抽 20 条看掩码边界。**加一步：GGUF 内嵌模板（线 A `--jinja` 实际使用的）vs HF 侧模板（本门渲染训练数据用的）显式 diff**——两侧漂移是雷区"chat template 不一致→静默崩坏"的另一种触发形态，评测侧与训练侧必须同源 |

**产出**：七门漏斗表 → `data/data_card.md`；`data/mix.yaml`（带 provenance）；去污染声明表；**sha256 manifest**。M0 只要求管线跑通 + 漏斗表齐，正式训练 mix 在 M1 开工前定稿即可。

---

## 6. 线 B · 板端 E4B W8A8 转换 smoke（与线 A/C 并行，拆单点风险）〔事实/雷区〕

**目的**：蓝图把这步从 M2 提到 M0，唯一理由是拆单点风险——Gemma4→RKLLM 有 `[PAD]` 乱码先例（Issue #424，补遗 §7.1）。本步用官方权重转，不涉及微调模型，只验证"E4B 能不能干净转成 W8A8 并输出正常文本"。成败都记录，失败不阻塞线 A/C。

**〔事实〕前提（W0 已就位）**：板端旧 v1.2.x 已移除；RKLLM runtime 1.3.0 + RKNPU driver 0.9.8（未升内核）；官方 `llm_demo` 板上原生构建并成功 init 既有 .rkllm 模型——**这证明用户态升级可用，不等于 Gemma4 转换验收**（W0 事实版原文口径）。

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
- [ ] `metrics.py` + 基线四指标表（parser 错误率与 tools-API 准确率分列）
- [ ] 磁带首批 5–10 盘固化 + 最小 replayer 脚本
- [ ] 数据七门漏斗表齐 + 去污染声明表 + mix.yaml（带 provenance）+ **sha256 manifest**
- [ ] 板端转换 smoke 有结论（成败皆记录）

**最小可交付**（进度崩了保什么）：`eval_config.yaml` + 官方基线一行（系统列可留空+脚注） + 数据漏斗表。TB 链路/BFCL/replayer/板端 smoke 可顺延到 M1 头两天，但**基线数字和评测配置冻结没有顺延选项**——没有 before 就没有整个项目的 after。W0 缺口（checksum/第二介质等）默认已在 M0 内补齐（§0.5/门①）；仅进度崩溃时随本原则顺延并记入待办。

**M0 结束状态声明**（写进 `docs/m0_summary.md`）：
> 评测已可复现（`harbor run -c m0_baseline_job.yaml`，lock.json + eval_config 双快照）；官方 gemma-4-e4b-it @Q4_K_M 的 TB2.1 子集成功率/parser 格式错误率/BFCL 工具调用准确率/GSM8K/MMLU/HumanEval/TTFT/TPOT 已入主表 before 行；摘要方案=___、上下文协议=___；数据池七门跑通、去污染声明齐、sha256 manifest 齐、Fable 偏科已配平封顶；板端 E4B W8A8 转换 smoke 结论=___。M1 开工无未决分叉：`teich→E4B QLoRA(vGPU-32)→merge=S → OPD polish(teacher=gemma-4-31b-it FP8 @Pro 6000 96GB)=S.O=M1 → PTQ 谱系 → 同一 job.yaml 重跑 → A/C 对照表 v1`。

---

## 8. 三线并行排布建议〔建议，R1 更新〕

| 日 | 线 A（评测） | 线 C（数据，独立 venv） | 线 B（板端） |
|---|---|---|---|
| D1 | **git init + config 骨架** + 端点钉参 + 读 KV 实测行 | 门①完整性 + **sha256 manifest + 第二介质备份** + 门②去重启动 | 转换 toolkit 装 + 官方权重转 |
| D2 | TB hello-world→1题探测 + **摘要方案定案** + **MMLU 抽样清单冻结** | 门③安全 + 门④结构 | 板上加载 + 乱码判定 |
| D3 | 选题20 + **job.yaml 成稿** + 镜像预拉 | 门⑤去污染（HumanEval 优先，MMLU 按清单） | （smoke 结论留档）|
| D4–5 | 官方基线慢档（`harbor run -c`，挂后台；中断用 `jobs resume`） | 门⑥配平 + 门⑦渲染掩码（含**模板 diff**） | — |
| D6 | 快档 BFCL/lm-eval + metrics.py | 漏斗表 + 数据卡 + mix.yaml | — |
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
