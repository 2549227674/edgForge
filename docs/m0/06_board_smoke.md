# M0 §6 · E4B W8A8 板端 smoke（R2.0 冻结事实版）

- 冻结日期：2026-08-11
- 对应主卡：`docs/m0/README.md` §6
- 平台：RK3588，RKLLM Toolkit / Runtime 1.3.0
- 冻结状态：**M0 线 B 结束，不再继续 X4、X5、H2 粒度阶梯、S3 或 3-core 试错**

## 1. 结案结论

Gemma 4 E4B 可转换为 RK3588 W8A8 / 16K 工件，并能在 1-core 上完成初始化、贪心解码和合法 UTF-8 输出。手动模板路径下，`thought` 与 `tool_call` 通道标记能成对产出，因此 agent 形态在结构上可行。

2-core 和 3-core 工件均无法初始化。分配层直接根因是单个 IOMMU domain 的 IOVA 窗口耗尽，不是 CMA 或物理内存不足；「窗口为驱动写死的 4 GiB」由板端 DT 身份与上游驱动共同支持，证据等级为「强、一步之遥」。3-core 按页对齐实际 map 口径尚缺 **44,933,120 B**。扩大 domain、切换 W4A16 和改写 `iommu_domain_id` 三条已评估路线均有明确负结果；结论仅限当前 RK3588 / RKLLM 1.3.0 合同，不外推到其他版本或平台。

S2b 语义质量没有完成 H2（W8A8 粒度）与 H3（校准不足）的切分：X4 的 N=128 成功，N=256 因 CUDA OOM 无工件，因而没有 N/2N logits 收敛结果。**S2b 的准确状态是「门禁未放行/未完成判定」，不是已证明的质量失败。owner 决定接受该未知并冻结；这是管理性结案，不是 S2b 技术通过，也不是对 H2/H3 的归因。**

3-core 曾被锁定为唯一交付形态，但本轮未达成。owner 沿用选项 A：保留「16K / 1-core 可运行」的 smoke 事实，将 3-core 的重开条件移交 M2；1-core 仍只是诊断工件，不是交付工件。

## 2. 冻结范围

本文中，`S*` 是 smoke 验收门，`H*` 是 S2b 病因假说，`X*` 是判别实验，`U*` 是实验期间登记的未知项。`owner` 指项目决策者；「当前合同」仅指 RK3588 + RKLLM Toolkit/Runtime 1.3.0 + W8A8/16K。

### 2.1 输入与转换合同

| 项 | 冻结值 |
|---|---|
| 模型 | Gemma 4 E4B IT，七个输入文件逐项 SHA-256 校验 |
| 量化 | `w8a8` / `normal` |
| 平台 | `RK3588` |
| `max_context` | 16,384；Toolkit 1.3.0 编译层允许区间为 32–16,384 |
| 校准基线 | 官方 19 条，3,627 token |
| 输入约束 | 原模型工作目录曾污染，已修复但不再直接使用；只认冻结 manifest |

冻结输入清单保留于 `manifests/gemma4_e4b_rkllm_frozen_input_sha256.json`。云端工作副本已删除，不再保留「修复后可继续转换」的运行态含义。

### 2.2 工件与运行结果

| 工件 | 大小 | 结果 | 角色/保留状态 |
|---|---:|---|---|
| 16K / 1-core W8A8 | 11,687,037,412 B | 初始化和生成成功 | **诊断工件，非交付物；板端唯一保留** |
| 16K / 2-core W8A8 | 11,726,642,116 B | IOVA 失败 | 已删除 |
| 16K / 3-core W8A8 | 11,767,487,820 B | IOVA 失败 | 已删除；未达成交付 |
| W4A16 家族 | — | RK3588 / Toolkit 1.3.0 明确拒绝 | 未产生工件 |
| 32K / 131K | — | `build()` 超出编译层上限 | 未产生工件 |

