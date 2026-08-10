# EdgeForge · 常驻事实与纪律基线

> 版本：2026-08-11。前身《PiLoop 对话结论补遗 2026-07-16》（81 行）——git 仓库建立后其"交接包第 2 层"身份消失，按归宿拆解重定位为本文件。
> **收录标准（唯一）**：只收"没有别的家"的东西——跨里程碑的机制事实、以及尚无执行卡的工序（M2/M4/M5/M6）所需的前置约束。凡已被仓库实测、蓝图或现行执行卡覆盖的条目，一律不在此重复（拆解去向见文末附录）。
> **权威层级**：仓库实测证据（`eval_config.yaml` / `logs/` / boot log）> 本文件 > [`docs/research/`](research/README.md) 中归档的 04 台账与 R1–R4 调研报告。本文件与实测冲突时，**以实测为准并回改本文件**，不得反向修正实测。
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

4.2 **Gemma4 训练三坑（20-step loss smoke 必查）**：跨层 KV 共享 × use_cache 致 loss 发散；fp16 mask 溢出 NaN；chat/thinking 模板不一致致工具调用静默崩坏。2026-08-06 已实测 HF Jinja、B0 Q4_K_M GGUF 与官方 QAT Q4_0 GGUF 的模板逐字节一致（18,569 bytes，SHA-256 `0a2c8073…`）。

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

5.1 RK3588 / RKLLM 1.3.0 的本轮 E4B 路径只产生 W8A8 工件。M0 转换基线使用官方 19 条、3,627 token 校准数据；它不是 M2 正式校准集，旧的 agent 域替换方案仍只是已废弃计划，不得当成冻结事实。chat/thinking 模板与训练侧核对；2026-08-06 三方模板实测逐字节一致（SHA-256 `0a2c8073…`）。

5.2 **板端算子边界（已查证，M8 立项依据）**：NPU LLM 路径闭源（RKLLM/RKNPU2 黑盒，无自定义算子入口，逆向 TRM 不做）；RKNN-Toolkit2 自定义算子面向 ONNX/视觉流不通 LLM；**可做三件** = ① CPU NEON kernel + 板上全功能 perf；② `rknn_matmul_run` 微基准（RK3588 支持 int4×int4→int16）产出"6 TOPS 标称 vs 实测"归因；③ RKLLM 阶段计时 + `/sys/kernel/debug/rknpu/load` 层级归因。

5.3 一切板端版本记录以**板上 init 打印**为准（网页缓存误导有先例）。

5.4 **RKLLM E4B W8A8 embedding 序列化事实（2026-08-08）**：完整 16K 1-core 工件为 11,687,037,412 bytes，`export_embedding=False` 工件为 4,707,715,428 bytes，差额 6,979,321,984 bytes；全部 embedding 参数为 3,489,660,928，乘以 2 bytes 为 6,979,321,856，余量仅 128 bytes。因此该差额可登记为全部 embedding 的 16-bit 序列化贡献加 128 bytes 元数据。不得由此断言具体浮点编码，也不得将其与某一 IOVA 分配直接等同。

5.5 **RK3588 E4B 核数/CMA 边界（2026-08-08）**：1-core 在 `cma=128M` 冷启动下完成 16K 固定五题 smoke（`rkllm_init` 成功、退出码 0、UTF-8 有效、无 `[PAD]`）；故此前临时 `cma=1G` 不是成功条件，已回滚。2-core 在两次独立冷启动、两种 demo 路径、约 1 GiB CMA 空闲下均固定失败于 `dma map 333053952` / `failed to allocate IOVA: -12`，退出码 135。该事实不授权修改驱动或 device-tree。

