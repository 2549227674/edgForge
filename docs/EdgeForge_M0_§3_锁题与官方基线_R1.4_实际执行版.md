# EdgeForge M0 §3：线 A · 锁题 + 镜像预拉 + 官方基线（R1.4 实际执行版）

> 状态：**已完成（2026-08-05）**。本文件保留执行前定案要求，并在相应小节补入实际结果；§10 已按更新后的精确边界完成校验、暂存与提交。
> 前置：§1 端点钉参已完成；§2 已过门——`terminal-bench/kv-store-grpc` 四段齐，`probe_link_closed=true`，`parser_name=json` / `max_turns=30` / 超时政策已冻结入 `eval_config.yaml`，`results/m0_tb_probe/2026-08-02__16-31-43/lock.json` 在库。端点在 §2 归档后已停止。
> 本节目标：**锁定 20 题清单 + 跑出官方 E4B 基线（主表第一行）**，同时把快档四件与磁带/replayer 落地。
> 原卡 §3 的四处过时点已在本版更正，差异清单见文末附录。

---

## 0. 本轮定案与边界

### 0.1 已锁项〔事实，本轮拍板〕

| 项 | 定案值 | 依据 |
|---|---|---|
| 单轮上限 | **32768**（重启端点生效） | 与 Pi 全局模型配置对齐；4096 在 §2 实测中 0/7 触顶，非绑定量 |
| per-turn 分布 | **不重测**，沿用 §2 的 p50=465 / p95=895 | 分布是模型属性而非上限产物；需补声明与证伪计数器（0.2） |
| `max_turns` | **30**（不变） | `900 / 19.07(p95) = 47.2`，30 为更低的预声明护栏 |
| agent setup | **预热镜像**，把 tmux/asciinema 烤进任务镜像 | §2 实测：harness 每 trial 在容器内安装，`docker pull` 覆盖不到 |
| 重试 | `max_retries=2`；模型侧失败留 `exclude_exceptions` 不重试 | 基础设施抖动重跑、模型失败如实计分（facts 6.2） |
| `max_format_errors` | **从 job.yaml 删除** | Harbor 0.18.0 terminus-2 无此实现，传入是伪参数 |
| 换题轮数 | **≤2 轮封顶** | 防以结果为条件的无界选择 |
| parser 指标 | **拆两列**：硬解析错误 + 软格式警告 | §2 实测硬错误为 0，软警告非 0，单列会塌成地板 |
| 磁带 | `traces/tapes/` 入库；原始 trajectory 本地 + sha256 manifest 入库 | 仓库即交接包 vs `/results/` 整体忽略的折中 |
| `n_concurrent` | **1**（不变） | 见 0.3 |
| 官方 QAT 锚 | **串行起服**，不与 B0 并存 | B0 加载后仅剩 2364 MiB |

### 0.2 32768 不重跑的可审计声明与证伪条件〔事实/纪律〕

`eval_config.yaml` 中的 `per_turn_tokens_p50/p95`、`per_turn_wallclock_s_p50/p95` 与由此推出的 `max_turns=30`，均取自 4096 上限下的探测。抬到 32768 后不重测，理由是**该上限从未生效**：7 轮中 0 次触顶，单轮最大 952 token，p95 仅 895——分布描述的是模型行为，不是上限的产物。

但尾部风险确实变了：单轮最坏值由 `4096 ÷ 52.8 ≈ 77.6 s` 变为 `32768 ÷ 49.2 ≈ 666 s`，一个失控轮次可吃掉 900 s agent 预算的四分之三，而 `max_turns` 拦轮数不拦单轮长度。

因此补两样，均零成本：

**① 声明入 `eval_config.yaml`**（让"不重跑"成为有依据的决定而非省事）：

```yaml
terminal_bench:
  per_turn_distribution_note: >-
    p50/p95 measured under a non-binding 4096 cap (0/7 turns reached it;
    max observed 952 tokens). The distribution is a model property, not a
    cap artifact, so it is not re-measured after raising n_predict to 32768.
    Falsifier: any finish_reason=length observed at 32768 invalidates this
    claim and requires re-deriving max_turns.
```

**② 基线运行期间数 `finish_reason=length`**——它是上面那句话的证伪条件。出现一次即：该 trial 单独标记、不混进平均、在 `m0_summary` 记录，并重新推导 `max_turns`。

**失败四分类**（`metrics.py` 与主表脚注都按此口径，不得合并）：

| 码 | 含义 | 处置 |
|---|---|---|
| F1 | verifier reward=0，模型做错 | 计入成功率分母与分子 |
| F2 | 轮数耗尽（`max_turns=30` 触顶） | 计为失败（`turn_exhaustion_policy: fail`） |
| F3 | agent timeout（900 s 触顶） | 计为失败（`agent_timeout_policy: task_defined_default`） |
| F4 | 基础设施（setup 失败 / 网络 / 容器） | **重跑，不计分**；逐条记录（facts 6.2） |
| L | 出现 `finish_reason=length` 的轮次数 | 非失败类，是 0.2 声明的证伪信号 |

不拆这四类，§4 归因时分不清"模型不会做"与"一个轮次跑飞把预算烧光了"。

### 0.3 `n_concurrent` 保持 1〔纪律，防后续手痒〕

B0 加载后仍余 2364 MiB，q8_0 KV 理论上可容约三槽——但并发不做，三条独立理由：

1. llama.cpp 的 `-c` 是**总量按槽平分**：N 个 131072 槽需 `-c = 131072 × N`；`-c 131072 --parallel N` 只给每槽 `131072/N`，直接破坏冻结的上下文协议。
2. 并发改变 TTFT/TPOT 口径，主表系统指标列失去可比性。
3. 网络纪律（facts 6.2）：串行 + 预拉是把下载抖动与模型分数解耦的前提。

### 0.4 本节不做〔边界〕

- 不跑官方 QAT 锚的慢档（TB 20×5）——定于 M6 三点对照同场（R1.2 拒绝项留档）。
- 不做 tau2-bench（E3 选型附注，理由不复议）。
- 不因官方 QAT 锚或任何其他模型的分数回头换题（R1.2）。
- §2 的探测题 `kv-store-grpc` 的成败**不进入选题判据**；该题可以出现在 20 题清单中，但仅按 3.1 的判据评估，不因"探测跑过"而优先或排除。

---

## 1. 端点重启（32768 生效）

§2 结束时服务已停，本次重启免费。与 §2 的唯一差异是 `-n`。