1-core 冻结工件的 SHA-256 为 `4bdad6bfa34e23562d65c86ad1fcc68c626c6eb6f2761b4d354f26f6d7edb10b`。板端保留路径为 `/home/orangepi/edgeforge_m0_frozen_r2/`。

## 3. 验收结果

| 门 | 冻结结果 | 边界 |
|---|---|---|
| S0 转换 | **通过** | W8A8 / RK3588 / 16K 工件可导出 |
| S1 初始化 | **仅 1-core 通过** | 2/3-core 因 IOVA 失败 |
| S2a 非退化文本 | **1-core 通过** | 固定五题、贪心解码、UTF-8 合法、无 `[PAD]` |
| S2b 语义对齐 | **门禁未放行/未完成判定；H2/H3 未归因，owner 接受冻结** | H1 只在事后 MMLU-only 路由规则下对 M0 决策不成立 |
| S2c agent 通道结构 | **手动模板路径通过** | 只判标记成对，不判语义 |
| S3 PC/板端定性对照 | **未执行，随冻结取消** | 原受 S2b 门控 |

## 4. 核心技术事实

### 4.1 IOVA 容量根因

RK3588 的 NPU 处于 IOMMU 之后。上游 Rockchip IOMMU 实现在 `rk_iommu_domain_alloc()` 中对 v1/v2 设置 `aperture_end = DMA_BIT_MASK(32)` 且 `force_aperture = true`，每个 domain 因此只有 4 GiB IOVA 窗口。板端 BSP 源码未直读，该结论的证据等级保留为「强、一步之遥」。

3-core 的 domain 0 前三笔实际 map 为：

- 12,709,888 B
- 88,829,952 B
- 3,972,792,320 B

合计 4,074,332,160 B，剩余 220,635,136 B。第 4 笔需 265,568,256 B，短缺 **44,933,120 B**。数字一律使用页对齐实际 map 口径；旧的 44,930,392 B 不再使用。

1-core 能运行不意味单 domain 容纳了全部映射。它实测使用两个 domain，总映射量 5,071,708,160 B；2/3-core 在需要同时可见的阶段撞到 domain 0 上限。

### 4.2 三条 3-core 路线的终局

| 路线 | 结果 | 终局 |
|---|---|---|
| X0：扩大 aperture | 上游驱动写死 32-bit aperture | **关闭** |
| X1：W4A16 降低权重块 | `w4a16` / `g32` / `g64` / `g128` 均被 RK3588 拒绝 | **关闭** |
| X2：第 4 笔 domain 0→1 | 1-core 五题 transcript 从 byte 940 起与基线分歧 | **数值安全阀失败，关闭** |

`w8a8_g128/g256` 会增加 scale 元数据，只会增大 domain 0 占用，不是容量解法。`w8a8_g512` 又因 E4B 的 256 维 tensor 无法被 512 整除而不适用。

### 4.3 模板与 agent 通道

自动 chat-template parser 的失败与「外部 `chat_template.jinja` 文件位置」无关。X5 将最小失败边界收缩为：

> RKLLM 1.3.0 parser 不支持 `raise_exception()` 实参中的相邻字符串字面量隐式拼接。

保留同一个不可达 `raise_exception()` 调用，只将相邻字符串合并为单字符串后，warning 由 1 变为 0。macro、namespace、`strip_thinking`、block-form `set`、tool-call 控制流和通道标记骨架均不是已证实根因。

`rkllm_set_chat_template` 会关闭内部自动模板处理，包括 automatic thinking。M0 只证明手动模板下 `thought` / `tool_call` 通道标记结构可行，未证明通道语义正确。

### 4.4 S2b 与校准边界

X3 的 `apply_chat_template=True` 重试中，MMLU fast-500 为 26.40%，`apply_chat_template=False` 对照为 41.60%；完整日志中没有 `Failed to parse chat_template`。HumanEval 完成 164 条生成后评分器报 `Expected list, got int`，没有原始通过数。原双任务预注册结论因此是无效/灰区；owner 后续的 MMLU-only 规则只用于 M0 路由，不能作为对外质量结论。

