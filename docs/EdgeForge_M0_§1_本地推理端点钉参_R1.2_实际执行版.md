# EdgeForge M0 §1：本地推理端点钉参（R1.2 实际执行版）

> 在 W0 已构建 llama.cpp 的目录执行。  
> 本节不重复构建 CUDA/llama.cpp。  
> 主基线 `gemma4-e4b-it-Q4_K_M.gguf` 当前不存在，必须先由官方 BF16 权重转换并量化生成。

## 1. 下载 Google 官方 BF16 权重

Gemma 仓库需要先在网页接受许可，并在本机登录 Hugging Face：

```bash
hf auth login
```

下载到本地模型目录：

```bash
mkdir -p models/hf/gemma-4-E4B-it

hf download google/gemma-4-E4B-it \
  --local-dir models/hf/gemma-4-E4B-it
```

记录本次使用的上游 revision：

```bash
python - <<'PY' | tee logs/m0/gemma4_e4b_hf_revision.txt
from huggingface_hub import HfApi
print(HfApi().model_info("google/gemma-4-E4B-it").sha)
PY
```

## 2. 将 HF BF16 权重转换为高精度 GGUF

创建日志目录：

```bash
mkdir -p logs/m0 models
```

执行转换：

```bash
python convert_hf_to_gguf.py \
  models/hf/gemma-4-E4B-it \
  --outfile models/gemma-4-E4B-it-BF16.gguf \
  --outtype bf16 \
  2>&1 | tee logs/m0/convert_gemma4_e4b_bf16_gguf.log
```

这一阶段只生成高精度中间文件：

```text
models/gemma-4-E4B-it-BF16.gguf
```

如果转换脚本提示缺 Python 依赖，再执行：

```bash
python -m pip install -r requirements.txt
python -m pip install -U transformers
```

然后重新运行转换命令。

## 3. 从 BF16 GGUF 量化为 Q4_K_M

M0 先采用“不使用 imatrix”的固定配方，避免引入尚未冻结的校准语料轴：

```bash
./build/bin/llama-quantize \
  models/gemma-4-E4B-it-BF16.gguf \
  models/gemma4-e4b-it-Q4_K_M.gguf \
  Q4_K_M \
  2>&1 | tee logs/m0/quantize_gemma4_e4b_q4_k_m.log
```

这一步完成后，才真正得到：

```text
models/gemma4-e4b-it-Q4_K_M.gguf
```

记录两个文件的 SHA256：

```bash
sha256sum \
  models/gemma-4-E4B-it-BF16.gguf \
  models/gemma4-e4b-it-Q4_K_M.gguf \
  | tee logs/m0/gemma4_e4b_model_sha256.txt
```

对应配置应写：

```yaml
model:
  baseline_id: B0-PTQ-Q4KM
  name: gemma-4-e4b-it
  role: longitudinal_before
  training_lineage: google_bf16_instruct
  quantization_method: PTQ
  quantization_format: Q4_K_M

  path: models/gemma4-e4b-it-Q4_K_M.gguf
  sha256: <Q4_K_M 本地实测 SHA256>
  source_repo: google/gemma-4-E4B-it
  source_revision: <logs/m0/gemma4_e4b_hf_revision.txt 中的值>
  source_file: models/gemma-4-E4B-it-BF16.gguf

  conversion_command: >-
    python convert_hf_to_gguf.py models/hf/gemma-4-E4B-it
    --outfile models/gemma-4-E4B-it-BF16.gguf --outtype bf16
  quantization_command: >-
    ./build/bin/llama-quantize models/gemma-4-E4B-it-BF16.gguf
    models/gemma4-e4b-it-Q4_K_M.gguf Q4_K_M
  quantizer_commit: ad8d8219915df8e423768d082d1dccfccb6e8437

  imatrix_used: false
  imatrix_manifest: null
  imatrix_provenance: null
  imatrix_note: M0 longitudinal baseline uses a fixed no-imatrix PTQ recipe
```

后续项目模型若要与此主基线作纵向比较，必须沿用同一 PTQ 配方；不能偷偷改用 imatrix 后再把差异全部归因于训练。

## 4. 启动 Q4_K_M 主基线