```bash
third_party/llama.cpp/build/bin/llama-server \
  -m models/gguf/gemma4-e4b-it-Q4_K_M.gguf \
  --alias gemma4-e4b \
  -ngl 99 \
  -c 131072 \
  --parallel 1 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --jinja \
  --reasoning-format auto \
  --temp 1.0 \
  --top-p 0.95 \
  --top-k 64 \
  --min-p 0 \
  --seed -1 \
  -n 32768 \
  --port 8080 \
  2>&1 | tee logs/m0/llama_server_baseline_c131072_q8_n32768.log
```

起服后三条防呆（同 §2 口径）：

```bash
curl -s http://localhost:8080/props | rg 'ignore_eos'          # 必须 false
grep -E 'llama_kv_cache: size' logs/m0/llama_server_baseline_c131072_q8_n32768.log
grep -A3 'sampler params' logs/m0/llama_server_baseline_c131072_q8_n32768.log | head -20
```

KV 两段仍应为 non-SWA 1088.00 + SWA 21.25 = **1109.25 MiB**；`min_p` 应为 0.000。与 `eval_config.yaml` 冲突时以实测为准并回改配置。

**本次基线全程（3.1 sanity + 3.2 慢档 + 3.3 快档）使用同一个端点进程，中途不重启**——重启会清空 prompt cache，改变 `ttft_convention: cache_warm` 的口径一致性。若不得不重启，记录重启点与影响的 trial 编号。

---

## 2. 开跑前的两项五分钟核验〔阻塞项〕

这两项都是"跑完 100 试验才发现就得重跑"的类型，必须在 3.2 之前做完。

### 2.1 trajectory 是否持久化 `reasoning_content`

`logs/m0/reasoning_format_check.json` 的实测：

```text
usage.completion_tokens = 217
content            = {"command": "ls -la"}      （约 10 token）
reasoning_content  = 约 200 token 的思考文本
```

**`usage` 不分列**，thinking 与 answer 混在一个数里。§4 那条"每任务 token 拆 thinking / answer / tool 三列"的待办，唯一取数路径是 trajectory 里的 `reasoning_content` 字段。

```bash
# 翻 §2 已有产物即可，零成本
rg -l 'reasoning_content' results/m0_tb_probe/2026-08-02__16-31-43/kv-store-grpc__7FvkxNN/
```

- **有** → 无需额外动作，`replayer.trajectory_*` 相关字段照实回填。
- **无** → 基线运行期间**同时开 server 侧请求录制**（`--log-file` + 提高 verbosity，或反向代理落盘请求/响应体），把这段补上。录制文件出 sha256 manifest，原始体积大不入库。

### 2.2 setup 超时抛的异常类名

`results/m0_tb_probe/2026-08-02__16-31-43/lock.json` 显示当前 `retry.max_retries = 0`，且 `exclude_exceptions` 含 `AgentTimeoutError`（即"不重试"）。本节要把 `max_retries` 设为 2，供基础设施类异常使用。

风险：若 agent **setup** 超时抛的也是 `AgentTimeoutError`，那它会与"模型侧 agent 超时"共用一个类名——放进 exclude 则 setup 失败不重试，拿出来则模型超时被重试（污染成功率）。

```bash
# 从 §2 第一次失败的运行里取异常类名（该目录未入库，本地仍在）
rg -i 'timeout|exception|error' results/m0_tb_probe/2026-08-02__16-28-28/ | head -30
```

- **两者异常类不同** → 按 3.2 的 retry 配置直接走。
- **同一个类名** → **不拆 exclude 列表**，改为完全依赖 §3 的预热镜像消除 setup 超时；`AgentTimeoutError` 保持不重试。这是首选解，因为它把问题从"重试掩盖"变成"根除"。

---

## 3. 镜像预拉 + 预热〔本节新增，原卡缺口〕

**原卡的缺口**：`docker pull` 只覆盖容器镜像本体。§2 实测到 harness 自己会在**容器起来之后**下载——terminus-2 的 agent setup 在每个任务容器内安装 `tmux`/`asciinema`（默认 120 s 窗口不够，靠 `agent_setup_timeout_multiplier=3.0` 才过）；示例任务的 verifier 还会临时取 `uv` 与 pytest。

100 试验 = 100 次安装。按 facts 6.2，网络抖动不得解释为模型失败，但一次 setup 超时在结果里就是一个 trial 失败。

### 3.1 预拉

```bash
# 20 题镜像全部预拉（清单来自 §4 锁题）
while read -r img; do docker pull "$img"; done < results/m0_task_images.txt
docker images --digests | tee logs/m0/m0_sanity_candidate_base_image_digests.tsv
```

镜像 digest 入库，作为"同一批镜像"的可审计证据（任务本体的 digest 另由 lock.json 的 `task.digest` 记录，§2 探测已见 `sha256:973c5d4c…`）。

### 3.2 预热〔建议，实现方式以当日 harbor 机制为准〕

目标：把 tmux/asciinema 从"每 trial 装一次"挪到"一次性"。两条路线，取当日可行者：

- **路线 A**：在任务镜像上叠一层装好 tmux/asciinema，本地重 tag，令 harbor 使用（`environment.force_build` / `extra_docker_compose` 等字段是入口，字段名以当日文档为准）。
- **路线 B（退路）**：本地 apt/pip 缓存或镜像源，把每次安装从公网变成局域网，不改镜像。

**验收门**：预热后跑 **2 题 × 1 次**，记录 agent setup 耗时；**p95 setup < 60 s** 视为解决，否则回到路线选择而不是继续加大 `agent_setup_timeout_multiplier`。

`agent_setup_timeout_multiplier=3.0` 仍保留在 job 配置中作兜底，但它是护栏不是方案。

### 3.3 用 allowed_hosts 把"运行期外网依赖"变成可检出〔建议〕

lock.json 里存在 `extra_allowed_hosts` 字段（agent 与 environment 两级，探测时均为 `[]`）。这给了原卡判据 R1/D17（"运行期不依赖外网下载"）一个**可执行的检测手段**，而不是靠读 task 描述猜：

预热完成后，对候选题在收紧的 allowlist 下各跑 1 次——需要运行期下载的任务会**确定性失败**而不是概率性抖动，据此把它们从 20 题清单里剔除。这一步的结果只用于选题判据，不计入任何分数。

---

## 4. 锁题（原 3.1，判据与流程更新）

### 4.1 手筛 20 题〔建议，`[未复核]` 20 这个数〕

