# OpenAI-compatible smoke report — `20260808-2d4e499a16`

> This is a six-case integration smoke suite, not a standardized model-quality benchmark. Passing shows that basic prompting, output schemas and one tiny code task worked on this endpoint. It does not establish frontier quality or comparability with published benchmark scores.

## Outcome

- Passed: **5/6**
- Failed: **1**
- Not run: **0**
- Median end-to-end latency: **249.9 ms**
- Reported usage: **18611 input / 262 output tokens**

## Configuration

- Model: `deepseek-v4-flash-0731-iq3xxs`
- Endpoint: `http://127.0.0.1:8080/v1/chat/completions`
- Suite: `2026-08-08.1`
- Temperature / top-p: `1.0` / `0.95`
- Seed: `—`
- Reasoning mode: `off`
- Raw evidence: [`reasoning-off.jsonl`](reasoning-off.jsonl)

## Cases

| Case | Category | Result | Latency | Input / output tokens | Server decode | Draft accepted | Detail |
|---|---|---:|---:|---:|---:|---:|---|
| exact-arithmetic | reasoning | FAIL | 246.6 ms | 42 / 2 | 52.90 tok/s | — | expected '716', got '703' |
| code-executable | code | PASS | 1435.7 ms | 69 / 145 | 119.32 tok/s | — | all executable tests passed |
| structured-json | structured-output | PASS | 253.2 ms | 50 / 22 | 121.38 tok/s | — | exact JSON match |
| tool-call-schema | tool-use | PASS | 620.9 ms | 333 / 68 | 127.95 tok/s | — | exact tool call match |
| instruction-following | instruction-following | PASS | 235.4 ms | 45 / 17 | 108.96 tok/s | — | exact match |
| long-context-needle | long-context | PASS | 242.7 ms | 18072 / 8 | 65.91 tok/s | — | exact match |

## Interpretation boundary

Use this report to catch endpoint, chat-template, parser, tool-calling and gross runtime regressions. For a public performance claim, run a named standardized benchmark and the Y benchmark-policy measurements (warm/cold repetitions, TTFT, TPOT, throughput, memory, errors, power and thermals) on pinned hardware and artifacts.
