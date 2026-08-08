# Latest open-model benchmark queue

**Watch window:** 2026-07-08 through 2026-08-08. Checked 2026-08-08.

This list includes only weights that Y could actually locate and download. A
public announcement, API product, waitlist or social post without weights does
not enter the benchmark queue. Dates below are public Hugging Face availability
dates, which can differ from announcement dates.

Hardware figures are planning estimates, not Y measurements. Context cache,
runtime overhead and operating-system memory still have to fit.

## Active queue

| Priority | Model | Available | License gate | First proof target | State |
|---:|---|---:|---|---|---|
| P0 | [DeepSeek V4 Flash 0731](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731) | Jul 31 | MIT | One H200, then a 128GB unified-memory device with a smaller Q2 | [First cloud run published](published/2026-08-08-deepseek-v4-flash-0731-iq3xxs-h200/README.md) |
| P0 | [Liquid LFM2.5 2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B) / [official GGUF](https://huggingface.co/LiquidAI/LFM2.5-2.6B-GGUF) | Jul 28 / Aug 1 | LFM Open License; commercial grant is revenue-limited | Q4 on Android-class ARM, then laptop CPU/GPU | Queued |
| P0 | [Microsoft VibeVoice ASR BitNet](https://huggingface.co/microsoft/VibeVoice-ASR-BitNet) | Jul 24 | MIT | ARM/AVX2 CPU speech recognition | Queued |
| P0 | [Audio8 TTS Preview 0.6B](https://huggingface.co/Audio8/Audio8-TTS-Preview-0.6b) / [INT4 ONNX](https://huggingface.co/Audio8/Audio8-TTS-Preview-0.6B-ONNX-INT4) | Jul 28 / Jul 31 | Apache-2.0 | INT4 phone/laptop CPU speech generation | Queued |
| P0 | [KAT-Coder V2.5 Dev](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev) | Jul 23 | Apache-2.0 | Q3/Q4 on a 24–32GB coding workstation | Queued |
| P0 | [Ling 3.0 Flash](https://huggingface.co/inclusionAI/Ling-3.0-flash) | Aug 2 | MIT | IQ2/IQ4 on 64–128GB memory, then full checkpoint reference | Queued; custom-runtime risk |
| P1 | [LongCat Flash Lite Sparse](https://huggingface.co/meituan-longcat/LongCat-Flash-Lite-Sparse) | Jul 31 | MIT | Official runtime on two 80GB-class GPUs; then test conversion | Queued; no credible GGUF located |

## Test order

1. Phone trio: LFM text/tool use, VibeVoice ASR and Audio8 TTS. Measure RAM,
   latency, sustained thermals, battery use and quality on an exact phone.
2. Vibe-coder workstation: KAT-Coder Q3/Q4. Measure executable patch success,
   tool-call validity, long-session repetition and tokens/second.
3. 128GB class: DeepSeek Q2 and Ling IQ2/IQ4. Start at 16K/32K context and
   record cache growth before attempting larger windows.
4. Cloud reference checkpoints: run only after the prompts, graders and local
   quant matrix are frozen, so the expensive result is directly comparable.

Every quant comparison needs the same prompt set against a higher-precision
reference, not just a tokens/second chart.

## Hold — not benchmarkable as advertised

- **Mach-1 Small Preview:** its public model endpoint returned HTTP 401 during
  the 2026-08-08 check. Keep the social claim in the watchlist until weights and
  the required runtime are anonymously downloadable.
- **Pokee Isaac 28B:** no public downloadable weights were located. A hosted or
  VPC product is not an open-weight release.
- **MiniMax H3:** weights exist, but the
  [H3 license](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/LICENSE)
  excludes use in the United States, EU, UK and South Korea without separate
  authorization. Y will not run or distribute it for the US program unless
  written authorization is obtained.
- **“Uncensored DeepSeek V4 Flash”:** this is not an official DeepSeek 0731
  product name. Community ablations must be identified by their own repository,
  revision and behavior tests.

## Admission rule

A model moves from queued to published only when its license permits the target
market, all consumed files and revisions are hashed, raw results are reviewed
for secrets, failures remain visible, and the result clearly distinguishes
cloud software proof from exact-device proof.
