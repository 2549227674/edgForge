# EdgeForge · 蓝图终稿（v4-R2）

> 定稿日期：2026-07-16。取代 07_v3 / 08_v3 / 09_v3 的计划职能（三份原文档归档不删，事实与调研内容按 §12 指针继承）。
> 文档制度：本文 = **稳定层**，改动需决策级理由并记入 §1 决策表；执行细节走**滚动层**（每个里程碑开工时出一张执行卡，做完再出下一张，不预写）。
> **执行卡制度**：执行卡是"已核实事实 + 操作建议"，非命令——真实机器前的判断优先，可自由偏离。卡内容双标注：**〔事实/雷区〕**（源自 04 台账或已核实结论，偏离需留一句理由）与**〔建议〕**（操作起点，随意改）；每张卡开头带一行**继承审查**——凡从原 zip 搬入、本对话未复核的具体数字/阈值/清单，一律标 `[未复核]`，开工时只需扫这些标记，无需回审全部历史文档。（此机制的必要性由 1k–10k 事件证明：错误常伪装成"既定背景设定"，不显式标记就会被无脑继承。）
> 继承层（不重写，只引用）：04 事实台账（版本锚点/坑清单，滚动修订）、R1–R4 调研报告（数据集/许可/benchmark 结论）、13 号发布卫生原则。
> **修订 R1（2026-07-16）**：决策 3 双线化（Google QAT 双格式锚点证实）；新增决策 14（PC 双引擎）、15（NVFP4 保留）；§4.3 QAT 锚点家族；§7 由曲线升级为矩阵并做场地分层（acceptance 本地化）；§4.1/§6/§11/§12/§13 联动更新。
> **修订 R2（2026-07-19）**：项目更名 **EdgeForge**（原 PiLoop——命名根由 Pi live loop 与 Pi 二开均已废弃/边缘化，旧名失去指称对象；旧文件名与交接包引用不批量改，仅 git mv 蓝图与执行卡两份活文档，正文统一新名）。新增决策 16（OPD 支线：统一机器双调用）；§0 一句话与 §3 DAG 增 [O] 节点；§2 租卡档位增 Pro 6000 96GB；§11 M1/M4 联动；§13 增蒸馏叙事更新与简历双线拆分口径；§14 增 MOPD 不做项；§7 存活矩阵行清单联动（S 与 S.O 分行，新增"OPD 重训 × stock draft"首测空白格；剪枝行注明含 O₂ 恢复）。
> **修订 R3（2026-07-24）**：新增决策 17，批准 q8_0 K/V @131072 为全项目纵向基线 KV 协议；为保留 llama.cpp 多槽并发头寸，f16 KV 不做消融，所有 candidate 沿用该配置。
> **修订 R4（2026-07-24）**：§5.1 的单序列协议上下文定为 131072；boot log 证实 `n_ctx_train=131072` 为原生上下文，iSWA 拓扑使该档位可行。多槽时保持每槽 131072，并按槽数放大 `-c` 总量；板端上下文档位留待 M2 实测。

---

## 0. 项目定义

**一句话**：把 Gemma4 家族（E4B 为贯穿轴）沿"微调蒸馏（跨族离线 + 同族在策略）→ 多粒度量化 → 剪枝+恢复 → QAT → 混合精度/NAS 搜索"的一体化优化循环推到底，每一圈产出的 candidate 部署到 PC（llama.cpp）/ RK3588（RKLLM）/ 租卡（vLLM）三档硬件，在**全程冻结**的评测协议（agent 能力 + 通用能力不塌陷 + 系统指标）上与官方原精度、第三方同精度量化对照；算子分析与自定义 kernel 贯穿全程（4060 主场，板端做跨 ISA 对照面）。

**交付物**：不是某个模型，是——
1. 主表：candidate × {TB 成功率, 工具调用准确率, MMLU/GSM8K/HumanEval, TTFT/TPOT/吞吐, 尺寸/内存} × 硬件档 的全量对照表；
2. 三个发布候选（PC-RC / Board-RC / Cloud-RC，从主表按 §1-2 标准选出）；
3. 投机兼容性存活曲线（工序 × acceptance length，公开空白）；
4. kernel 池产出（每个含 roofline 相对分 + ncu 归因 + 端到端回连报告）；
5. 层选择性混合精度 vs uniform 对照报告；
6. 数据卡（七道门漏斗表 + 去污染声明）。

**不是什么**：不是 agent 产品、不是 kernel 教程仓库、不是刷榜（4B 微调版不以打过官方大模型为目标）、不发布任何权重（全语料 AGPL 系，只发评测报告）。

---

## 1. 决策记录（18 条，已全部拍板）

