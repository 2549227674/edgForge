# EdgeForge M0 §4：线 A · Agent 指标脚本（R1.7 执行终稿）

> 状态：**可执行终稿，无分支**。所有 schema 分歧已用真实数据消解（远端评审在沙盒内对 100 条 trajectory 实跑，分支判定 = B，见版本记录）。
> 前置：§1/§2/§3 完成；100 条 B0 trajectory 本地留存并已按 `traces/trajectories_sha256.txt` 逐位校验通过。
> 本节目标：**把 100 条 trajectory 变成主表的 agent 列，口径写死进脚本，M1 之后换输入目录重跑一条命令即可。**
> **本卡随附两个脚本与一份参考输出**：`metrics.py`（v2）、`count_response_tokens.py`、`agent_metrics_reference.json`。**验收判据是本地重跑逐位复现参考值**——比任何文字规格都硬。

## 版本记录

| 版本 | 变更 |
|---|---|
| R1.5 | 首版，基于远程可见件起草 |
| R1.6 | 补本地资源清单 + 三分支列集（A/B/C），因起草侧未见过 trajectory |
| **R1.7** | **远端拿到 100 条真实 trajectory（哈希全对），分支 B 确认，所有口径用实测定死，脚本已写并在真数据上跑通、参考值随附。以下三处相对 R1.6 的实质更正见「实测带来的更正」** |

---

## 0.0 实测带来的更正〔R1.7 必读，含两处对我方前几版的纠正〕

拿到真实数据后，有两条 R1.6 的判断被推翻，如实记录：

**更正一：`premature_complete_rate` 撤回。** R1.6 建议加这一列，并推断「92 条 = agent 干净宣告完成、末轮不发命令」。实测相反：**92 条 F1 的最后一步全部带 `tool_calls`**（92/92），不带命令的恰好只有 F2(7)+F3(1) 那 8 条。ATIF 日志里**没有任何结构化 `task_complete` 字段**，该率无从算起。F1=92 只如实表述为「zero-reward 且未耗尽轮数、未超时的 trial」，不包装成从字段算出的率。

**更正二：thinking 缺失的处理方向反转。** R1.6 §3.4 假设缺失是「解析失败的副产物」，据此说「不得当 0、分母用 711」。实测证明缺失与硬错误几乎不相干（`|S_missing∩S_hard|` 仅 14），且是**模型行为**：无思考的 111 条被接受响应，completion 中位数 **110**，而有思考的 711 条中位数 **677**——6 倍差。因此正确处理是：`no_reasoning_rate` 作为 836 分母上的一等列（125/836 = **14.95%**），thinking token 统计**条件在 711 条**上。这一列本身就是 M1 可比信号（SFT 后模型更爱/更少思考）。

**同时确证的旧发现**（真数据复核，均写进脚本参考值）：parser 四数 149/498/836/125 逐位复现；失败四分类从原始文件独立重建 = 92/7/1/0；聚簇 SE 5.93pp、设计效应 20.1×；64/100 trial 零硬错误、per-trial 硬错误率中位数 0。

**新增可用信号**（R1.6 起草时不知道）：
- `tool_calls` 携带完整 `keystrokes` 文本（559 步 / 1340 次 / 446 步带 keystrokes）→ `command_content_tokens` + `tool_calls_per_turn` 两列可出，标注 harbor 规范化口径。
- **恢复列**：42 次硬错误事件在若干轮后恢复（median 1 轮），**3 条 trial 锁死在硬错误直到结束**——这是 parser 列之外最直接的「模型能否自愈」信号。
- 当前 trajectory schema **未持久化** `summarization_count` → `enable_summarize=false` 仍是已冻结的配置策略，但不能将其写成运行期计数证据。
- `final_metrics` 每条带 `total_prompt/completion/cached_tokens`，可与逐步 metrics 求和互校。

**一条数据边界**：F3 超时那条 trial 的 `n_episodes=6` 而 agent step 只有 5——超时发生在第 6 次请求途中，未落 step。不影响任何计数，脚注记一句即可。

---

## 0.5 给本地 agent 的执行红线

