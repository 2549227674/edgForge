# EdgeForge · 常驻事实与纪律基线

> 版本：2026-07-24。前身《PiLoop 对话结论补遗 2026-07-16》（81 行）——git 仓库建立后其"交接包第 2 层"身份消失，按归宿拆解重定位为本文件。
> **收录标准（唯一）**：只收"没有别的家"的东西——跨里程碑的机制事实、以及尚无执行卡的工序（M2/M4/M5/M6）所需的前置约束。凡已被仓库实测、蓝图或现行执行卡覆盖的条目，一律不在此重复（拆解去向见文末附录）。
> **权威层级**：仓库实测证据（`eval_config.yaml` / `logs/` / boot log）> 本文件 > 原 zip 的 04 台账与 R1–R4 调研报告。本文件与实测冲突时，**以实测为准并回改本文件**，不得反向修正实测。
> 计划基准始终是《EdgeForge 蓝图终稿 v4-R2》；本文件不含计划。

---

## 1. 硬件与环境

1.1 **本地主环境 = WSL2（Ubuntu）**。理由链（面试可展开）：Triton 官方仅 Linux（torch.compile/Inductor 同受牵连）、harbor/TB 与 SWE 系全是 Docker Linux 容器、vLLM 无 Windows 支持、与板端/云端 POSIX 同构。文件放 ext4（`~/`）内，勿放 `/mnt/c`；`.wslconfig` 限 memory≈12GB + `autoMemoryReclaim=gradual`。

1.2 **ncu 在 WSL2 可用**：Linux 版 Nsight Compute 装 WSL2 内，需 Windows 宿主 NVIDIA 控制面板开启 GPU Performance Counters（首跑遇 `ERR_NVGPUCTRPERM` 即此因），驱动 ≥545。Windows 原生 ncu 为兜底。（M3 前置，尚未实测）

1.3 WSL2 内 Linux `perf` 硬件 PMU 事件受限（非原生内核）；**板端是原生 aarch64，perf 全功能**——CPU 侧硬件计数器分析放板上做反而最完整。

1.4 **E = effective**。E4B = 4.5B 有效参数（纸面总参 7–8B 级，含 per-layer embedding 等），E2B = 2.3B。GPU 侧按有效参数估成立：boot log 实测 GPU 2868 MiB + CPU_Mapped 2730 MiB，后者为 per-layer embedding；但 RKLLM W8A8 需整模驻留，板端一律按纸面 7.52B 估，16GB 板可容。成本/显存一律按有效参数估的规则仅适用于 GPU 侧。

1.5 **显存与上下文：不再估算，以实测为准**（`eval_config.yaml` + `logs/m0/llama_server_pi_c131072_q8_*.log`）。
   - **机制修正（2026-07-24）**：原补遗"每 token KV 50–150KB 级 / 16k 稳 32k 贴边"的估算**高估近一个数量级**，因为它假设所有层都携带全窗 KV。实测 iSWA 拓扑下 **仅 4 层扛全窗（131072 cells），20 层为 1024 格滑窗**，@q8_0 KV 合计仅 1109.25 MiB（non-SWA 1088 + SWA 21.25）。教训：Gemma4 系的显存账**必须按 iSWA 分段算**，任何"层数 × 全窗"式估算都会错。
   - 此后凡引用显存/上下文数字，引 boot log，不引估算。
   - boot log 报告 `n_ctx_train=131072`，为模型原生上下文而非 RoPE 外推；基线 KV 的项目级冻结（K/V `q8_0`、单序列 `n_ctx=131072`；f16 不做消融）见《EdgeForge 蓝图终稿》决策 17。
   - **机制事实（2026-07-24）**：prefill 是 TTFT 主体，按实际输入长度付费；decode 是 TPOT 主体。上下文分配不等于消耗：分配 131K 只预留显存，不增加算力开销；prefix cache 命中时 agent 多轮只为新增后缀付费。boot log 的 task 517 恢复了 5116 tokens，为该路径的实测证据。

1.6 **FA3 需 sm_90（Hopper）**；4060 = sm_89；租卡池无 Hopper。**sm_120 级（RTX 6000D / Pro 6000 / 5090 同代）禁 pip flash-attn**（issue #1987）——租这几张卡时冒烟统一查，走 SDPA 或预编译轮子。任何文档不得出现"FA3/FA4 对比"表述。

1.7 4060 Laptop 峰值带宽 ~256GB/s 量级（roofline 分母；实做时以 datasheet/实测校准）。目标机实测可用显存：8187 MiB 总量，启动时约 7096 MiB 可用。