| # | 决策 | 结论 | 关键理由 |
|---|---|---|---|
| 1 | 尺寸布局 | **A**：E4B 完整循环；E2B/12B 配方迁移 | 保住"同模型跨硬件"对照列；三尺寸全循环 = 三倍成本换冗余信息；配方跨尺寸迁移性本身是发现 |
| 2 | 发布候选标准 | 各硬件档内：**TB 子集掉分 ≤3pp 且 GSM8K 掉分 ≤3pp 前提下，取最快/最小** | 阈值可在主表数据齐后复议一次 |
| 3 | QAT 深度 | **B-R1（双线双锚）**：QAT→Q4_0（llama.cpp 部署，锚 `google/*-qat-q4_0-gguf`）与 QAT→W4A16-ct（vLLM 部署，锚 `google/*-qat-w4a16-ct`）各做"我的 QAT vs 官方 QAT vs 我的 PTQ"三点对照；QAT→W8A8 维持先做 RKLLM 方案匹配小实验；可选分支：`qat-q4_0-unquantized` 作 SFT 底座的逆序探索（M6 可选位，非主线） | QAT 收益只在假量化方案=部署端真方案时兑现；Google QAT 家族提供双格式官方锚点（§4.3）；RKLLM 方案仍不公开 |
| 4 | 剪枝范围 | **B**：深度+宽度都做；深度先行，宽度进 M7 搜索空间 | 深度便宜雷少；宽度触 GQA/宽 KV 几何（E4B 端侧卖点），必须搜索而非拍脑袋 |
| 5 | NAS-lite 空间 | **A**：受限空间 = {深度剪枝配置 × 每层精度分配}，候选 ≤8 个/轮；官方嵌套切片轴（若模型卡证实 E4B 含 E2B 级子网）优先探索 | 开放搜索是无底洞 |
| 6 | 投机实验层级 | **C**：全工序存活曲线 + acceptance 崩塌后做 draft 短程再对齐；从头训 DSpark 式 draft = stretch | 中间 candidate 循环本来就产出，测量边际成本≈0；只测最终版丢归因 |
| 7 | 慢档评测规模 | TB 2.1 子集 **20 题 × k=5**（串行，可整批扔租卡）；SWE-bench Pro 子集租卡窗口选做 | 100 次试验下 SE≈3.5pp，成功率差 <7pp 视为噪声，归因靠快档辅助指标 |
| 8 | 通用能力套件 | **MMLU 抽样子集 + GSM8K + HumanEval**，lm-eval-harness 钉版本 | GSM8K 是量化退化最敏感金丝雀（4B NVFP4 AIME −17pp 先例）；GPQA-Diamond 对 4B 贴地板，弃用 |
| 9 | FA3 对照 | **B**：放弃 FA3/FA4；云档 attention 后端轴 = FlashInfer / FA2 / SDPA | 租卡池无 Hopper（sm_90）；sm_120 禁 pip flash-attn |
| 10 | 12B 活动范围 | **A**：仅云档；兼任 DSpark draft 官方目标 | PC 8GB 塞不下；板端 12GB/16GB 勉强且速度不可用 |
| 11 | KernelBench | **B**：借口径（roofline 相对分/随机化正确性）+ 选做子集题（agent 辅助 kernel 小实验）；两个 kernelbench trace 数据集**永不进训练**（去污已定） | 兼顾方法论与差异化实验 |
| 12 | 板端算子 | **全做**：NEON kernel / RKNN matmul 微基准 / 层级归因 | 三件都轻量高信息比，且对应面经密集考点（SIMD/NEON） |
| 13 | 层选择性混合精度 | **做**：逐层敏感度扫描 + ModelOpt AutoQuantize 生成配置，vs 官方 uniform 默认对照，挂 M7 | 敏感度不可加（层间误差抵偿）；MoE 有效参数架构直接适用；有"同分 +20% 吞吐"外部先例 |
| 14 | PC 双引擎 | **定**：llama.cpp 主（GGUF/k-quant 家族、int-KV 轴、QAT-Q4_0 线、agent serving）+ vLLM-local 副（AWQ/GPTQ/compressed-tensors 粒度轴、2:4 本地兑现、QAT-W4A16 线、调度器对照、投机 acceptance 本地测量） | 两组独占能力互不覆盖；调度器对照实验定义上需要双引擎；E4B AWQ ≈3GB 进 8GB 无压力 |
| 15 | NVFP4 列 | **保留**（租卡 P1，可独立裁剪、砍掉不伤主表骨架） | 4B 级 NVFP4 在 agent 任务上的退化是公开空白格；现成 checkpoint + ModelOpt 一个周末窗口的成本 |
| 16 | OPD 支线 | **统一机器，双调用**：GKD 逐 token 反向 KL + vLLM 起 teacher FP8 logprob 打分服务 + 学生 QLoRA；租卡 RTX Pro 6000 96GB 单卡（¥5.95/h，teacher FP8 ~31GB 与学生 ~17GB 同卡共存）。调用①：M1 SFT 后 polish，teacher = `gemma-4-31b-it`（dense，bf16→FP8）；调用②：M4 剪枝后恢复蒸馏的 loss 即此，teacher = **剪枝前 merged checkpoint**。同一代码路径，teacher 仅为配置里一行地址；评测走既有冻结协议 | Fable teacher 已下线（语料冻结根因），离线蒸馏物理上不可升级为 OPD，同族 31B dense 补位（26B 为 MoE、E4B/31B 为 dense，官方技术报告证实；同族同 tokenizer 规避跨族错配与 rollout 漂移放大）；恢复蒸馏 teacher 必须是剪枝前自身——原版 31B 没学过 Pi/teich 工具格式与 agent 行为，会一边恢复容量一边冲刷 SFT 习得能力，且父模型分布近、避开"teacher 对学生 token 概率塌掉致信号失效"的多轮失败模式；SFT 冷启动→OPD 精修是 Qwen3/Thinking Machines 的标准配方顺序 |
| 17 | 基线 KV 协议 | **冻结**：基线 K/V 均为 `q8_0`，单序列 `n_ctx=131072`；M1–M7 所有 candidate 的纵向对照沿用此配置。f16 KV 不做消融 | 按 boot log 实测预算（可用 7096 − 模型 2868 − compute 711 ≈ 3517 MiB 可用于 KV），f16 约 2088 MiB/序列仅容 1 条序列，会把 llama.cpp 侧并发上限锁死为 1，使决策 14 的调度器对照（槽位式 vs continuous batching）无法执行；q8_0 1109 MiB/序列可容约 3 条。故 KV 量化不再是实验轴，而是基线冻结项，全项目 candidate 一律沿用 |
| 18 | Line C 数据治理 | **定**：门②只处理可验证的字面重叠；门④新增 ④b 退化/模板/身份噪声检测；门⑥全量保留硬过滤后数据，以保守源模型家族 × Hermes `category`/`subcategory` 双轴记录分布，家族比例仅在训练时采样实现。Mythos 仅在去样板、去重后达到原集 2% 才可作小比例掺料，否则整集剔除。 | Mythos 实测为高度模板化合成镜像，不是可靠配平锚；来源标签不等于 teacher 身份。Crown 上游实际为 228,968 行聚合 export，且实测合格池的家族极不均衡；不为未验证的比例先删除可用样本。 |

