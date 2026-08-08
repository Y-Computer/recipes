# Attribution

## Original experiment

DS4 × H3 Video Gen Factory
Author: Tony Dinh / TonyD2Wild / @tonyd2wild
Source: https://github.com/tonyd2wild/ds4-h3-video-gen-factory
Audited commit: e9d31d7bf674ed01e1fbafa4ea45d5c277708d7d
Upstream license: MIT

TonyD2Wild performed the original hardware experiment and measurements. Those
results have not been independently reproduced by Y.

## Y contribution

Y independently reviewed:

- Repository classification and architecture.
- Raw benchmark files and claim consistency.
- Memory and device-fit implications.
- Model and dependency license boundaries.
- Workflow correctness and reproducibility gaps.
- Security differences between a lab experiment and a customer deployment.

This repository does not copy the upstream launch scripts or workflow files.
If code is incorporated later, its original copyright and MIT notice must be
preserved in the copied files and in the release package.

## DeepSeek V4 Flash DGX Spark proof

- Base model: DeepSeek V4 Flash 0731 by DeepSeek AI
- Base source: https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731
- Consumed GGUF target and upstream DSpark artifact: Unsloth
- GGUF source: https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF
- Quantization and inference runtime: llama.cpp by its contributors
- Runtime source: https://github.com/ggml-org/llama.cpp

Y's contribution is the pinned IQ3_M sidecar derivation recipe, exact-device
execution, comparative measurements, regression harness, raw evidence review,
and publication format. Y did not create the base model or the upstream GGUF
target. This Git repository does not redistribute either upstream or derived
model weights.