1. **`results/baseline_e4b_q4km/parser_metrics.json` 不得覆盖**（sha 已进 `eval_config`）。调试输出一律 `/tmp`。
2. **与已冻结值冲突先停**。实测优先于文档，但回改冻结件是决策级动作，须先报告——本卡已含两处需回改的精确 diff（§8.1），照它执行即可，不要自行发挥。
3. **不新增未经实证的具体数字/身份/阈值**（facts 6.6）。
4. **`git add` 一次性在 §8 做**。
5. 不为取数改动常驻端点启动参数。

---

## 0.1 待你拍板项〔本卡已用实测填了建议值〕

| 项 | 建议值（实测支撑） | 备注 |
|---|---|---|
| `premature_complete_rate` | **不出**（字段不存在） | 见 0.0 更正一 |
| thinking 缺失 | **`no_reasoning_rate` 一等列 + thinking 条件在 711** | 见 0.0 更正二，6 倍 completion 差为证 |
| command 列 | **出 `command_content_tokens` + `tool_calls_per_turn`**，标 `harbor_normalized` | keystrokes 文本存在 |
| tokenizer | **B0 `/tokenize` 端点 + 同一基线 GGUF** | 复原既有冻结参数的 B0 transient service；避免逐片启动 `llama-tokenize` 反复加载 tokenizer。 |
| 脚本形态 | **metrics.py 升 v2 + 内置 v1 回归断言 + 另出 `agent_metrics.json`** | 已实现并验证断言会触发 |
| 0/100 表述 | **rule of three 按 20 题 = 95% 上界 15%** | Wald 在 0 上失效 |
| 回改 `eval_config` `absent_on_hard_parser_error_steps` | **改名 + 补 111 条真相**（§8.1 diff） | facts 6.6 第三实例 |
| 回改 `§3 实际执行版` §8.2 那句 | **更正**（§8.1 diff） | 同上 |
| 回改 `facts.md` 6.1 | **补聚簇设计效应 20× + 「数值相等不构成同一集合」** | 见 §8.1 |

---

## 1. 开跑前确认〔勘察已完成，此处只是形式确认〕

§4.0 勘察卡已跑完，分支 B 已定，红灯已在本卡 0.0 消解（两处回改已备好 diff）。本地重跑前只需确认输入在位：

```bash
sha256sum -c <(awk '{print $1"  "$2}' traces/trajectories_sha256.txt) | grep -c ': OK$'   # 期望 100
```

100 才能往下。脚本内部也会再校验一次（`--trajectory-manifest`），这是双保险。

---

## 2. 列集（分支 B 终版）

| 列 | 分母 | 来源 | 口径要点 |
|---|---|---|---|
| `success_rate` | 100 | job `result.json` | 0/100，按 3.2 表述 |
| `failure_f1..f4` | 100 | trajectory + `result.json` | 92/7/1/0；F1 不叫「假完成」，见 0.0 |
| `parser_hard_error_rate` | 836 | trajectory | 149，与软列不可加 |
| `parser_soft_warning_rate` | 836 | trajectory | 498 |
| `parser_hard_error_rate_per_trial_median` | 100 | trajectory | **0**（双峰的证据，必与 pooled 并列） |
| `trials_with_zero_hard_errors` | 100 | trajectory | 64 |
| `turns_per_trial` | 100 | trajectory | median 6，右删失 7 例 |
| `parser_recovery_turns` | 每次硬错误事件 | trajectory | 42 事件 median 1 |
| `unrecovered_lockin_trials` | 100 | trajectory | 3 |
| `no_reasoning_rate` | 836 | trajectory | **14.95%**，模型行为（0.0 更正二） |
| `completion_tokens_per_trial` | 100 | `metrics.completion_tokens` | server 真值总量 |
| `prompt_tokens_per_trial` | 100 | `metrics.prompt_tokens` | agent 成本主体 |
| `cached_token_share` | 每响应（分母 835） | `metrics.cached_tokens` | 缺 1 条，按 0 计，脚注声明 835 |
| `thinking_tokens`（条件在 711） | 711 | sidecar | 与 836 分开登记 |
| `message_tokens`（harbor 规范化） | 可解析响应 | sidecar | non-thinking 散文的**下界** |
| `command_content_tokens`（harbor 规范化） | 有命令的响应 | sidecar | 非原始体，标注 |
| `tool_calls_per_turn` | 559 步 | trajectory | 1340/559 |