列 TB 2.1 全部 89 任务，按判据手筛 20 个：

1. 不需要 GPU；
2. 单容器不过大；
3. 本地几分钟级可完成——**现在有实测口径**：§2 探测的中等题（`kv-store-grpc`，专家估时 15 min）单 trial 墙钟 **110.90 s**（agent 81.65 s + 环境/verifier/收尾 29.25 s），以此为量级参照；
4. **运行期不依赖外网下载**——用 §3.3 的 allowlist 检测替代主观判断，或其 pip/apt 依赖可并入预热；
5. 参考 TB 官方 empirical difficulty，优先 Easy/Medium。

### 4.2 可测区间 sanity + 换题上限〔纪律，本版收紧〕

**显式目标（E1）**：让官方 E4B 基线落在子集成功率 **15–30%** 一带。官方发布图 E4B @TB2 全集仅 ≈2.2%（前代 0.0%），随机取题会让成功率贴地板、before/after 在该列失效。

流程：

1. 手筛 20 题后，**仅由 B0-PTQ-Q4KM（基线本尊）** 对其中 3–5 题各跑 1 次做量级 sanity（半小时级）。
2. 明显 <10% → 换更容易的题，重跑 sanity。
3. **最多 2 轮换题。第 2 轮后无论落在哪个区间一律锁定**，成功率列如实记录，不硬拗；测量重心按 §7 移到高功效指标。

**为什么要封顶**：无界迭代"换到基线落进 15–30%"本身就是一个以结果为条件的选择过程，时间上也可能吃掉整个 D3。封顶后代价是明确且有限的——该数字不可与官方 2.2% 横向比较（本来就不可比，它是子集），而 before/after 的纵向有效性不受影响（同一固定子集）。这一句要写进 `m0_summary`。

**锁定后不改**：不因官方 QAT 锚或任何其他模型的分数回头换题（R1.2）。

### 4.3 锁定动作

1. 20 个 task 写进 `m0_baseline_job.yaml`（取代"手抄 ID 进 eval_config"）；
2. `eval_config.terminal_bench.task_manifest` 挂 job.yaml 指针；
3. 挑 **2 个实测 trial wallclock 最短**的标为烟测对（`smoke_pair`）——用 sanity 阶段量到的真实墙钟，不靠目测。

---

## 5. 官方 E4B 基线（原 3.2，before 列 / 主表第一行）〔事实〕

冻结载体用 harbor 原生机制：job 是 YAML，`harbor run -c <yaml>` 运行，解析后的 JobConfig 持久化为 job 目录内 **lock.json**。`eval_config.yaml` 挂其指针即可。

### 5.1 `m0_baseline_job.yaml`（骨架，字段名以当日 harbor 文档为准）

```yaml
job_name: baseline_e4b_q4km
jobs_dir: results/
n_attempts: 5
n_concurrent_trials: 1          # 串行，网络纪律，见 0.3

retry:
  max_retries: 2                # 供基础设施类异常；见 0.1 与 §2.2
  exclude_exceptions:           # 列内异常不重试 = 模型侧失败如实计分
    - AgentTimeoutError
    - VerifierTimeoutError
    - RewardFileEmptyError
    - RewardFileNotFoundError
    - ApiUsageLimitError
    - VerifierOutputParseError

# dataset: terminal-bench/terminal-bench-2-1 + §4 锁定的 20 个 task 显式清单
timeout_multiplier: 1.0
agent_setup_timeout_multiplier: 3.0   # 护栏；方案是 §3 的预热镜像

agent:
  name: terminus-2
  model_name: openai/gemma4-e4b        # LiteLLM provider 选择器，后端为 llama.cpp
  kwargs:
    api_base: http://localhost:8080/v1
    temperature: 1.0
    max_turns: 30
    parser_name: json
    enable_summarize: false
    # max_format_errors 已删除：Harbor 0.18.0 terminus-2 无此实现，
    # 传入只会被 **kwargs 静默接收并写进 lock.json，误导后续复现者。

verifier:
  disable: false
```

**`model_name` 用 `openai/` 而非 `hosted_vllm/`**：§2 实测 Harbor 0.18.0 对 `hosted_vllm/` 强制要求非空 `model_info`，与冻结的 `model_info=null` 冲突。两种前缀都只描述 OpenAI 兼容协议形状，**后端是 llama.cpp `llama-server`，不是 vLLM**——报告与面试口径一律如此。运行时需 `OPENAI_API_KEY=not-needed` 满足 LiteLLM 客户端校验，llama.cpp 端点不校验该值。

### 5.2 运行

```bash
OPENAI_API_KEY=not-needed harbor run -c m0_baseline_job.yaml      # 20 题 × k=5 × 串行

# 中断后续跑（按 trial 配置识别已完成试验，只补未完成的）
OPENAI_API_KEY=not-needed harbor jobs resume -p results/baseline_e4b_q4km/
```

### 5.3 墙钟预算〔实测推算，原卡"1–2 天，主要是等"的量化版〕

| 情形 | 单 trial | 100 试验串行 |
|---|---:|---:|
| 乐观（贴近 §2 探测：7 轮） | ~111 s | **~3.1 h** |
| 典型（15 轮 × p50 9.43 s + 开销） | ~200 s | **~5.6 h** |
| 悲观（30 轮 × p95 19.07 s + 开销） | ~600 s | **~16.7 h** |

D4–D5 装得下。**方差主要来自 agent setup**：§2 探测那次 110.90 s 很可能未含冷启安装（第一次尝试即在 120 s setup 窗口超时，第二次成功距其仅 3 分 15 秒，apt/layer 缓存已热）。§3 的预热验收门（setup p95 < 60 s）就是把这个方差压住的手段；预热未达标时按悲观档排期。

### 5.4 预期量级与产出纪律

台账"小模型 TB ~15%"是通用小模型锚；官方发布图给出 E4B @TB2 全集 ≈2.2%——不做 §4.2 的可测区间控制，100 试验可能只有 0–2 个成功。目标：子集基线落在 15–30%（对应 100 试验 15–30 个成功，SE≈3.5–4.6pp；聚簇修正见 §7）。

**所有 session/trajectory 文件保留，不删**（快档指标来源 + 磁带素材 + kernel shape 采样源）。留存与入库规则见 §8。

**运行期同时记录**（零额外成本，从 trajectory 取）：

