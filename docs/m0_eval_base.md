# M0 evaluation base

Frozen 2026-08-05. The machine-readable contract is `eval_config.yaml`; the
detailed audit trail is
`docs/EdgeForge_M0_§3_锁题与官方基线_R1.4_实际执行版.md`.

## Link probe

- 2026-08-02 — TB 2.1 probe `terminal-bench/kv-store-grpc`: endpoint
  request/reply, container command execution, and verifier result were all
  observed (`probe_link_closed=true`). Reward `0.0` is a link probe only and
  does not enter task selection or baseline scoring. Evidence:
  `results/m0_tb_probe/2026-08-02__16-31-43/`.

## B0 longitudinal baseline

Model: `gemma-4-e4b-it` PTQ `Q4_K_M`, alias `gemma4-e4b`, 131072 context,
single slot, q8_0 K/V cache, `n_predict=32768`.

| Metric | Frozen value |
|---|---:|
| TB 2.1 locked 20-task subset, 5 attempts each | 0/100 |
| Terminus hard parser errors | 149/836 (17.823%) |
| Terminus soft format warnings | 498/836 (59.569%) |
| BFCL v4 `simple_python` | 363/400 (90.75%) |
| MMLU frozen fast 500, 5-shot | 0.598 ± 0.0200 |
| GSM8K frozen fast 200, strict / flexible | 0.840 / 0.845 |
| HumanEval | 0/5 valid smoke only; no formal full baseline claimed |
| Cache-warm TTFT p50 / p95 | 349.459 / 1762.491 ms |
| Cache-warm throughput p50 | 52.029 tok/s |
| Cache-warm TPOT p50 | 19.220 ms/token |

TB failure classes F1/F2/F3/F4 are 92/7/1/0; `finish_reason=length` is 0.
Per-trial peak-context p50/p95 is 6292.5/22340.55 tokens. The final 5-task
sanity was 0/5; the list was frozen after one swap round as predeclared, so
the score is retained rather than selecting tasks until it rises.

## Official QAT-Q4_0 deployment anchor

This is a separately labelled anchor, not the longitudinal B0 before row.
Endpoint/tools smoke passed; BFCL `simple_python` is 364/400 (91.00%);
GSM8K strict/flexible is 0.850/0.865. Its cache-warm replay has TTFT p50/p95
377.423/848.977 ms, throughput p50 52.188 tok/s, and TPOT p50
19.161 ms/token. The 20-task × 5 TB slow gate remains deferred to the M6
three-point comparison.

## Artifact boundary

Versioned artifacts include configs, runners, task/manifests, five B0-derived
tapes, the 100-trajectory SHA-256 manifest, relevant static logs, and selected
small result snapshots. Raw trajectories, large lm-eval sample files, dataset
caches, and GGUF files remain local/ignored and are represented by pinned
provenance and hashes.
