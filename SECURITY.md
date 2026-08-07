# Security

Y Recipes documents experiments. A source-audited recipe is not automatically
safe to expose on a customer network.

## Known risks in the featured upstream experiment

- Privileged containers.
- Host networking.
- InfiniBand device access.
- Remote SSH orchestration.
- Runtime remote-code trust.
- Unauthenticated vLLM and ComfyUI endpoints bound to all interfaces.
- Mutable container references and unpinned model artifacts.
- Read-write host mounts.
- System-wide page-cache flushing.
- No durable readiness timeout, authorization layer or automatic rollback.

Do not expose the upstream configuration directly to the public internet.

## Y OS deployment baseline

A supported profile should use:

- Pinned model revisions, hashes and container digests.
- Private management and model-serving networks.
- Authenticated TLS at every user-facing endpoint.
- Least-privilege containers and read-only mounts where possible.
- Explicit readiness, shutdown and recovery gates.
- Input-rights checks and output provenance for media workflows.
- Structured audit logs that do not record private prompts by default.

## Reporting

Do not open a public issue containing credentials, private prompts, customer
data or unpublished vulnerability details. Contact security@y.computer with a
minimal description and a safe return address.