5.6 **2-core IOVA 分配链（2026-08-08）**：在 `cma=128M` 的冷启动厂商 2-core trace 中，runtime 经 `/dev/dri/card1` 的 RKNPU DRM ioctl 依次成功 map 8,482,816、59,256,832、3,972,792,320 bytes；三组在同一 IOVA domain 无缝覆盖 `0x0f2a6000..0x100000000`，合计 4,040,531,968 bytes，窗口残余 254,435,328 bytes。第四个 `__rknpu_gem_create_ioctl` 进入 IOVA 分配而没有发生 map，用户态请求正是 333,053,952 bytes，超出残余 78,618,624 bytes 后回收前三组。故 2-core 的分配级根因是该 4 GiB IOVA domain 的确定性容量耗尽，非 CMA 不足或碎片化；3,972,792,320-byte 组是成功映射而非失败申请。第四对象的具体 tensor/缓存语义尚未证明，不能把它等同于 embedding 或任何指定权重。

5.7 **Gemma4 自动模板边界（2026-08-08）**：将冻结 Jinja 模板注入 `tokenizer_config.json` 的 A 组与原样 B 组在板端均仍报 `Failed to parse chat_template`；证据支持 RKLLM 不接受该完整 Jinja 模板子集，而非外部模板文件布局错误。`rkllm_set_chat_template` 的手动路径会关闭自动 thinking 处理，M2 若消费 thought/tool 场景必须自行构造并验证该通道。

5.8 **P7 · 2-core IOVA 请求身份字段（2026-08-08）**：可逆的 `LD_PRELOAD` shim 记录到四笔 `rknpu_mem_create` 全部请求 `iommu_domain_id=0`、`core_mask=0x00000001`；第 1 笔为 8,482,816 B / flags `0x0000040b`，第 2–3 笔为 59,256,832 B 与 3,972,792,320 B / flags `0x00000403`，均成功；第 4 笔为 333,053,952 B / flags `0x00000403`，返回 `EFAULT`。第 4 笔失败后约 1.424 秒才开始销毁前三个对象，故 runtime 没有在创建第 4 笔之前释放前三笔。此事实只闭合 U2；其时仍不能由 allocation lifetime 断言计算阶段的同时可见性。该缺口后来由 X2 的 1-core 数值安全阀闭合为「需同时可见」，故不授权 domain 自动切换补丁；最终边界见 `docs/m0/06_board_smoke.md`。

5.9 **P1 · 16K IOVA 并发预算（2026-08-08）**：同一 `cma=128M` boot 下，以 ioctl shim 的 create/destroy lifetime 加 ftrace map/unmap 交叉采样。1-core 初始化成功；domain 0 四笔同时 map 的峰值是 **4,186,705,920 B**，4 GiB 容量余 **108,261,376 B**。随后 domain 1 的四笔峰值为 885,002,240 B，且其生命周期与 domain 0 重叠、IOVA 地址复用，故不得跨 domain 累加。2-core 的 domain 0 成功峰值为 4,040,531,968 B、余 254,435,328 B；第 4 笔 333,053,952 B 因短 78,618,624 B 失败。3-core 的 domain 0 成功峰值为 4,074,332,160 B、余 220,635,136 B；第 4 笔 265,568,256 B 因短 44,933,120 B 失败。该事实闭合 U8；KV 的随 token 增量未测，但 P3 已关闭 32K / 131K 工件分支，故该未知不再授权预写任何越限 `max_context`。第 4 笔分配的具体 tensor / cache 身份仍未知；同时可见性则已由随后 X2 的 1-core 逐字节安全阀闭合。

5.10 **P3 · RKLLM 1.3.0 的上下文 B 层硬上限（2026-08-08）**：绕过本项目 A 层 `MAX_CONTEXT_LIMIT` 后，独立探针两次均先成功 `load_huggingface`（返回 0），再调用同一 `RKLLM.build`：`max_context=32768` 与 `131072` 均返回 `-1`，进程返回码均为 1，stderr 原文为 `ERROR: max_context must be within [32, 16384]`。`RKLLM.build` 的可见 Python 包装器把调用转给编译的 `rkllm_base.cpython-312-x86_64-linux-gnu.so`；不修改二进制。故以该 toolkit 1.3.0 重新构建 32K / 131K 工件的路线关闭，P2 无 32K 工件可作差值采样。此结论关闭的是越限可行性，不把 U4/U5 的 KV 机制未测误写为任何特定值。

