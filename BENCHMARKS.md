# Benchmark policy

Every number in Y Recipes must name its provenance.

## Result classes

- **Source-reported:** inherited from a named third party.
- **Community-reproduced:** repeated by a named independent contributor.
- **Y-verified:** repeated by Y on the exact named configuration.
- **Estimate:** derived from public specifications and never presented as a
  measurement.

## Minimum Y verification

A Y-verified release records:

- Hardware model, firmware, driver and interconnect.
- Model repository, revision, filenames and SHA-256 values.
- Runtime and container digests.
- Prompt or input class, input size and output size.
- Concurrency and request arrival pattern.
- Warm and cold run counts.
- TTFT, TPOT, end-to-end latency, queue time and throughput.
- Errors, restarts, OOM or Xid events.
- Usable memory, power, temperature and throttling.
- Raw machine-readable results and the failed runs.

Configured context is not tested context. Aggregate throughput must always be
paired with concurrency and per-stream behavior. Speculative-decoding results
must state the prompt class.

## Featured source dataset

The current TonyD2Wild dataset is a one-sweep microbenchmark using a
deterministic counting prompt. It is preserved here only as a source-audited
baseline. It is not a Y acceptance result.