- 每题**峰值上下文占用**（§2 探测单题为 5,770 tokens）——决定 M2 板端 `max_context_len` 与 §8 磁带上下文档位；
- **失败四分类计数**（F1/F2/F3/F4）与 **`finish_reason=length` 轮次数**（0.2 证伪信号）；
- 每轮 `usage` 与 `prompt_tokens_details.cached_tokens`（cache 命中率，支撑 `ttft_convention: cache_warm` 的可审计性）。

---

## 6. 快档基线（原 3.3）

### 6.1 BFCL 工具调用准确率〔网核〕

- `pip install bfcl-eval`（勿混淆 PyPI 上无关的 `bfcl` 包；CalVer 锁版记进 config）。
- **必须设 `BFCL_PROJECT_ROOT`**（结果/配置存放位置，`.env` 在 `$BFCL_PROJECT_ROOT/.env` 下查找）——不设则结果埋进 site-packages。
- 本地端点：`--skip-server-setup` + `.env` 里 `REMOTE_OPENAI_BASE_URL=http://localhost:8080/v1`（+ dummy `REMOTE_OPENAI_API_KEY`，社区有 401 先例）。
- **模型名按 BFCL 支持列表对好 handler**（`[未复核]`，与 category 清单一并锁定并写进 `eval_config.bfcl`）。
- `--test-category` 选非 live 子集起步（单轮 AST 评分，分钟级，量化退化金丝雀）。
- **校准锚（E2）**：官方 E4B @BFCL ≈66.6%。量级严重偏离时**先怀疑 handler/模板配置而非模型**。该值已在 `eval_config.external_anchors.bfcl` 登记。

BFCL 走 OpenAI `tools` 字段，与 terminus-2 的纯文本解析是**两套机制**——这也是 §7 里两列不得混用的原因。

### 6.2 lm-eval〔网核，本版补两个新雷〕

钉版本（commit + task 版本）。任务→端点映射不可自由选：

- **MMLU（loglikelihood/MCQ）只能走 `local-completions`**——chat-completion 端点不支持 loglikelihood 类任务；`base_url` 写全路径 `http://localhost:8080/v1/completions`，指定 tokenizer（loglikelihood 必需），instruct 模型加 `--apply_chat_template`。
- GSM8K / HumanEval（生成式）：`local-chat-completions` 指 `.../v1/chat/completions`。
- **HumanEval 需显式 `--confirm_run_unsafe_code`**。
- `num_concurrent=1` 与 server `--parallel 1` 匹配。

**〔新雷一，本版新增〕`max_gen_toks` 是比 `max_length` 更早触发的坑**：GSM8K 等生成式任务的默认 `max_gen_toks` 仅 **256**。thinking 已确认开启且**思考量占压倒多数**（`reasoning_format_check.json`：一道 12+30 的题就产出 217 completion tokens，其中约 200 是 `reasoning_content`），256 会在思考中途截断，`content` 直接为空 → 分数塌到 0，而现象长得像"模型不会做数学题"。**显式调大（起步 4096）并记入 config**；`max_length` 默认 2048 同样显式调大并与 `-c` 对齐。

**〔新雷二〕MMLU 走 `local-completions` 依赖 llama.cpp 的 `echo` + `logprobs` 支持**，这是已知薄弱点。**先跑 5 题冒烟**确认能出 loglikelihood，再投 500–1000 题全量——不要在锁定抽样清单后才发现端点出不了数。

**实际执行补记（2026-08-04）**：当前锁定的 llama.cpp `/v1/completions` 只返回生成 token 的 logprobs，不返回 `echo` prompt 的 `token_logprobs`；lm-eval 0.4.9.1 的模板路径另有 `JsonChatStr.rstrip()` 兼容错误。因此补入 `scripts/llama_loglikelihood.cpp` + `scripts/edgeforge_llamacpp_loglikelihood.py` 兼容层：仍由 lm-eval 构造聊天模板、5-shot MCQ 与四个 continuation，兼容层直接从**同一 Q4_K_M GGUF、同一 llama.cpp commit、同一 131072/Q8 KV/CUDA 配置**读取 continuation-token logits，不改成生成式判题。显式 `--num_fewshot 5 --limit 5 --apply_chat_template` 的冒烟已完成，`college_mathematics` 为 1/5；该值只标为协议冒烟，不是正式基线。日志、结果及源码/二进制哈希登记在 `eval_config.yaml` 与 `results/baseline_lmeval.json`。

**HumanEval 同日补记**：`code_eval` 的 `multiprocessing.Manager` 失败不是 WSL 本体限制，而是 Python 临时目录落在 `/mnt/c/.../AppData/Local/Temp`，该挂载点不支持所需 AF_UNIX socket。将 `TMPDIR/TMP/TEMP` 固定为原生 Linux `/tmp` 后，官方执行器正常完成 5 题，`pass@1=0/5`；这是有效模型分数，不再标为基础设施阻塞。

**依赖执行记录（2026-08-04）**：已冻结 `manifests/mmlu_fast_500.json`（`cais/mmlu@c30699…`，500 题、57 学科分层）及 `manifests/gsm8k_fast_200.json`（`openai/gsm8k@740312…`，200 题固定随机抽样），清单及生成器哈希在 `manifests/lm_eval_fast_manifests.sha256`。此前 5 题冒烟已暴露的 MMLU `college_mathematics` 0–4 与 GSM8K 0–4 均排除，防止冒烟反馈进入正式快档。门⑤去污染应按这两个清单扫描。

**正式快档执行记录（2026-08-04）**：MMLU 冻结 500 题已完成，覆盖 57 个学科、5-shot、聊天模板和四个选项的 continuation-token loglikelihood，`acc=0.598`、`stderr=0.0200326`；结果为 `results/lmeval/mmlu_fast_500_llamacpp_logits/models__gemma-4-E4B-it/results_2026-08-04T22-26-56.630433.json`（SHA-256 `c710eb8c…`）。GSM8K 冻结 200 题已完成，5-shot、聊天模板、温度 0、`max_gen_toks=4096`、单并发，严格精确匹配 `0.840±0.0259880`，宽松提取 `0.845±0.0256547`；结果为 `results/lmeval/gsm8k_fast_200/gemma4-e4b/results_2026-08-04T23-11-46.389008.json`（SHA-256 `39c18793…`）。完整哈希、样本文件、运行日志和模型/评分器版本均登记在 `eval_config.yaml` 与 `results/baseline_lmeval.json`；MMLU/GSM8K 的 5 题结果保留为 smoke，不混入正式分快档。

