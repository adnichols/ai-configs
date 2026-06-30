---
name: ml-evaluation-and-tracking
description: "Benchmark and track machine learning experiments: lm-eval-harness for LLM benchmarks and Weights & Biases for experiment logging."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [ml, evaluation, benchmarking, wandb, experiment-tracking, llm]
    related_skills: [llm-inference-and-serving, huggingface-hub]
---

# ML Evaluation and Tracking

## Evaluating LLMs (lm-eval-harness)

Run standardized benchmarks (MMLU, GSM8K, HellaSwag, etc.) against any HuggingFace-compatible model or local API endpoint.

### Install
```bash
git clone https://github.com/EleutherAI/lm-evaluation-harness
cd lm-evaluation-harness
pip install -e .
```

### Run a Benchmark
```bash
lm_eval --model hf --model_args pretrained=meta-llama/Llama-2-7b-hf --tasks mmlu,gsm8k --batch_size 8 --device cuda
```

### Tasks Available
| Task | Measures |
|------|----------|
| `mmlu` | Multi-subject knowledge |
| `gsm8k` | Grade-school math reasoning |
| `hellaswag` | Commonsense inference |
| `arc_challenge` | Science questions |
| `truthfulqa_mc` | Truthfulness |

### Output Formats
```bash
lm_eval ... --output_path ./results --log_samples
# Produces JSON with aggregated scores and per-sample details
```

### Custom Tasks
Add YAML task definitions to `lm_eval/tasks/`:
```yaml
dataset_path: json
validation_split: validation
process_docs: !function utils.process
doc_to_text: "{{question}}\nA. {{choices[0]}}\nB. {{choices[1]}}"
doc_to_target: "{{answer}}"
metric:
  - accuracy
```

### API Models
```bash
lm_eval --model local-completions --model_args base_url=http://localhost:8000/v1/completions,num_concurrent=8 --tasks mmlu
```

## Weights & Biases (W&B)

Log experiments, track metrics, manage model registry, and build dashboards.

### Setup
```bash
pip install wandb
wandb login
```

### Basic Logging
```python
import wandb
wandb.init(project="my-project", config={"lr": 0.001, "epochs": 10})
for epoch in range(10):
    loss = train_step()
    wandb.log({"loss": loss, "epoch": epoch})
wandb.finish()
```

### Artifacts (Model Versioning)
```python
artifact = wandb.Artifact("model", type="model")
artifact.add_dir("./checkpoints")
wandb.log_artifact(artifact)
```

### Sweeps (Hyperparameter Search)
```yaml
# sweep.yaml
program: train.py
method: bayes
metric:
  name: val_loss
  goal: minimize
parameters:
  lr:
    distribution: uniform
    min: 0.0001
    max: 0.01
```
```bash
wandb sweep sweep.yaml
wandb agent sweep-id
```

### Common Pitfalls
- `lm-eval-harness` task names are case-sensitive
- W&B offline mode requires `wandb sync` later; don't forget
- Large batch sizes in lm-eval can OOM on consumer GPUs — start with 1 and scale up
- Always pin `lm-eval-harness` to a specific git commit for reproducibility