已废弃的 v3 机制：三支柱框架与 6/4 比例、路由脊柱、双轨数据配比（统一轨 + 权重不发布）、自建任务集（保留 2 个 TB 快题当烟测对）、自采 trace 数据集发布、逐周计划、最小叙事/MVP 分级、Pi live loop（由 benchmark 运行承担负载与采集职能）、Open-SWE（走纯 Fable/Mythos 蒸馏叙事）、板端并发/多模型、提前批投递。Pi 运行时二开 = 可选尾项。

---

## 2. 模型阵容与硬件档

| 尺寸 | 有效参数 | 角色 | PC (4060 8GB) | RK3588 (16GB) | 租卡 |
|---|---|---|---|---|---|
| **E4B** | 4.5B | **贯穿轴**，完整循环唯一对象 | Q4_K_M ≈3.5GB 全 offload | W8A8 ≈4.5GB 级 | bf16 训练 / NVFP4 / serving |
| E2B | 2.3B | 配方迁移 + 板端轻载位 + 回连 demo（bf16 ≈5GB 可进 8GB） | 可 | W8A8（官方锚 11.12 tok/s @2499MB） | 可 |
| 12B | — | 配方迁移上探 + DSpark 官方目标 | 不部署 | 不部署 | 唯一场地 |

租卡档位（价格锚以台账为准，实租日复核）：vGPU-32（¥1.58/h，E4B QLoRA 17GB 够用）→ 4090/48G 级（评测批量）→ RTX Pro 6000 96GB（¥5.95/h，OPD 场地：teacher FP8 + 学生 QLoRA 同卡，决策 16）→ RTX 6000D/6000（sm_120，NVFP4 与大 LoRA；sm_120 flash-attn 雷区见 §12，对 Pro 6000/5090 同代卡同查）。

---

## 3. 工序 DAG 与冲突边界

```text
gemma-4-e4b-it 官方权重
   └─ [S] SFT/离线蒸馏（trace 数据，QLoRA→merge）
        └─ [O₁] OPD polish（teacher=gemma-4-31b-it，决策 16 调用①）= M1 模型
             ├─ 支线A: M1 → [P] PTQ 谱系（粗→细粒度扫描）→ candidates
             ├─ 支线B: M1 → [R] 剪枝(深度先行) → [O₂] 恢复蒸馏（on-policy，teacher=剪枝前 M1，决策 16 调用②）→ [P/Q] → candidates
             ├─ 支线C: M1 → [Q] QAT（格式定向：Q4_0 主线 / W8A8 待验）→ candidates
             └─ [N] NAS/混合精度 = 在 {B 的剪枝配置 × 每层精度分配} 上外层搜索
```

**基座声明**：主线 SFT 基座 = `google/gemma-4-e4b-it`（原精度 bf16 instruct），全谱系由它出发。`qat-*-unquantized` 系**不是基座**——那是"已训练到贴近量化网格、但尚未做最终舍入"的 bf16 权重，仅供 M6 可选分支（在其上 SFT 的逆序探索）使用，不进主线谱系。

