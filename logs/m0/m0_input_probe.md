# M0 输入勘察结论

**分支判定：B。** 100 条 trajectory 中有 711/836 条保存了 `steps[].reasoning_content`，但没有保存包含 `commands` 数组的原始模型响应体；559 条的 `steps[].tool_calls` 是规范化后的结构，不能还原原始 JSON。`task_complete` 没有任何结构化键，只在文本片段中出现，不能据此可靠计算 `premature_complete_rate`。

**红灯清单：** 分支 B 会使 `prose_tokens` 改为 `non_thinking_tokens`、`command_payload_tokens` 作废，并在修改 `eval_config` 的 token 字段名前需要远端确认。更关键的是，`reasoning_content` 缺失集合与硬解析错误集合不相符：`|S_missing|=125`、`|S_hard|=149`、`|S_hard_warn|=125`，但交集仅 14，另有 111 条缺失不属于硬错误。因此 `absent_on_hard_parser_error_steps` 的身份断言不成立，触发本卡“停下并回传”条件。

**与已冻结结论的差异：** parser 四数完整复现（硬/软/分母/硬错误带 extra-text = 149/498/836/125），F1–F4 也复现为 92/7/1/0，成功率为 0/100；没有数值差异。差异在字段语义：`reasoning_content` 的 125 条缺失不等于那 125 条硬错误带 extra-text，且并非硬错误子集。怀疑方向是两项曾因同一计数而被错误关联；建议未来改为中性字段名 `reasoning_content_absent_steps`，但本次不修改 config。

**对 §4 的具体建议：** 先回传并取得 B 分支列集/字段名确认；可输出 server 真值的 completion、prompt、cached-token 指标，以及在 711 条有值响应上的 thinking 与整体渲染散文的 non-thinking 下界；不要输出 `command_payload_tokens` 或 `premature_complete_rate`。B0 服务当前未运行，`/tokenize` 不可用；不启动服务的前提下，可改用现存 `third_party/llama.cpp/build/bin/llama-tokenize` 或 `models/gemma-4-E4B-it/` 的 HF tokenizer 资产。
