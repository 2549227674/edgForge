# EdgeForge M1 · 执行卡(R1.0 开工规格版)

- 拟稿日期:2026-08-11
- 里程碑:M1(循环第一圈:SFT → OPD polish + PTQ 谱系)
- 状态:**开工规格,继承审查与 T0 已完成,T1 待执行**;T0 事实见 `t0_开工前置_2026-08-11.md`
- 建议入库路径:`docs/m1/README.md`
- 计划基准:《EdgeForge 蓝图终稿 v4-R2》§11 M1 行;机制事实:`docs/facts.md`;评测合同:`eval_config.yaml`(M0 冻结,M1 沿用不改)
- 执行卡性质:**已核实事实 + 操作建议,非命令**——真实机器前的判断优先,可自由偏离;偏离〔事实/雷区〕须留一句理由,〔建议〕随意改

---

## 0. 继承审查(开工时只需扫本节 `[未复核]` 标记)

以下具体数字/结论从蓝图、facts、台账或本次拟卡对话搬入,**未在本仓实测**,开工时逐项复核:

| # | 条目 | 来源 | 复核方式 |
|---|---|---|---|
| U-1 | Pro 6000 96GB ¥5.95/h;vGPU-48 ¥2.88/h;vGPU-32 ¥1.58/h `[未复核]` | 蓝图 §2 / 台账 | 实租日查平台报价 |
| U-2 | Pro 6000 实例 cgroup 内存 110 GiB `[已复核 2026-08-11]` | owner 订单口径 + 实机 | `memory.max=118111600640` bytes;`free -h` 只显宿主视图 |
| U-3 | E4B QLoRA `max_length=2,048` 实测峰值 allocated/reserved = 50.44/53.04 GiB `[已复核 2026-08-11]`;原“~17GB”估计不成立 | 台账 44 条 + T0 smoke | 长上下文峰值继续由 T1/T2 实测 |
| U-4 | teacher `gemma-4-31b-it` FP8 ~31GB `[未复核]` | 蓝图决策 16 | T3 加载后实测 |
| U-5 | TRL 1.9.2 experimental `DistillationTrainer` 参数 `[文档已复核]`;运行闭环 `[未复核]` | 2026-08-11 TRL 官方文档 | T3 spike |
| U-6 | teich 0.3.3 API `[API 已复核]`;冻结掩码语义 `[不兼容,已降级 2026-08-11]` | T0 20 条 spike | 7 条被丢弃,其余 13 条 token/mask 均非逐条相等;复用 M0 renderer |
| U-7 | 全池一 epoch ≈ 250–400M token `[未复核]`;Pro 6000 QLoRA SDPA 冒烟 2,895 input tok/s `[已复核 2026-08-11]` | 本次拟卡估算 + T0 smoke | 全池 token 总量由 T1 第 0 步复核 |
| U-8 | agent-32 档资源外推(GPU ~55–65 GiB / CPU ~95–105 GiB)`[未复核]` | 由 X4 实测线性外推 | 本卡不消费(agent-16 单档),仅留档 |
| U-9 | 2×vGPU-48 双实例 OPD fallback 的跨实例带宽可行性 `[未复核]` | 本次拟卡推断 | 仅触发 fallback 时验证 |
| U-10 | sm_120 + SDPA `[已复核 2026-08-11]`;E4B 整模 FA2/FA4 `[当前不适用]` | 2026-08-11 实机 + T0 smoke | E4B 滑窗/全局 head dim = 256/512;主线固定 SDPA |
| U-11 | TB 20×5 慢档单 candidate 墙钟 `[未复核]`(M0 未留总时长记录) | — | 首个慢档实跑记录,后续照排 |

### 0.1 开工入口扫查结果(2026-08-11)

本节已扫完;“待实跑”是按原定触发点保留,不阻塞进入 T0。

