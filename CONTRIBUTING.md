# Contributing a Y Recipe

We welcome reproducible local-AI builds, corrections and independent reruns.

## Recipe requirements

A proposal must include:

- A useful outcome, not only a model name.
- Exact hardware and usable memory.
- Exact model revisions and artifact hashes.
- Runtime and container versions or digests.
- Model and dependency license status.
- Workload definition, prompt class and output settings.
- Repeated measurements plus raw machine-readable results.
- Known failures and configurations that did not work.
- Security boundary and exposed services.

## Evidence labels

- **Y-verified:** Y repeated the workload on named hardware and published raw
  results.
- **Source-audited:** source claims and files were inspected but not reproduced
  by Y.
- **Community reproduction:** a named third party repeated a pinned recipe.
- **In the lab:** planned work only; it must not contain performance claims.

## Claim rules

- Configured context is not the same as tested long-context behavior.
- Aggregate throughput must state concurrency and per-stream experience.
- Speculative-decoding results must name the prompt class.
- File size is not peak working memory.
- A model that fits is not automatically a useful co-tenant.
- Open weights does not automatically mean open source or commercial use.
- Vendor, source, community and Y measurements must remain visibly distinct.

Open an issue before a large recipe contribution so the acceptance workload can
be agreed first.
