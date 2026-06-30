---
name: llm-inference-and-serving
description: "Run, serve, and optimize LLMs: llama.cpp local inference, vLLM high-throughput serving, and abliteration with Obliteratus."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [llm, inference, vllm, llama.cpp, gguf, serving, obliteratus]
    related_skills: [huggingface-hub]
---

# LLM Inference and Serving

Three distinct but related domains: local CPU/GPU inference with llama.cpp, high-throughput server deployment with vLLM, and model surgery (abliteration) with Obliteratus.

## llama.cpp (Local GGUF Inference)

### Setup
```bash
brew install llama.cpp          # macOS (Metal)
# OR clone and build with CUDA / ROCm flags
```

### Download Models
```bash
# Via huggingface-cli (preferred)
huggingface-cli download TheBloke/Llama-2-7B-GGUF llama-2-7b.Q4_K_M.gguf --local-dir ./models

# Via curl (direct)
curl -L -o ./models/model.gguf "<url>"
```

### Run Inference
```bash
# Interactive chat
llama-cli -m ./models/model.gguf --color -c 4096 -p "You are a helpful assistant."

# Single completion
llama-cli -m ./models/model.gguf -p "The capital of France is" -n 32

# Server mode (OpenAI-compatible API)
llama-server -m ./models/model.gguf -c 4096 --port 8080
# Test: curl http://localhost:8080/v1/chat/completions -d '{"messages":[{"role":"user","content":"hello"}]}'
```

### Key Flags
| Flag | Meaning |
|------|---------|
| `-m` | Model path |
| `-c` | Context size |
| `-n` | Tokens to generate |
| `--color` | Syntax-highlight special tokens |
| `-ngl` | Number of GPU layers to offload |
| `--port` | Server port |

### GGUF Quantization
```bash
# Convert HF model to GGUF
python convert_hf_to_gguf.py ./hf-model/ --outfile ./model.gguf --outtype q4_k_m
```

Quantization types (smaller = faster but less accurate): `Q2_K`, `Q3_K_M`, `Q4_K_M`, `Q5_K_M`, `Q6_K`, `Q8_0`, `FP16`

## vLLM (High-Throughput Serving)

### Setup
```bash
pip install vllm
```

### Launch Server
```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-hf \
  --tensor-parallel-size 1 \
  --port 8000
```

### Client Usage (OpenAI-compatible)
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(model="meta-llama/Llama-2-7b-hf", messages=[...])
```

### Key Flags
| Flag | Meaning |
|------|---------|
| `--tensor-parallel-size` | GPUs per model replica |
| `--pipeline-parallel-size` | Model replicas |
| `--max-model-len` | Max context length |
| `--quantization` | `awq`, `gptq`, `squeezellm` |
| `--enable-prefix-caching` | Automatic prompt caching |

### Benchmark
```bash
python benchmarks/benchmark_throughput.py --model meta-llama/Llama-2-7b-hf --input-len 512 --output-len 128
```

## Obliteratus (Abliteration)

Remove refusal behaviors from open-weight LLMs via diff-in-means abliteration.

### Setup
```bash
pip install obliteratus
```

### Run Abliteration
```python
from obliteratus import abliterate
abliterate(
    model_path="meta-llama/Llama-2-7b-hf",
    output_path="./unhinged-llama-7b",
    harm_categories=["illegal", "hate", "harassment"],
)
```

### Post-Abliteration Verification
- Run a refusal test suite (e.g., `jailbreak` benchmarks)
- Check that helpfulness wasn't degraded on standard benchmarks
- Quantize to GGUF and test with llama.cpp if deploying locally

## Common Pitfalls
- **llama.cpp GPU layers:** `-ngl` too high for your VRAM causes OOM; start at 99 and reduce if crashes
- **vLLM CUDA version:** vLLM is tightly coupled to PyTorch CUDA version; use the exact wheel for your CUDA
- **GGUF context size:** `-c` larger than model's training context causes gibberish; respect model card
- **Obliteratus ethics:** Only abliterate models you own or have explicit license to modify; never redistribute without checking license terms