**不出**：`premature_complete_rate`（无字段）、`command_payload_tokens`（原始 JSON 体未留存，`command_content_tokens` 取而代之）。

**官方 QAT 锚**：agent 列全部留空 + 脚注（锚无 TB 慢档），不得用 B0 值填充。

---

## 3. 统计口径〔写进脚本注释与主表脚注，已内置于随附脚本〕

### 3.1 聚簇：按任务 bootstrap（实测值）

真数据复算（可用仓库 `parser_metrics.json` 同法复核）：硬错误率 pooled 17.823%，**cluster bootstrap SE = 5.93pp**（4000 次，seed 0，按任务重抽样），naive 二项 SE 1.32pp，**设计效应 20.1×**。149 次硬错误中 59 次挤在 2 条 trial（30/30 与 29/30），64/100 trial 零硬错误，per-trial 中位数 0——**双峰，非均匀劣化**。

三个后果（脚本已落实）：主表 pooled 与 per-trial 中位数并列；输出 cluster SE，naive SE 标 `do_not_cite`；M1 按 20 任务配对比较。**E2「后三指标功效高一个量级」修正为**：聚簇后约 ±12pp，与 TB 同量级；parser 列真正的优势是「不在地板上」。

### 3.2 0/100：rule of three

Wald SE 在 p̂=0 时为 0，「<7pp 未分辨」失效。按 20 题 rule of three，95% 上界 **15%**（按 100 试验算是 3%，过于乐观，标 `do_not_cite`）。主表脚注：**成功率 0/100；真实值 95% 上界 ≈15%；M1 判据是「是否出现非零成功」，非「掉分 ≤3pp」。**

### 3.3 右删失

均值 8.36 是截断均值（7 例撞 30 轮、1 例超时）；headline 用**中位数 6**，同出限制均值。

### 3.4 no_reasoning 是模型行为（方向已按实测反转）

见 0.0 更正二。脚本把 `no_reasoning_rate` 作为 836 上的列，thinking token 条件在 711，并在输出里带 completion 分布三组作为「行为而非缺陷」的自证据。

### 3.5 三机制不混用（C13）

terminus 文本解析 → `metrics.py` → `agent_metrics.json`；BFCL tools 字段 → `run_bfcl.py` → `baseline_bfcl.json`；lm-eval → `run_lm_eval.py` → `baseline_lmeval.json`。三者永不同文件。

---

## 4. 脚本〔随本卡交付，已在真数据跑通〕

### 4.1 冻结件处理

- `metrics.py` → `SCHEMA_VERSION = "edgeforge-agent-metrics/v2"`，新增列，**parser 两列算法逐字不动**。
- 输出 `results/baseline_e4b_q4km/agent_metrics.json`；**不碰** `parser_metrics.json`。
- 内置 v1 回归断言：重算 parser 四数须与 `--verify-v1` 指向的 committed 文件同时等于 149/498/836/125，否则退出码 2 并打印 diff。**已验证篡改 committed 文件时断言正确触发。**
- `eval_config.metrics` 里 `parser_runner_sha256` 分列为 `parser_runner_sha256_v1`（历史）+ `agent_runner_sha256`（v2 当前）。

### 4.2 运行（两阶段）

```bash
# 阶段一：token sidecar（B0 端点与冻结基线 GGUF 相同；只落计数不落文本）
# 若 transient unit 在当前用户会话丢失，先按 §1/§3 的冻结启动参数恢复
# edgeforge-b0.service；不得更改模型、上下文、KV、采样或端口参数。
python3 scripts/count_response_tokens.py \
  --input results/baseline_e4b_q4km \
  --tokenizer-mode endpoint \
  --endpoint http://localhost:8080 \
  --schema-branch B \
  --output results/baseline_e4b_q4km/token_counts.json \
  2>&1 | tee logs/m0/m0_token_counts.log

# 阶段二：指标（离线，不需端点）
python3 metrics.py \
  --input results/baseline_e4b_q4km \
  --job-result results/baseline_e4b_q4km/result.json \
  --trajectory-manifest traces/trajectories_sha256.txt \
  --token-sidecar results/baseline_e4b_q4km/token_counts.json \
  --verify-v1 results/baseline_e4b_q4km/parser_metrics.json \
  --schema-branch B \
  --output results/baseline_e4b_q4km/agent_metrics.json \
  2>&1 | tee logs/m0/m0_agent_metrics.log
```

