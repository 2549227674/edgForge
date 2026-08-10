# Model asset boundary

The repository tracks only the small files needed to inspect and reproduce the
Gemma 4 interface contract: model configuration, generation configuration,
processor/tokenizer configuration, the tokenizer vocabulary, chat template,
and upstream model cards. Model weights remain local and are deliberately
ignored by Git.

After a normal clone, the following large paths are absent:

- `gemma-4-E4B-it/model.safetensors`
- `gguf/gemma4-e4b-it-Q4_K_M.gguf`
- `gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B_q4_0-it.gguf`
- `gguf/google__gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B-it-mmproj.gguf`

Their roles, current local sizes, available file granularity, and identity sources are listed
under the corresponding `LOCAL-MODEL-*` entries in
[`docs/本地项目目录索引.md`](../docs/本地项目目录索引.md). Checksums for files
included in a normal clone are frozen in
[`manifests/remote_clone_assets.sha256`](../manifests/remote_clone_assets.sha256).
