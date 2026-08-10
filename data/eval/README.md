# Frozen evaluation inputs

This directory is included in a normal clone and contains the parquet inputs
used by the M0 MMLU, GSM8K, and HumanEval evaluations. Hugging Face downloader
state under nested `.cache/` directories is intentionally excluded; it is not
part of the evaluation identity.

The task/subset manifests remain authoritative for sample selection. File-level
checksums for the clone-visible inputs are listed in
[`manifests/remote_clone_assets.sha256`](../../manifests/remote_clone_assets.sha256).

| Path | Role |
|---|---|
| `mmlu/cais_mmlu/` | pinned MMLU dev/test source used to construct and audit the fast subset |
| `mmlu/fast_500/` | frozen 500-question MMLU fast subset |
| `gsm8k/main/` | pinned GSM8K train/test source |
| `gsm8k/fast_200/` | frozen 200-question GSM8K fast subset |
| `humaneval/openai_humaneval/` | HumanEval source used by the smoke task |
