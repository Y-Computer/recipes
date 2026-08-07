# Two DGX Sparks: one agent endpoint and two video lanes

> A 1M-context agent model and two video generators. At the same time.

| Recipe status | Value |
|---|---|
| Evidence | Source-audited |
| Y reproduction | Not completed |
| Upstream commit | e9d31d7bf674ed01e1fbafa4ea45d5c277708d7d |
| Exact US/EU availability | License-blocked without separate MiniMax authorization |

**Measurement credit:** TonyD2Wild. These results have not been independently
reproduced by Y.

## The outcome

The source experiment runs DeepSeek V4 Flash 0731 tensor-parallel across two
NVIDIA DGX Sparks. Each Spark also hosts an independent ComfyUI video lane.
The agent endpoint remains available while both video jobs render.

This is a co-tenancy and scheduling experiment. It is not a new model,
quantization or training release.

## The exact device

| Component | Source configuration |
|---|---|
| Nodes | 2 × NVIDIA DGX Spark |
| Architecture | GB10 |
| Usable unified memory | About 121 GiB per node |
| Interconnect | 200G RoCE through ConnectX-7 |
| Agent layout | Tensor parallel 2 across both nodes |
| Video layout | One independent ComfyUI lane per node |

## The topology

    Operator
      |
      +-- Agent API :8888
      |      |
      |      +-- Node A · DeepSeek rank 0 · head
      |      |        +-- Video lane A · ComfyUI
      |      |
      |      +== 200G RoCE ==+
      |                       |
      |                Node B · DeepSeek rank 1 · worker
      |                         +-- Video lane B · ComfyUI
      |
      +-- Two independent render queues

There is no committed agent-to-video control loop in the upstream repository.
The agent and video services run beside each other.

## The reported memory map

Per node:

| Component | GiB |
|---|---:|
| DeepSeek weights · half-share | 79.51 |
| KV cache | 10.28 |
| Activations and CUDA graphs | About 5.2 |
| OS and container overhead | About 10 |
| Remaining headroom for video | About 16–18 |

The useful finding is load order. DeepSeek starts first and claims about
105 GiB per node. The adaptive video runtime then evicts components and works
inside the remaining headroom. Starting video first can prevent DeepSeek from
loading.

## What the source reports

Aggregate generation throughput in tokens per second:

| Concurrency | Agent only | + one render | + two renders |
|---:|---:|---:|---:|
| C1 | 88.87 | 40.98 | 28.48 |
| C2 | 149.37 | 68.38 | 50.99 |
| C3 | 199.47 | 88.19 | 66.74 |
| C4 | 214.90 | 97.19 | 73.44 |
| C5 | 203.93 | 92.14 | 74.25 |
| C6 | 285.95 | 130.77 | 100.79 |

The C6 headline is a deterministic counting-prompt ceiling. The source reports
about 28:31 to 28:54 to render each 15.08-second, 832 × 480 clip with audio.

## Evidence receipt

Treat these figures as an anecdotal baseline:

- One sweep per condition; no repetitions, randomization or uncertainty.
- Short counting prompts and outputs, not a one-million-token request.
- The raw two-render result contains maximum TTFT values of 1.329 seconds and
  1.121 seconds although the README says every condition stayed below one
  second.
- Baseline and loaded result files use different served-model names.
- The runtime image, ComfyUI revision, model revisions and weight hashes are
  not pinned.
- Reverse contention—sustained agent traffic affecting render time—was not
  measured.

## What our source audit caught

### Reference workflow mismatch

Both upstream reference-to-video examples load the FL2VA checkpoint. ComfyUI's
official reference-to-video template uses the separate Ref2VA checkpoint.

### Reproduction gap

The repository does not include its H3 container build, exact runtime digest,
model lockfile, artifact checksums or an end-to-end output validator.

### Security gap

The lab scripts use privileged containers, host networking, remote code trust
and unauthenticated APIs bound to all interfaces. Those are not customer-safe
deployment defaults.

## How the source runs it

1. Qualify two matched GB10 nodes and the private 200G RoCE fabric.
2. Start the DeepSeek worker first, then the API head.
3. Wait for weights, KV allocation and a healthy model endpoint.
4. Start one video lane on each node only after the agent service is ready.
5. Queue fixed video jobs and run the agent concurrency sweep.
6. Stop video before restarting the agent pair.
7. Verify throughput recovery and inspect the machines for OOM or Xid events.

Do not reproduce the H3 portion in the US, EU, UK or South Korea unless a
separate MiniMax authorization has been verified.

## Which Y hardware fits

| Target | Status for this exact topology |
|---|---|
| Two matched GB10 systems | Architecture match; requires licensed video backend and new benchmark |
| Y Computer Max 192 | Promising but unverified; discrete PCIe memory differs from GB10 |
| Y Computer Max 96 | Different profile; suitable for video or a smaller agent model |
| Y Mini 128 / Pro 64 | Separate ROCm profiles; current CUDA/NVFP4 artifacts do not transfer |

## What Y OS changes

- Fail-closed model and territory license gate.
- Hardware, memory, storage, fabric, driver and thermal diagnostics.
- Pinned model revisions, hashes, container digests and workflow graphs.
- Worker-head-video readiness gates and automatic rollback.
- Authenticated private endpoints instead of public unauthenticated ports.
- End-to-end upload, queue, progress, artifact retrieval and validation.
- Repeated workload benchmarks with raw results from the customer's machines.
- Documented recovery and handover.

The commercial goal is the same useful outcome with components licensed for
the customer's territory—not a promise to ship this exact H3 configuration.

## Primary sources

- Upstream experiment:
  https://github.com/tonyd2wild/ds4-h3-video-gen-factory
- DeepSeek V4 Flash 0731:
  https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731
- MiniMax H3 Community License:
  https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE
- Official ComfyUI H3 reference-to-video template:
  https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_r2v.json

## Attribution

The original factory experiment was built and measured by Tony Dinh
(@tonyd2wild) and published under MIT. Y's contribution here is an independent
source, evidence, license, compatibility and deployment audit.