| 项 | 状态 | 扫查结论 / 下一触发点 |
|---|---|---|
| U-1 | 部分复核 | 实例已证为 RTX PRO 6000 96GB;shell 不提供计费单价,Pro 6000/vGPU 三档价格继续 `[未复核]`,以平台订单页为准 |
| U-2 | **已复核** | 订单口径 110GB;实机 cgroup `memory.max=118111600640` bytes = 110 GiB。`free -h` 显示的 1.0 TiB 是宿主视图,不作实例配额 |
| U-3 | **已复核** | E4B NF4 QLoRA + bf16 + SDPA,`max_length=2,048`,20/20 step 通过;峰值 allocated/reserved 50.44/53.04 GiB,原“~17GB”估计不成立 |
| U-4 | 待实跑 | teacher FP8 实际占用由 T3 加载后记录 |
| U-5 | **文档已复核** | TRL 1.9.2 当日文档仍为 `trl.experimental.distillation`:`lmbda=1.0` 全 on-policy,`beta=1.0` 为逆向 KL,外部 teacher 仍用 `use_teacher_server`/`teacher_model_server_url`;逆向 KL + teacher server 还要求 `loss_top_k=1`。运行闭环留给 T3 spike |
| U-6 | **实跑不兼容,已降级** | 20 条中 7 条因 `unsupported_tool_call` 被丢弃;剩余 13 条与冻结 renderer 的 token/mask 精确匹配均为 0/13,且 audit 捕获工具响应边界。按 §2.6 复用 `render_linec_samples.py` |
| U-7 | **吞吐已复核** | T0 SDPA 20-step = 2,894.78 input tok/s;全池 token 总量仍由 T1 第 0 步统计 |
| U-8 | 不消费 | M1 只用 agent-16,agent-32 外推保留为未复核档案,不构成阻塞 |
| U-9 | 条件触发 | 只在 fallback-B 真正启用时做跨实例 smoke |
| U-10 | **SDPA 已复核;FA2/FA4 不消费** | 实机 compute capability 12.0 / 97,887 MiB;PyTorch 2.11.0+cu128 可用且 20-step 通过。SM120 已有部分 FA4 beta 路径,但 E4B 滑窗 `head_dim=256`、全局 `global_head_dim=512`;当前不能作为可靠整模训练后端。取消 1.036GB FA2 下载;不装系统 toolkit、不源码编译 |
| U-11 | 待实跑 | 首个 TB 20×5 慢档记录墙钟后销号 |

