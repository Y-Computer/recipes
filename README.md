# Y Proof Lab

**See an AI demo online? We turn it into a reproducible local build.**

Send us an X post, a Hugging Face model, or a GitHub workflow. We reproduce
it on the cheapest sensible cloud GPU, quantize it when that genuinely helps,
then prove the smallest Y Computer that can run it.

No machine recommendation until the workload runs.

- [See the visual Proof Lab](https://y.computer/recipes/)
- [Send Y a model or demo to prove](https://y.computer/contact/?subject=Prove%20this%20model)
- [Read the cloud and quantization plan](LAB.md)
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