5.11 **P6 · 手动模板下的 thought / tool_call 通道（2026-08-08）**：16K / 1-core 工件用 `skip_special_token=false` 运行两条原始 prompt；probe 将 callback 片段直接写为原始 `.bin`。进程退出码与两次 `rkllm_run` 均为 0。44-byte tool 输出（SHA-256 `275c77acc8dab90909658fa55aa4c7d03de2b3af0a38a819571f6e8565cd678f`）在字节偏移 0 / 27 有 `<|tool_call>` / `<tool_call|>`；650-byte thought 输出（SHA-256 `c684a794ea328393b76905fe4e898a3efb10e91ca5be4064a6d718618a34cdb8`）在偏移 523 / 560 有 `<|channel>thought` / `<channel|>`，并有后续重复标记。故按 S2c 的纯结构判据，两通道均可行，U10 闭合。该事实限于 `rkllm_set_chat_template` 的手动模板路径；不证明自动 chat-template parser 或 automatic thinking 可用，且不评价生成语义质量。

5.12 **P4 · PC `eval_accuracy` 模板路径（2026-08-08）**：可见的 `rkllm.api.rkllm.RKLLM.eval_accuracy` Python 包装器将 `apply_chat_template` 原样转发给 `self.base.eval_accuracy(...)`；实际 `RKLLMBase.eval_accuracy` 位于编译模块 `rkllm.api.rkllm_base.cpython-312-x86_64-linux-gnu.so`，`inspect.getsource` 不可用。产生 MMLU fast-500 `AVERAGE ACC:41.60` 的日志与产生 164 条 HumanEval 结果的日志均记录 `apply_chat_template=false`。对这两份日志及原始 HumanEval 评分日志 grep `Failed to parse chat_template` 的返回码为 1、stdout 为 0 B，故该 warning 未复现。PC 数值对照应继续显式调用 `eval_accuracy(apply_chat_template=False, ...)`；其独立的缺数据和 `Expected list, got int` 评分错误不得写成模板故障。该事实不修复板端的自动模板解析问题，且不单独闭合 H1/H2/H3 归因。

5.13 **P5 · 校准集勘测与主机成本边界（2026-08-08）**：冻结 `GemmaTokenizer` 逐条以 `enable_thinking=true`、`preserve_thinking=true` 渲染全部 154,097 条 Line C 记录，未出现模板渲染错误；渲染长度 p50/p90/p95/max 为 827/3,055/3,912/4,060,703 token，2,555 条大于 16,384。官方 19 条 `data_quant.json` 按逐条 `input+target` 直接拼接计数为 3,627 token（input=1,153、target=2,475；分字段相加为 3,628，差异来自边界 token 合并）。分层选出的嵌套 16/32/64 条经 16K 截断后为 112,946/244,760/524,596 token；三通道段数分别为 55/963/156、127/1,727/402。当前云主机以同一 RKLLM 1.3.0 W8A8 build-only 配置各尝试一次，均在 `build()` 返回前退出 137；CPU HWM 约 92.65/92.89/93.51 GiB，GPU 峰值 19,630/4/4 MiB。因无成功 build 点，秒/token 斜率和收敛点均未得出；退出 137 与近 93 GiB HWM 相符，但现有日志没有可单独证明内核 OOM 的行。该事实保留 H3 为待 X 归因候选、禁止在此主机启动收敛检验；不产生或冻结 M2 正式校准集。

5.14 **IOVA 数字口径（2026-08-09）**：容量和缺口一律使用页对齐后的实际 `iommu:map` 字节数，不使用 ioctl 的未对齐 `requested_size_bytes` 相加。3-core 前三笔实际 map 为 12,709,888、88,829,952、3,972,792,320 B，合计 4,074,332,160 B；第 4 笔请求 265,568,256 B，故短缺 **44,933,120 B**。旧值 44,930,392 B 仅是未对齐请求相加的算术差，不能用于 IOVA 预算或对外陈述。

