# EdgeForge M0 §2：线 A · TB 2.1 接自家端点跑通（R1.4 实际执行版）

> 状态：§1–§6、§8–§10 已于 2026-08-02 执行；§7 是按需排障、未触发。端点在产物入库后已按要求停止。本文件保留实际执行卡与证据索引；现有实测协议为单轮 4096。Pi 对齐的 32768 已恢复为 `eval_config.yaml` 的待重启目标，但尚未用于本线运行或成为证据。
> 前置：§1 已完成（`eval_config.yaml` 冻结、`logs/m0/` 三份日志在库）。
> 本节目标不变：跑通 1 题，**不论成败**，只要 agent 发请求 → 收回复 → 执行命令 → verifier 出结果，即算过门。
> 本节新增的实质工作是端点重起与协议参数定案——原卡假设 §1 的端点状态可直接复用，boot log 落地后该假设不成立（见 0.2）。

---

## 0. 本轮定案与边界

### 0.1 已锁项〔事实，本轮拍板〕

| 项 | 定案值 | 理由 |
|---|---|---|
| thinking | **开**（reasoning budget 不限） | 与门⑦"训练侧渲染必须与评测端点同模式"同源；关掉会连累整条模板链 |
| 单轮生成上限 | **4096** tokens | 防单轮跑飞吃掉 TB 任务超时；反推见 §6 |
| `--min-p` | **0**（显式） | 对齐 Gemma 模型卡；消除 llama.cpp 默认 0.05 的未冻结采样轴 |
| `--reasoning-format` | **auto** | thinking 剥进 `reasoning_content`，`content` 留干净 JSON 给 terminus 解析；亦是 token 三列拆分唯一可取数路径 |
| `--ignore-eos` | **不带** | 见 0.2 |
| harness | **terminus-2 不变** | Pi 方案已评估否决，见 0.3 |
| 摘要 | `enable_summarize=false`，溢出计为失败，`model_info=null` | R1.3 定案，不复议 |

### 0.2 为什么重起服务并留新证〔事实/雷区〕

本节确实以一条显式、逐旗标可审计的命令重起了服务，并留下 `logs/m0/llama_server_tb_probe_c131072_q8.log`。这避免把此前 Pi 会话日志混入 TB 协议证据。

**更正原先的 EOG 推断**：`-lv 4` 中 `common_init_: added ... logit bias = -inf` 是候选 token bias 的诊断输出，未启用 `--ignore-eos` 时也会出现，不能用其行数判断 EOG 抑制是否生效。实际 TB 端点的启动命令不含 `--ignore-eos`，且 `/props` 返回 `ignore_eos=false`；这是唯一采用的状态证据。旧 Pi 日志仍可作为 KV/显存历史证据，但不再承担 endpoint flag 证明。

### 0.3 Pi 替换 terminus-2：已评估，否决〔决策留档〕

技术上可行（harbor 有 agent 接口），但否决，理由按分量：

1. **训练/评测同源污染**：`armand0e__qwen3.7-max-pi-traces`、`armand0e__claude-opus-4.8-pi-traces` 均为 Pi 格式且进训练 mix。harness 若也是 Pi，after 行涨幅中"学会 Pi 工具格式"的部分与"agent 能力提升"不可拆分，与门⑤去污染逻辑正面冲突。terminus-2 的价值正在于它是 held-out harness。
2. **塌掉一列高功效指标**：terminus parser 格式错误率（纯文本解析机制）与 BFCL tools-API 准确率（tools 字段机制）是两列；换 Pi 后 TB 列退化为第二个 tools-API 列，parser 错误率消失。E2 已把四个高功效指标升格为主要测量手段，丢一列代价大于丢成功率。
3. **外部锚作废**：官方 E4B @TB2 ≈2.2% 是 harbor 官方 agent 的数；§3.1 的可测区间判据挂在它上面。
4. **冻结载体要自造**：harbor 原生给 job.yaml + lock.json + `jobs resume`；Pi 侧 W0 明记无原生 max-turn 控制、工具子进程需进程组清理兜底（`use_pi = conditional`）。
5. **蓝图已废弃 Pi live loop**，且 harness 一旦选定要冻结到 M8，稳定性债按 candidate 数量放大。