**循环定义**：一圈 = 从当前最优 candidate 出发 → 改动**一个**工序旋钮 → 产出新 candidate（编号+配置快照，§9）→ 快档评测 → 晋级或回退。项目末期每档硬件从主表**选出**发布候选——"最终稳定版本"是选举结果，不是事先指定。

**五条冲突边界（硬约束，循环内不可违反）**：

1. **顺序不可逆**：剪枝先于量化；恢复蒸馏紧跟剪枝；QAT 是最后一道训练工序。旋钮值随便换，工序拓扑不许换。
2. **QAT × 部署量化器匹配**：假量化方案 ≠ 部署端真方案 → 白训甚至更差。Q4_0 线有官方先例直接做；W8A8 线先做匹配小实验（M6 门槛）。
3. **剪枝 × E 系结构**：E4B 含 18 层跨层 KV 共享——深度剪枝前必须先画 KV 共享拓扑图，产 KV 层与消费层成对处理；砍 KV 头会破坏 GQA 分组与宽 KV 几何（端侧卖点），宽度剪枝只在 M7 搜索内做。嵌套子网轴以模型卡实证为准。
4. **剪枝 × 官方 draft**：assistant draft 共享目标 KV/隐状态，剪过的目标结构上直接不可用（非 acceptance 下降问题）——剪枝支线的投机 = 再对齐 draft 或声明放弃。
5. **重训 × draft 对齐**：PTQ 舍入保持对齐；QAT 重训可致 acceptance 崩塌到投机为负（外部实证在案）；QLoRA SFT + 独立式 draft 有保留 92% 加速的先例。→ 正是 §7 存活曲线要测的东西。

---

## 4. 技术空间参照表（立项时查这两张表，防"全都要"变"全都浅"）

### 4.1 剪枝 × 兑现路径

| 类型 | 方法代表 | 恢复需求 | PC/llama.cpp | 板/RKLLM | 云/vLLM | 结论 |
|---|---|---|---|---|---|---|
| 非结构化 | magnitude/SparseGPT/Wanda | 免训~轻训 | ✗ | ✗ | ✗（无稀疏收益） | 不做 |
| 半结构化 2:4 | SparseGPT 2:4 | 一次性+恢复训练 | ✓ 仅 vLLM-local 路径（Sparse-Marlin sm_80+；llama.cpp 不吃） | ✗ | ✓（Sparse-Marlin/TRT-LLM） | 选做（决策 14 后本地可兑现） |
| **结构化-深度** | 整层删除（Minitron 式） | **恢复蒸馏必做** | ✓ | ✓ | ✓ | **主线（M4）** |
| 结构化-宽度 | FFN 维/头/隐藏维 | 恢复蒸馏更重 | ✓ | ✓ | ✓ | M7 搜索内 |

> 核心论点素材：剪枝收益由部署路径决定而非算法——**同一块 4060 上，2:4 走 llama.cpp 路径收益为零、走 vLLM 路径可兑现**；板端两条路径都不可兑现。

### 4.2 量化四维度

| 维度 | 阶梯/选项 | 本项目落点 |
|---|---|---|
| 粒度 | per-tensor → per-channel → per-group(g128/64/32) → 块+超块(k-quant) → 码本 | PTQ 谱系扫描轴（M1 支线A）；码本不碰 |
| 对象 | weight-only(W4A16) / W+A(W8A8, 激活静态/动态) / NVFP4(W4+FP8 scale) / **KV cache 独立轴**(f16/q8_0/q4_0) | 三范式 + KV 轴进引擎矩阵（§6） |
| 校准 | RTN → GPTQ → AWQ → SmoothQuant → QAT | GGUF 自带 imatrix 校准；W8A8 走 RKLLM 校准集（agent 域样本替换官方 21 条）；QAT 见决策 3 |
| **精度分配** | uniform / 层选择性混合精度（敏感度驱动搜索） | **决策 13 实验**：逐层敏感度扫描 → AutoQuantize → vs uniform 同预算对照。MoE 特殊件：路由器保 FP16；共享 vs 路由专家差异化；embedding tying 下 lm_head 保护（Q4_K_M 把 output.weight 留 Q6_K 即此理） |

### 4.3 QAT 官方锚点家族（Google，全尺寸覆盖 E2B/E4B/12B/26B/31B，2026-07 证实）

| 官方仓库后缀 | 是什么 | 项目用途 |
|---|---|---|
| `qat-q4_0-gguf` | QAT 后已量化的 GGUF | llama.cpp 线三点对照锚（我的 QAT / 官方 QAT / 我的 PTQ） |
| `qat-w4a16-ct` | QAT 定向 W4A16（compressed-tensors，vLLM 生态原生格式） | vLLM 线三点对照锚 |
| `qat-q4_0-unquantized` | 量化适应后、最终舍入前的 bf16 权重 | M6 可选分支底座（**非主线基座**，见 §3 基座声明） |
| `qat-*-unquantized-assistant` | 与 QAT 变体配对的官方 draft（78M–0.5B） | §7 存活矩阵"QAT 配套 draft"列 |

---

## 5. 评测协议（全程冻结件）

### 5.1 冻结清单（eval_config.yaml，任何数字挂其快照）

