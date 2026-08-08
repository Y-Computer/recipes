# OpenAI-compatible model smoke suite

This directory contains a small, fixed integration suite for a model served by
an OpenAI-compatible `/chat/completions` endpoint. It is intentionally standard
library only and is suitable for a fresh, disposable Runpod container.

The six cases check:

1. exact arithmetic;
2. Python generation with executable tests;
3. strict structured JSON;
4. an actual schema-constrained tool call;
5. multi-constraint instruction following; and
6. exact retrieval from a deterministic synthetic long context.

## This is not a standardized benchmark

A pass is evidence that the endpoint, chat template, parser and a few basic
capabilities work together. Six hand-written cases cannot rank models or support
claims such as “95% of the original model.” It is not GPQA, MMLU-Pro, BFCL,
SWE-bench, RULER or a substitute for those suites. It also does not measure TTFT,
TPOT, concurrent throughput, sustained power, thermals or quality across a
representative dataset.

Use this suite as the first cheap gate. Only models that pass should proceed to
pinned standardized benchmarks and the measurements required by
[`BENCHMARKS.md`](../BENCHMARKS.md).

## Published runs

- [DeepSeek V4 Flash 0731 `UD-IQ3_XXS` on one H200](published/2026-08-08-deepseek-v4-flash-0731-iq3xxs-h200/README.md)
  — provisional raw evidence for target-only and DSpark performance, adaptive
  smoke testing, and a 20-prompt IFEval pilot.

The [latest open-model queue](LATEST_MODEL_QUEUE.md) tracks releases from the
last month, license gates, realistic first hardware and the next proof order.

## Run it

From the repository root:

```bash
python3 scripts/run_openai_smoke.py \
  --base-url http://127.0.0.1:8000/v1 \
  --model deepseek-ai/DeepSeek-V4-Flash-0731 \
  --output-dir benchmarks/results \
  --temperature 1 \
  --top-p 0.95 \
  --reasoning-mode auto \
  --allow-code-execution \
  --metadata provider=runpod \
  --metadata runtime=vllm
```

The defaults use DeepSeek's recommended `temperature=1` and `top_p=0.95`, but
both are explicit CLI options. `--seed 0` adds an OpenAI-style seed for servers
that support it. Some servers ignore seeds and some reject that field; the raw
request makes the choice auditable.

Reasoning controls vary across servers:

- `auto` omits a reasoning control and is the safest first run;
- `adaptive` deterministically enables thinking only for the fixed suite's
  `reasoning` category and disables it for every other category;
- `off` or `on` sends
  `chat_template_kwargs: {"enable_thinking": false|true}`; and
- `low`, `medium` or `high` sends `reasoning_effort`.

If the serving engine uses another switch, use `auto` and record its server-side
configuration with `--metadata`.

Use `--list-cases` to inspect case IDs and `--only CASE_ID` for a debugging run.
The full six-case run is the evidence run.

## API-key handling

Do not put a key on the command line. Export it into an environment variable:

```bash
export OPENAI_API_KEY='replace-in-your-shell-only'
python3 scripts/run_openai_smoke.py \
  --base-url https://your-authenticated-endpoint.example/v1 \
  --model exact-served-model-id \
  --require-api-key \
  --allow-code-execution
```

The harness never dumps the process environment. Authorization headers are
stored as `[REDACTED]`, secret-looking metadata keys are rejected, and the live
key is scrubbed from response/error objects before writing. Rotate a key if it
has ever been pasted into chat, logs, shell history or a public issue.

Prefer an SSH tunnel to a public unauthenticated vLLM port. If a public endpoint
is necessary, enforce authentication and a source-IP firewall before loading the
model.

## Generated-code safety

`--allow-code-execution` is required for the code case. The harness rejects
imports, top-level execution, dunder access and obvious dynamic-code/file calls,
then runs the answer in a short-lived subprocess with resource limits and a
minimal environment. This reduces accidents; it is **not a security sandbox**.
Run it only inside a disposable container or VM with no credentials, private
data, mounted host paths or cloud control-plane permissions.

Without the flag, the code case is recorded as `NOT_RUN` and the process exits
non-zero.

## Evidence files

Each run creates:

- `smoke-<run-id>.jsonl` — a `run_start`, one full `case_result` per request,
  and a `run_end`; and
- `smoke-<run-id>.md` — a compact human-readable report linking to the JSONL.

Each case record includes the complete credential-free request body, complete
JSON response (or raw non-JSON response), safe response headers, latency,
provider-reported token usage, grader observation, pass/fail state and captured
client/GPU metadata. llama.cpp `timings`, `draft_n` and `draft_n_accepted` fields
are retained and normalized into `server_metrics`. Add exact
image/container/model revisions and quantization details with repeatable
`--metadata KEY=VALUE` flags.

Raw prompts and model outputs may contain sensitive information if you change
the suite. Review evidence files before publishing them.

## Tests

The grader and parser tests do not contact a model endpoint:

```bash
python3 -m unittest discover -s benchmarks -p 'test_*.py' -v
```