---

## 2. 引擎与量化机制

2.1 **Q4_0 vs Q4_K_M**：Q4_0 = 遗留格式，32 权重/块、单 fp16 scale、对称无零点；Q4_K_M = k-quant，256 超块 ×8 子块、子 scale 以 6-bit 打包，_M 混精（attn.v/部分 ffn down 与 output.weight 保 Q6_K——后者因 embedding tying 保护 logits）。"Q4≈92% FP16" 质量锚指 k-quant。
   - **辖域限定（必读）**：上述"Q4_0 = 遗留格式"**仅适用于普通 PTQ 之间的格式比较**。官方 QAT-Q4_0 是独立训练谱系（权重在训练中已适应 Q4_0 网格），**格式名相同 ≠ 谱系相同**，不得用"遗留格式"判其质量。登记时 `training_lineage` 与 `quantization_format` 必须分列。
   - QAT 定向 Q4_0 而非 k-quant 的机制原因：Q4_0 均匀对称网格在训练图里可精确 fake-quant 模拟；k-quant 的超块双层 scale + 逐张量混精无法如实模拟（违反"假量化方案必须等于部署真方案"）。

2.2 **QAT × GGUF 转换网格错位〔雷区，M6 触发〕**：把 QAT checkpoint 朴素转成 llama.cpp Q4_0，转换器按自己的规则选 scale/舍入，与 QAT 训练所贴的 bf16 网格不对齐——外部先例（Unsloth，26B）top-1 从 85.6% 掉到 70.2%，**−15pp 级**。后果特异性：这会让"我的 QAT"分数莫名难看，而最自然的误读是"我的 QAT 训练没做好"——归因错位，三点对照白做。**排雷法**：转换后先与在盘官方 `qat-q4_0-gguf` 锚在同一批 prompt 上对 KLD/logits，偏差异常则先修转换再入表。

2.3 **llama.cpp 能力边界**：不吃 2:4 稀疏、不吃 AWQ/GPTQ、`--parallel` 为槽位式（非 continuous batching）、装不进 Triton custom op、E 系 MTP 被 issue #22337 挡住（12B MTP 可用，`--spec-type draft-mtp`）。`-fa` 是其自有 FA 实现，无版本选择概念。

2.4 vLLM `--cpu-offload-gb` = 权重整块搬运（吞吐场景），**不是** `-ngl` 式层级常驻混合推理，交互延迟塌方，本地禁用；`swap-space` 是 KV 抢占交换区非容量扩展。

2.5 vLLM-local @4060 可行性：E4B AWQ 权重 ~2.5–3GB，`gpu_memory_utilization≈0.85` 预算 ~6.8GB；上下文与小并发档位须按同架构的 KV 开销及 M0 §3.2 的真实任务上下文分布重算，不沿用已被 boot log 推翻的 16K 估算；显存紧/首启编译慢用 `--enforce-eager`；sm_89 在 Marlin 支持范围。

2.6 PagedAttention 是 vLLM 本体机制非开关；调度器对照实验（同硅片：槽位式 vs continuous batching+Paged）定义上需要双引擎——蓝图决策 14 的根据之一。

2.7 引擎叙事分层："一深两实一略"——llama.cpp 深、vLLM+RKLLM 实、TRT-LLM touch 一次 + ONNX 经板端 PyTorch→ONNX→RKNN 链有真实触点、SGLang 概念级。

---

## 3. 投机解码

3.1 PR **#47216**（DSpark Gemma4-12B draft）截至 2026-07-16 仍 Open（reviewer 有未决 change request）；外部 198 tok/s@RTX5090 数据来自 PR 分支，使用需 checkout。draft 仅对 12B。**状态需在 M5 开工日复查。**

3.2 PR **#41745** = vLLM 的 Gemma4 官方 MTP assistant draft 支持线，覆盖全家族（E2B/E4B/26B/31B）。

3.3 **对齐敏感性三锚点**：PTQ 舍入保持 draft 对齐；QAT 重训杀死对齐（DSpark draft 对 bf16 目标训练，官方 QAT 即崩）；QLoRA 微调目标 + 独立式 draft 保留 92% 加速（issue #42068）。**OPD 是第四种重训类型，无任何外部先例**（测量格见蓝图 §7 存活矩阵）。

3.4 **acceptance length 是模型对的分布属性、与显卡无关** → E4B 各工序节点的 acceptance 在 4060 本地 vLLM 测（AWQ 目标 + 78.8M assistant draft），租卡只测 tok/s×并发/NVFP4/12B+DSpark。