模型文件+SHA256；引擎 commit（llama.cpp 实际 commit / vLLM SHA / RKLLM runtime 版本以板上 init 打印为准）；server 参数（单序列 `-ngl 99 -c 131072 --jinja --parallel 1`；并发 N 槽时每槽仍为 131072，`-c` 总量 = `131072 × N`；K/V 均为 q8_0）；采样（模型卡推荐值钉死，k=5 要求 temp>0，seed 记录）；TB 任务 ID 清单（20 题，选定后不再改）；烟测对（2 个快题）；lm-eval 版本 + 任务版本 + 抽样清单；BFCL 子集清单；chat/thinking 模板处理决定。板端上下文档位不适用本值，由 M2 实测决定。

### 5.2 快慢两档与晋级规则

| | 快档（每个 candidate 必跑，~1–2h） | 慢档（晋级者才跑） |
|---|---|---|
| 内容 | ① replay 磁带 → TTFT/TPOT/吞吐/cache 命中 ② BFCL 式工具调用准确率子集（数百次调用，统计功效高） ③ 烟测对 2 题 ④ GSM8K 快抽样 | ① TB 子集 20×k=5（串行/租卡整批） ② MMLU 子集 + GSM8K 全量 + HumanEval ③ 板端候选加板上实测 |
| 晋级线 | 工具调用准确率相对父 candidate 掉 ≤3pp 且 GSM8K 快抽样掉 ≤3pp；系统指标回归需有解释 | 进入主表；发布候选按决策 2 选举 |

统计纪律：TB 100 次试验 SE≈3.5pp，成功率差 <7pp 一律写"未分辨"，归因交给工具调用准确率/修复轮数/token 消耗三个高功效指标。

### 5.3 replay 磁带（负载录制回放器）

benchmark 运行天然留三样：harness episode 日志（工具调用/轮数/成败）、server 侧指标、任务元数据。从中固化 5–10 盘磁带（含 repeated-prefix 场景；磁带上下文档位由 M0 §3.2 基线跑出的真实任务上下文分布确定）——**磁带把工作负载定死，引擎配置成为唯一变量**，是 §6 全部组合扫描的仪器。磁带同时是 kernel shape 分布的采样来源（§8）。

---

## 6. 系统面 · 引擎组合矩阵 × 硬件档

| 档 | 引擎 | 扫描轴（磁带上跑） | 备注 |
|---|---|---|---|
| PC·主 | llama.cpp（实际 commit 钉死） | `-fa` on/off × `--cache-type-k/v` {f16,q8_0,q4_0} × `--parallel` {1,2,4,8} | GGUF 生态载体；12B 移出本地后混合 offload 轴取消；E4B 全 offload 单一形态 |
| PC·副 | vLLM-local（SHA 钉死，决策 14） | AWQ/GPTQ 粒度 {g128,g64,g32} × 2:4 on/off × 并发 {1,2,4} × MTP assistant draft on/off | E4B AWQ ≈3GB + 78.8M draft 进 8GB；显存紧时 `--enforce-eager`；**不用** `--cpu-offload-gb`（整块搬运非混合推理，见 §12） |
| 板 | RKLLM v1.3.0 | prompt cache save/load（系统提示 KV 落盘 → 冷启 TTFT A/B）；定频脚本；层级计时 | 无投机；W8A8 唯一 LLM 格式 |
| 云 | vLLM（SHA 钉死） | attention 后端 {FlashInfer, FA2, SDPA} × prefix caching on/off × 并发 {1,2,4,8,16} × 投机 {no-spec, MTP-assistant, DSpark(仅12B)} | NVFP4 列按难度分层报告；Marlin 回退关键字冒烟必查 |

---

## 7. 投机解码 · 工序存活矩阵（M5 招牌实验，R1 由曲线升级为矩阵）

**矩阵**（行 = 工序节点 candidate，全为循环天然产物；列 = draft 方案；格 = acceptance length 为主、tok/s 为辅）：

| 工序节点 ↓ / draft → | no-spec | stock assistant（对官方 bf16 训练） | QAT 配套 assistant（`qat-*-unquantized-assistant`） | 再对齐 draft（修复步） |
|---|---|---|---|---|
| 官方 E4B | 基线 | 参考锚 | — | — |
| S（SFT 后） | ✓ | **核心格**：QLoRA 扰动掉多少（外部先例：独立式 draft 保 92%） | — | 崩则做 |
| M1 = S.O（OPD polish 后） | ✓ | **新空白格（首测）**：OPD 重训把分布推向 31B teacher，对 stock draft 对齐的影响无外部先例（第四种重训类型，PTQ/QAT/QLoRA 三锚之外） | — | 崩则做 |
| PTQ 各格式 | ✓ | ✓（外部先例：舍入保持对齐） | — | — |
| 剪枝+恢复后（O₂） | ✓ | **N/A**（结构不匹配，非性能问题） | — | 唯一路径，或声明该支线放弃投机 |
| QAT 后 | ✓ | 预期崩塌（外部先例） | **新增格**：官方配对 draft 能否修复对齐 | 备用 |

