# Build the Y IQ3_M DSpark sidecar on DGX Spark

This recipe requantizes Unsloth's DSpark draft named `Q8_0` for DeepSeek V4
Flash 0731 into the smaller Y `IQ3_M` speculative-decoding sidecar. It reproduces
the artifact tested on an NVIDIA DGX Spark; it does not create a standalone
chat model.

| Item | Pinned value |
|---|---|
| Upstream repository | `unsloth/DeepSeek-V4-Flash-0731-GGUF` |
| Upstream revision | `fbbb5b93fb787c21338159b0af3318bb3f4d9768` |
| Input | `dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf` |
| Input SHA-256 | `2c7ac54b0b64a99df1f139a9f1371a00198265e1d6a614b77597d20a655a4249` |
| llama.cpp commit | `69bf6437914596fbbc4caf09a7ac16f2acdd1a94` |
| Output | `dspark-DeepSeek-V4-Flash-0731-Y-IQ3_M.gguf` |
| Output SHA-256 | `02d621a2075faddc5dbb792166568fe57dbafc991e8b86e090e5109540e98954` |
| Output size | `8,537,851,488` bytes |

## Derive and verify the sidecar

Run this in a new working directory on DGX Spark. It requires Git, CMake,
GNU 13.3 or a compatible compiler, the CUDA toolkit, `curl`, and
`sha256sum`.

```bash
set -euo pipefail

REVISION=fbbb5b93fb787c21338159b0af3318bb3f4d9768
LLAMA_CPP_COMMIT=69bf6437914596fbbc4caf09a7ac16f2acdd1a94
INPUT=dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf
OUTPUT=dspark-DeepSeek-V4-Flash-0731-Y-IQ3_M.gguf
INPUT_SHA256=2c7ac54b0b64a99df1f139a9f1371a00198265e1d6a614b77597d20a655a4249
OUTPUT_SHA256=02d621a2075faddc5dbb792166568fe57dbafc991e8b86e090e5109540e98954

curl --fail --location --retry 3 --continue-at - --output "$INPUT" \
  "https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF/resolve/$REVISION/$INPUT?download=true"
printf '%s  %s\n' "$INPUT_SHA256" "$INPUT" | sha256sum --check --strict

git clone --filter=blob:none https://github.com/ggml-org/llama.cpp.git
git -C llama.cpp checkout --detach "$LLAMA_CPP_COMMIT"
test "$(git -C llama.cpp rev-parse HEAD)" = "$LLAMA_CPP_COMMIT"

cmake -S llama.cpp -B llama.cpp/build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DCMAKE_CUDA_ARCHITECTURES=121a-real
cmake --build llama.cpp/build --target llama-quantize llama-server \
  --parallel "$(nproc)"

./llama.cpp/build/bin/llama-quantize \
  --allow-requantize "$INPUT" "$OUTPUT" IQ3_M 20

printf '%s  %s\n' "$OUTPUT_SHA256" "$OUTPUT" | sha256sum --check --strict
test "$(stat --format='%s' "$OUTPUT")" -eq 8537851488
```

The final `20` is the quantizer thread count. Do not omit
`--allow-requantize`: despite its filename, the input is an already-quantized
mix of MXFP4, Q8_0, BF16, and F32 tensors. The captured quantizer log reports
4.39 BPW for that input and 3.44 BPW for the Y output.

## Compatible target and tested launch

The exact compatible target is Unsloth's four-shard `UD-IQ3_XXS` target from
revision `fbbb5b93fb787c21338159b0af3318bb3f4d9768`. Download all four files in
the pinned [`UD-IQ3_XXS` directory](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF/tree/fbbb5b93fb787c21338159b0af3318bb3f4d9768/UD-IQ3_XXS), then pass shard 1 to `--model`; llama.cpp discovers the other
shards. Compatibility with a different target or revision is not asserted.

The DGX Spark evidence used this exact command (including paths and flags):

```bash
/workspace/y/src/llama.cpp/build/bin/llama-server \
  --model /workspace/y/models/UD-IQ3_XXS/DeepSeek-V4-Flash-0731-UD-IQ3_XXS-00001-of-00004.gguf \
  --spec-draft-model /workspace/y/models/dspark-DeepSeek-V4-Flash-0731-Y-IQ3_M.gguf \
  --spec-type draft-dspark \
  --spec-draft-n-max 3 \
  --spec-draft-ngl all \
  --spec-draft-type-k f16 \
  --spec-draft-type-v f16 \
  --alias deepseek-v4-flash-0731-iq3xxs \
  --host 127.0.0.1 \
  --port 8080 \
  --offline \
  --load-mode dio \
  --ctx-size 32768 \
  --parallel 1 \
  --n-gpu-layers all \
  --flash-attn on \
  --batch-size 2048 \
  --ubatch-size 512 \
  --cache-type-k f16 \
  --cache-type-v f16 \
  --cache-ram 0 \
  --ctx-checkpoints 0 \
  --fit off \
  --jinja \
  --threads 20 \
  --threads-batch 20 \
  --temp 1.0 \
  --top-k 0 \
  --top-p 0.95 \
  --min-p 0 \
  --metrics \
  --reasoning-format deepseek \
  --reasoning on
```

The server is deliberately loopback-only and unauthenticated. Add an
authenticated proxy before exposing it beyond the host.

## Quality, attribution, and license caveats

This is lossy requantization from an already-quantized mixed-tensor artifact,
not quantization from an FP16/BF16 source. The byte hash proves artifact
identity, not model quality. Do not use the sidecar as a standalone model. Its
reduced fidelity can change draft acceptance, performance, and—in the tested
DSpark implementation—observable output behavior. Validate all three on your
workload before making it a default.

DeepSeek created the base model and Unsloth distributed the GGUF input and
compatible target. The copied evidence identifies the base model license as
MIT, but this recipe neither redistributes weights nor grants model rights.
Preserve upstream notices and review the
[DeepSeek license](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/main/LICENSE)
and the
[pinned Unsloth model card](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF/blob/fbbb5b93fb787c21338159b0af3318bb3f4d9768/README.md)
before using or distributing the derived artifact. The repository's license
does not relicense third-party weights.

The hashes, output size, hardware identity, build selection, logs, and original
one-line launch command are in the copied
[DGX Spark evidence bundle](../../benchmarks/published/2026-08-08-deepseek-v4-flash-0731-y-dspark-iq3m-dgx-spark/evidence/).