约定沿用仓库现状：`from __future__ import annotations`、argparse、`json.dumps(..., indent=2, ensure_ascii=False, sort_keys=True)`、失败返回码 2、无第三方依赖（token 脚本用 `subprocess`/`urllib`，与 `replay_tapes.py` 一致）。

---

## 5. 验收：逐位复现随附参考值〔本卡的核心判据〕

`agent_metrics_reference.json` 是远端在真数据上跑出的**非 token 部分**（token 部分因沙盒无 tokenizer/GGUF 未算）。本地重跑**必须逐位复现下表**，任一不符即为环境差异，查清再冻结：

| 字段 | 参考值 |
|---|---|
| `denominators` | trials 100 / tasks 20 / agent_responses 836 / responses_with_reasoning 711 |
| `failure_breakdown` | F1 92 / F2 7 / F3 1 / F4 0 |
| `parser_hard_error_rate` | 0.17822966507177032 |
| `parser_soft_warning_rate` | 0.5956937799043063 |
| `parser_hard_error_rate_per_trial_median` | 0.0 |
| `trials_with_zero_hard_errors` | 64 |
| `turns` median / mean / censored | 6.0 / 8.36 / 7 |
| `cluster_statistics.cluster_se` | 0.05928809903738477 |
| `cluster_statistics.design_effect` | 20.063693200877402 |
| `recovery` events / median / lockin | 42 / 1.0 / 3 |
| `no_reasoning_rate` / count | 0.14952… / 125 |
| `cached_tokens_missing` | 1 → `pypi-server__H4HV8jE:step2` |
| `success_rate_zero_ci.upper_95_over_tasks` | 0.15 |

**token 部分**（`--token-sidecar` 提供后新增的 `tokens` 段）无参考值，由本地首次产出；产出后连同 sidecar 的 sha 一并回传远端登记。其中 `residual_check.stable` 须为 `true`（分支 B 下残差为正且非常数是预期的，判据是「分布稳定、无异常长尾」，不是接近零）。

---

## 6. token 取数与残差〔分支 B 口径〕

- tokenizer 走 B0 的 `/tokenize` 端点（该端点由冻结的同一基线 GGUF 提供）；sidecar 只存计数与 endpoint 指纹，不存响应文本。不得逐片启动 `llama-tokenize`，以免对每个片段重复加载 tokenizer。
- 三段：`thinking`=`reasoning_content`；`message`=`message` 字段（渲染散文，non-thinking 下界）；`command_content`=拼接各 `tool_calls[].arguments.keystrokes`。
- 残差 = `completion_tokens − (thinking + message + command_content)`。分支 B 下原始 JSON 封套未留存，残差**为正且非常数**，判据是分布稳定、无负值长尾；`message_tokens` 明确声明为 non-thinking 下界。
- **降级**：若 `llama-tokenize` 不可用或残差异常，token 段留空，主表脚注「M1 补测」，其余列照出。**不启用 server 侧录制**——原始 trajectory 已冻结哈希入库，该列可随时离线补算（与基线分数不同，基线无顺延选项）。

---

## 7. eval_config 回填骨架

