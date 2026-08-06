# M0 §5 门④b：退化、模板与身份噪声

近重率将在门②使用剥样板后的 5-gram 会话聚类计算，并回填本表。

| 数据集 | 合格 IR | 最高频前缀覆盖率 | 集内精确重复率 | 身份/桩代码正则命中 |
|---|---:|---:|---:|---|
| AletheiaResearch__GLM-5.2-Agent | 319 | 0.31% | 0.00% | — |
| Crownelius__Complete-FABLE.5-traces-2M | 201,786 | 0.17% | 1.50% | ansi=2, identity=3 |
| Glint-Research__Fable-5-traces | 4,665 | 0.04% | 0.00% | — |
| WithinUsAI__claude_mythos_distilled_25k | 25,000 | 100.00% | 99.14% | invented_eval=3500, stub=1830 |
| armand0e__claude-opus-4.8-pi-traces | 4 | 25.00% | 0.00% | — |
| armand0e__qwen3.7-max-pi-traces | 47 | 2.13% | 0.00% | — |
| lambda__hermes-agent-reasoning-traces | 14,701 | 0.07% | 0.00% | claude_control=1, identity=2 |

`boilerplate_strings.txt` 保存覆盖率超过 20% 的最长共同前缀；后续去重和去污染在剥除它们后运行。
Glint 的高重复来自已核实的前缀展开，故明确不写入剥样板列表；它由门②按源会话折叠。
`gate4b_review_samples.jsonl` 为每集抽样记录；20 条人工复核结果见 `gate4b_manual_review.md`。

## 经验证的集内近重复率（门② L2）

L2 使用 128-entry bottom-k 5-gram MinHash 生成候选、完整 5-gram Jaccard ≥0.8 验证。分母为 L1 后保留数。

| 数据集 | L1 后 | L2 删除 | 经验证近重复率 |
|---|---:|---:|---:|
| AletheiaResearch__GLM-5.2-Agent | 234 | 0 | 0.00% |
| Crownelius__Complete-FABLE.5-traces-2M | 152,686 | 1,322 | 0.87% |
| Glint-Research__Fable-5-traces | 2 | 1 | 50.00% |
| WithinUsAI__claude_mythos_distilled_25k | 13 | 1 | 7.69% |
| armand0e__claude-opus-4.8-pi-traces | 0 | 0 | — |
| armand0e__qwen3.7-max-pi-traces | 38 | 0 | 0.00% |
| lambda__hermes-agent-reasoning-traces | 2,910 | 0 | 0.00% |
候选生成阶段跳过 4 个过大 band；该项已在门②报告留档。