X4 采用 W8A8 / 16K / 1-core 合同：

| 档位 | token | 结果 | 资源峰值 |
|---|---:|---|---|
| N=128 | 105,865 | `load/build/export=0/0/0`；工件 SHA-256 `3829c6f…8d02` | CPU HWM 61,524,640 KiB；GPU 38,080 MiB |
| N=256 | 211,725 | 优化 0/42 时 CUDA OOM；`build=-1`；无工件 | CPU HWM 89,792,264 KiB；GPU 45,374 MiB |

N=128 成功仅证明先前的校准 OOM 主要由过长单样本驱动（U11 闭合）。由于 N=256 无工件，32 条 probe 的 logits 比较未执行，不存在 mean cosine、argmax 一致数或 H3 结论。

## 5. 冻结决策

### 5.1 不再执行

- 不在更大 GPU 上重开 X4。
- 不执行 `w8a8_g128/g256` 的 H2 精度阶梯。
- 不重跑 HumanEval，不补分、不拼接历史结果。
- 不执行 S3。
- 不下调 `max_context` 换取 IOVA 余量。
- 不修改 driver、device-tree、kernel 或 `rkllm_base.*.so`。
- 不继续 X5 候选、板端模板试错或大工件传输。

### 5.2 冻结未知

| 未知 | 冻结口径 |
|---|---|
| 第 4 笔分配的具体 tensor / cache 身份 | 未知，不影响 IOVA 容量根因 |
| H2 还是 H3 | 未归因，owner 接受冻结 |
| W4A16 激活缓冲是否翻倍 | 当前平台无可上板 W4A16 工件，不可测 |
| KV eager/lazy 与 iSWA 机制 | 无 32K 工件，不可测 |

这些项目不是待办，不得因「未知」而自动重开。

### 5.3 唯一重开条件

只有 owner 明确撤销冻结，且至少出现以下一项外部变化，才能新建项目，不得续写本卡：

1. 厂商 toolkit/runtime 明确支持 RK3588 W4A16 或其他显著缩小权重块的格式。
2. 厂商 BSP/driver 更改 IOMMU aperture 或提供可审计的多 domain 同时可见设计。
3. 更换硬件或受支持的平台合同。

重开必须使用新的 artifact 身份、manifest、预注册判据和独立证据包。

## 6. M0 → M2 移交

M2 尚未启动，本次冻结不是 M2 启动授权。仅保留下列输入：

- 1-core W8A8 / 16K 可运行，但不是交付形态。
- 3-core 的 4 GiB IOVA 根因、精确缺口和三条关闭路线。
- 正式校准集、agent 通道语义、上下文压缩/prompt cache 与性能数字均不属于 M0 结论。
- 若 M2 未来启动，须使用其自身新的授权与执行卡，不复用本轮云端/板端工作目录。

简化后的移交边界见 `docs/M2_板端前置清单.md`。

## 7. 冻结证据

本地只保留 7 个压缩包及对应 `.sha256`；已删除解压副本、失败轮次副本、空日志、`.pid`、`__pycache__`和过程脚本。

| 证据包 | SHA-256 | 内容 |
|---|---|---|
| `exports/m0/board/EdgeForge_M0_S6_lineB_E4B_W8A8_smoke_evidence_20260808.zip` | `02b6f144…5e586ec` | P1–P7、基线转换与板端原始证据 |
| `exports/m0/board/EdgeForge_M0_X0_iommu_aperture_evidence_20260809.zip` | `4fb17b1f…a575ed` | X0 板端只读采集 |
| `exports/m0/board/EdgeForge_M0_X1_w4a16_3core_probe_evidence_20260809.zip` | `6128faf1…8231` | W4A16 拒绝与平台矩阵 |
| `exports/m0/board/EdgeForge_M0_X2_iommu_domain_rewrite_evidence_20260809.zip` | `5ac2f0c7…cc2` | domain 改写数值安全阀 |
| `exports/m0/board/EdgeForge_M0_X3_apply_chat_template_true_retry1_evidence_20260809.zip` | `6fcdc01e…405b` | X3 MMLU/HumanEval 日志与 manifest |
| `exports/m0/board/EdgeForge_M0_X4_short_calibration_evidence_20260810.zip` | `a4558ace…3bafc` | N=128 成功与 N=256 CUDA OOM |
| `exports/m0/board/EdgeForge_M0_X5_minimal_template_bisection_evidence_20260811.zip` | `19453ff9…376d` | 模板候选、转换日志和板端 warning 计数 |