```bash
./build/bin/llama-server \
  -m models/gguf/gemma4-e4b-it-Q4_K_M.gguf \
  --alias gemma4-e4b \
  -ngl 99 \
  -c 131072 \
  --parallel 1 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --jinja \
  --temp 1.0 \
  --top-p 0.95 \
  --top-k 64 \
  --seed -1 \
  --port 8080 \
  2>&1 | tee logs/m0/llama_server_boot.log
```

实测并冻结使用 q8_0 K/V KV cache、`n_ctx=131072`；全项目 candidate 沿用，f16 不作为消融轴。iSWA 模型会打印两段 KV cache 日志（full + SWA），都要记录；完整冻结字段见仓库根目录 `eval_config.yaml`。

## 5. 根据日志定最终上下文

```bash
grep -E \
  'KV self size|creating .*KV cache|CUDA.*buffer|compute buffer' \
  logs/m0/llama_server_pi_c131072_q8_reasoning_unrestricted.log
```

实测结果：RTX 4060 Laptop GPU 在 `n_ctx=131072`、K/V `q8_0` 下已完成 server 启动与两次 5121-token 请求；不再沿用“16K→12K”降级流程。SWA 和 non-SWA 的 KV 行须相加：non-SWA 1088.00 MiB + SWA 21.25 MiB = 1109.25 MiB。未来硬件若遇 OOM，单独记录该硬件的实际端点配置，不回写本冻结基线。

## 6. 验证 alias

```bash
curl -s http://localhost:8080/v1/models \
  | tee logs/m0/v1_models.json
```

结果应包含：

```text
gemma4-e4b
```

## 7. 验证 Q4_K_M 的 tools-API

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gemma4-e4b",
    "messages": [
      {
        "role": "user",
        "content": "What is the weather in Taipei? Use the provided function."
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_current_weather",
          "description": "Get current weather for a location.",
          "parameters": {
            "type": "object",
            "properties": {
              "location": {"type": "string"}
            },
            "required": ["location"]
          }
        }
      }
    ],
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
    "max_tokens": 128
  }' \
  | tee logs/m0/llama_direct_tool_call_q4_k_m.json
```

W0 的 tools 结果属于官方 QAT-Q4_0，不能代替当前 Q4_K_M 的验证。

## 8. 回填端点实测值

```yaml
llama_cpp:
  commit: ad8d8219915df8e423768d082d1dccfccb6e8437
  context_size: 131072
  gpu_layers: 99
  parallel: 1
  jinja: true
  alias: gemma4-e4b
  kv_cache_type_k: q8_0
  kv_cache_type_v: q8_0
  kv_self_size_mib: 1109.25  # non-SWA + SWA
  kv_cache_log: logs/m0/llama_server_pi_c131072_q8_reasoning_unrestricted.log

sampling:
  server_temperature: 1.0
  server_top_p: 0.95
  server_top_k: 64
  server_seed: -1
  terminus_temperature: 1.0
```

## 9. 官方 QAT-Q4_0 的本节处理

在盘 QAT-Q4_0 只登记：

```yaml
external_anchors:
  official_qat_q4_0:
    role: official_deployment_anchor
    training_lineage: google_official_qat
    quantization_method: QAT
    quantization_format: Q4_0
    source_repo: google/gemma-4-E4B-it-qat-q4_0-gguf
    source_revision: <实测>
    source_file: <实际文件名>
    path: <实际本地路径>
    sha256: <本地实测>
    alias: gemma4-e4b-qat-q4_0
    fast_gate_results: null
    slow_gate: deferred_to_M6_three_point
```

本节不启动它；快档在 D6–D7。

## 10. 提交

```bash
git add \
  eval_config.yaml \
  logs/m0/gemma4_e4b_hf_revision.txt \
  logs/m0/convert_gemma4_e4b_bf16_gguf.log \
  logs/m0/quantize_gemma4_e4b_q4_k_m.log \
  logs/m0/gemma4_e4b_model_sha256.txt \
  logs/m0/llama_server_boot.log \
  logs/m0/v1_models.json \
  logs/m0/llama_direct_tool_call_q4_k_m.json

git commit -m "feat(m0): build and pin Q4_K_M baseline"
```