5.15 **R1.6 交付形态（2026-08-08，2026-08-09 状态回填）**：3-core 是唯一可采纳的板端交付形态。1-core 和 2-core 不进入交付；1-core 保留为模板观测、IOVA 改写逐字节安全阀及 PC/板端对照的诊断仪器。X1 的 `w4a16` 主路线已因 U13 不支持关闭；X2 随后因 1-core 逐字节回归失败关闭，3-core 已无剩余技术路线。owner 已选择 §8.5 A：M0 记录 16K 1-core 可运行的事实，将 3-core 连同重开条件移交 M2，且不把 1-core 重定义为交付物。

5.16 **RKLLM 1.3.0 量化格式合同（2026-08-08，2026-08-09 X1 矩阵回填）**：`build()` 一手清单为 `w4a16`、`w4a16_g32`、`w4a16_g64`、`w4a16_g128`、`w8a8`、`w8a8_g128`、`w8a8_g256`、`w8a8_g512`。不存在 `w4a8` 或 `w4a4`；`grq/grq_r*` 只支持 4-bit。以冻结 E4B 输入、RK3588、3-core / 16K build-only 实测：四个 W4A16 变体均由 target platform 明确拒绝；`w8a8`、`w8a8_g128`、`w8a8_g256` 均 build 成功；`w8a8_g512` 因本模型 tensor shape 不能整除 group size 512 而失败，不能写成通用平台不支持。此为 build 支持性结论，不代替板端 init/质量结论；且可 build 的分组 W8A8 仍不能作为 IOVA 容量解法。

5.17 **分组 W8A8 不能解决多核容量（2026-08-08）**：`w8a8_g*` 增加 scale 元数据，因此相对 W8A8 会增加 domain 0 占用；它们只能在 H2 被确立后作为精度实验，不得作为 3-core IOVA 容量路线。

5.18 **CMA 与 NPU IOVA（2026-08-08）**：CMA 面向没有 IOMMU、需要物理连续 DMA 的设备；RK3588 NPU 在 IOMMU 之后，IOVA 容量耗尽不能由增大 CMA 修复。2-core 在约 1 GiB 与 128 MiB CMA 下于同一请求失败，1-core 在 128 MiB 成功，构成该机制的实证对照。

5.19 **X0 · IOMMU aperture（2026-08-09）**：板端 root 在 boot id `91368c69-6c37-4d37-aba8-b1e578cc6619` 的只读采集确认 `fdab0000.npu` 属于 IOMMU group 0，且 device-tree 的 phandle 指向 `rockchip,iommu-v2`；dmesg 亦确认 RKNPU 处于 IOMMU mode。板端未导出 aperture/geometry，且 BSP 源码未直接读取；但以上游 `rk_iommu_domain_alloc()` 对 v1/v2 一律写死 `aperture_end = DMA_BIT_MASK(32)`、`force_aperture = true` 及 RK3588 的 v2 ops 绑定，**U15 闭合为 per-domain 4 GiB 硬编码**（证据等级：强、一步之遥）。扩大 domain 路线关闭；X2 不扩窗口，仍按独立安全阀判别。原始证据归档为 `exports/m0/board/EdgeForge_M0_X0_iommu_aperture_evidence_20260809.zip`。

5.20 **X1 · RK3588 W4A16 build-only（2026-08-09）**：先发现云端原模型目录的模板与 tokenizer 配置偏离冻结 W8A8 身份，故在 `build()` 前中止该无效尝试；随后以隔离输入恢复并逐项验证七个基线 SHA-256。Toolkit 1.3.0 在 `load_huggingface=0` 后对 `target_platform=RK3588`、3-core、16K、`quantized_dtype=w4a16` 返回 `-1`，原文为 `target_platform: rk3588 not support quantized_dtype: w4a16!`，进程退出 1。故 U13 闭合为不支持、X1 关闭；没有 export、W4A16 artifact、传板、P7 shim、U14、S2a/S2c 或 PC 对照。不能由此断言其它 SDK 列举格式支持或不支持 RK3588；其后的唯一 X2 路线亦已由数值安全阀关闭。原始证据归档为 `exports/m0/board/EdgeForge_M0_X1_w4a16_3core_probe_evidence_20260809.zip`。

