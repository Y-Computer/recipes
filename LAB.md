# Cloud reproduction and quantization lab

Research cutoff: **August 8, 2026**. Cloud prices change; confirm the linked
provider page before starting a long job.

## The short answer

- Start on **Runpod**, not a DGX Spark. It is the cheapest predictable path we
  found for public-weight smoke tests.
- Use **Modal** when per-second automation and serverless job orchestration are
  worth more than the lowest hourly rate.
- Rent a high-host-RAM or multi-GPU machine only to create a quant that cannot
  be produced on the target box.
- Finish on a physical **DGX Spark / Y Computer 128** if the product claim is
  about GB10 performance. A datacenter GPU proves compatibility, not Spark
  speed, power, thermals, or ARM64 behavior.

## Cheapest sensible first run

| Finished model | First useful machine | Published price | Use it for |
|---|---|---:|---|
| 7–8B Q4 | Runpod RTX A5000, 24GB | $0.27/hour | Harness, prompts, API, tool use |
| 27–35B Q4 | Runpod A40, 48GB | $0.44/hour | Fit and basic quality checks |
| 70B Q4 | Runpod A100 PCIe, 80GB | $1.39/hour | Useful speed and memory curve |
| ~100B Q4 | Runpod RTX PRO 6000, 96GB | $1.99/hour | Large single-GPU fit test |
| 200B-class MoE Q4 | Runpod H200, 141GB | $4.39/hour | Large-checkpoint reproduction |
| Blackwell kernel test | Runpod B200, 180GB | $5.89/hour | Datacenter Blackwell compatibility |

Source: [Runpod pricing](https://www.runpod.io/pricing). Storage and network
charges are separate. Vast.ai can list lower marketplace offers, but host-set
pricing and hardware variance make it less suitable for evidence-grade runs.

Modal's comparable published GPU compute is approximately $0.80/hour for L4,
$1.95/hour for L40S, $2.50/hour for A100 80GB, $4.54/hour for H200, and
$6.25/hour for B200, before separate CPU and RAM charges. Modal is a clean
automation layer, not the lowest-cost fixed bench. Source:
[Modal pricing](https://modal.com/pricing).

## What we actually test

### 1. Reproduce

- Pin the upstream repository, model revision, tokenizer, runtime, and CUDA
  image.
- Save the prompt or workload and the unedited output.
- Record cold-load time, prefill, decode speed, peak memory, and failures.
- Label every unreplicated third-party example **Upstream demo**.

### 2. Quantize

- Keep the original checkpoint as the baseline.
- Create at least two candidate precisions where practical.
- Compare task quality, not just file size and tokens per second.
- Publish the quant method, calibration data description, hashes, and runtime.
- Treat 1-bit, ternary, and additive models as research builds: they usually
  need retraining and custom kernels, not merely a lower quantization setting.

### 3. Sign off the target device

- Run three or more repetitions on the exact sellable hardware.
- Test the advertised context length and the realistic default separately.
- Measure power and thermals under a sustained workload.
- Publish the limit: what stops fitting or stops being useful.

## Hardware needed to create the quant

Running a finished quant is much cheaper than building it. Standard GGUF
conversion can use host RAM; AWQ, GPTQ, NVFP4, activation-aware calibration,
and QAT typically need much more accelerator memory.

| Source-model class | Practical build machine | Typical path |
|---|---|---|
| 1–4B | 16–32GB RAM or 12–24GB GPU | Local workstation or low-cost cloud GPU |
| 8–14B | 32–64GB RAM or 24–48GB GPU | A40 / L40S class |
| 27–35B | 80GB GPU or 128GB unified memory | A100 80GB, GH200, or DGX Spark |
| 70–122B | 2 × 80GB GPUs or ≥384GB host RAM | Multi-GPU or large-RAM cloud node |
| 284B+ | Multi-B200/GB300 class | Datacenter quantization job |

For llama.cpp GGUF quantization, the source checkpoint is loaded into host RAM
and comparable scratch space is needed. Its reference examples show roughly
32.1GB source → 4.9GB Q4 for 8B, 280.9GB → 43.1GB for 70B, and 1.63TB →
249GB for 405B. Source:
[llama.cpp quantization documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md).

Useful large-RAM options include Lambda's GH200 instance with 432GB system RAM
at $2.29/hour and its 4 × A100 40GB / 900GB RAM instance at $7.96/hour. A
405B-class CPU quant needs closer to a 2TB-RAM node; CoreWeave publishes an
8 × A100 80GB / 2TB configuration at $21.60/hour on demand or $9.65/hour spot.
Sources: [Lambda instances](https://lambda.ai/instances) and
[CoreWeave pricing](https://wf.coreweave.com/pricing).

## August 2026 model reality check

| Model | What is real now | Y decision |
|---|---|---|
| Liquid LFM2.5-2.6B | Official 1.59GB Q4_0 and 1.67GB Q4_K_M; vendor reports phone inference | Phone proof candidate; LFM commercial license changes above $10M annual revenue |
| Mach-1 Additive 35B | 8.13GB beta checkpoint and custom Apple Silicon engine | Laptop-class lab candidate; not phone-proven and compression recipe is not public |
| Pokee-Isaac 28B | Product announcement and managed service; no public weights found | Cannot independently quantize, bundle, or verify yet |
| DeepSeek V4 Flash | Public 284B/13B-active weights; large community/vendor quants | Cloud or cluster lab; do not market as a one-Spark model |

Primary sources:

- [Liquid LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B) and
  [official GGUF files](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF)
- [Mach-1 Additive 35B](https://huggingface.co/SyzygyResearch/Mach-1-Additive-35B)
- [Pokee model documentation](https://docs.pokee.ai/docs/models)
- [DeepSeek V4 Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)

## DGX Spark: buy, borrow, or rent?

NVIDIA's current DGX Spark reference has 128GB unified memory and a $4,699
listed price. It is the correct final bench for GB10 claims. It is unnecessary
for the first software test.

Third-party services advertise remote Spark access as low as $0.75/hour, but
those providers are not NVIDIA and must be validated before sending private
models or accepting their results as product evidence. Use public weights for
an initial provider check, then retain the raw environment and benchmark data.

Sources: [NVIDIA DGX Spark listing](https://marketplace.nvidia.com/en-us/enterprise/personal-ai-supercomputers/dgx-spark/),
[DGX Spark porting guide](https://docs.nvidia.com/dgx/dgx-spark-porting-guide/overview.html),
and [CUDA GPU compute capability table](https://developer.nvidia.com/cuda/gpus).

## First three proof runs

1. **Phone:** LFM2.5-2.6B Q4_K_M — offline chat, tool call, long document, and
   thermal soak on an 8GB-class Android phone.
2. **Solo-company box:** Qwen3.6-35B-A3B NVFP4 — coding, browser research,
   cited document search, and one background image task on a 128GB machine.
3. **Pro Max:** gpt-oss-120b — useful context, concurrency, and sustained
   power/thermal measurements on an exact 128GB target.

Each finished run becomes a public proof file with reproducible commands and a
one-command Y OS install profile.
