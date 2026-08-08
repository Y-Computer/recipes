# Benchmark run manifests

A run manifest identifies the exact model, runtime, machine, command, price and
evidence behind one test run. It complements the raw JSONL/log files; it does
not replace them and it does not make a result verified merely by validating.

- [`run-manifest.schema.json`](run-manifest.schema.json) is the reusable JSON
  Schema (Draft 2020-12).
- [`run-manifest.template.json`](run-manifest.template.json) is prefilled for
  the first DeepSeek V4 Flash smoke run. Every `null`, open issue and provisional
  reason is intentional until captured from the live machine.

## Use it

1. Copy the template to the run's private staging directory and give it the same
   run ID as the raw evidence.
2. Fill immutable identities and the advertised price **before** requests start.
3. Add timestamps, actual billing, results, failed runs and artifact hashes when
   the run finishes.
4. Resolve or retain every known issue. Review all artifacts for credentials and
   private inputs.
5. Only then copy the reviewed manifest beside evidence selected for publication.

Use UTC RFC 3339 timestamps such as `2026-08-08T14:03:27Z`. JSON syntax can be
checked without dependencies:

```bash
python3 -m json.tool benchmarks/manifests/run-manifest.template.json >/dev/null
```

Use any Draft 2020-12 JSON Schema validator for structural validation. A schema
pass proves shape, not that a hash, benchmark, price or claim is truthful.

## What must be recorded

| Area | Required evidence |
|---|---|
| Model | Repository URL/ID, requested ref, resolved immutable revision, license review, and every consumed weight, index, config, adapter and tokenizer file with byte size and SHA-256. Hash the local bytes actually loaded, not a similarly named upstream file. |
| Quant | Format and method, producer revision, base-model revision, nominal bits/weight, plus calibration dataset/revision/hash when applicable. Use `is_quantized: false` for an unmodified checkpoint; do not guess for a third-party artifact. |
| Runtime | Engine version and full commit, container image digest, base-image digest, build flags/features/patches, and effective launch configuration. `command.argv` is canonical; the display string is only for readers. |
| Cloud and hardware | Provider/service/region/market type, instance type, exact GPU count/name/memory, CPU/RAM/storage/interconnect, OS/kernel/architecture, driver, CUDA and whether this is the exact sellable target. A cloud GPU is not an exact DGX Spark result. |
| Price | The advertised rate, pricing URL and time checked, then billed duration and actual compute/storage/network/other cost. Spot/community offers and list prices must be labelled; never reconstruct the price from a newer price page. |
| Workload | Suite version/commit, exact client argv and effective sampling settings, input hashes, prompt class, configured versus tested context, concurrency/arrival pattern, cold/warm repetitions and measurement window. |
| Results | Claim status, publication labels, summary, individual metrics with units/aggregation/sample count/source, raw artifacts and failed runs. Keep each affected metric provisional. |
| Issues | Anything that can change interpretation: missing usage counters, retries, OOM/Xid, restarts, throttling, unsupported kernels, manual patches, incomplete hashes, provider substitutions or measurement gaps. Link the supporting artifact. |

For sharded checkpoints, record the index and every shard. Record tokenizer and
chat-template identity separately: the same weights with a different template
can produce a materially different result. Container tags, branches and model
names are convenient labels, not immutable identity.

## Provisional and publication labels

The fields work together:

- `run.evidence_class` follows [`BENCHMARKS.md`](../../BENCHMARKS.md):
  `source-reported`, `community-reproduced`, `y-verified` or `estimate`.
  `unclassified` is allowed only while evidence is being assembled.
- `run.provisional` and `provisional_reasons` state why the run cannot yet back a
  claim.
- `results.claim_status`, `publishable` and `labels` state the review decision.
- every metric has its own `provisional` flag so valid measurements can coexist
  with unresolved ones.

The DeepSeek template starts as `unclassified`, `PROVISIONAL`,
`NOT-A-PERFORMANCE-BENCHMARK` and `NOT-Y-VERIFIED`. A smoke-suite pass should
remain labelled that way: it checks integration, not comparative quality,
million-token context, sustained throughput, power, thermals or exact-device
performance.

Do not set `y-verified`, `accepted` or `publishable: true` until the policy in
[`BENCHMARKS.md`](../../BENCHMARKS.md) is satisfied and the exact published
artifacts have passed a privacy review.

## Secrets and public evidence

Never put API/Hugging Face tokens, cookies, SSH material, signed download URLs,
cloud credentials, private prompts or full provider control-plane IDs in a
manifest. Record secret variable **names** under `redacted_environment_keys`,
not values. Use public-safe internal references for licenses and billing rather
than embedding contracts or invoices. Hashes, immutable revisions and redacted
artifact paths are sufficient for public verification.
