# M0 §5 门②：L0/L1 去重

单位为结构化后的源会话/训练样本。L0 仅记录 Crownelius 上游 `seen_count>1` 信号；L1 依次折叠同源会话、首轮 user 精确重叠、以及剥样板后的 assistant 正文精确重复。

| 数据集 | 门④输入 | L0 上游已知重复 | L1后保留 |
|---|---:|---:|---:|
| AletheiaResearch__GLM-5.2-Agent | 319 | 0 | 234 |
| Crownelius__Complete-FABLE.5-traces-2M | 201,786 | 4,573 | 152,686 |
| Glint-Research__Fable-5-traces | 4,665 | 0 | 2 |
| WithinUsAI__claude_mythos_distilled_25k | 25,000 | 0 | 13 |
| armand0e__claude-opus-4.8-pi-traces | 4 | 0 | 0 |
| armand0e__qwen3.7-max-pi-traces | 47 | 0 | 38 |
| lambda__hermes-agent-reasoning-traces | 14,701 | 0 | 2,910 |

- 同源会话折叠删除：4,447
- 首轮 user 精确重叠删除：85,997
- 剥样板后 assistant 正文精确重复删除：195
- L2 近重 MinHash 将在本结果上运行；簇明细在 `gate2_dupe_clusters.jsonl`。

## L2 近重

使用 128-entry bottom-k 5-gram MinHash 生成候选，后以完整 5-gram Jaccard ≥0.8 验证。候选对 137,958，验证阳性对 1,372，删除 1,324 个样本；跳过过大 band 4 个。
- AletheiaResearch__GLM-5.2-Agent: L2 后保留 234，本级删除 0
- Crownelius__Complete-FABLE.5-traces-2M: L2 后保留 151,364，本级删除 1,322
- Glint-Research__Fable-5-traces: L2 后保留 1，本级删除 1
- WithinUsAI__claude_mythos_distilled_25k: L2 后保留 12，本级删除 1
- armand0e__qwen3.7-max-pi-traces: L2 后保留 38，本级删除 0
- lambda__hermes-agent-reasoning-traces: L2 后保留 2,910，本级删除 0