正方唯一有力论点（Pi 原生 tool calling 成功率更好看）不成立：E2 已预先接受"打不正"本身即被测量对象；为让成功率好看而换 harness，与"看过分数再换题"是同一种选择偏差。

**留作可选旁支**：M2 或 M8 做一次性 harness 敏感性检查——同 candidate、同题单，terminus-2 与 Pi 各跑一遍，报告"换 harness 分数差多少"。明确标注旁支，不进主表 before/after。

### 0.4 本节不做〔边界〕

- 不恢复或补交已删除的 32768 临时 smoke 文件；alias 的正式证据为 `logs/m0/v1_models_tb_probe_c131072.json`，tools-API 不属于 terminus-2 过门条件。
- 不做 harbor 独立钉版动作；`eval_config.harbor.version` 保持 `null`，旗标拼写以当日 `harbor run --help` 为准，运行配置的冻结由 **lock.json** 承担。
- 不跑成套子集、不锁题单（§3.1）、不跑官方 QAT 锚（§3.3）。
- 探测题的成败**不得进入 §3.1 选题判据**——与"题单锁定后不因任何模型分数换题"同一条防选择偏差纪律。

---

## 1. 重起端点并留新证

```bash
mkdir -p logs/m0 results
```

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
  -n 4096 \
  --port 8080 \
  2>&1 | tee logs/m0/llama_server_tb_probe_c131072_q8.log
```

说明：

- **不带** `--ignore-eos`。
- `-fa` 不显式传：§1 日志显示 flash attention 已自动启用（`flash_attn = enabled`），保持默认并如实记录，不新增消融轴。
- prompt cache（默认 8192 MiB）与 context checkpoints（默认 max 32）**保持开启**——agent 多轮的 prefix cache 命中是真实部署形态（facts 1.5）。代价：TB 运行中的 TTFT 是 **cache-warm 口径**，该口径要写进主表脚注，且全项目 candidate 一致。
- `-n 4096` 是服务端默认上限；agent 侧若另传 max_tokens 以 agent 侧为准，两处都要记录。

**起服后立刻做三条防呆检查**：

```bash
# ① 直接查看实际生效值；不可由 boot log 的 logit-bias 行反推
curl -s http://localhost:8080/props | rg 'ignore_eos'

# ② KV 两段仍与冻结值一致（non-SWA 1088.00 + SWA 21.25 = 1109.25 MiB）
grep -E 'llama_kv_cache: size|creating .*KV cache' logs/m0/llama_server_tb_probe_c131072_q8.log

# ③ 采样链里 min_p 应为 0.000
grep -A3 'sampler params' logs/m0/llama_server_tb_probe_c131072_q8.log | head -20
```

① 必须显示 `ignore_eos=false`；否则停下核对实际命令行再继续。②③ 与 `eval_config.yaml` 冲突时，按仓库纪律**以实测为准并回改配置**。

---

## 2. 端点自检（alias + reasoning 分离）

```bash
curl -s http://localhost:8080/v1/models \
  | tee logs/m0/v1_models_tb_probe_c131072.json
```

应含 alias `gemma4-e4b`。

**reasoning_format 生效验证**——这是本节最关键的一条 curl，决定 terminus 能不能解析：

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gemma4-e4b",
    "messages": [
      {"role": "user", "content": "Think through 12 + 30 in the reasoning channel. In the final answer, reply with exactly this JSON and nothing else: {\"command\": \"ls -la\"}"}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "min_p": 0,
    "max_tokens": 4096
  }' \
  | tee logs/m0/reasoning_format_check.json
```

判据：

- `choices[0].message.reasoning_content` **存在且非空**（思考文本被剥离）；
- `choices[0].message.content` **只含 JSON**，前面没有思考文本；
- `finish_reason` 不是 `length`（是 `length` 说明模型没自然收尾，直接顶到 4096，见 §7④）。

任一不满足，先修 `--reasoning-format`，不要进 harbor。