**thinking 的一个正面副作用**：`--reasoning-format auto` 把思考剥进 `reasoning_content`，lm-eval 读 `content` 拿到的是干净答案，正则抽取不受思考文本干扰。这是 §2 定案的顺带收益，值得记进报告。

### 6.3 官方 QAT-Q4_0 锚快档（零下载，约 1–2 h）〔R1.2〕

**必须串行起服**：B0 加载后 GPU 仅余 **2364 MiB**，两个端点不可能并存。顺序是——停 B0 → 起锚（`--alias gemma4-e4b-qat-q4_0`，模型 `models/gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B_q4_0-it.gguf`，sha256 已在 `external_anchors` 登记）→ 跑四件 → 停 → 回 B0。

协议参数（题单/采样/上下文/模板/agent kwargs/单轮上限 32768）与基线**完全一致**，仅 alias 与模型文件不同。

四件：① endpoint smoke（`/v1/models` + tools 请求）；② BFCL 同 category 子集；③ GSM8K 快抽样；④ §8 磁带回放取系统指标。

结果入 `results/anchor_official_qat_q4_0/`，登记进 `eval_config.external_anchors`（**非主表 before 行**，`training_lineage: google_official_qat` 分列标注）。

**慢档（TB 20×5）明确不在 M0 跑**——定于 M6 三点对照时与"我的 QAT Q4_0""我的 PTQ Q4_0"同场同鲜落成。

**实际执行记录（2026-08-05）**：官方 `gemma-4-E4B_q4_0-it.gguf` 的 SHA-256 已核对为 `676c3507…`，以与 B0 相同的 131072 上下文、Q8 K/V、单并发、模板、采样默认值和 32768 单轮上限串行启动。端点 smoke 通过：`/v1/models` 返回 `gemma4-e4b-qat-q4_0`，聊天探针返回 `OK`，原生 tools 探针产生有效 `get_weather({"city":"Beijing"})` 调用。BFCL `simple_python` 同类子集为 **364/400 = 91.00%**（B0 同一子集 363/400 = 90.75%，差值仅作同协议观察）；GSM8K 冻结 200 题为严格精确匹配 **0.850±0.0253121**、宽松提取 **0.865±0.0242241**。从 B0 真实 trajectory 冻结的 5 盘磁带（11 请求/遍）均连续回放两遍，第二遍 cache-warm 11/11 成功，TTFT p50/p95 为 **377.423/848.977 ms**，TPOT p50 为 **19.161 ms/token**（吞吐 p50 **52.188 tok/s**）。原始结果、样本、响应、日志和哈希均登记在 `eval_config.external_anchors.official_qat_q4_0.fast_gate_results`。QAT 完成后已停止；B0 `gemma4-e4b` 已作为用户级 systemd 瞬态服务 `edgeforge-b0.service` 恢复常驻，独立恢复日志为 `logs/m0/llama_server_baseline_systemd_2026-08-05.log`，并已以 health、`/v1/models` 与 `OK` 探针复核。

### 6.4 选型附注：tau2-bench 已考虑未选〔E3〕

官方发布图另一半（Tau2 Retail/Airline/Telecom）不入本项目：① 需模拟用户 LLM 在环，引入 API 成本 + 一个**无法冻结的评测组件**（模拟器换版本分数即漂，与全程冻结协议直接冲突）；② 客服对话域与终端 agent 部署叙事不贴。建议同步进蓝图 §1 决策表。

另注：发布图 "TB2 (Agents)" 的括号是能力类别标注，非官方子集——TB 2.1 无 agents 子集，只有任务级难度/类别元数据（即 §4.1 选题所用维度）。

---

## 7. parser 指标拆两列〔本版新增，喂 §4 metrics.py〕

§2 实测暴露的问题：hello-world json 运行 **0 个 parser 拒绝**，TB probe 7 轮 **0 个 parser `ERROR`**。而 E2 把"terminus parser 格式错误率"升格为主要测量手段之一，正是因为成功率列信噪比太低——这列现在有塌成第二个地板的风险。

可救的信号是 §2 记录到的**软层**：hello-world 里有 4 条"JSON 对象前/后额外文本"warning，被 parser 容忍但确实是格式不洁，且**非 0**。

因此指标定义为两列，`metrics.py` 分别输出、不得合并：

| 列 | 定义 | 来源 |
|---|---|---|
| **硬解析错误率** | parser 拒绝该轮回复（`ERROR` / `Previous response had parsing errors`） | trajectory |
| **软格式警告率** | 回复可解析但 JSON 对象前后夹带额外文本 | trajectory warning |

两列都从基线 trajectory 数——这决定了 §5 跑完后 trajectory 必须保留哪些字段（见 §8）。

**（提醒）** 这两列与 BFCL 的 tools-API 准确率是**三种不同机制**，M1 归因时不得混用：terminus 走纯文本解析（单工具 tmux），BFCL 走 OpenAI `tools` 字段。

**实际执行记录（2026-08-05）**：已新增根目录 `metrics.py`，只读取 ATIF trajectory 中 Terminus 写入的 parser feedback（不扫描任意终端输出中的 `ERROR`，避免误计）。完整 B0 基线的 100 条 trajectory 共含 **836** 个 `source=agent` 响应：硬解析错误为 **149/836 = 17.823%**；软格式警告为 **498/836 = 59.569%**。软列仅计“parser 接受、但 JSON 对象前/后有额外文本”的响应；另有 125 个硬拒绝响应也带这类 warning，明确排除在软列外，故两列不可相加。结果在 `results/baseline_e4b_q4km/parser_metrics.json`（SHA-256 `4903c43d…`），脚本 SHA-256 `1e3d19bb…`；两者及分母、重叠计数均已登记在 `eval_config.yaml` 的 `metrics`。Harbor 的 invalid-JSON 金样例也已校验为“1 个硬拒绝、0 个软警告”。

---

## 8. 磁带首批固化 + 最小 replayer（原 3.4）

### 8.1 磁带

- 从 §5 的 trajectory 里挑 **5–10 条**固化成 replay 磁带（含 repeated-prefix 场景；上下文档位由基线跑出的真实分布确定——§2 单题峰值 5,770 tokens 只是起点参照）。
- **磁带唯一来源 = B0-PTQ-Q4KM 的轨迹（R1.2）**：固化一次后，同一批磁带回放所有模型（含官方 QAT 锚与后续全部 candidate），不得按各模型自己的成功轨迹分别选带——负载定死，模型文件才是唯一变量。
- **保真度（B8，R1.3 已消解）**：`enable_summarize=false`，轨迹天然线性，不依赖 `linear_history` / `raw_content` 透传。