**场地分层（R1 修正——不再全云端）**：
- **本地（vLLM-local，决策 14）**：acceptance length 是模型对的分布属性、与显卡型号无关——E4B 各行的 acceptance 测量全部在 4060 完成（AWQ 目标 + 78.8M draft，batch=1），零租金反复迭代。
- **租卡**：有硬件意义的 tok/s × 并发曲线；NVFP4 变体行；12B 配方迁移 + DSpark（PR #47216 仍 Open，需 checkout 分支）；SWE-Pro 顺带。
- **不存在的场地**：板端（RKLLM 无投机）；llama.cpp 本地 E 系（issue #22337 未解，不投入）。

**崩塌处置阶梯**：矩阵测量（≈零边际成本）→ draft 短程再对齐（天级租卡）→ 从头训 draft（stretch，不做主线承诺）。
外部锚点三点（PTQ 保持 / QAT 杀 / QLoRA+独立 draft 92%）是本矩阵的先验；矩阵是它们在同一模型链上的系统化补全 + "官方配对 draft 修复"格的首测。

---

## 8. 算子面

**PC（4060 = 全项目唯一 kernel 证据场地：sm_89 已知 + ncu 计数器 + 峰值可查 ~256GB/s 级以 datasheet 校准）**

- 流程：磁带提 shape 分布 → 立项过 A/B/C/D 四问 → 预注册（带宽帐 + kill criteria）→ 实现（Triton/CUDA）→ 四条验收【① roofline 相对分（kernelbench.com 口径）② shape 来自真实 trace 分布 ③ 注册 PyTorch custom op 回连 replay 报端到端收益/副作用 ④ 三基线（eager/torch.compile/参考实现）+ 随机化正确性】→ ncu 归因段落。
- **K1 = 方法论验门砖**（RMSNorm 或 fused softmax，M3）；此后 kernel 池常开、与模型循环并行：GQA decode attention（16k–32k 场景）、in-kernel KV 反量化、fused dequant+GEMM、Inductor 生成码逐段对照（TORCH_COMPILE_DEBUG）。16k–32k 对应并发下的每槽上下文与单任务真实区间，**待磁带分布确认**；不得先验写死 shape。上不封顶，每个都过四条验收。
- 回连路径：llama.cpp 不吃 Triton → 回连走 transformers/PyTorch 重放（E2B bf16 直载 8GB，或 E4B 4-bit 加载）。"kernel 加速 ≠ token 加速"双层报告为默认格式。

**板端三件（全做，决策 12）**：① CPU NEON kernel + 板上 perf（原生 aarch64 全功能计数器）；② RKNN matmul API 微基准（`rknn_matmul_run`，RK3588 int4×int4→int16 / int8），LLM 相关 shape 实测 NPU 吞吐 vs CPU NEON → "6 TOPS 标称 vs 实测"归因；③ 层级归因（RKLLM 阶段计时 + `/sys/kernel/debug/rknpu/load`）。边界：NPU LLM 路径闭源，不逆向。

**KernelBench（决策 11B）**：口径借用 + 选做子集题（agent 辅助 kernel 小实验，A4Q 模板）；两个 trace 数据集只作案例库。

---

## 9. 数据管线 · 七道门（零租卡成本，与 M0 并行）

| 门 | 内容 | 产出 |
|---|---|---|
| ① 完整性 | 以 HF `refs/convert/parquet` 完整 export 为冻结源，文件 SHA-256、revision、上游/本地行数逐一对账；Crown 实测 228,968 行 | 完整性表 + archive manifest |
| ② 字面去重 | 结构归一后按源会话做 L0/L1 字面折叠；L2 仅以 MinHash 生成候选、完整 Jaccard 验证后删除 | 去重前后条数与簇明细 |
| ③ 安全清扫 | TruffleHog 密钥扫描 + PII/路径脱敏 + 人工抽样 50 条 | 清扫记录 |
| ④ 结构有效性 | 多 harness 解析归一；相邻 assistant 事件碎片合并但不虚构轮次或工具调用；截断/坏 JSON 剔除；解析失败率按数据集记录 | 失败率表 |
| ④b 退化检测 | 样板前缀、集内精确/近重复率、身份/桩代码噪声与 20 条抽样；Mythos 按 2% 规则处置 | 退化报告 + 复核样本 |
| ⑤ 去污染 | 对 TB 2.1 / **HumanEval（最高危：编码轨迹含题解概率高）** / GSM8K / 全量 MMLU 做 canary 与 13-gram 重叠扫描；只删训练记录。SWE-Pro 留待 M5 | **去污染声明表**（面试素材） |
| ⑥ 配平（数量=质量门的输出，不预设） | 门②只管字面重叠；本门全量保留门⑤后合格数据，按保守源模型家族 × Hermes 任务类别记录分布，来源标签不推定 teacher 身份；Mythos 去样板去重后不足原集 2% 则整集剔除；mix yaml 带 provenance，并定义原始均匀、80/20、60/40 三个训练时采样配方，在相同 optimizer-step 与 token 预算下对照后选默认。**过拟合用留出验证集 early stopping 控制，不靠预先砍数** | mix yaml + 分布/采样配方表 |
| ⑦ 渲染与掩码 | 统一渲染 Gemma4 chat template（thinking 模板决定入冻结清单）；loss 仅落 assistant token、工具返回掩除（teich mask_data）；tokenizer 往返校验 + 人眼抽 20 条看掩码边界 | 渲染样本 + 校验记录 |

