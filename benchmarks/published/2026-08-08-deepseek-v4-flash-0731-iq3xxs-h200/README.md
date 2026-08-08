# DeepSeek V4 Flash 0731 on one H200

**Status:** provisional Y-run evidence, published for review. This is not yet a
full Y-verified product claim under [`BENCHMARKS.md`](../../../BENCHMARKS.md),
and it is not a DGX Spark, Mac, laptop, or phone result.

On 2026-08-08, Y loaded the public
[`DeepSeek-V4-Flash-0731`](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)
model as Unsloth's `UD-IQ3_XXS` GGUF on one Runpod Secure Cloud NVIDIA H200.
The target quant is 104,202,502,492 bytes (97.05 GiB). A 10,896,057,440-byte
(10.15 GiB) Q8 DSpark draft was also tested. Every consumed model file is
listed with a SHA-256 digest in [`environment/model-sha256.txt`](environment/model-sha256.txt).

## Results

| Test | Result | Scope |
|---|---:|---|
| `llama-bench` prompt processing, 512 tokens | 1,171.47 tok/s | Three measured repetitions, target only |
| `llama-bench` prompt processing, 4,096 tokens | 1,171.31 tok/s | Three measured repetitions, target only |
| `llama-bench` generation, 128 tokens | 62.70 tok/s | Three measured repetitions, target only |
| Fixed 256-token generation, target only | 61.42 tok/s | Mean of five measured runs after one warm-up |
| Fixed 256-token generation, DSpark Q8 `n=3` | 90.95 tok/s | Mean of five measured runs after one warm-up |
| DSpark speed-up | **1.48x** | Same request, runtime, GPU, context and output length |
| End-to-end latency reduction | **32.24%** | 4,216.19 ms to 2,856.97 ms mean |
| DSpark draft acceptance | 51.51% | 770 of 1,495 drafted tokens accepted |
| Peak target-only GPU memory | 100,334 MiB | One-second telemetry; server run |
| Peak target + DSpark GPU memory | 111,182 MiB | One-second telemetry; server run |
| Fixed Y smoke suite, thinking globally on | 4/6 | Code and strict instruction cases exhausted their output caps |
| Fixed Y smoke suite, thinking globally off | 5/6 | Arithmetic failed |
| Fixed Y smoke suite, adaptive thinking | **6/6** | Thinking on for reasoning; off for the other five categories |
| IFEval v4 pilot, prompt strict | 90.0% | First 20 of 541 prompts; not a leaderboard score |
| IFEval v4 pilot, instruction strict | 93.33% | First 20 prompts, zero-shot, thinking off |

The fixed generation measurement uses one sequential client, a 32,768-token
server context, `temperature=0`, `seed=42`, thinking disabled, one warm-up, five
measured requests, and exactly 256 generated tokens per request with EOS
ignored. The server's own generation timing is used for tok/s; wall-clock
latency is captured independently by the client. Raw requests, responses and
all five measurements are in [`raw/performance`](raw/performance/).

DSpark consumed an additional 10,848 MiB (10.59 GiB) of peak GPU memory in this
run. Its fixed-prompt output was not byte-identical to the target-only output
despite greedy settings. That makes broader quality regression testing a
required gate before DSpark becomes a default.

## What Y improved

This run did not create a new weight quant. It exercised a third-party Unsloth
quant and improved the serving profile around it:

1. Q8 DSpark speculative decoding increased fixed-length generation throughput
   by 48.1% on this prompt class.
2. A deterministic adaptive reasoning policy moved the unchanged six-case
   integration suite from 4/6 or 5/6 with a global toggle to 6/6.
3. The public smoke harness now normalizes a stray leading `</think>` runtime
   artifact at the grading boundary while preserving the raw response, and it
   retains per-token timing fields without weakening credential redaction.

Adaptive mode enables thinking only for the suite's `reasoning` category and
disables it for code, structured output, tool use, instruction following and
long-context retrieval. The exact choice is present in every saved request;
prompts and output caps were not changed.

## Runtime

- GPU: one NVIDIA H200, 143,771 MiB reported memory, driver `570.124.06`
- Provider: Runpod Secure Cloud, US-NC-1
- Advertised rate at pod creation: USD 4.59/hour
- Recorded runtime before deletion: 2,033 seconds
- Estimated compute charge: USD 2.5921 (`2033 / 3600 * 4.59`); provider billing
  history had not settled, so this is not an invoice value
- Container tag: `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`
- CUDA toolkit: 12.8.93
- llama.cpp: tag `b10327`, commit
  `69bf6437914596fbbc4caf09a7ac16f2acdd1a94`, clean tree, CUDA enabled
- Model GGUF revision:
  `fbbb5b93fb787c21338159b0af3318bb3f4d9768`

The DSpark server configuration was:

```text
llama-server \
  -m DeepSeek-V4-Flash-0731-UD-IQ3_XXS-00001-of-00004.gguf \
  -md dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf \
  -ngl 999 -ngld 999 -c 32768 -np 1 -fa on \
  --spec-type draft-dspark --spec-draft-n-max 3 \
  --host 127.0.0.1 --port 8080 --metrics \
  --reasoning-format deepseek --reasoning on
```

The target-only comparison removed only the draft model and speculative flags.
Both servers were loopback-only and unauthenticated; the endpoint was never
published to the internet.

## Quality evidence

The adaptive smoke result is in
[`raw/smoke/reasoning-adaptive.jsonl`](raw/smoke/reasoning-adaptive.jsonl).
It covers exact arithmetic, executable generated Python, strict JSON, an exact
OpenAI-format tool call, multi-constraint instruction following, and retrieval
from a 65,536-character synthetic archive (18,072 prompt tokens in this run).
It is an integration gate, not a model-ranking benchmark.

The IFEval pilot used `lm-eval` 0.4.12, IFEval task version 4.0, zero-shot chat
completions, thinking off, `temperature=0`, a 1,280-token output cap and one
sequential client. Only 20 of 541 prompts were evaluated. See
[`raw/ifeval/results.json`](raw/ifeval/results.json) and the full
[`raw/ifeval/samples.jsonl`](raw/ifeval/samples.jsonl). The pilot is useful for
catching serving regressions but must not be compared with full-run leaderboard
scores.

## Known limits

- This cloud H200 run proves the software path, not performance or fit on a
  128GB DGX Spark or Mac. Unified memory, operating-system use and KV-cache
  headroom differ materially.
- The configured context was 32K. The longest tested smoke input was 18,072
  tokens; this is not a 1M-context result.
- TTFT, streaming TPOT, queue time, sustained concurrent throughput, throttling
  and comparable power windows were not captured.
- The container image digest, GPU firmware, interconnect and separately hashed
  embedded tokenizer/chat template were not captured.
- `lscpu` and `free` expose host-level resources inside this container, not the
  pod's contractual CPU/RAM allocation.
- The IFEval run was deliberately limited to 20 examples and the lm-eval source
  Git revision was not recorded; the task hash and lm-eval package version are
  retained in the result JSON.
- Existing smoke files from suite versions `.1` and `.2` redact two benign
  per-token timing values. Equivalent tok/s values and the unfiltered fixed-run
  server timings remain available; suite `.3` fixes this for future runs.

These gaps keep the result provisional. The next acceptance run should freeze
the container digest, run the full public quality suite, stream requests for
TTFT/TPOT, add concurrency and sustained power windows, and repeat on the exact
device Y intends to sell.