```yaml
metrics:
  parser_runner_sha256_v1: 1e3d19bb54db8843488b8686269ab57cd20b3b8ca2b8752fe10ff88ccd9bef8a
  agent_runner: metrics.py
  agent_runner_sha256: <v2 实测>
  agent_result: results/baseline_e4b_q4km/agent_metrics.json
  agent_result_sha256: <实测>
  schema_branch: B
  input_probe: logs/m0/m0_input_probe.json
  v1_regression_check: passed

  # 统计
  cluster_unit: task
  cluster_bootstrap_draws: 4000
  cluster_bootstrap_seed: 0
  parser_hard_error_rate_cluster_se: 0.0592880990
  parser_hard_error_rate_design_effect: 20.0636932
  parser_hard_error_rate_per_trial_median: 0.0
  trials_with_zero_hard_errors: 64
  naive_binomial_se_policy: computed_but_not_citable
  success_rate_zero_ci_method: rule_of_three_over_tasks
  success_rate_95_upper_bound: 0.15
  m1_comparison_design: task_paired_over_20_locked_tasks

  # 轮数与恢复
  turns_per_trial_median: 6
  turns_restricted_mean_at_30: 8.36
  turns_censored_at_max_turns: 7
  turns_censored_by_agent_timeout: 1
  parser_recovery_events: 42
  parser_recovery_turns_median: 1
  unrecovered_lockin_trials: 3

  # reasoning 缺失（模型行为）
  no_reasoning_rate: 0.14952
  no_reasoning_count: 125
  reasoning_absence_interpretation: model_behavior_not_logging_gap
  completion_tokens_with_reasoning_median: 677
  completion_tokens_absent_accepted_median: 110

  # F1 语义
  f1_semantics: zero_reward_not_turn_exhausted_not_timeout
  premature_complete_rate: not_computed_no_task_complete_field

  # trajectory 未持久化 summarization_count；不得虚填运行期计数

  # token（本地首跑后回填）
  token_sidecar: results/baseline_e4b_q4km/token_counts.json
  token_sidecar_sha256: <本地实测>
  tokenizer_source: llama_server_tokenize_endpoint_same_gguf
  thinking_tokens_denominator: 711
  cached_token_share_denominator: 835
  cached_tokens_missing_step: pypi-server__H4HV8jE:step2
  token_split_residual_stable: <本地实测>
```

---

## 8. 回改冻结件与产物入库

### 8.1 三处回改的精确 diff〔0.5 红线 2 授权，照此执行〕

**A. `eval_config.yaml` — `replayer.repository_handoff.reasoning_content_coverage`**

原（身份断言被推翻）：
```yaml
    reasoning_content_coverage:
      baseline_agent_response_attempts: 836
      persisted: 711
      absent_on_hard_parser_error_steps: 125
```
改为：
```yaml
    reasoning_content_coverage:
      baseline_agent_response_attempts: 836
      persisted: 711
      absent_steps: 125
      # Corrected 2026-08-05: the 125 absent steps are NOT the hard-parser-error
      # steps. Overlap with the 149 hard errors is only 14; 111 absent steps are
      # on parser-ACCEPTED responses. The absence is model behaviour (absent-
      # accepted completions median 110 vs 677 with reasoning), not a logging gap.
      absent_on_accepted_responses: 111
      absent_on_hard_error_responses: 14
      hard_error_responses_total: 149
```

**B. `docs/EdgeForge_M0_§3_...实际执行版.md` §8.2 实际执行记录那句**

原：
> …全量基线的 836 个 agent 响应中 711 个有该字段，缺失的 125 个恰为硬 parser-error 记录的原始响应。

改为：
> …全量基线的 836 个 agent 响应中 711 个有该字段。缺失的 125 个**并非**硬 parser-error 响应——与 149 个硬错误的交集仅 14，其余 111 个落在 parser 接受的响应上。该缺失是模型行为（无思考的被接受响应 completion 中位数 110，有思考的 677），非日志缺陷；详见 §4 与 `agent_metrics.json`。

**C. `docs/facts.md` 6.1 与 6.6**

6.1 末尾补一句：
> **聚簇量级（2026-08-05 实测）**：parser 硬错误率按 20 题 cluster bootstrap 的 SE≈5.9pp，naive 二项 SE 仅 1.3pp，设计效应≈20×。故「后三指标功效高一个量级」应修正为「与成功率同量级，但不在地板上」。

6.6 新增一条实例：
> **第三实例（2026-08-05）**：`eval_config` 曾断言「缺失 reasoning 的 125 条 = 硬错误带 extra-text 的 125 条」，仅因两个计数都等于 125。实测交集仅 14。**教训**：数值相等不构成同一集合的证据；凡「A 数等于 B 数所以 A=B」的隐含推断一律打 `[未复核]`。

### 8.2 入库