5.21 **X2 · 第 4 笔 IOMMU domain 改写（2026-08-09）**：在 1-core W8A8/16K 的五题贪心回归中，shim 仅将 ordinal 4、`request=0xC0306442`、178,782,208 B 的 `iommu_domain_id` 0→1；其余 ordinal 1–3 与 5–8 未改。进程退出 0，但 raw transcript 在偏移 940 起分歧，基线 2,087 B、改写 4,083 B，`cmp -s` exit 1。按预注册安全阀立即停止，未运行 2/3-core、3-core init、S2a 或 S2c；U3 闭合为「需同时可见」，用户态/驱动 domain 改写路线关闭。`LD_PRELOAD` 已随子进程退出自动回滚，未改 driver、DT、内核、CMA、工件或共享脚本。原始证据归档为 `exports/m0/board/EdgeForge_M0_X2_iommu_domain_rewrite_evidence_20260809.zip`。

5.22 **X3 · `apply_chat_template=True` 完整重试（2026-08-09，固定事实）**：隔离冻结七文件输入、RKLLM 固定 `api/dataset/` 的 116 文件 manifest 校验、W8A8 / RK3588 / 16K / 1-core 合同均通过；`load_huggingface=0`、`build=0`，MMLU frozen fast_500 为 `26.40%`，既有 `apply_chat_template=false` 对照为 `41.60%`。HumanEval 生成到 164/164 后原生评分器报 `Expected list, got int`，`eval_accuracy_end.result=-1`，未输出 HumanEval 原始通过数；完整 stdout / stderr 未出现 `Failed to parse chat_template`。原双任务预声明判据规定任一任务异常或缺少原始得分即为无效/灰区；该历史处置不补写 HumanEval 分数，也不得与此前 48/164 的中断尝试拼接。日志已封存，临时原生评测目录已恢复；原始证据归档为 `exports/m0/board/EdgeForge_M0_X3_apply_chat_template_true_retry1_evidence_20260809.zip`。

5.23 **X3 · owner 事后 MMLU-only 判据修订（2026-08-09，已完成）**：HumanEval 评分器异常且 owner 决定不重跑时，以冻结 MMLU fast_500 为 X3 唯一归因判别器；MMLU < 43.60% 且完整日志无 `Failed to parse chat_template`，则仅为 M0 决策用途判 H1 不成立，授权进入 X4。HumanEval 只标记为失效仪器：不补分、不拼接、不作为性能结论。本次 `26.40% < 43.60%` 且 warning 计数为 0，故 H1 **仅对 M0 决策不成立**，并在当时授权 X4；X4 的后续执行结果见 §5.24。当时 X5 因无 warning 未获授权；用户于 2026-08-10 另行显式授权后的 X5 结果见 §5.26，不追溯改写本条 X3 路由。H2 与 `w8a8_g*` 在 X4 未形成有效 H3 判别后继续挂起。此为运行和原双任务预注册判据之后的事后 decision rule，只改变路由授权，不增加对外质量/性能主张，也不把缺失的 HumanEval 分数伪称为结果。

5.24 **X4 · 短样本校准 build 与主机边界（2026-08-10）**：owner 基于 X3 的事后 MMLU-only 路由授权 X4。冻结 N=128 manifest 为 105,865 tokens、0 truncation；W8A8/RK3588/16K/1-core 的 `load/build/export=0/0/0`，外层 exit 0，工件 11,687,037,412 B、SHA-256 `3829c6f4983f4c9addb9796ade0a469dd907ee378c9921f6f6dc612a9c268d02`，peak CPU HWM/GPU 为 61,524,640 KiB/38,080 MiB。故 U11 按预注册闭合为「单条长度驱动」。冻结 N=256 为 211,725 tokens、0 truncation；同合同在优化第 0/42 步申请额外 7.50 GiB 时 CUDA OOM，`build=-1`、exit 1，peak CPU HWM/GPU 为 89,792,264 KiB/45,374 MiB，无工件。未运行 32-probe logits 或比较器，H3 不可推断。owner 于 2026-08-11 冻结 M0 线 B，不再重开 X4 或启动 H2/`w8a8_g*`；原始证据归档为 `exports/m0/board/EdgeForge_M0_X4_short_calibration_evidence_20260810.zip`。

