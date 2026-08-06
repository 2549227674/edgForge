# M0 §5 门①完整性对账

上游行数来自执行时冻结的 Hugging Face Dataset Viewer `/size` 响应；下载集以记录的 `refs/convert/parquet` commit 为准。

| 数据集 | 上游行数 | 本地行数 | 完整度 | revision | 结论 |
|---|---:|---:|---:|---|---|
| AletheiaResearch/GLM-5.2-Agent | 319 | 319 | 100.0% | `d032fa92b465d6f8e64c014d8239564a8e3adb74` | 通过 |
| Crownelius/Complete-FABLE.5-traces-2M | 228,968 | 228,968 | 100.0% | `e9e7757647a0b51c86c5c7ad5425535ed62e0d08` | 通过 |
| Glint-Research/Fable-5-traces | 4,665 | 4,665 | 100.0% | `7c96478a42e0d5149e9b0bfa9cb966dcc007d3f1` | 通过 |
| Infatoshi/kernelbench-hard-traces | 383 | 383 | 100.0% | `6cae9dcb349c09c9b138b0a1cab7f34ef8b0ece3` | 通过 |
| Infatoshi/kernelbench-mega-traces | 75 | 75 | 100.0% | `0f6b0d0ef5c76d64d4f51681412b514c53edc13e` | 通过 |
| WithinUsAI/claude_mythos_distilled_25k | 25,000 | 25,000 | 100.0% | `2c5e638c51a22b8b883def51bab685ae7e282c72` | 通过 |
| armand0e/claude-opus-4.8-pi-traces | 4 | 4 | 100.0% | `7014bac3ba1b23292469dab3dbb33d3a6f0acf93` | 通过 |
| armand0e/qwen3.7-max-pi-traces | 47 | 47 | 100.0% | `bae934b1c4285b6d2ac720b9c2a127dad9c1c39a` | 通过 |
| lambda/hermes-agent-reasoning-traces | 14,701 | 14,701 | 100.0% | `b92885e4f0161d4b2536512710e004d4892cac6e` | 通过 |

## 口径说明

- Crownelius 原 `data/archive/` 单分片为 50,651 行；已补齐并冻结 `refs/convert/parquet` 的 4 个分片，共 228,968 行。
- Hermes 以 `kimi` 与 `glm-5.1` 两 config 的唯一 `id` 计数。顶层二分片的 7,646 个 id 与 config 集的交集为 7,646，故它们不另计入分母。
- Glint 的 4,665 行是前缀展开行；门④解析并标注源会话标识，实际折叠发生在门②，不在门①行数口径中处理。
- KernelBench 两集在 manifest 中登记并保留 checksum，但文件角色为 `kernelbench_excluded`，不进入训练。