```bash
git add metrics.py scripts/count_response_tokens.py \
        'docs/EdgeForge_M0_§4.0_输入勘察卡_R1.0.md' \
        'docs/EdgeForge_M0_§4_指标脚本_R1.7_执行终稿.md' \
        eval_config.yaml docs/m0_eval_base.md docs/facts.md \
        'docs/EdgeForge_M0_§3_锁题与官方基线_R1.4_实际执行版.md' \
        docs/本地项目目录索引.md
git add logs/m0/m0_agent_metrics.log logs/m0/m0_token_counts.log \
        logs/m0/m0_input_probe.json logs/m0/m0_input_probe.md
git add -f results/baseline_e4b_q4km/agent_metrics.json \
           results/baseline_e4b_q4km/token_counts.json
git diff --cached --check -- . ':(exclude)logs/m0/**'
git commit -m "feat(m0): add agent-metric columns; correct reasoning-absence identity"
```

**不入库**：trajectory 原文、任何把 `reasoning_content`/响应正文复制出来的中间件（sidecar 只存计数）。索引用勘察卡重生成的版本更新（旧基准 `57b6f99` 已落后于 `fd1a05b`）。

---

## 9. 本节产出

- `metrics.py` v2 + `scripts/count_response_tokens.py`（随本卡交付，已在真数据验证）
- `results/baseline_e4b_q4km/agent_metrics.json`（含 per-task 段，供 M1 配对比较）+ `token_counts.json`
- 主表 B0 行 agent 列补齐（§2 全表）
- `docs/m0_eval_base.md` 主表更新 + 四条脚注（rule of three、聚簇 SE、no_reasoning 是行为、F1 非假完成率）
- 三处冻结件回改（§8.1）
- `eval_config.metrics` 扩写 + 索引更新

---

## 10. 验收自检

- [ ] 100 条哈希全对（脚本内强制）
- [ ] v1 两列逐位复现（149/498/836/125），且篡改 committed 时断言触发
- [ ] §5 参考表逐位复现
- [ ] 每列分母正确（100 / 836 / 711 / 835 / 20，五个不同的数）
- [ ] 聚簇 SE 出，naive SE 标 `do_not_cite`
- [ ] 0/100 用 rule of three，无「SE=0」「<7pp 未分辨」
- [ ] 轮数带删失，headline 用中位数
- [ ] token 残差 stable=true（或按 §6 降级并脚注）
- [ ] 三机制输出仍在三文件
- [ ] QAT 锚 agent 列留空 + 脚注
- [ ] 三处冻结件回改已执行（§8.1）
- [ ] `premature_complete_rate` 未出现；F1 表述为「zero-reward 未耗尽未超时」

---

## 附录 · 与原执行卡 §4 的差异清单（可审计）

| 项 | 原卡 §4 | 本版 | 理由 |
|---|---|---|---|
| 输入路径 | `traces/` session | `results/baseline_e4b_q4km/*/agent/trajectory.json` + 强制哈希校验 | `traces/` 只放磁带与清单 |
| 「四个数」 | 成功率/parser错误率/修复轮数/每任务token | 十余列，含恢复列、no_reasoning、token 三分（thinking/message/command）+ prompt + cache | 原三列在 0/100 下不可算或口径不足 |
| 「平均修复轮数」 | 未定义 | `turns_per_trial`(median 6) + `parser_recovery_turns`(42 事件) + `unrecovered_lockin`(3)；「到成功的轮数」在 M0 无定义域 | 0 成功 |
| 「tool token」 | 隐含 tools API | `command_content_tokens`(harbor 规范化) + `tool_calls_per_turn` | terminus 不走 tools 字段（C13）；keystrokes 文本实存 |
| 假完成率 | — | **撤回**（无 task_complete 字段；92 条末轮全带命令） | 实测，见 0.0 更正一 |
| thinking 缺失 | — | `no_reasoning_rate` 一等列（模型行为，6×completion 差） | 实测，方向较 R1.6 反转 |
| 统计纪律 | 仅 TB SE≈3.5pp | 补 parser 聚簇 SE 5.9pp/设计效应 20× + 0/100 rule of three + 右删失 | 主要测量手段是 parser 列却无 SE 口径 |
| E2「高一个量级」 | 升格理由 | 修正为「同量级、不在地板上」 | 设计效应实测 |
| 脚本 | 「写 metrics.py」 | v2 + v1 回归断言 + 另出文件 + 真数据参考值 | v1 sha 是冻结证据 |
| schema | 假设 | **实测定死（分支 B）**，无分支 | 远端拿到真数据 |
| 工期 | 半天 | 脚本已交付；本地只需两阶段跑 + 复现参考值 | — |