**顺带确认（B4，零成本）**：记下 `usage` 字段的构成——`completion_tokens` 是否把 reasoning 一并计入。这决定 §4 "每任务 token 拆 thinking / answer / tool 三列"的取数口径；若 usage 不分列，则三列只能从 trajectory 的 `reasoning_content` 长度侧算，须在本节确认 terminus-2 的 trajectory 是否持久化该字段——不持久化则记为待办，磁带/指标改走 server 侧请求日志录制。

---

## 3. harness 侧准备

**〔雷区〕环境隔离**：安装 harbor 会把 `datasets` 升到 ≥4.0，线 C 数据管线必须独立 venv。Docker ≥20.10、Compose ≥2.0、Python 3.12（当前实测环境：Docker 29.6.1、Compose 5.3.1、Python 3.12）。

**hello-world 任务来源**（R1/D15）：`examples/tasks/` 是 harbor 仓库内路径，pip 安装环境不存在。二选一：

```bash
# 方式一：clone harbor 仓库只为取该路径
git clone --depth 1 <harbor 仓库> third_party/harbor

# 方式二：本地造一个最小任务
harbor tasks init
```

`third_party/` 已在 `.gitignore` 中，不入库。

**api_base 可达性预检〔30 秒〕**：terminus-2 在宿主机运行、经 docker exec 驱动容器内 tmux，故 `http://localhost:8080/v1` 成立。若当日版本把 agent 装进容器内运行，localhost 指向容器自身，需改 `http://host.docker.internal:8080/v1` 或 bridge IP。跑第一条命令前确认一次，结论记进本节产出。

---

## 4. hello-world 探测 + `parser_name` 一次性定案

**`parser_name` 升格为冻结前必须定案的协议参数**：它直接影响格式错误率与成功率，看过基线分数再换 parser 即选择偏差。做法是两种各跑一次，**在跑任何 TB 真题之前锁死**。

```bash
# json
OPENAI_API_KEY=not-needed harbor run -a terminus-2 -m openai/gemma4-e4b \
  --path third_party/harbor/examples/tasks/ --include-task-name hello-world \
  --agent-kwarg api_base=http://localhost:8080/v1 \
  --agent-kwarg temperature=1.0 \
  --agent-kwarg max_turns=30 \
  --agent-kwarg parser_name=json \
  --agent-kwarg enable_summarize=false \
  --jobs-dir results/m0_hello_json

# xml
OPENAI_API_KEY=not-needed harbor run -a terminus-2 -m openai/gemma4-e4b \
  --path third_party/harbor/examples/tasks/ --include-task-name hello-world \
  --agent-kwarg api_base=http://localhost:8080/v1 \
  --agent-kwarg temperature=1.0 \
  --agent-kwarg max_turns=30 \
  --agent-kwarg parser_name=xml \
  --agent-kwarg enable_summarize=false \
  --jobs-dir results/m0_hello_xml
```

**模型 provider（2026-08-02 实测）**：Harbor 0.18.0 对 `hosted_vllm/gemma4-e4b` 强制要求非空 `model_info`，与本节冻结的 `model_info=null` 冲突，故本次使用等价的 `openai/gemma4-e4b`，地址仍由 `api_base` 指向本地端点。`OPENAI_API_KEY=not-needed` 仅满足 LiteLLM 的客户端校验，llama.cpp 端点不校验该值。两种前缀都只描述 OpenAI 兼容协议形状；**后端是 llama.cpp `llama-server`，不是 vLLM**。

**Harbor 0.18.0 兼容性纠正（§6 实测）**：当前 terminus-2 构造器和运行循环没有 `max_format_errors` 参数或计数器；传入的值只被 `**kwargs` 静默接收，不产生护栏效果。故未来命令移除此伪参数，配置中明确记为 `null / unsupported`，格式重试由 `max_turns` 与任务 timeout 共同封顶。`max_turns=30` 在本节仍为探测起步值。

**定案判据**：取两次运行中 format error 计数较低者。两者接近（差 <20%）时取 `json`（默认值，减少偏离）。定案后写进 `eval_config`，此后不再更换。