机器入口记录:云端为 RTX PRO 6000 Blackwell Server Edition(compute capability 12.0),96GB GPU / 110GB RAM / 250GB 标称存储;容器可见 30 GiB 系统盘 + 200 GiB 数据挂载。学术加速在 SSH shell 中经 `source /etc/network_turbo` 启用后,GitHub 与 Hugging Face 均返回 HTTP 200。板端连通已确认:Orange Pi 5 / RK3588 / 8 CPU / 15 GiB RAM / 117 GiB NVMe;M1 本卡不上板,因此不做额外板端检查。外部依据:[TRL Distillation Trainer](https://huggingface.co/docs/trl/distillation_trainer),[teich PyPI](https://pypi.org/project/teich/)。

M0 教训(facts 6.6)在此重申:**数值相等不构成同一集合的证据;未经实证的身份/数字,无论继承还是当场推断,一律打标。**

---

## 1. 范围与本卡决策登记

### 1.1 M1 = 六条线

```text
T0 前置:环境/探针/纪律       (¥25–50, ~1 天)
T1 数据消费:全量渲染 + 赛马续跑 (raw-uniform vs 80/20)
T2 SFT:M0 冻结 renderer→QLoRA→merge = C01-S
T3 OPD polish:决策 16 调用① = C02-S.O(M1 模型)
P  PTQ 谱系:从 S.O 出发的 llama.cpp 无-imatrix 纵队(5 新格)
B  板向工件:agent-16 校准集定义 + S.O→W8A8 build-only(不上板)
横切:B0 补测(HumanEval 全量 + GSM8K 全量)、快/慢档评测、对照表 v1、candidate 快照
```

### 1.2 owner 已拍板(2026-08-11 对话,均为决策级)

| # | 决策 | 结论 |
|---|---|---|
| D-1 | T1 配方对照形态 | **赛马续跑**:raw-uniform 与 80/20 各训至 1/8 预算(同超参、同 seed 纪律),按 §3.4 预注册判据比对;赢家从自身 checkpoint 续跑至全量。60/40 剔除 |
| D-2 | 校准集 | agent 域校准集定义**提前至 M1**,单档 **agent-16**(≈112,946 token),不设 agent-32 机会位;**不跑官方 19 条对照**;S.O→W8A8 **build-only,不上板** |
| D-3 | 租卡 | **全程 Pro 6000 96GB** + 双重 fallback(§7.2);SFT 不再走 vGPU-32(蓝图 §11 M1 行括号为过时值,费用差百元级而墙钟/单环境收益更大) |
| D-4 | 慢档左值补齐 | 以 **M1 身份**补测 B0 的 HumanEval 全量(164)与 GSM8K 全量(1,319),同一冻结合同、同一端点会话;不追改 M0 文档 |
| D-5 | 评测载体约定 | 训练级 candidate(S、S.O)统一以 **Q4_K_M 无 imatrix**(B0 同配方、同 llama.cpp commit)转换为纵向评测载体,隔离训练旋钮;该载体同时充当 PTQ 谱系的 Q4_K_M 格 |

### 1.3 蓝图 §1 决策表回写建议(两行,owner 审后粘贴)

> | 19 | 门⑥配方对照降档 | 60/40 剔除;raw-uniform vs 80/20 赛马续跑(各 1/8 预算对照,赢家续跑至全量),平局默认 raw-uniform | 3,177 条小池在 40% 权重下平均每条重复 ~19 次,过拟合先验最差;续跑设计使对照边际成本≈输家的 1/8 段(~¥25–50) |
> | 20 | 校准集提前与档位 | agent 域校准集定义提前至 M1,单档 agent-16;S.O→W8A8 build-only 不上板;官方 19 条对照不做,H2 保持未归因;M2 若重开,B0 须以同一 agent-16 重转以配对 | agent-16 处于 X4 已证安全包络(N=128/105,865 tok 成功:CPU 61.5 GiB / GPU 38 GiB);板端 3-core 未解锁,规模效应实验回报不确定,不预付 |

联动:§11 M1 行括号 `(vGPU-32)` 改 `(Pro 6000 96GB,fallback 见 M1 卡)`。

---

## 2. 线 T0 · 开工前置(全线阻塞项,先做)

1. **实租复核**〔纪律〕:Pro 6000 到手当日记录:实际价格、`nvidia-smi`(核对 sm_120 与 96GB)、cgroup `memory.max` + `free -h`(核对 U-2)、CUDA toolkit/runtime 版本(**13.2 禁用**,facts 4.3〔雷区〕;`nvidia-smi` 页眉仅表示驱动兼容上限)、磁盘容量与挂载点。
2. **sm_120 训练栈 smoke**〔雷区,U-10〕:装训练环境(Transformers/TRL/PEFT/bitsandbytes;Unsloth 视 spike 结论),E4B QLoRA 跑 20 step;attention 后端按"SDPA 先行,预编译 flash-attn 轮子为升级项"处理;**pip flash-attn 直装禁止**(facts 1.6)。**若 smoke 失败且当日不可修:触发 fallback-A(§7.2)。**
3. **三坑 20-step loss smoke**〔事实/雷区,facts 4.2,强制〕:① 跨层 KV 共享 × `use_cache` → loss 发散;② fp16 mask 溢出 → **一律 bf16**;③ chat/thinking 模板不一致 → 与冻结模板(18,569 bytes,SHA-256 `0a2c8073…`)逐字节核对训练侧实际渲染。三项全过才准开正式训练。
4. **数据身份冻结**〔纪律,facts 6.3:语料不可再生〕:对 `data/pipeline/mix_records/` 5 个 JSONL 生成 SHA-256 manifest(新文件 `manifests/mix_records_sha256.json`)并入库;训练机上传后先校验再消费。第二介质备份缺口维持 M0 声明状态,本卡不伪称完成。
5. **seed 纪律**〔纪律,M0 教训:"seed 未可证地固定"〕:数据抽样序、初始化、rollout 采样的 seed 全部显式设置并写入 candidate 快照;不承诺逐 bit 确定性,但 seed 记录必须可证。
6. **teich spike**〔建议,U-6〕:半天上限——装 teich,对 1 个来源走 `load_traces→prepare_data→mask_data`,与门⑦冻结掩码语义(loss 落 assistant content+thought+tool-call;system/user/工具声明/tool response/turn 标记掩除)逐条比对 20 条。**若掩码语义不合或 API 变动过大:降级为自研渲染器(复用 `render_linec_samples.py` 路径),偏离理由记快照。**

### 2.1 T0 实跑结论(2026-08-11)

T0 已完成并进入 T1。SDPA 20-step、bf16、冻结模板、数据 manifest 与 seed 纪律均通过;平台单价因 shell 不可见而保留显式缺口。Teich 0.3.3 与冻结语义不兼容,已按本节预案降级为 M0 renderer。完整命令、版本与数值见 `t0_开工前置_2026-08-11.md`。

---

## 3. 线 T1 · 数据消费

### 3.1 第 0 步:全量渲染与统计(定预算的地板)

- 以门⑦冻结口径(`enable_thinking=true`、`preserve_thinking=true`)渲染全池 154,097 条,产出:**渲染 token 总量、按家族/task_type 分组的长度直方图、>8,192 与 >16,384 条数**。
- 〔事实〕已知分布锚(facts 5.13):p50/p90/p95/max = 827/3,055/3,912/**4,060,703**;2,555 条 >16,384(1.66%)。
- `max_seq_length`〔建议〕:候选 16,384(覆盖 98.3%),但 T0 在 2,048 已实测 reserved 53.04 GiB,因此 16,384 **尚未获显存许可**。超长样本由 M0 冻结 renderer 外围的确定性裁剪层处理:①按消息边界反复删除尾部完整 follow-up 回合并重渲染;②若不可再删仍超长,则对 `input_ids`/loss mask 同步保留前 `max_seq_length` token;③裁后无任何监督 token 才丢弃。逐条记录原始/保留 token 数、删除消息数、裁剪模式和 drop reason;禁止静默裁剪。**最终长度由本节直方图 + 4K/8K/候选长度显存阶梯 smoke 决定,预注册进快照后不再改。**
- 子代理权重〔建议〕:`is_subagent` 不做降权,原样进入两配方(本圈变量最少原则);字段保留供后续圈调。

### 3.2 留出验证集(门⑥ early stopping 的仪器)

〔建议〕从规范池按 家族 × task_type 分层抽 ~1,500 条(≈1%),冻结 manifest(`manifests/m1_holdout.json`),**训练与 OPD 的 prompt 池双双排除**;验证 loss 按门⑦同掩码计算。early stopping 规则预注册:验证 loss 连续 2 个评估点无改善即停(评估间隔 = 总 step 的 1/16,〔建议〕可调)。

### 3.3 两配方定义(引 `data/mix.yaml`,不重复数字)

raw-uniform = 池自然比例(Anthropic 风格标签 97.94%);80/20 = 训练时把其他家族(3,177 条)上采样至 20% 权重,平均每条重复 ~9.7 次/epoch 当量。均为采样实现,不动数据。〔事实〕来源标签 ≠ 已核实 teacher 身份(门⑥口径),对照表措辞沿用 `claimed_anthropic_from_source_label`。

### 3.4 赛马续跑协议(预注册,开工后不改)

1. 两配方同超参、同 seed 纪律、同 `max_seq_length`,各训至 **1/8 全量 token 预算**;checkpoint 落盘。
2. 比对(在 1/8 checkpoint 上):**主判据 = 留出验证 loss**;差 ≥ 2× 验证集 loss 标准误判胜负,否则平局。副观察(不判胜负,仅红旗用):BFCL `simple_python`、GSM8K fast-200 各跑一遍(载体 = 各自 Q4_K_M 临时转换)。
3. **平局默认 raw-uniform**(自然分布 = 零假设,少一层人为假设)。
4. 赢家从自身 1/8 checkpoint **续跑**剩余 7/8;输家 checkpoint 留档不删(语料级资产纪律)。
5. 全程两配方的采样实现与 mix hash 写入快照;判定书(数字 + 规则引用)入 `results/m1/recipe_race.md`。

---

## 4. 线 T2 · SFT(C01-S)

- 基座〔事实〕:`google/gemma-4-e4b-it` bf16(蓝图 §3 基座声明;QAT-unquantized 非基座)。
- 配方〔建议〕:QLoRA(4-bit NF4 底座 + bf16 LoRA),r/alpha/lr/warmup 开工按当日 Unsloth/TRL 推荐起步并全部记快照;**bf16 强制**(三坑②);epoch 当量 1(= 赛马 1/8 + 续跑 7/8),early stopping 按 §3.2。
- 96GB 显存富余的用法〔建议〕:优先加大 batch/梯度累积与 `max_seq_length` 覆盖率,**不**改为全参或 bf16-LoRA(那是另一个旋钮,本圈不动)。
- merge〔建议〕:LoRA merge 回 bf16 → 完整 checkpoint 落盘 + SHA-256;此为 candidate **C01-S** 的权重身份。
- 评测载体(D-5)〔纪律〕:`convert_hf_to_gguf --outtype bf16` → `llama-quantize Q4_K_M`,**命令与 llama.cpp commit(`ad8d821…`)与 B0 完全一致**,无 imatrix;载体 SHA 入快照。对照 B0 时唯一变量 = 训练。
- 20-step loss smoke 通过记录随 run 归档(§2.3)。

---

## 5. 线 T3 · OPD polish(C02-S.O,决策 16 调用①)

### 5.1 架构(决策 16 冻结,本节只做操作化)

统一机器双调用之调用①:同一张 Pro 6000 上,vLLM 起 teacher(`gemma-4-31b-it` bf16→FP8)logprob 打分服务,学生 = C01-S 之上继续 QLoRA;GKD 逐 token **逆向 KL**;同族同 tokenizer(〔事实〕E4B 与 31B 均 dense,facts 4.5;跨 tokenizer 的 GKD 会静默算错,TRL issue #4562 佐证决策 16 理由)。

### 5.2 实现路线〔建议,U-5〕

主线 = TRL 1.9.2 experimental `DistillationTrainer`:teacher 起独立 vLLM server(`use_teacher_server=True` + `teacher_model_server_url`),`lmbda=1.0` 全 on-policy;`beta=1.0` 逆向 KL;teacher server 模式下配 `loss_top_k=1`。若实装版本不是 1.9.2,再查对应版本文档(experimental namespace,API 可变)。备选 = verl OPD recipe(多卡 RL 基建,单卡场景过重,仅主线不可用时评估)。**开工 spike(半天上限):最小 prompt 集跑通 rollout→teacher 打分→loss 回传;失败两次则升级讨论,不硬扛。**

### 5.3 teacher 准备与显存账

- FP8 转换〔建议〕:优先 vLLM 在线 FP8(`--quantization fp8` 动态)起服务;若显存/吞吐不达标再离线 llm-compressor 出 FP8 checkpoint。teacher 权重预算 ~31GB `[未复核 U-4]`。
- 同卡预算〔T0 已推翻原估〕:teacher FP8 ~31G `[未复核 U-4]` + 学生 QLoRA 在 2,048 smoke 已实测 reserved **53.04 GiB** = ~84 GiB,尚未计 teacher KV、rollout 缓冲与长上下文增量,因此原“同卡 ≤96G”包络**不成立**。T3 开工先做 teacher/学生分阶段加载与最小回传 smoke;只有实测共驻留通过才进入同卡主线,否则直接触发 fallback-B,不再预设 `gpu_memory_utilization=0.40` 可行。
- **logprob 一致性 smoke**〔雷区,新增〕:同一模型同一序列的 logprob 在 HF 与 vLLM 间可因实现差异不一致(外部先例在案)。正式跑前:teacher 对固定 32 条序列分别以 vLLM 服务与 HF 前向各算一遍 per-token logprob,偏差分布留档;异常大则先归因再开跑。

### 5.4 prompt 池与预算

- prompt 池〔建议〕:从规范池(按赛马赢家配方分布)抽取**对话前缀**(截至任一 assistant 轮开始处,前缀 ≤8,192 token),排除 §3.2 留出集;冻结 prompt 清单 manifest。前缀式比仅首轮更贴 agent 部署分布。
- 预算〔建议〕:rollout 生成总量 ~10–30M token(SFT 预算的 5–10% 量级,polish 定位);`max_new_tokens` ~2,048;thinking 开(与门⑦/部署一致)。early stopping 同用留出验证 loss + 快档红旗。
- 产物:OPD 后 LoRA merge → bf16 checkpoint + SHA = **C02-S.O**;Q4_K_M 载体同 D-5。
- 〔事实〕S.O 对 stock draft 的 acceptance 是存活矩阵首测空白格(蓝图 §7):**本卡只保证 S 与 S.O 的 bf16 工件完整留存**,acceptance 测量可延后至 vLLM-local 环境就绪的里程碑,不算 M1 缺口。

---

## 6. 线 P · PTQ 谱系(从 C02-S.O 出发)

〔建议〕清单 = llama.cpp 无-imatrix 纵队,粗→细:

| candidate | 格式 | 备注 |
|---|---|---|
| (C02 载体) | Q4_K_M | D-5 已产出,免费格,不重复编号 |
| C03-S.O.P(Q8_0) | Q8_0 | 近无损上锚 |
| C04-S.O.P(Q6_K) | Q6_K | |
| C05-S.O.P(Q5_K_M) | Q5_K_M | |
| C06-S.O.P(Q4_0) | Q4_0 | 项目自转 PTQ Q4_0;〔雷区,facts 2.1〕与官方 QAT-Q4_0 谱系严格分列 `training_lineage`/`quantization_format`,"遗留格式"评语仅限 PTQ 间比较 |
| C07-S.O.P(Q3_K_M) | Q3_K_M | 下探退化拐点 |

- imatrix 轴**本圈不开**(引入校准数据 = 第二旋钮;留后续圈)。
- 每格:量化命令原文 + SHA + 快档全套;晋级线与慢档按 §8。
- 5 新格 × 快档 ~1–2h ≈ 本地 1–2 天墙钟,与 T3 并行。

---

## 7. 线 B · agent-16 校准集 + W8A8 build-only

### 7.1 校准集定义(新身份,不复用 M0 X 运行目录——M2 清单要求)

1. 从规范池按 家族 × task_type 分层抽 **16 条**,排除留出集;以门⑦口径渲染、**16,384 截断**(〔事实〕toolkit B 层硬上限,facts 5.10),转 `data_quant.json` 的 input/target 形态;目标 token 量对齐 P5 勘测锚 ≈112,946 `[允许 ±20%]`。
2. 冻结 `manifests/m1_calib_agent16_sha256.json`(逐条 UID、渲染 SHA、token 数)。
3. 〔事实〕安全包络:X4 实测 N=128(105,865 tok)build 成功于 CPU HWM 61.5 GiB / GPU 38,080 MiB(facts 5.24)——agent-16 同量级,在 96GB GPU / 110–120GB RAM 内安全。
4. 〔雷区,facts 5.25〕**TMPDIR 修复必用**:`TMPDIR/TMP/TEMP`、工作目录与最终 `.rkllm` 工件同时固定到同一 run-scoped 大容量数据盘;build 前以 `SpooledTemporaryFile` 复现 39,321,600-byte 写入探针。

### 7.2 build 与登记

- 合同:RKLLM 1.3.0、RK3588、`w8a8`、`max_context=16384`;输入 = C02-S.O 的 HF 权重(转换前逐文件 SHA 校验,冻结输入纪律沿 M0)。
- 产物:`.rkllm` 工件 + SHA,登记为 **C08-S.O.W8A8(agent16)**;**不上板、不评测、不宣称质量**。
- **登记纪律**〔纪律,防继承污染〕:M0 的 B0-W8A8 用官方 19 条校准;本工件换 agent-16,板端纵列一次变了两个旋钮(训练+校准)。M1 无板端比较故无害;**M2 若重开,B0 须以同一 agent-16 重转配对后方可对照**。此句随工件登记原文保留。
- H2/H3 维持**未归因**;本卡不做且不暗示"agent 域校准更好"的任何宣称。
- fallback 见 §9.2。

---

## 8. 评测、晋级与对照表 v1

### 8.1 B0 补测(D-4,开工即可做,与训练并行)

同一冻结合同(B0 Q4_K_M、llama.cpp `ad8d821…`、131K/q8_0 KV、冻结采样)单次端点会话内:HumanEval **164 全量** + GSM8K **1,319 全量**。结果以 M1 身份入对照表 before 行;M0 文档不动。〔雷区,M0 §3〕HumanEval 执行器须将 `TMPDIR/TMP/TEMP` 置于 Linux `/tmp`。

### 8.2 快档(每个 candidate 必跑,合同 = eval_config 冻结值)

① 5 盘磁带 ×2 遍(只计第二遍 cache-warm)→ TTFT/TPOT/吞吐;② BFCL `simple_python` 400;③ 烟测对 2 题;④ GSM8K fast-200。
**晋级线**(蓝图 5.2):工具调用准确率相对**父 candidate** 掉 ≤3pp 且 GSM8K 快抽样掉 ≤3pp;系统指标回归须有解释。父子关系:S←B0(注:跨训练旋钮,晋级线照用但解释权归对照表)、S.O←S、P 线各格←S.O(载体格)。

### 8.3 慢档(晋级者)

TB 2.1 20×5(本地串行为主;租卡整批为墙钟兜底)+ MMLU fast-500 + GSM8K 全量 + HumanEval 全量。统计纪律〔事实,facts 6.1〕:成功率差 <7pp 一律"未分辨"(聚簇 SE≈5.9pp);归因主线 = 工具准确率 / parser 硬错误率 / 修复轮数 / 每任务 token。B0 的 TB=0/100 系地板,S/S.O 的 TB 列以 rule-of-three 口径解读。

### 8.4 A/C 对照表 v1 列定义(M1 验收物)

candidate | 谱系(training_lineage / quantization_method / format)| 工件 SHA | 尺寸 | TB 20×5 | BFCL | hard/soft parser | MMLU fast-500 | GSM8K fast-200 / 全量 | HumanEval 全量 | TTFT p50/p95 | TPOT p50 | 吞吐 p50 | 快照指针。行:B0(补齐后)、C01-S、C02-S.O、P 线晋级者;官方 QAT 锚保持独立锚区不混入。

---

## 9. 登记、预算与 fallback

### 9.1 candidate 快照(蓝图 §10,缺项不入表)

目录〔建议〕`configs/m1/candidates/C{NN}.yaml`:父 candidate、本圈唯一旋钮、数据 mix hash(含赛马判定书指针)、seed 清单、训练/量化/转换命令原文、引擎 SHA、快档结果指针、20-step smoke 与(T3)logprob smoke 证据指针。

### 9.2 双重 fallback(D-3)

- **fallback-A(SFT/校准)**:T0 的同配置 QLoRA reserved 53.04 GiB 已超过 vGPU-48 名义 48GB,故原“原样落 vGPU-48”fallback **撤销**。Pro 6000 缺货或 sm_120 栈不可修时,必须另选 ≥64GB GPU,或先以更短 `max_seq_length`/更小训练包络重跑 smoke 后再决策;不得把未经实测的降配写成等价 fallback。agent-16 build 的 GPU 38G/CPU 62G 包络仍可单独落 vGPU-48,不代表 SFT 可落。
- **fallback-B(OPD)**:→ **2×vGPU-48 双实例**,teacher vLLM server 独立实例 + TRL `use_teacher_server` 跨机(合计 ¥5.76/h ≈ Pro 6000);带宽可行性 `[未复核 U-9]`,触发时先 smoke。

### 9.3 预算与日历(全 `[未复核 U-7]`,T0/T1 实测后回填)

| 项 | 时长估 | 费用估(¥5.95/h) |
|---|---|---|
| T0 前置 + 两 spike | 4–8h | ¥25–50 |
| T1 赛马(2 × 1/8) | 8–16h | ¥50–95 |
| T2 续跑(7/8) | 13–40h | ¥80–240 |
| T3 OPD | 10–30h | ¥60–180 |
| B 线校准 + build | 4–10h | ¥25–60 |
| 慢档租卡兜底(可选) | — | ¥0–150 |
| **合计** | | **≈¥240–775** |

日历〔建议〕:T0 一天 → T1 赛马 1–2 天 → T2 续跑 1–2 天(P 线/B0 补测本地并行)→ T3 2–3 天 → P/B 线收尾 + 慢档 2–3 天 ≈ **1.5–2.5 周**,贴 9 月初 M0–M3 地板。进度单位 = 入表的可审计格子数,非跑通的命令数(facts 6.5)。

---

## 10. M1 雷区索引(开工前查)

| 雷 | 内容 | 触发场景 |
|---|---|---|
| 三坑 smoke | KV 共享 × use_cache 发散;fp16 mask NaN;模板不一致 | T2/T3 每个正式 run 前(§2.3) |
| CUDA 13.2 toolkit/runtime | Unsloth 明禁;`nvidia-smi` 页眉的 13.2 仅是驱动兼容上限 | 租卡镜像选择 |
| sm_120 禁 pip flash-attn | issue #1987 | Pro 6000 全程;走 SDPA/预编译轮子 |
| HF↔vLLM logprob 差异 | 同模型同序列 logprob 可不一致 | T3 teacher 打分通道,先做一致性 smoke(§5.3) |
| TRL experimental API | DistillationTrainer 在 experimental namespace,可变 | 开工日读当日文档,spike 先行 |
| teich alpha | API 未在本仓训练侧实测 | §2.6 spike;不合即降级自研渲染 |
| Q4_0 谱系混淆 | 项目 PTQ Q4_0 ≠ 官方 QAT-Q4_0 | C06 登记双列分离(facts 2.1) |
| RKLLM 导出 scratch | TMPDIR 未固定 → 假性磁盘不足 | B 线 build(facts 5.25) |
| max_context 16,384 硬上限 | toolkit B 层拒绝 32K/131K | B 线校准渲染截断(facts 5.10) |
| 上游语料冻结 | 不可再生;仓库名/文件名数字非行数证据 | T0 manifest 校验(§2.4) |
| seed 可证性 | M0 先例:seed 未可证固定 | 所有 run(§2.5) |
| 网络抖动 | 不解释为模型失败 | 慢档 TB 串行 + 镜像预拉(facts 6.2) |

---

## 11. 验收清单(预注册;勾选 = 形成可审计结论或显式缺口)

- [x] T0 五项前置证据齐(实租记录 / sm_120 smoke / 三坑 smoke / mix_records manifest / seed 纪律声明;单价显式缺口)
- [ ] 赛马判定书 + 默认配方结论(`results/m1/recipe_race.md`)
- [ ] C01-S、C02-S.O:bf16 权重 SHA + Q4_K_M 载体 SHA + 快档全套 + 慢档全套入表
- [ ] B0 before 行补齐(HumanEval 164 / GSM8K 1,319)
- [ ] P 线 C03–C07 快档入表;晋级者慢档完成
- [ ] agent-16 校准 manifest + C08 工件登记(含双旋钮登记纪律原文;不上板)
- [ ] A/C 对照表 v1 成文(§8.4 列齐;缺格显式标注而非留白)
- [ ] 全部 candidate 快照齐全;蓝图 §1 回写决策 19/20
- [ ] `[未复核]` 清单逐项销号或转正为新雷区条目

## 12. 明确不做

上板运行与任何板端评测;3-core 任何尝试;H2/H3 归因宣称;官方 19 条校准对照;60/40 配方;imatrix 轴;AWQ/GPTQ 与 vLLM-local 环境(acceptance 首测延后,工件留存即可);12B/E2B;QAT;剪枝;从头 draft;任何 RL;第二介质备份补齐(缺口维持声明状态)。

---

*本卡执行完毕后按 M0 惯例出事实版收口;下一张卡按里程碑链依赖序另开,不预写。*