七个门各出进/出条数 → 漏斗表进数据卡。许可后果（已接受）：全池 AGPL 系 → 任何权重不发布，只发报告。

---

## 10. Candidate 编号与配置快照

- 编号：`C{序号}-{谱系}`，如 `C07-S.P(g64)`（SFT 后、per-group64 PTQ）。
- 每个 candidate 一份快照文件：父 candidate、本圈改动的**那一个**旋钮、数据 mix hash、引擎 SHA、转换/量化命令原文、快档结果指针。
- 纪律：一圈一个旋钮；快照缺任何一项的 candidate 不得进主表。

---

## 11. 里程碑链（依赖序，非周历）

| # | 里程碑 | 内容 | 验收 |
|---|---|---|---|
| M0 | 评测底座 + 数据管线 + 板端转换 smoke（三线并行） | server 钉参（读 KV self size 定 `-c`）；TB terminus-2 接本地端点跑通 1 题；20 题清单锁定 + 镜像预拉；官方 E4B 基线（快档全套 + 慢档一轮）；lm-eval/BFCL 钉版；磁带首批固化；七道门全过；**官方权重 E4B W8A8 转换 smoke（拆单点风险，防 [PAD] 先例）** | 基线数字入主表第一行；漏斗表齐；转换 smoke 有结论（成败皆记录） |
| M1 | 循环第一圈：SFT → OPD polish + PTQ 谱系 | teich→QLoRA(vGPU-32)→merge（candidate S）→ OPD polish（决策 16 调用①，Pro 6000 96GB）= M1（candidate S.O）；PTQ 扫描（Q4_K_M/Q4_0/W8A8 + 粒度轴）从 M1 出发；快档全跑、晋级者慢档 | A/C 对照表 v1（含工具准确率列）；S 与 S.O 各为一圈一旋钮的两个 candidate，同入主表 |
| M2 | 板端落地 | 最优 W8A8 candidate 上板实测 + prompt cache A/B + 板 vs PC 同任务表；板端三件算子开工 | 板端行入主表；NEON/matmul 微基准首批数字 |
| M3 | Profiling 底座 + K1 验门 | nsys/torch.profiler 采 decode 路径；K1 走完整四条验收流水线 | K1 报告（roofline 相对分 + ncu 归因 + 回连）；kernel 池开闸 |
| M4 | 剪枝圈 | KV 共享拓扑图 → 深度剪 ≥2 个比例 → 恢复蒸馏（= 决策 16 调用②：on-policy，teacher=剪枝前 M1，同一 OPD 代码路径换 teacher 地址）→ PTQ → 评测 | 剪枝 candidate 入表；拓扑图入库 |
| M5 | 租卡打包 | 存活矩阵的租卡部分（tok/s×并发、NVFP4 行、12B+DSpark——acceptance 主体已在本地 vLLM 预测完）+ NVFP4 列（难度分层）+ vLLM serving 矩阵（§6 云档）+ 12B/E2B 配方迁移 + SWE-Pro 选做 | 存活矩阵图 + 云档矩阵入表 |
| M6 | QAT 圈 | 双线：QAT→Q4_0（llama.cpp 锚）+ QAT→W4A16-ct（vLLM 锚），各做三点对照；RKLLM 匹配小实验 →（通过则）QAT-W8A8；可选分支：`qat-q4_0-unquantized` 底座逆序探索；QAT×配套 draft 格采数 | 双线 QAT candidate 入表 + 匹配实验结论 |
| M7 | 混合精度/NAS 圈 | 逐层敏感度扫描 → AutoQuantize vs uniform 同预算对照（决策 13）；宽度剪枝进搜索；嵌套切片轴（若证实） | 混合精度报告 + 搜索空间 ≤8 候选结果 |
| M8 | 收口 | 主表定稿、三个 RC 选举、数据卡、去污染声明、各报告成文 | 全部交付物齐 |

并行规则：kernel 池自 M3 起与 M4–M7 并行滚动；板端算子三件自 M2 起独立推进。日历参照：今天距 9 月初简历定稿约 7 周；M0–M3 是 9 月的地板，你的目标是全链——速度富余优先加厚 kernel 池与 M7。

---

## 12. 雷区索引（开工前查此表，来源：04 台账 + 本轮核实）