**实测定案（2026-08-02）**：两次运行均无 parser 拒绝，format error 计数均为 0，按预先声明的差值 <20% 规则冻结为 **`json`**，已写入 `eval_config.yaml`。JSON 运行 `results/m0_hello_json/2026-08-02__16-04-07/`：reward 1.0、无异常、2 轮；每轮各有“JSON 对象前/后额外文本”警告（共 4 条，均被 parser 容忍，非 format error）。XML 运行 `results/m0_hello_xml/2026-08-02__16-04-59/`：reward 0.0、无异常、2 轮；其首条 `keystrokes` 缺失必需的末尾换行，故 tmux 没有执行命令。这是 XML 输出协议的端到端失效证据，不重跑、不因后续分数换 parser。

---

## 5. TB 2.1 单题探测

```bash
harbor run -d terminal-bench/terminal-bench-2-1 -a terminus-2 -m openai/gemma4-e4b \
  --include-task-name "terminal-bench/kv-store-grpc" \
  --agent-kwarg api_base=http://localhost:8080/v1 \
  --agent-kwarg temperature=1.0 \
  --agent-kwarg max_turns=30 \
  --agent-kwarg parser_name=json \
  --agent-kwarg enable_summarize=false \
  --agent-setup-timeout-multiplier 3 \
  -k 1 --n-concurrent 1 \
  --jobs-dir results/m0_tb_probe
```

本机 Harbor 0.18.0 的 `hosted_vllm` provider 与冻结的 `model_info=null` 不兼容，故沿用 §4 已验证的 `openai/gemma4-e4b` 协议映射；后端仍为本地 llama.cpp。`kv-store-grpc` 是本机已缓存的 TB 2.1 候选里专家估时最短的中等题（15 分钟），仅作为链路探测，不据此选题或计分。

首次实测中，任务镜像的 terminus-2 setup 安装 `tmux`/`asciinema` 在默认 120 秒窗口超时，尚未发生模型请求；故本次只将 `agent_setup` 超时倍率设为 3，以覆盖 harness 工具安装。任务的 agent/verifier 900 秒预算未变，此 setup 参数也不属于 §6 要定案的评测超时政策。

**必须带任务过滤**（R1/A1），否则跑满全部 89 题。

**过门判据（不看成败）**：agent 发出请求、收到回复、在容器里执行了命令、verifier 产出了结果。四段齐即链路成立。

**〔雷区〕TB 版本**：W0 已证 2.1 本地可解析、容器/Oracle/verifier 闭环可用；仅当当日拉取失败才降 `terminal-bench-2`（89→2.0 小模型分差 ~3pp，降锚不伤主线），记录探测日期。**网络抖动不解释为模型失败**（facts 6.2，W0 同口径）。

**实测结果（2026-08-02）**：`terminal-bench/kv-store-grpc` 的正式闭环运行在 `results/m0_tb_probe/2026-08-02__16-31-43/`。agent 使用 `openai/gemma4-e4b`、本地 `api_base`、冻结的 `parser_name=json`，完成 7 个回合和 7 条容器命令；verifier 正常执行 7 个测试，reward 为 0.0、无异常。四段（agent 请求、端点回复、容器命令、verifier 结果）齐全，`probe_link_closed=true` 已回填 `eval_config.yaml`。失败来自任务实现本身（`Server` 类名与 protobuf `value` 字段不符合 verifier），不归因为端点或 parser。此前 `results/m0_tb_probe/2026-08-02__16-28-28/` 在 agent setup 安装 tmux/asciinema 时 120 秒超时、尚未请求模型，故不计入本探测结论。

---

## 6. 从实测反推 `max_turns` 与超时档位〔本节最重要的产出〕

原卡把 `max_turns=30` 当固定起点，boot log 落地后该值需要重算。

**已知实测**（`logs/m0/llama_server_pi_c131072_q8_reasoning_unrestricted.log`）：

| 量 | 实测值 |
|---|---|
| decode | 52.8 t/s |
| prefill | 2593 t/s |
| 单次 2086 token 解码墙钟 | 40.6 s |
| prefix cache 命中 | task 517 由 checkpoint 恢复 5116 tokens，仅新增 5 token 走 prefill |