### 8.2 入库规则〔本版新增，解 `/results/` 整体忽略与"仓库即交接包"的冲突〕

`.gitignore` 现在整体忽略 `/results/`，只靠 `git add -f` 提交挑选的 `lock.json`。磁带必须可审计，故分层：

| 物件 | 处置 |
|---|---|
| `traces/tapes/` 选定的 5–10 盘磁带 | **入库**（体积小，是冻结件） |
| 原始 trajectory / session 文件 | 本地保留不删；**出 `traces/trajectories_sha256.txt` manifest 入库** |
| server 侧录制（若 §2.1 触发） | 同上，manifest 入库，原始体积大不入库 |
| `results/baseline_e4b_q4km/lock.json` | `git add -f` 入库 |

**实际执行记录（2026-08-05）**：已逐项校验 5 盘 `traces/tapes/` 冻结件（合计 11 请求/遍）及其 `source_trajectory_sha256`；每盘 tape 哈希均与其本地 B0 原始 trajectory 一致。`traces/trajectories_sha256.txt` 已扩展为**完整 100 条**保留的 B0 ATIF trajectory 哈希（其中 5 条为磁带源），而非只列磁带源；`traces/tapes/manifest.json` 同时声明该完整 manifest 的路径和条目数。`traces/` 不受 `.gitignore` 影响，供 §10 统一暂存；原始 trajectory 仍在 `results/baseline_e4b_q4km/` 本地保留且按规则忽略，不复制入仓库。§2.1 已实证 Terminus trajectory 可持久化 `reasoning_content`，故未触发 server 侧请求录制；全量基线的 836 个 agent 响应中 711 个有该字段。缺失的 125 个**并非**硬 parser-error 响应——与 149 个硬错误的交集仅 14，其余 111 个落在 parser 接受的响应上。该缺失是模型行为（无思考的被接受响应 completion 中位数 110，有思考的 677），非日志缺陷；详见 §4 与 `agent_metrics.json`。交接状态与两份 manifest 的 SHA-256 已登记在 `eval_config.yaml.replayer`；实际 `git add` / `git add -f lock.json` 留待 §10，避免提前改变 index。

### 8.3 最小 replayer〔C9〕

读磁带逐条重发请求，记 TTFT / TPOT / 总吞吐；不做扫描矩阵，只对官方 E4B 跑一遍补齐主表第一行的系统指标列。

**实现上的便宜（§2 证据）**：llama.cpp 的响应里直接带 `timings` 块，不必靠外部墙钟计时——

```json
"timings": {"cache_n": 47, "prompt_n": 5, "prompt_ms": 320.202,
            "predicted_n": 217, "predicted_ms": 4411.707,
            "predicted_per_second": 49.187}
```

`prompt_ms` → TTFT；`predicted_per_second` → TPOT/吞吐；`cache_n` 与 `prompt_tokens_details.cached_tokens` → cache 命中量。三者一并记录，否则 `cache_warm` 口径不可审计。

**〔纪律〕回放的 cache 状态必须一致**：prompt cache 保持开启（真实部署形态），因此每盘磁带**连续回放两遍、取第二遍**，并声明为 cache-warm；否则首遍冷、次遍热，TTFT 不可比。该规则对所有模型一视同仁。

**实际执行记录（2026-08-05）**：B0 `gemma4-e4b` 使用同一 5 盘磁带从零完整回放 **22/22 成功**，第二遍 cache-warm **11/11 成功**。主表系统列冻结为：TTFT p50/p95 **349.459/1762.491 ms**，吞吐 p50 **52.029 tok/s**，TPOT p50 **19.220 ms/token**，`cache_n` p50 **996**。正式输出是 `results/baseline_e4b_q4km/replayer/{records.jsonl,summary.json}`，SHA-256 分别为 `46457b6b…` / `6ea8dfc9…`，日志为 `logs/m0/m0_baseline_replayer.log`（`f5b72e55…`）。一次前台会话中断留下的 17/22 记录仅本地审计，未进入统计或冻结集；正式值全部来自后续单进程完整重放。

**降级方案**：若进度崩，第一行系统列留空 + 主表脚注"M1 补测"，该决定写进 `m0_summary`。

---

## 9. eval_config 回填

```yaml
harbor:
  version: "0.18.0"                       # 由 lock.json 实证回填（原为 null）
  baseline_job: m0_baseline_job.yaml
  lock_json: results/baseline_e4b_q4km/lock.json

llama_cpp:
  n_predict_default: 32768                # 已重启生效，注释中的 "requires restart" 删除
  baseline_boot_log: logs/m0/llama_server_baseline_c131072_q8_n32768.log

sampling:
  server_n_predict: 32768

terminal_bench:
  agent_max_tokens: 32768
  max_format_errors: null                 # Harbor 0.18.0 无实现；已从 job.yaml 删除
  task_manifest: m0_baseline_job.yaml
  smoke_pair: [<最快两题>]
  per_turn_distribution_note: <见 0.2>
  finish_reason_length_turns: <实测；0 则 0.2 声明未被证伪>
  failure_breakdown:                      # 失败四分类，见 0.2
    f1_verifier_zero: <实测>
    f2_turn_exhausted: <实测>
    f3_agent_timeout: <实测>
    f4_infrastructure_rerun: <实测，不计分>
  task_selection_swap_rounds: <0/1/2>
  sanity_subset_success_rate: <实测>
  baseline_peak_context_tokens_p50: <实测>
  baseline_peak_context_tokens_p95: <实测>

metrics:
  parser_hard_error_rate: <实测>
  parser_soft_warning_rate: <实测>

lm_eval:
  version: <锁定>
  tasks:
    mmlu: {task_version: <锁定>, manifest: <D2 清单>, tokenizer: <锁定>, max_length: <显式调大>}
    gsm8k: {task_version: <锁定>, max_length: <显式调大>, max_gen_toks: 4096}
    humaneval: {task_version: <锁定>, max_length: <显式调大>, max_gen_toks: 4096}

bfcl:
  version: <CalVer 锁定>
  project_root: <BFCL_PROJECT_ROOT 实际路径>
  categories: [<锁定>]
  handler: <对照支持列表锁定>

replayer:
  tapes_manifest: traces/tapes/manifest.json
  trajectories_sha256: traces/trajectories_sha256.txt
  replay_cache_convention: second_pass_warm

external_anchors:
  official_qat_q4_0:
    fast_gate_results: results/anchor_official_qat_q4_0/
```

