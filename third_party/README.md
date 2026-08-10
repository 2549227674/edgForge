# Third-party dependencies

`llama.cpp` and Harbor are tracked as Git submodules, so the main repository
records their exact upstream commits without copying their build trees, caches,
virtual environments, or full Git history into EdgeForge.

Initialize them after cloning:

```bash
git submodule update --init --recursive
```

| Path | Upstream | Pinned role |
|---|---|---|
| `third_party/llama.cpp` | `ggml-org/llama.cpp` | B0 inference and evaluation runtime |
| `third_party/harbor` | `harbor-framework/harbor` | Terminal-Bench task harness |

The Harbor submodule is intentionally pinned to a clean upstream commit. The M0
local example change is preserved separately in
`patches/harbor/hello-world-m0.patch`.