**推论**：单轮上限 4096 tokens ÷ 52.8 t/s ≈ **77.6 s**，即单轮墙钟最坏值。`max_turns=30` 的最坏情况是 **~39 分钟纯解码**，不含容器内命令执行——TB 任务自带的 `max_agent_timeout_sec` 常见档位接不住。

**若不处理，后果是大批任务被超时判负而非被能力判负**，这会同时毁掉两件事：§3.1 "官方基线落进 15–30% 可测区间"的目标（超时率盖过题目难度），以及 D4–D5 的墙钟可控性（20 题 × k=5 × 最坏 39 min ≈ 65 h 串行）。

**本节要从探测轨迹里量出四个数**（零额外成本，从 `results/m0_tb_probe/**/trial_*` 取）：

| 量 | 用途 |
|---|---|
| 每轮生成 token 的 p50 / p95 | 反推真实单轮墙钟；确认 4096 上限触顶频率 |
| 每轮墙钟 p50 / p95（含容器命令执行） | 反推 `max_turns` |
| 单题总轮数与总墙钟 | 反推 timeout 档位与 §3.2 的 100 试验预算 |
| 峰值上下文占用 | 喂 R1.4 待办：决定 M2 板端 `max_context_len` 与 §3.4 磁带上下文档位 |

**反推口径**：`max_turns ≈ 可用 agent 预算秒数 ÷ 每轮墙钟 p95`。若该值显著小于 30，二选一并写进协议声明：① 下调 `max_turns` 并声明"轮数耗尽计为失败"；② 统一放大 TB agent timeout 并声明放大量是评测协议的一部分。**两者都成立，但不能悬置**——与 R1.3 处理摘要方案同一条纪律。

若 4096 触顶频率高（大量轮次 `finish_reason=length`），说明 thinking 在吃掉预算，回到 §7④ 排查而不是直接调大上限。

**实测反推与冻结（2026-08-02）**：以正式 trial `results/m0_tb_probe/2026-08-02__16-31-43/kv-store-grpc__7FvkxNN/` 为唯一输入。分位数采用线性口径 `q=(n-1)p`；每轮墙钟用 agent execution 起点及相邻 agent 响应时间戳切成 7 个完整周期，周期总和 81.65 秒，包含期间的容器命令执行。

| 量 | 实测 / 定案 |
|---|---|
| 每轮 completion tokens | `[690, 465, 378, 761, 952, 195, 229]`；p50 = **465**，p95 = **894.7（配置取 895）** |
| 4096 上限触顶 | **0 / 7**；单轮最大 952 |
| 每轮墙钟 | p50 = **9.43 s**，p95 = **19.07 s** |
| 单题 agent | **7 轮，81.65 s** |
| 单题完整 trial | **110.90 s**（含环境、agent、verifier 与收尾） |
| API 请求耗时合计 | **74.38 s** |
| 峰值上下文 | **5,770 tokens**（最大 `prompt_tokens + completion_tokens`；cache 是 prompt 子集，不重复相加） |

本题 task-defined agent 预算为 900 秒，`900 / 19.07 = 47.2` 轮；原探测护栏 30 轮低于该实测上限，按 p95 估算为 `30 × 19.07 = 572.1` 秒，仍留约 327.9 秒尾部余量。因此冻结 **`max_turns=30`**，不放大 agent timeout：`agent_timeout_policy=task_defined_default`、`agent_timeout_multiplier=1.0`。轮数耗尽与任务超时均计失败；harness 首次安装工具所需的 `agent_setup_timeout_multiplier=3.0` 单独保留，不改变任务 agent 预算。

格式方面，7 轮均无 parser `ERROR`（有可容忍的对象前后额外文本 warning）；Harbor 0.18.0 terminus-2 源码确认不存在 `max_format_errors` 实现。最终协议为 **`max_format_errors=null / unsupported`**，格式错误重试由 30 轮与 task timeout 共同限制，不能把 lock.json 中曾传入的 64 当成生效参数。

