# M0 §5 门③安全清扫

TruffleHog 完整扫描原始 archive 与 parquet export（缓存排除）；下表仅保留检测器与文件计数，绝不复述候选凭据。所有结果均为未验证或验证超时，仍按高风险训练内容处理。

| 检测器 | 命中数 | 涉及文件数 |
|---|---:|---:|
| Aiven | 3 | 1 |
| AlgoliaAdminKey | 2 | 2 |
| Box | 25 | 5 |
| CloudflareApiToken | 5 | 2 |
| Coda | 2 | 1 |
| Docker | 4 | 2 |
| EightxEight | 1 | 1 |
| Eraser | 4 | 2 |
| GitHubOauth2 | 4 | 2 |
| Github | 1 | 1 |
| Gitlab | 44 | 4 |
| GoogleGeminiAPIKey | 2 | 1 |
| Groq | 453 | 11 |
| Imagekit | 2 | 2 |
| JWT | 121 | 3 |
| LogzIO | 2 | 1 |
| Miro | 1 | 1 |
| Mockaroo | 4 | 2 |
| MongoDB | 111 | 4 |
| NpmToken | 8 | 4 |
| OpenAI | 31 | 3 |
| Postgres | 891 | 4 |
| Shortcut | 3 | 2 |
| Sirv | 1 | 1 |
| SlackWebhook | 17 | 4 |
| Stripe | 6 | 3 |
| TLy | 13 | 2 |
| TravisCI | 2 | 1 |
| URI | 18 | 4 |

结构化 IR 中命中可复用脱敏规则的样本：515。具体 uid/rule 映射在 `gate3_sensitive_hits.jsonl`，不含匹配文本。
脱敏写回严格顺延至门⑤之后，保证去污染 n-gram 扫描仍以原文进行。
