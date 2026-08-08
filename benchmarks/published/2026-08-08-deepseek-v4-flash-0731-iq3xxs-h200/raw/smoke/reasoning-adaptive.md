# OpenAI-compatible smoke report — `20260808-5b5947cc2a`

> This is a six-case integration smoke suite, not a standardized model-quality benchmark. Passing shows that basic prompting, output schemas and one tiny code task worked on this endpoint. It does not establish frontier quality or comparability with published benchmark scores.

## Outcome

- Passed: **6/6**
- Failed: **0**
- Not run: **0**
- Median end-to-end latency: **438.4 ms**
- Reported usage: **18611 input / 291 output tokens**

## Configuration

- Model: `deepseek-v4-flash-0731-iq3xxs`
- Endpoint: `http://127.0.0.1:8080/v1/chat/completions`
- Suite: `2026-08-08.2`
- Temperature / top-p: `1.0` / `0.95`
- Seed: `—`
- Reasoning mode: `adaptive`
- Raw evidence: [`reasoning-adaptive.jsonl`](reasoning-adaptive.jsonl)

## Cases

| Case | Category | Result | Latency | Input / output tokens | Server decode | Draft accepted | Detail |
|---|---|---:|---:|---:|---:|---:|---|
| exact-arithmetic | reasoning | PASS | 591.2 ms | 42 / 62 | 132.50 tok/s | — | exact match |
| code-executable | code | PASS | 1013.9 ms | 69 / 114 | 122.15 tok/s | — | all executable tests passed |
| structured-json | structured-output | PASS | 265.3 ms | 50 / 22 | 121.23 tok/s | — | exact JSON match |
| tool-call-schema | tool-use | PASS | 611.6 ms | 333 / 68 | 127.63 tok/s | — | exact tool call match |
| instruction-following | instruction-following | PASS | 230.5 ms | 45 / 17 | 110.68 tok/s | — | exact match |
| long-context-needle | long-context | PASS | 285.6 ms | 18072 / 8 | 64.52 tok/s | — | exact match |

## Interpretation boundary

Use this report to catch endpoint, chat-template, parser, tool-calling and gross runtime regressions. For a public performance claim, run a named standardized benchmark and the Y benchmark-policy measurements (warm/cold repetitions, TTFT, TPOT, throughput, memory, errors, power and thermals) on pinned hardware and artifacts.