5.25 **RKLLM `.rkllm` 校准导出 scratch 修复（2026-08-10）**：SDK/NumPy 会对匿名临时文件调用 `fallocate64(FALLOC_FL_KEEP_SIZE, offset=13,107,200, length=26,214,400)`；若 `TMPDIR` 未固定，临时写入可能落到容量不足的系统盘/overlay，即使最终工件指向数据盘仍报 `Not enough free space`。有效做法是把 `TMPDIR`、`TMP`、`TEMP`、进程工作目录和最终 `.rkllm` 工件同时固定到同一个容量充足的 run-scoped 数据盘目录，并在 build 前用 `SpooledTemporaryFile(max_size=1)` 复现 13,107,200 + 26,214,400 = 39,321,600-byte 写入。N=128 在 `/autodl-fs/data` 的 131 次 fallocate 全部成功，证明该修复有效；无需修改 RKLLM wheel、共享 `api/dataset`、模型或校准正文。本项是 RKLLM 导出方法，不是 RKNN `.rknn` 导出。

5.26 **X5 · 自动 chat-template parser 最小边界（2026-08-11，U6 已闭合）**：用户于 2026-08-10 独立授权 X5。固定 Toolkit/Runtime 1.3.0、RK3588、W8A8、16K、1-core，在隔离 HF 输入上逐候选 build/export 并板端初始化。冻结完整模板 warning=1；macro/namespace/`strip_thinking`/block-form `set`/mapping/dictsort/`map('upper') | list`、tool-call 控制流与 `<|tool_call>...<tool_call|>` 标记骨架均 warning=0。最小失败候选为 7 行、208 B 的不可达 `raise_exception()` 调用，其参数由相邻字符串字面量隐式拼接，warning=1；保留同一个不可达调用、仅合并为单字符串的对照 warning=0。因此 U6 精确闭合为 **`raise_exception()` 实参中的相邻字符串字面量隐式拼接不受 RKLLM 1.3.0 parser 支持**，而非 `raise_exception`、macro、namespace 或 tool-call 标记本身。每轮云端 `load/build/export=0/0/0`，板端重建 SHA 匹配、probe exit 0、`rkllm init success`；原始证据归档为 `exports/m0/board/EdgeForge_M0_X5_minimal_template_bisection_evidence_20260811.zip`。

5.27 **M0 线 B R2.0 冻结（2026-08-11，owner 决策）**：owner 接受 S2b 的 H2/H3 未归因状态并终止后续执行。该决定取消未来 X4、H2 粒度阶梯和 S3 的当前授权，是管理性结案而非 S2b 技术通过；3-core 未达成、1-core 仍只是诊断工件。云端 M0/X5 工作目录已删除；板端只保留 `/home/orangepi/edgeforge_m0_frozen_r2/` 中 SHA-256 为 `4bdad6bf…d7edb10b` 的 1-core 工件；本地原始证据收敛为 R2.0 §7 的七个压缩包。环境删除和空间变化是本次维护操作记录，不是由旧实验证据包支撑的技术门禁结论。任何重开都必须先有 owner 明确撤销冻结，并建立新的执行卡、artifact 身份、manifest 和证据目录。

5.28 **M0 整体 R2.0 收敛（2026-08-11）**：当前唯一 M0 主卡为 `docs/m0/README.md`，§1–§6 事实卡统一放在 `docs/m0/`。M0 无活动待办；HumanEval 无全量基线、数据无第二介质备份、板端 S2b 未归因均是已声明的冻结缺口，不是自动重开授权。本地保留冻结 export、`mix_records/`、100 条 trajectory、聚合结果和重建脚本，删除约 20 GiB 可再生中间物；云端重复模型 ZIP 已删除；板端仍只保留冻结 1-core 诊断工件。

