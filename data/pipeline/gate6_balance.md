# M0 §5 门⑥配平

Mythos 在剥样板和去重后仅余 12 条（低于原始25,000条的2%），按预声明方案整集剔除。另有 2 条记录因最终 mix TruffleHog 候选无法安全精确替换而按门③高风险规则排除。其余通过硬门的 154,097 条记录全部保留为规范数据池，不再物理执行家族 cap。Crownelius 当前完整 export 的 `first_source_dataset` 远超原卡所列三家；因此仅将其数据源标签中的 Claude/Fable/Opus/Sonnet/Mythos 声明归为 `claimed_anthropic_from_source_label`，不把名称推定为已核实 teacher 身份。

| 家族/来源标签 | 记录数 |
|---|---:|
| claimed_anthropic_from_source_label | 150,919 |
| fable-5 | 1 |
| glm-5.1 | 1,116 |
| glm-5.2 | 232 |
| kimi-k2.5 | 1,791 |
| qwen3.7-max | 38 |

| 任务类型 | 记录数 |
|---|---:|
| chat_or_reasoning | 146,243 |
| hermes:Agent Tools/Background Processes | 21 |
| hermes:Agent Tools/Clarification | 4 |
| hermes:Agent Tools/Delegation | 120 |
| hermes:Agent Tools/Deployment | 2 |
| hermes:Agent Tools/Memory & Context | 119 |
| hermes:Agent Tools/Sandbox Execution | 74 |
| hermes:Agent Tools/Session & Memory | 73 |
| hermes:Agent Tools/Skill Invocation | 252 |
| hermes:Agent Tools/Testing & CI | 7 |
| hermes:Agent Tools/Todo & Planning | 74 |
| hermes:Browser Automation/Browser Tasks | 278 |
| hermes:Conversational/Conversational Tasks | 20 |
| hermes:File Operations/File Tasks | 86 |
| hermes:Multi-Tool/Multi-Tool Tasks | 116 |
| hermes:Planning & Organization/Planning Tasks | 55 |
| hermes:Repository Tasks/Bug Fix | 416 |
| hermes:Repository Tasks/Code Review & Refactoring | 2 |
| hermes:Repository Tasks/Codebase Exploration | 162 |
| hermes:Repository Tasks/Documentation | 36 |
| hermes:Repository Tasks/Environment Setup | 218 |
| hermes:Repository Tasks/Feature Implementation | 158 |
| hermes:Repository Tasks/General | 81 |
| hermes:Repository Tasks/Maintenance | 18 |
| hermes:Repository Tasks/Testing | 130 |
| hermes:Scheduling/Cron Jobs | 28 |
| hermes:Terminal & Coding/Terminal Tasks | 357 |
| tool_agent | 4,947 |

- 门⑤后输入：154,111；Mythos 规则删除 12；门③安全排除 2；规范池保留 154,097。
- 原始均匀采样的 Anthropic-style 占比：97.94%（150,920/154,097）；非 Anthropic 分组 3,177。
- 不物理删除家族样本；`data/mix.yaml` 同时记录 raw-uniform、80/20、60/40 三种训练时采样配方，须在相同 optimizer-step 与 token 预算下对照后定稿。
- 脱敏规则命中记录数：10,904；脱敏在门⑤后、门⑦前落地。
- KernelBench 排除断言：通过。