**不可虚填**：`<>` 内各项在对应步骤完成前保持 `null`。

**实际执行记录（2026-08-05）**：已用 `results/baseline_e4b_q4km/lock.json` 回填 Harbor **0.18.0**、job/lock 指针及 SHA-256。慢档 100 trial 的互斥失败分类为 F1 verifier-zero **92**、F2 30-turn 耗尽 **7**、F3 `AgentTimeoutError` **1**、F4 基础设施重跑 **0**，成功 **0/100**。最终 sanity 是 `results/m0_tb_sanity_round2` 的 5 题、**0/5**；目录名称与已锁 20 题清单表明仅发生 **1** 次换题轮，之后未再按分数换题。每 trial 取 trajectory 的最大 `prompt_tokens`，以 inclusive-linear 分位得到峰值上下文 p50 **6292.5**、p95 **22340.55** tokens。836 个 agent 响应的最大 completion 为 7428，小于冻结端点上限 32768，且 server log 的 1673 个 slot release 全为 `truncated = 0`，故 `finish_reason_length_turns=0`，0.2 声明未被证伪。§7 的硬/软 parser 两列、快档与 BFCL 已回填；§8.3 的 B0 replayer 也已以 22/22 完整运行回填结果、路径和哈希。`project.status` 冻结为 `frozen_with_declared_humaneval_gap`：HumanEval 只有官方执行器的 5 题有效 smoke，不冒充正式全量基线。无证据的 `source_revision`、imatrix provenance、模板对照等字段仍保持 `null`。

---

## 10. 产物入库

**实际审计结论（2026-08-05）**：原清单已经过时，不能原样执行。实际 job 目录是无时间戳的 `results/baseline_e4b_q4km/`；原列出的 `logs/m0/baseline_image_digests.txt` 并不存在，20 题镜像证据实际为 `logs/m0/m0_sanity_candidate_base_image_digests.tsv`，另有预热映射和原生 VM allowlist 核验表。§6–§9 还新增了 llama.cpp loglikelihood 兼容层、固定抽样 manifest、task YAML、parser 指标、B0/QAT replayer 与磁带交接件，均属于复现所需源码或小型冻结证据，必须一并入库。

入库边界保持“**源码/配置/小型冻结件进 Git，大型可再生数据和原始 trajectory 留本地并登记哈希**”：不提交 43 MiB 的 `results/baseline_e4b_q4km/` 全目录、不提交 lm-eval 大型 samples JSONL、不提交 5.3 GiB GGUF 和本地 parquet 数据缓存；这些对象已由 `eval_config.yaml`、结果摘要和 manifest 钉住来源或 SHA-256。中断的 17/22 B0 重放记录只作本地审计，不进入正式冻结集；正式集只接纳完整 22/22、第二遍 11/11 成功的输出。

**补充入库（2026-08-05）**：在首次冻结后复核到 B0 的 BFCL 原始输出/评分明细，以及 MMLU、GSM8K、HumanEval 在配置中明确指向的正式或有效 smoke 聚合结果 JSON；其中 BFCL 的两个 `.json` 是逐行 JSON（JSONL）记录。它们先前仅由 `results/baseline_bfcl.json`、`results/baseline_lmeval.json` 和 SHA-256 摘要定位。七个 JSON/JSONL 合计约 672 KiB，均非 samples JSONL；将其逐一强制入库，使远端可直接复核原生 harness 结果，仍不提交任何 samples、原始 trajectory 或 `results/bfcl/.env`。

实际暂存按下列五组精确执行，避免 `git add results/` 或 `git add data/` 把大文件误带入：

```bash
git add \
  eval_config.yaml \
  m0_baseline_job.yaml \
  m0_allowlist_check.yaml \
  m0_allowlist_check_vm.yaml \
  docker/m0-prewarm.Dockerfile \
  metrics.py \
  scripts/edgeforge_llamacpp_loglikelihood.py \
  scripts/freeze_b0_tapes.py \
  scripts/freeze_lmeval_fast_manifests.py \
  scripts/llama_loglikelihood.cpp \
  scripts/replay_tapes.py \
  scripts/run_bfcl.py \
  scripts/run_lm_eval.py \
  manifests/ tasks/ traces/

git add docs/m0_eval_base.md \
  docs/EdgeForge_M0_执行卡_R1.2_2026-07-20.md \
  'docs/EdgeForge_M0_§3_锁题与官方基线_R1.4_实际执行版.md'

# 只加与冻结结论直接相关的启动、选题、正式评测与 replayer 日志；
# 不加历史 Pi 日志、中断重放日志和仍在写入的临时服务日志。
git add \
  logs/m0/llama_server_baseline_c131072_q8_n32768.log \
  logs/m0/llama_server_baseline_systemd_2026-08-05.log \
  logs/m0/llama_server_tb_probe_c131072_q8.log \
  logs/m0/llama_server_anchor_qat_q4_0_c131072_q8_n32768.log \
  logs/m0/m0_allowlist_check.log \
  logs/m0/m0_allowlist_check_vm_r3.tsv \
  logs/m0/m0_prewarm_two_task_image_map.tsv \
  logs/m0/m0_sanity_candidate_base_image_digests.tsv \
  logs/m0/m0_sanity_candidate_image_prepull.log \
  logs/m0/m0_baseline_run.log \
  logs/m0/m0_bfcl_simple_python.log \
  logs/m0/m0_anchor_qat_q4_0_bfcl_simple_python.log \
  logs/m0/m0_anchor_qat_q4_0_gsm8k_fast_200.log \
  logs/m0/m0_anchor_qat_q4_0_replayer.log \
  logs/m0/m0_baseline_replayer.log \
  logs/m0/m0_fetch_mmlu_pinned.log \
  logs/m0/m0_lmeval_gsm8k_fast_200.log \
  logs/m0/m0_lmeval_gsm8k_smoke.log \
  logs/m0/m0_lmeval_humaneval_smoke_fixed.log \
  logs/m0/m0_lmeval_mmlu_fast_500_llamacpp_logits.log \
  logs/m0/m0_lmeval_mmlu_logprob_diagnostic.log \
  logs/m0/m0_lmeval_mmlu_smoke.log \
  logs/m0/m0_lmeval_mmlu_smoke_5shot_llamacpp_logits.log

# /results/ 被整体忽略，仅强制加入下列小型冻结快照。
git add -f \
  results/baseline_e4b_q4km/lock.json \
  results/baseline_e4b_q4km/result.json \
  results/baseline_e4b_q4km/parser_metrics.json \
  results/baseline_e4b_q4km/replayer/records.jsonl \
  results/baseline_e4b_q4km/replayer/summary.json \
  results/baseline_bfcl.json \
  results/baseline_lmeval.json \
  results/anchor_official_qat_q4_0/endpoint_smoke/ \
  results/anchor_official_qat_q4_0/bfcl/result/edgeforge-gemma4-e4b-qat-q4_0-FC/non_live/BFCL_v4_simple_python_result.json \
  results/anchor_official_qat_q4_0/bfcl/score/edgeforge-gemma4-e4b-qat-q4_0-FC/non_live/BFCL_v4_simple_python_score.json \
  results/anchor_official_qat_q4_0/gsm8k_fast_200/gemma4-e4b-qat-q4_0/results_2026-08-05T01-48-40.988614.json \
  results/anchor_official_qat_q4_0/replayer/records.jsonl \
  results/anchor_official_qat_q4_0/replayer/summary.json

# 补充：B0 原生聚合结果（不含 samples JSONL；切勿添加 results/bfcl/ 整目录）。
git add -f \
  results/bfcl/result/edgeforge-gemma4-e4b-FC/non_live/BFCL_v4_simple_python_result.json \
  results/bfcl/score/edgeforge-gemma4-e4b-FC/non_live/BFCL_v4_simple_python_score.json \
  results/lmeval/mmlu_fast_500_llamacpp_logits/models__gemma-4-E4B-it/results_2026-08-04T22-26-56.630433.json \
  results/lmeval/mmlu_smoke_5shot_llamacpp_logits/models__gemma-4-E4B-it/results_2026-08-04T21-20-04.183529.json \
  results/lmeval/gsm8k_fast_200/gemma4-e4b/results_2026-08-04T23-11-46.389008.json \
  results/lmeval/gsm8k_smoke_fixed/gemma4-e4b/results_2026-08-04T20-46-10.907230.json \
  results/lmeval/humaneval_smoke_fixed/gemma4-e4b/results_2026-08-04T21-08-20.611861.json

# 原始运行日志保持原样，不因行尾空格/空行篡改证据；
# whitespace 硬检查覆盖其余全部暂存件。
git diff --cached --check -- . ':(exclude)logs/m0/**'
git diff --cached --stat
git commit -m "feat(m0): freeze line A official baselines and replay artifacts"
```

