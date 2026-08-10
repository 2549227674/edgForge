## 新会话开场

> 本仓库即交接包。计划基准 = `docs/EdgeForge_蓝图终稿_v4-R2_2026-07-19.md`（稳定层，
> 改动需决策级理由并记入 §1 决策表）；M0 当前唯一执行卡 = `docs/m0/README.md`；
> 跨里程碑机制事实与纪律 = `docs/facts.md`；环境起点 = `docs/W0_环境准备说明_2026-07-14.md`。
> M0 §1–§6 事实卡统一收纳于 `docs/m0/`；M0 已冻结，无活动待办。
> 数据下载形态、完整性和 Git 边界见 [`data/SOURCES.md`](data/SOURCES.md)；
> 外部依赖以 [`third_party/README.md`](third_party/README.md) 中的固定子模块提交为准。
>
> **实测证据优先于一切文档**：凡涉及模型文件、上下文、显存、采样、量化配方的具体值，
> 以 `eval_config.yaml` 与 `logs/` 下的实际日志为准，文档与之冲突时回改文档。
>
> 历史继承材料统一收纳于 [`docs/research/`](docs/research/README.md)，包括 2026-07 的 04
> 事实台账、R1–R4 调研报告与面经库；它们用于溯源，权威低于实测、现行执行卡和
> `docs/facts.md`。原 zip 中 07/08/09 的计划内容已被蓝图整体取代。不要基于已废弃机制提出建议：周计划、三支柱比例、双轨配比、
> 路由脊柱、自建任务集、自采数据集、最小 MVP 分级、Pi live loop、1k–10k 子集抽样、
> MOPD 多 teacher 合版、任何 RL 阶段。
