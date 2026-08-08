# Y Proof Lab

**See an AI demo online? We turn it into a reproducible local build.**

Send us an X post, a Hugging Face model, or a GitHub workflow. We reproduce
it on the cheapest sensible cloud GPU, quantize it when that genuinely helps,
then prove the smallest Y Computer that can run it.

No machine recommendation until the workload runs.

- [See the visual Proof Lab](https://y.computer/recipes/)
- [Send Y a model or demo to prove](https://y.computer/contact/?subject=Prove%20this%20model)
- [Read the cloud and quantization plan](LAB.md)
- [Track the latest downloadable model queue](benchmarks/LATEST_MODEL_QUEUE.md)
- [Browse upstream demos queued for reproduction](DEMOS.md)

## The path from post to product

```text
X / Hugging Face / GitHub
            |
            v
cheap cloud reproduction
            |
            v
quantize + test quality
            |
            v
exact-device sign-off
            |
            v
one-command Y OS install
```

Cloud proves that the software works. Only the target hardware proves the
product.

## One Spark. 284B local. 28.29 tok/s.

We rented an actual NVIDIA DGX Spark, verified the NVIDIA P4242 board and GB10,
and loaded all 284.3 billion parameters of DeepSeek V4 Flash 0731 locally.
Then we built a smaller Y speculative-decoding sidecar on the same machine.

| Result | Provisional Y measurement |
|---|---:|
| Target files | 97.051 GiB |
| Configured context | 32,768 tokens |
| Target-only generation | 16.93 tok/s |
| Y path generation | **28.29 tok/s** |
| Speed-up / latency reduction | **1.67x / 39.40%** |
| Minimum observed available memory | **9.07 GiB** |
| Integration smoke | **6/6** |
| Spark compute billed | **USD 0.504** |

The Y sidecar is 2.196 GiB smaller than the upstream draft—a 21.64% sidecar
reduction—while matching its measured speed and smoke result. Raw requests,
responses, hashes, build flags, conversion logs, memory telemetry, limitations,
and a schema-valid run manifest are public.

- [Inspect the complete DGX Spark proof](benchmarks/published/2026-08-08-deepseek-v4-flash-0731-y-dspark-iq3m-dgx-spark/README.md)
- [Build the Y IQ3_M sidecar](recipes/dgx-spark-deepseek-v4-flash-y-dspark/README.md)
- [Inspect the initial H200 software-path run](benchmarks/published/2026-08-08-deepseek-v4-flash-0731-iq3xxs-h200/README.md)

## Proof file 001

### One long-context agent endpoint and two video generators, concurrently

A source-audited community experiment uses two NVIDIA DGX Sparks as one
distributed DeepSeek V4 Flash endpoint while each node also runs an independent
video-generation lane.

| Result | Source-reported measurement |
|---|---:|
| Configured agent context | 1,048,576 tokens |
| Agent throughput during two renders | 100.79 aggregate tok/s at C6 |
| Video output | Two 15.08-second, 832 × 480 clips with audio |
| Reported render wall time | About 28.5 minutes per clip |

**Evidence:** source-audited, not Y-reproduced. The throughput result is a
deterministic counting-prompt ceiling from one sweep, not ordinary prose speed.
Measurements are reported by TonyD2Wild.

**Availability:** research example only. MiniMax H3's community license excludes
the United States and European Union. A US/EU deployment needs an authorized or
commercially permitted video backend.

[Open the complete proof file](recipes/dgx-spark-agent-video-factory/README.md)

## What the labels mean

- **Y verified** — repeated by Y on the named hardware, with the prompt,
  versions, raw results, memory use, and limitations published.
- **Source audited** — we inspected the upstream code and evidence, but have
  not reproduced the run.
- **Upstream demo** — an original third-party example. Its claims are
  source-reported and linked; it is not presented as Y's work.
- **In the lab** — a queued experiment, not a performance claim.

## What every finished proof file contains

1. The useful outcome and visible output.
2. The exact device and memory limit.
3. Model, quant, runtime, prompt, and commit hashes.
4. Cold load, prefill, decode, peak memory, power, and thermals where relevant.
5. Quality checks against the source checkpoint.
6. License and US commercial-use gates.
7. A DIY runbook and the Y OS one-command path.

## About Y

Y builds private AI computers and Y OS for people who want to own the AI their
work depends on: solo founders, AI-native studios, privacy maximalists, and
small teams operating at unreasonable speed.

- Website: <https://y.computer>
- Y OS: <https://y.computer/y-os/>
- Company GitHub: <https://github.com/Y-Computer>

This repository distributes documentation and orchestration guidance, not
third-party model weights. Models, projects, and trademarks belong to their
respective owners. A compatibility test does not imply endorsement.