提交前必须再跑 YAML/JSON 解析、Python 语法、manifest 哈希和 replayer 请求数检查；提交哈希无法反写进同一提交，故由 `git log -1` 与本执行记录共同定位。

---

## 11. 本节产出

- **20 题清单已锁定**：`m0_baseline_job.yaml`；换题 1 轮，最终 sanity 0/5，烟测对为 `nginx-request-logging` / `count-dataset-tokens`。
- **B0 主表第一行已冻结**：TB 0/100；parser hard/soft 17.823% / 59.569%；BFCL 90.75%；MMLU 59.8%；GSM8K strict/flexible 84.0% / 84.5%；HumanEval 只声明 0/5 smoke；TTFT p50 349.459 ms、TPOT p50 19.220 ms/token、吞吐 p50 52.029 tok/s。
- **锚区一行已冻结**：官方 QAT-Q4_0 快档四件，`training_lineage=google_official_qat`；TB 慢档定于 M6，不在 M0 补跑。
- **冻结快照路径已更正**：`results/baseline_e4b_q4km/lock.json`（无时间戳）；镜像证据为 `logs/m0/m0_sanity_candidate_base_image_digests.tsv`，而非旧清单中不存在的文件名。
- **磁带与交接已完成**：`traces/tapes/` 5 盘 / 11 请求每遍；`traces/trajectories_sha256.txt` 覆盖本地保留的 100 条 B0 trajectory。
- **喂下游的实测分布已回填**：峰值上下文 p50/p95 6292.5 / 22340.55 tokens；F1/F2/F3/F4 = 92/7/1/0；`finish_reason=length` = 0。

---

## 附录 · 与原执行卡 §3 的差异清单（可审计）

| 项 | 原卡 | 本版 | 理由 |
|---|---|---|---|
| 单轮上限 | 未提及 | **32768**，附不重跑声明 + 证伪计数器 | §2 后新增的冻结项；4096 从未生效，但尾部风险变了 |
| `max_format_errors` | 列入 job.yaml 的 agent_kwargs | **删除** | Harbor 0.18.0 无实现；探测 lock.json 已误记 64 一次 |
| 镜像预拉 | 仅 `docker pull` | **预拉 + 预热镜像 + 验收门** | harness 自己在容器内下载，预拉覆盖不到 |
| 重试 | 未提及 | `max_retries=2`，模型侧失败不重试 | 基础设施抖动与模型失败必须可分（facts 6.2） |
| 换题 | "<10% 则回换更容易的题" | **≤2 轮封顶** | 无界迭代 = 以结果为条件的选择 |
| 失败计数 | 只有成功率 | **四分类 + length 计数** | 分不清"不会做"与"轮次跑飞" |
| parser 指标 | 单列格式错误率 | **硬错误 + 软警告两列** | §2 实测硬错误为 0，单列会塌成地板 |
| lm-eval | 只提 `max_length` 2048 | **加 `max_gen_toks` 256 雷 + MMLU 5 题冒烟** | thinking 占压倒多数，256 必截断 |
| QAT 锚 | "以独立 alias 起服务" | **明确串行，不可并存** | B0 加载后仅余 2364 MiB |
| 磁带入库 | "保留进 traces/" | **磁带入库 + 原始 trace 出 manifest** | `/results/` 整体 gitignore，原表述无法落地 |
| replayer 计时 | 外部计时 | **用响应 `timings` 块 + 两遍回放取第二遍** | §2 证据给了现成字段；cache 状态必须一致 |
| 墙钟 | "1–2 天，主要是等" | **3.1 / 5.6 / 16.7 h 三档实测推算** | §2 给了 per-turn 分布 |
| `harbor.version` | `null` | **0.18.0** | lock.json 已实证 |
| 选题判据 4 | 主观判断"不依赖外网下载" | **allowlist 收紧后确定性检出** | lock.json 的 `extra_allowed_hosts` 是现成入口 |