---

## 7. 排障顺序（更新版）

原卡顺序写于 16K 上下文假设下，"上下文不够"曾排第二；131K 端点下该项降至末位，新增两条排在最前。

1. **reasoning_format**：`content` 里是否混进思考文本 → 重跑 §2 的 curl 看 `reasoning_content` 是否分离。这是解析失败的第一嫌疑。
2. **EOG 状态**：查 `/props` 的 `ignore_eos` 与实际启动命令；不得由 boot log 的 `logit bias = -inf` 行推断。实测应为 `false`。
3. **chat template / parser_name**：`--jinja` 是否生效；json ↔ xml 换一下（仅在 §4 定案前允许换）。
4. **单轮上限触顶**：`finish_reason=length` 是否高频、`n_decoded` 是否稳定停在 4096 → 模型没自然收尾，查 template 与 EOG，不要直接调大上限。
5. **format error 重试**：Harbor 0.18.0 terminus-2 无 `max_format_errors` 计数器；直接看 trajectory 中 `Previous response had parsing errors` / parser `ERROR`，重试上界由冻结的 `max_turns=30` 与 task timeout 给出。warning 不算 error。
6. **api_base 可达性**：agent 实际运行在宿主机还是容器内（§3 预检）。
7. **LiteLLM 未知模型**：`unknown model` 警告行；成本核算失效属预期（token 数仍由 llama.cpp 的 `usage` 返回），不是故障。
8. **上下文**：131K 端点下溢出概率极低；真溢出即按协议计为失败，不改端点。

---

## 8. eval_config 回填

```yaml
llama_cpp:
  # ...§1 已冻结字段不动...
  reasoning_format: auto
  reasoning_budget: unrestricted
  ignore_eos: false
  flash_attn: enabled          # 自动启用，非显式旗标
  n_predict_default: 4096
  prompt_cache_ram_mib: 8192   # 默认值，保持开启
  context_checkpoints_max: 32  # 默认值，保持开启
  ttft_convention: cache_warm  # TB 运行中 TTFT 为 prefix-cache 命中口径
  boot_log_tb_probe: logs/m0/llama_server_tb_probe_c131072_q8.log

sampling:
  server_temperature: 1.0
  server_top_p: 0.95
  server_top_k: 64
  server_min_p: 0.0            # 显式对齐模型卡，覆盖 llama.cpp 默认 0.05
  server_seed: -1
  server_n_predict: 4096
  terminus_temperature: 1.0    # §2 已由 --agent-kwarg 实传验证

terminal_bench:
  dataset: terminal-bench/terminal-bench-2-1
  probe_date: "2026-08-02"
  probe_task: terminal-bench/kv-store-grpc
  probe_link_closed: true
  parser_name: json
  max_turns: 30
  max_format_errors: null  # Harbor 0.18.0 terminus-2 不支持该参数。
  format_error_policy: bounded_by_max_turns_and_task_timeout
  agent_max_tokens: 4096
  agent_timeout_policy: task_defined_default
  agent_timeout_multiplier: 1.0
  probe_agent_timeout_seconds: 900
  agent_setup_timeout_multiplier: 3.0
  turn_exhaustion_policy: fail
  enable_summarize: false
  context_overflow_policy: fail
  model_info: null
  per_turn_tokens_p50: 465
  per_turn_tokens_p95: 895
  per_turn_wallclock_s_p50: 9.43
  per_turn_wallclock_s_p95: 19.07
  probe_total_turns: 7
  probe_agent_wallclock_s: 81.65
  probe_trial_wallclock_s: 110.90
  peak_context_tokens: 5770  # 喂 M2 / §3.4
  litellm_model_string: openai/gemma4-e4b  # provider 选择器；后端仍为 llama.cpp
```

以上字段已由 §1–§6 的 boot log、端点自检与 TB probe 产物回填；未被该流程实测的字段继续保持 `null`。

---

## 9. 产物入库

**已完成（提交 `8d0e903`）**：以下忽略规则、显式快照、配置、日志和结论文档已入库。命令保留为可审计的归档配方，不需重复执行。