完整 SHA-256 以同名 `.zip.sha256` 文件为准。事实级结论同步保留于 `docs/facts.md` §5 和 `eval_config.yaml` 的 `board` 段。

快速复核关键主张时，可直接查看压缩包内以下成员：

| 主张 | 包内快速入口 |
|---|---|
| 3-core IOVA 峰值与缺口 | P 证据包 `P1_iova_budget/derived/p1_domain_peak.tsv` 与 `p1_failed_requests.tsv` |
| X2 从 byte 940 分歧 | X2 证据包 `raw_board/raw/{baseline_1core_raw_transcript,1core_x2.raw_transcript}.log` |
| X4 N=128/N=256 结果 | X4 证据包 `n128/build/run_result.json`、`n256/build/run_result.json` 与 `n256/final_failure_excerpt.txt` |
| X5 warning 1→0 | X5 证据包候选 22/23 的 `parser_warning_count` 及各自 `board.stdout` |

## 8. 环境清理记录

本节是 2026-08-11 的维护操作记录，用于交代删除范围与保留边界；它不是七个历史实验证据包覆盖的技术门禁结论。

### 8.1 本地

- 删除 `tmp/edgeforge_m0_board_smoke` 中约 25 GiB 的重复 `.rkllm`、虚拟环境、旧证据包和中断传输。
- 删除 X4/X5 上传 scratch、旧拟稿、会话导出、失败轮次和 20 个 Line B 过程脚本。
- `exports/` 由解压目录与重复证据收敛为 7 个可校验压缩包，约 14 MiB。

### 8.2 云端

- 删除 `/root/autodl-tmp/edgeforge_m0_lineb_20260807`。
- 删除 `/autodl-fs/data/edgeforge_x5`。
- 在后续 M0 整体收敛中删除 `/root/autodl-tmp/gemma-4-E4B-it.zip` 重复模型包。
- `/autodl-fs/data` 已使用量由约 145 GiB 降至 2.7 GiB，约释放 142 GiB。
- 共享 `rknn-llm-release-v1.3.0.zip` 及非 Line B 目录未动。

### 8.3 板端

- 删除 `edgeforge_m0_smoke_20260807`、`edgeforge_m0_r11_board`、`edgeforge_m0_r11_evidence` 和 `edgeforge_x5`。
- 保留 `/home/orangepi/edgeforge_m0_frozen_r2/` 下的 1-core 基线工件、`SHA256SUMS` 和 `FROZEN.txt`。
- 板端根分区已使用量由约 53 GiB 降至 20 GiB，约释放 33 GiB。
- 共享 runtime/SDK、API Server 及其他项目未动。

## 9. 最终验收

- [x] W8A8 / RK3588 / 16K 转换有结论
- [x] 1/2/3-core 初始化边界有结论
- [x] 3-core IOVA 根因和字节级缺口有结论
- [x] agent 通道结构有结论
- [x] 自动模板 parser 最小失败边界有结论
- [x] S2b H2/H3 未归因被明确标注，未伪装为通过
- [x] owner 冻结决策、不再执行清单和重开条件已固化
- [x] 本地、云端、板端过程资产已精简

**R2.0 为线 B 的最终事实版。不再产生 R2.x 补丁卡。**
