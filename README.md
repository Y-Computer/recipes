# Y Recipes

### Build private AI systems that should not fit on one desk.

Y Recipes is the open systems library behind [Y Computer](https://y.computer):
pinned models, optimized runtimes, exact-device benchmarks, raw evidence and
reproducible builds for people who want to own the intelligence their work
depends on.

[![DeepSeek V4 Flash 0731 benchmark snapshot on one NVIDIA DGX Spark](assets/benchmarks/deepseek-v4-flash-dgx-spark-snapshot.svg)](benchmarks/published/2026-08-08-deepseek-v4-flash-0731-y-dspark-iq3m-dgx-spark/README.md)

## Flagship proof: 284.3B on one DGX Spark

We ran all 284.3 billion parameters of DeepSeek V4 Flash 0731 on one NVIDIA
DGX Spark, then built a smaller Y speculative-decoding sidecar on that same
machine.

| Exact same-machine result | Target only | Upstream DSpark | **Y IQ3_M** |
|---|---:|---:|---:|
| Fixed 256-token generation | 16.93 tok/s | 28.09 tok/s | **28.29 tok/s** |
| Mean wall time | 15.41 s | 9.40 s | **9.34 s** |
| Sidecar size | — | 10.15 GiB | **7.95 GiB** |
| Minimum observed memory available | 16.02 GiB | 7.01 GiB | **9.07 GiB** |
| Integration gate | 6/6 | 6/6 | **6/6** |

That is **1.67× target-only throughput**, **39.40% less wall time**, a
**21.64% smaller sidecar** than upstream, and **2.06 GiB more observed memory
headroom** than the upstream path. The server was configured for 32,768 tokens;
the longest tested input was 18,072 tokens; maximum process swap was 0 KiB.

- [Inspect every result, request, hash and memory sample](benchmarks/published/2026-08-08-deepseek-v4-flash-0731-y-dspark-iq3m-dgx-spark/README.md)
- [Build the Y IQ3_M sidecar](recipes/dgx-spark-deepseek-v4-flash-y-dspark/README.md)
- [Open the machine-readable summary](benchmarks/published/2026-08-08-deepseek-v4-flash-0731-y-dspark-iq3m-dgx-spark/evidence/derived/summary.json)
- [See the visual benchmark on y.computer](https://y.computer/recipes/)

## Where does the intelligence sit?

[![DeepSeek V4 Flash 0731 official checkpoint intelligence reference](assets/benchmarks/deepseek-v4-flash-intelligence-reference.svg)](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)

The official DeepSeek checkpoint launches in the **frontier agentic band**. In
DeepSeek's own same-panel evaluation, V4 Flash 0731 scores 82.7 on
Terminal-Bench 2.1 versus 81.0 for GLM-5.2 and 85.0 for Claude Opus 4.8. It
also lands between those two on DeepSWE, Toolathlon-Verified and Agents' Last
Exam. [See the official model card and full table.](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731)

That locates the **official checkpoint**, not this exact 3-bit target and Y
sidecar. Speed is measured here; intelligence must be measured on a common
harness. The exact Y stack is therefore getting a paired three-profile suite:

1. Target-only `UD-IQ3_XXS`.
2. The same target with the upstream DSpark sidecar.
3. The same target with the Y `IQ3_M` sidecar.

The first public quality panel will use pinned MMLU-Pro, GPQA Diamond,
LiveCodeBench v6 and BFCL v4 prompts, seeds and output budgets across all three
profiles. We will publish the scores, parse failures and raw outputs together.
The existing 6/6 gate proves the serving stack works; it is not presented as an
intelligence score.

## Open systems, not screenshots

### Private frontier reasoning

Run one large OpenAI-compatible endpoint for coding agents, research,
automations and internal tools without sending every prompt to a model host.

[Open the DeepSeek-on-Spark build →](recipes/dgx-spark-deepseek-v4-flash-y-dspark/README.md)

### Agent + video factory

Connect a long-context agent endpoint to independent video-generation lanes
and let one private system reason, plan and render.

[Open the dual-Spark video factory →](recipes/dgx-spark-agent-video-factory/README.md)

### Models from phone to desk-side

Y tracks the newest downloadable weights, their real memory class, license,
runtime and smallest useful device—from phone-class models to 284B desk-side
systems.

[Open the August model queue →](benchmarks/LATEST_MODEL_QUEUE.md)

## What Y OS adds

The repository gives you the build. Y OS turns the build into a product:

- installs and pins the model, runtime and tools;
- exposes one private OpenAI-compatible endpoint;
- routes coding, research, media and automation apps to local models;
- manages updates, health, memory and recovery;
- keeps the full evidence record attached to the running configuration.

You can fork everything here and build it yourself. Or Y can ship the machine
configured, benchmarked and ready to work.

- [Configure a Y Computer](https://y.computer/build/)
- [Explore Y OS](https://y.computer/y-os/)
- [Talk to Y](https://y.computer/contact/?subject=Build%20this%20system)

## Evidence standard

Every published result names the model revision, runtime commit, exact hardware,
prompt class, context, concurrency, run count and known boundary. Finished proof
files include raw machine-readable outputs, hashes, commands, telemetry and a
schema-valid manifest.

- [Benchmark policy](BENCHMARKS.md)
- [Run-manifest schema](benchmarks/manifests/run-manifest.schema.json)
- [Contribution guide](CONTRIBUTING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

This repository distributes Y-authored documentation, harnesses and
orchestration guidance—not third-party model weights. Models, projects and
trademarks belong to their respective owners. Preserve upstream notices and
review the applicable license before commercial deployment.
