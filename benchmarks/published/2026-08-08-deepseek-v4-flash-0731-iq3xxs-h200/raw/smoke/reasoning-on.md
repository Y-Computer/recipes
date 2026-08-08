# OpenAI-compatible smoke report — `20260808-f03336805f`

> This is a six-case integration smoke suite, not a standardized model-quality benchmark. Passing shows that basic prompting, output schemas and one tiny code task worked on this endpoint. It does not establish frontier quality or comparability with published benchmark scores.

## Outcome

- Passed: **4/6**
- Failed: **2**
- Not run: **0**
- Median end-to-end latency: **1344.2 ms**
- Reported usage: **18611 input / 954 output tokens**

## Configuration

- Model: `deepseek-v4-flash-0731-iq3xxs`
- Endpoint: `http://127.0.0.1:8080/v1/chat/completions`
- Suite: `2026-08-08.1`
- Temperature / top-p: `1.0` / `0.95`
- Seed: `—`
- Reasoning mode: `on`
- Raw evidence: [`reasoning-on.jsonl`](reasoning-on.jsonl)

## Cases

| Case | Category | Result | Latency | Input / output tokens | Server decode | Draft accepted | Detail |
|---|---|---:|---:|---:|---:|---:|---|
| exact-arithmetic | reasoning | PASS | 725.0 ms | 42 / 61 | 124.32 tok/s | — | exact match |
| code-executable | code | FAIL | 5460.7 ms | 69 / 512 | 98.15 tok/s | — | grader error: ValueError: answer must define exactly one function named merge_intervals |
| structured-json | structured-output | PASS | 1397.2 ms | 50 / 127 | 105.73 tok/s | — | exact JSON match |
| tool-call-schema | tool-use | PASS | 1291.2 ms | 333 / 95 | 127.90 tok/s | — | exact tool call match |
| instruction-following | instruction-following | FAIL | 1081.8 ms | 45 / 96 | 106.61 tok/s | — | expected '<answer>APPLE\|BANANA\|DATE\|FIG</answer>', got '' |
| long-context-needle | long-context | PASS | 17693.5 ms | 18072 / 63 | 105.18 tok/s | — | exact match |

## Interpretation boundary

Use this report to catch endpoint, chat-template, parser, tool-calling and gross runtime regressions. For a public performance claim, run a named standardized benchmark and the Y benchmark-policy measurements (warm/cold repetitions, TTFT, TPOT, throughput, memory, errors, power and thermals) on pinned hardware and artifacts.