| 雷 | 内容 | 触发场景 |
|---|---|---|
| llama.cpp MTP 回归窗 | b9702+ 回归先例；E2B/E4B MTP issue #22337 未解 | 本地任何投机尝试前查当前 commit |
| RKLLM [PAD] 乱码 | 转换后输出 garbage 先例（Issue #424） | M0 转换 smoke 的存在理由 |
| KV 共享 × use_cache | 训练时 loss 发散先例 | M1 训练配置；20-step loss smoke 必做 |
| fp16 mask 溢出 | 训练 NaN 先例 | 同上 |
| chat template 不一致 | 工具调用静默崩坏 | `--jinja` + ⑦ 门往返校验 |
| CUDA 13.2 | Unsloth 明禁（乱码 bug） | 租卡镜像选择 |
| sm_120 禁 pip flash-attn | issue #1987 | 租 6000D/6000 时 |
| Marlin 回退 | 回退路径 −22% 先例 | vLLM 冒烟日志查关键字 |
| HumanEval 污染 | 编码轨迹含题解概率高 | ⑤ 门最高优先 |
| 上游语料冻结 | 原始本地文件树可不完整，仓库名/旧台账数字不可作行数证据；Crown frozen export 为 228,968 行 | ① 门以 `refs/convert/parquet` 对账后冻结 |
| DSpark PR 未合 | #47216 Open，需 checkout 分支 | M5 |
| 嵌套子网待证 | E4B 含 E2B 级子网与否以模型卡为准 | M7 前核 |
| RKLLM 版本口径 | 一律以板上 init 打印为准（缓存页误导先例） | 所有板端记录 |
| vLLM cpu-offload | `--cpu-offload-gb` 是整块权重搬运，非 `-ngl` 式层级混合推理，交互延迟塌方 | vLLM-local 配置时禁用 |
| llama.cpp E 系投机 | issue #22337 未解，E2B/E4B MTP 不可用 | 本地投机一律走 vLLM-local |

---

## 13. 证据 → 岗位映射（叙事出口）

| JD 关键词（🟢 主投档） | 本项目证据 |
|---|---|
| 量化 PTQ/QAT/剪枝/蒸馏 | 全工序 DAG + 主表 + **跨族离线蒸馏（Fable trace SFT）+ 同族在策略蒸馏（GKD 逐 token 反向 KL，31B→E4B polish 与剪枝恢复双调用）** + QAT 格式匹配结论 + 混合精度报告；自带问答：为何 Fable 不能 OPD（teacher 已下线，约束意识展示位） |
| NPU 工具链/RKNN/端侧部署 | W8A8 自转换（agent 域校准集）+ 板端实测 + prompt cache A/B + matmul 微基准 |
| KV cache / TTFT / 推理优化 | 引擎组合矩阵 + KV 量化轴 + 磁带 replay 方法论 + prefix/prompt cache 双档数据 |
| 算子/CUDA/profiling | kernel 池（roofline 相对分 + ncu 归因 + 回连）+ NEON + "kernel≠token" 归因 |
| vLLM/投机解码/serving | 云档矩阵 + 存活矩阵 + NVFP4 难度分层 |
| 常见推理引擎（八股→实证） | llama.cpp 深 / vLLM+RKLLM 实 / TRT-LLM touch、ONNX 经板端 PyTorch→ONNX→RKNN 链有真实触点 / SGLang 概念级 | 决策 14 双引擎 + 调度器对照（同硅片槽位式 vs continuous batching） |
| 面试拷打防线 | 每数字挂 eval_config 快照；每 candidate 有谱系；负结果照报（存活崩塌/并发退化/剪枝塌分都是内容） |

**简历拆分口径（一个项目，两份简历条目）**：

| 简历条目 | 标题（可直接用） | 归属证据 |
|---|---|---|
| 项目一 · 模型侧优化 | 端侧 Agent 小模型全工序压缩：前沿模型轨迹蒸馏（跨族离线 + 同族在策略）× 量化（PTQ/QAT/混合精度）× 剪枝+恢复 × 投机解码，部署跨 PC / RK3588 / 云三档 | §3 全 DAG、§7 存活矩阵、§9 数据七门、主表与三 RC |
| 项目二 · 算子/系统性能 | LLM 推理系统性能剖析与算子工程：同硅片双引擎调度对照（槽位式 vs continuous batching）、roofline + ncu/perf 归因、CUDA/NEON kernel、NPU matmul 微基准与层级归因 | §6 引擎矩阵、§8 算子面、replay 磁带方法论、板端三件 |

两条共享同一冻结评测底座与磁带（各自简历里一句话带过即可，面试被问到跨项目关系时是加分项而非破绽）；Pi 二开缺席不影响任一条目的完整性（可选尾项）。

---

## 14. 边界清单（明确不做）

路由机制；自采数据集发布；multi-agent swarm / 垂直 agent demo；NPU 逆向；从头训 DSpark draft（stretch 除外）；FA3/FA4（无 Hopper）；Open-SWE；权重发布（报告替代）；非结构化剪枝；码本量化；三尺寸全循环；预写周计划；MOPD 多 teacher 合版与任何 RL 阶段（无多 domain 合版语境，OPD 仅按决策 16 双调用使用）。Pi 二开 = 全链完成后的可选尾项。

---

*下一份文件：M0 执行卡（评测底座 × 数据管线 × 板端转换 smoke 三线并行的操作清单）。*