`results/` 为 harbor 运行产物目录，整体不入库，只提交显式挑选的快照。`.gitignore` 追加：

```text
# harbor 运行产物：只提交显式挑选的快照（lock.json / 结论摘要）
/results/
```

提交：

```bash
git add -f \
  results/m0_tb_probe/**/lock.json

git add \
  eval_config.yaml \
  .gitignore \
  logs/m0/llama_server_tb_probe_c131072_q8.log \
  logs/m0/v1_models_tb_probe_c131072.json \
  logs/m0/reasoning_format_check.json \
  docs/m0_eval_base.md

git commit -m "feat(m0): verify terminus-2 x local endpoint link, freeze agent protocol params"
```

**本机 smoke 适配（2026-08-02）**：当前 Docker 默认代理失效，且上游示例 verifier 会在 120 秒验证窗口内临时下载 `uv` 与 pytest，实测会超时；本机 `third_party/harbor/examples/tasks/hello-world/` 已仅为此探测预装 `tmux`/`asciinema`，并将 verifier 改为无网络依赖的同一精确断言（`/app/hello.txt` 内容必须等于 `Hello, world!`）。该本地适配只验证端点—agent—容器链路，不进入 TB 正式评分。

---

## 10. 本节产出

**已完成**：以下产物均已生成并按 §9 处理；服务已在归档后停止。

- **链路结论一行**入 `docs/m0_eval_base.md`：探测日期、题名、四段是否齐、成败（成败不作为任何判据）。
- **协议六项定案**入 `eval_config.yaml`：`parser_name` / `max_turns` / `max_format_errors` / `reasoning_format` / 单轮上限 / 超时与轮数耗尽政策。
- **端点新证据**：`logs/m0/llama_server_tb_probe_c131072_q8.log`（`min_p=0`、KV 两段与冻结值一致；`ignore_eos=false` 由 `/props` 与启动命令确认）、`v1_models_tb_probe_c131072.json`、`reasoning_format_check.json`。
- **实测分布四项**：per-turn token / 墙钟 / 总轮数 / 峰值上下文——直接喂 §3.2 的墙钟预算与 §3.1 的选题可行性。
- **`results/m0_tb_probe/**/lock.json`**：本次探测的官方快照。

**过门后 §3 才有意义**：题单选择判据（§3.1 的 15–30% 可测区间）依赖本节量出的超时与轮数政策；这两项没定案就锁题，锁的是一个会被超时率盖掉的区间。

---

## 附 · 与原执行卡 §2 的差异清单（可审计）

| 项 | 原卡 | 本版 | 理由 |
|---|---|---|---|
| 端点状态 | 复用 §1 | **已重起并留新证** | 旧 log 的 logit-bias 行不能诊断 `--ignore-eos`；实际状态由 `/props` 与命令行确认 |
| `--reasoning-format` | 未提及 | **auto，冻结项** | terminus 只解析 `content`；内联思考必崩 |
| `--min-p` | 未提及 | **显式 0** | 实测 0.05 在生效但未冻结 |
| 单轮上限 | 未提及 | **4096，冻结项** | 防单轮跑飞吃掉任务超时 |
| `max_turns` | 固定 30 | **由 §6 实测反推** | 52.8 t/s 下 30 轮最坏 39 min |
| 超时政策 | 未提及 | **必须二选一并声明** | 否则超时率盖过难度，§3.1 目标失效 |
| `parser_name` | 排障手段 | **冻结前一次性定案** | 防选择偏差 |
| 摘要方案 | (a)/(b) 待选 | 已由 R1.3 定案 | 不复议 |
| 排障顺序 | 上下文排第二 | 降至末位，新增 reasoning/EOG 两条 | 131K 端点下溢出概率极低 |
| 产物目录 | `outputs/m0_tb_probe` | `results/m0_tb_probe` | 与 §3.2 的 `jobs_dir: results/` 统一 |
| 探测题 | 未约束 | **不得进入 §3.1 选题判据** | 防选择偏差 |
| harness | terminus-2 | 不变（Pi 方案否决留档） | 见 0.3 |
