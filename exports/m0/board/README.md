# M0 板端冻结证据

本目录只保留 §6 板端 smoke 的 7 个小型证据 ZIP 及同名 `.sha256`。权威结论、包含范围和快速复核入口见 `docs/m0/06_board_smoke.md` §7。

校验：

```bash
cd exports/m0/board
for manifest in *.zip.sha256; do sha256sum -c "$manifest"; done
for archive in *.zip; do unzip -tq "$archive"; done
```

ZIP 内的历史执行卡、输入 manifest 和观测日志是证据内容，不是当前执行授权。