3.5 Google QAT 家族含配对 draft（`qat-*-unquantized-assistant`，78M–0.5B）——官方以"换配对 draft"修复 QAT 对齐崩塌，是存活矩阵"修复格"的依据。

3.6 消费级 Q4 batch=1 投机普遍打不正 baseline（台账锚）；板端 RKLLM 无投机支持。

---

## 4. 训练与架构约束

4.1 E4B QLoRA ~17GB → vGPU-32（¥1.58/h）够用；官方口径 E4B QLoRA 优于 E2B LoRA。

4.2 **Gemma4 训练三坑（20-step loss smoke 必查）**：跨层 KV 共享 × use_cache 致 loss 发散；fp16 mask 溢出 NaN；chat/thinking 模板不一致致工具调用静默崩坏。

4.3 租卡镜像：CUDA 13.2 禁用（Unsloth 明禁，乱码 bug 关联）；vLLM 冒烟查 Marlin 回退关键字。

4.4 **蒸馏概念坐标（2026-07-24 更新）**：
   - trace SFT 本身 = **离线蒸馏**（teacher 轨迹 → student SFT），本项目对 Fable/Mythos 走此路；
   - **OPD = 在策略蒸馏**（学生自采样 + 活 teacher 逐 token 反向 KL）。**对 Fable 物理上不可行**——需活 teacher 算 logprob，而源模型 2026-06-22 已下线（见 §6.3）；
   - 剪枝后的"恢复蒸馏"= 原模型作 teacher 的 KD + 少量续训（Minitron 式），本项目**已升级为 on-policy 版**，teacher = 剪枝前 merged checkpoint（蓝图决策 16 调用②）；
   - 恢复蒸馏 teacher **必须是剪枝前的自身**，不可换成原版 31B——后者没学过本项目的工具格式与 agent 行为，会一边恢复容量一边冲刷 SFT/OPD 习得能力；且父模型分布近，避开"teacher 对学生 token 概率塌掉致信号失效"的多轮失败模式。

4.5 **E4B 结构约束（剪枝前置，M4）**：
   - **KV 拓扑已由模型元数据闭合**：`block_count=42`，`attention.shared_kv_layers=18`；non-SWA 为 4 层、每层 131072 cells、`n_embd_head_k/v=512`；SWA 为 20 层、每层 1024 cells、head dim 256、`sliding_window=512`。因此 `42 = 18 + 4 + 20`；`n_expert=0` 证实 E4B 为 dense。M4 画拓扑图时据此展开，不再保留“待对账”状态。
   - 深度剪枝先画共享拓扑（产 KV 层与消费层成对）；砍 KV 头破坏 GQA 分组与宽 KV 几何（端侧卖点）；嵌套 E2B 子网存在与否以模型卡实证为准（M7 前核）；MoE 件：路由器保 FP16、共享 vs 路由专家差异化处理。
   - 家族架构（teacher 选型依据）：**E4B dense / 26B MoE / 31B dense**。

4.6 层选择性混合精度的机制依据：层间量化误差可相互抵偿（error(a)+error(b) < error(a) alone），"保护直觉重要层"的启发式会输给敏感度搜索；外部先例同尺寸预算"同分 +20% 吞吐"；工具 = 逐层敏感度扫描 + ModelOpt AutoQuantize。

---

## 5. 板端边界

5.1 RK3588 LLM 仅 W8A8；校准集用 agent 域样本替换官方 21 条通用样本；chat/thinking 模板与训练侧核对。

5.2 **板端算子边界（已查证，M8 立项依据）**：NPU LLM 路径闭源（RKLLM/RKNPU2 黑盒，无自定义算子入口，逆向 TRM 不做）；RKNN-Toolkit2 自定义算子面向 ONNX/视觉流不通 LLM；**可做三件** = ① CPU NEON kernel + 板上全功能 perf；② `rknn_matmul_run` 微基准（RK3588 支持 int4×int4→int16）产出"6 TOPS 标称 vs 实测"归因；③ RKLLM 阶段计时 + `/sys/kernel/debug/rknpu/load` 层级归因。

5.3 一切板端版本记录以**板上 init 打印**为准（网页缓存误导有先例）。

---

## 6. 跨里程碑纪律

