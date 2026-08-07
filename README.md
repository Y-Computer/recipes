# Y Recipes

**Real AI stacks. Exact devices. Measured limits. DIY instructions. Or Y OS
does it for you.**

Y Recipes answers the question spec sheets avoid:

> What can this machine actually do?

Every recipe names the useful outcome, exact hardware, complete software
topology, memory budget, evidence level, license status and operating runbook.
The impressive number and the uncomfortable limitation live on the same page.

## Important license boundary

This repository contains documentation, orchestration guidance and benchmark
analysis only. It does not distribute model weights or container images.
MiniMax H3 is governed by a restricted custom license that excludes use,
running, modification, distribution, display, hosted services and output use
in the United States, European Union, United Kingdom and South Korea without
separate authorization. Verify every upstream license before deployment.

This project is independent and is not endorsed by the named model, software
or hardware vendors.

## Featured recipe

### A 1M-context agent model and two video generators. At the same time.

A source-audited community experiment uses two NVIDIA DGX Sparks as one
distributed DeepSeek V4 Flash endpoint while each node also runs an independent
video-generation lane.

| | Source-reported result |
|---|---:|
| Configured agent context | 1,048,576 tokens |
| Agent throughput during two renders | 100.79 aggregate tok/s at C6 |
| Video output | Two 15.08-second 832 × 480 clips with audio |
| Reported render wall time | About 28½ minutes per clip |

**Evidence:** source-audited, not yet Y-reproduced. The throughput figure is a
deterministic counting-prompt ceiling from one sweep, not normal prose speed.
Measurements are by TonyD2Wild and have not been independently reproduced by Y.

**Availability:** research example only. MiniMax H3's community license excludes
the United States and European Union. A US/EU Y OS deployment must use an
authorized or commercially permitted video backend.

[Open the complete recipe](recipes/dgx-spark-agent-video-factory/README.md)

## The evidence labels

- **Y-verified** — repeated by Y on the named hardware with raw results.
- **Source-audited** — code, raw files and claims inspected; not yet reproduced.
- **In the lab** — planned experiment, not a performance claim.

## What every recipe includes

1. **Outcome** — the useful work that runs at the same time.
2. **Device** — exact memory, accelerators, storage and interconnect.
3. **Stack** — models, runtimes, services and their relationship.
4. **Memory map** — what occupies the machine and where the cliffs are.
5. **Measurements** — workload, method, raw results and evidence grade.
6. **License gate** — where the stack may legally run and be sold.
7. **DIY runbook** — start order, readiness checks and recovery.
8. **Y OS path** — what we pin, secure, benchmark and maintain for you.

## About Y

Y builds private AI computers and deploys Y OS on supported customer hardware.
The goal is simple: own the AI your work depends on.

- Website: https://y.computer
- Recipes: https://y.computer/recipes/
- Y OS: https://y.computer/y-os/

Third-party projects and trademarks belong to their respective owners. A
recipe documents compatibility; it does not imply sponsorship.