---

## 6. 跨里程碑纪律

6.1 **统计功效**：TB 20 题 ×k=5 = 100 试验 → 成功率 SE ≈ 3.5pp，**差异 <7pp 一律写"未分辨"**；且 20×5 为聚簇结构（同题重复相关），真实 SE 略大于 3.5pp，故 7pp 是**下界**而非精确线。归因靠高功效指标：工具调用格式错误率、修复轮数、每任务 token（功效高一个量级）。
   - 官方锚校正：E4B 在 TB2 全集官方数 **≈2.2%**（前代 0.0%），不是通用小模型的 ~15% 泛锚——成功率列在小模型上信噪比极低，测量重心以高功效指标为主线。BFCL 官方 ≈66.6% 可作快档配置校准锚。
   - **聚簇量级（2026-08-05 实测）**：parser 硬错误率按 20 题 cluster bootstrap 的 SE≈5.9pp，naive 二项 SE 仅 1.3pp，设计效应≈20×。故「后三指标功效高一个量级」应修正为「与成功率同量级，但不在地板上」。

6.2 **网络抖动不解释为模型/Oracle 失败**（Docker Hub/GitHub 下载失败）；正式评测串行或低并发 + 镜像预拉。

6.3 **语料冻结的根本原因**：源模型 2026-06-22 因出口管制下线，语料**不可再生**。这条同时决定了：数据必须 checksum + 第二介质；以及 §4.4 的"Fable 无法做 OPD"。

6.4 kernelbench 两个 trace 集（hard+mega，~70 条）**永不进训练**：极小规模 + 跨 harness 格式 + 高端 GPU 分布；且训了会污染 agent 辅助 KernelBench 实验。保留为项目 2 案例库；排除须以 `data/pipeline/kernelbench_exclusion.json` 的可审计断言件证明，不接受口头约定。

6.5 **进度单位 = 入表的可审计格子数，非跑通的命令数。**

6.6 **继承污染教训（2026-07-24 扩充）**：
   - 原实例：原 zip 未经审查的具体数字会伪装成"既定背景设定"被无脑继承（1k–10k 事件为证）。
   - **新实例**：M0 卡 R1.1 曾把在盘 Q4_0 写成"官方 QAT 对照线伴生资产"——这个身份**从未核验**，仅凭文件名推断，且语气笃定、未打标记；后经核验实为官方 `qat-q4_0-gguf` 锚本尊。
   - **第三实例（2026-08-05）**：`eval_config` 曾断言「缺失 reasoning 的 125 条 = 硬错误带 extra-text 的 125 条」，仅因两个计数都等于 125。实测交集仅 14。**教训**：数值相等不构成同一集合的证据；凡「A 数等于 B 数所以 A=B」的隐含推断一律打 `[未复核]`。
   - **第四实例（2026-08-06）**：台账将 Crownelius 的仓库名 `2M` 和 981.5MB 作为行数/规模证据；冻结的上游 parquet export 实测为 228,968 行。仓库名或文件名中的数字不构成行数证据。
   - **教训升级**：污染不止来自"从旧文档继承"，**也来自"本次新写入"**。`[未复核]` 标记的适用范围因此扩大——凡未经实证的具体身份/数字/阈值，无论来源是继承还是当场推断，一律打标。

6.7 **Line C 语料事实（2026-08-06）**：九个归档源均已按 frozen revision 与 SHA-256 完整度冻结；许可、行数及 archive 文件清单见 `manifests/data_archive_sha256.json`。Crownelius 是跨集聚合镜像，保留 `row_hash`/`seen_count` 与 `first_source_dataset` provenance；来源标签不等同于已核实 teacher 身份。Glint 的 4,665 行在 Gate 4 解析为 218 个 prefix-expanded source sessions。Hermes 的来源家族按 config provenance 分为 Kimi-K2.5（7,646）与 GLM-5.1（7,055）。

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