6.1 **统计功效**：TB 20 题 ×k=5 = 100 试验 → 成功率 SE ≈ 3.5pp，**差异 <7pp 一律写"未分辨"**；且 20×5 为聚簇结构（同题重复相关），真实 SE 略大于 3.5pp，故 7pp 是**下界**而非精确线。归因靠高功效指标：工具调用格式错误率、修复轮数、每任务 token（功效高一个量级）。
   - 官方锚校正：E4B 在 TB2 全集官方数 **≈2.2%**（前代 0.0%），不是通用小模型的 ~15% 泛锚——成功率列在小模型上信噪比极低，测量重心以高功效指标为主线。BFCL 官方 ≈66.6% 可作快档配置校准锚。
   - **聚簇量级（2026-08-05 实测）**：parser 硬错误率按 20 题 cluster bootstrap 的 SE≈5.9pp，naive 二项 SE 仅 1.3pp，设计效应≈20×。故「后三指标功效高一个量级」应修正为「与成功率同量级，但不在地板上」。

6.2 **网络抖动不解释为模型/Oracle 失败**（Docker Hub/GitHub 下载失败）；正式评测串行或低并发 + 镜像预拉。

6.3 **语料冻结的根本原因**：源模型 2026-06-22 因出口管制下线，语料**不可再生**。这条同时决定了：数据必须 checksum + 第二介质；以及 §4.4 的"Fable 无法做 OPD"。

6.4 kernelbench 两个 trace 集（hard+mega，~70 条）**永不进训练**：极小规模 + 跨 harness 格式 + 高端 GPU 分布；且训了会污染 agent 辅助 KernelBench 实验。保留为项目 2 案例库。

6.5 **进度单位 = 入表的可审计格子数，非跑通的命令数。**

6.6 **继承污染教训（2026-07-24 扩充）**：
   - 原实例：原 zip 未经审查的具体数字会伪装成"既定背景设定"被无脑继承（1k–10k 事件为证）。
   - **新实例**：M0 卡 R1.1 曾把在盘 Q4_0 写成"官方 QAT 对照线伴生资产"——这个身份**从未核验**，仅凭文件名推断，且语气笃定、未打标记；后经核验实为官方 `qat-q4_0-gguf` 锚本尊。
   - **第三实例（2026-08-05）**：`eval_config` 曾断言「缺失 reasoning 的 125 条 = 硬错误带 extra-text 的 125 条」，仅因两个计数都等于 125。实测交集仅 14。**教训**：数值相等不构成同一集合的证据；凡「A 数等于 B 数所以 A=B」的隐含推断一律打 `[未复核]`。
   - **教训升级**：污染不止来自"从旧文档继承"，**也来自"本次新写入"**。`[未复核]` 标记的适用范围因此扩大——凡未经实证的具体身份/数字/阈值，无论来源是继承还是当场推断，一律打标。

---

## 附录 · 拆解去向（可审计）

原补遗 81 行的处置：

| 原条目 | 去向 |
|---|---|
| 新对话开场指令模板 | → 仓库 `README.md`（git 仓库取代了"上传交接包"这个动作） |
| §1.5 显存账估算 | **删除**（实测推翻）→ 本文 1.5 改为指针 + 机制修正 |
| §4.1 统计 / §4.5 网络纪律 | 保留（跨里程碑）→ 本文 6.1 / 6.2 |
| §4.2 benchmark 选型 / §4.3 全景 / §4.4 TB 链路 | **删除**（蓝图 §5 + M0 执行卡 §3 已覆盖）；仅官方锚校正保留至 6.1 |
| §5.1 kernelbench / §5.6 语料冻结根因 | 保留 → 本文 6.4 / 6.3 |
| §5.2–5.5 数据细则 | **删除**（M0 执行卡 §5 七门表已覆盖） |
| §7.1 W0 板端实证 | **删除**（W0 事实版 + M0 卡线 B 已覆盖） |
| §8.1 Pi/采集三件套 | **删除**（W0 事实版已覆盖；采集职能已并入 benchmark 运行） |
| §8.2 一圈一旋钮 / §8.5 卡制度 | **删除**（蓝图 §10 与蓝图头部已覆盖） |
| §8.4 交接包结构 | **删除**（仓库取代） |
| 其余 §1/§2/§3/§6/§7/§8.3/§8.6 | 保留并更新 → 本文各节 |

**新增条目**（本对话产出，此前无归宿）：2.1 辖域限定、2.2 QAT×GGUF 转换雷区、3.3 OPD 第四类、4.4 蒸馏概念坐标重写、4.5 KV 拓扑对账要求与家族架构、6.6 教训升级。
