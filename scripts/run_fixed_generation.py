#!/usr/bin/env python3
"""Measure one fixed non-streaming prompt through an OpenAI-compatible API.

The runner deliberately uses only the Python standard library and the shared
credential-safe HTTP helpers in ``openai_smoke_lib``.  It writes one warm-up,
then the requested number of measured exchanges, without discarding failures.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openai_smoke_lib import (
    OpenAICompatibleClient,
    append_jsonl,
    collect_environment_metadata,
    normalize_usage,
    parse_metadata_pairs,
    sanitize_for_log,
    sanitize_url,
    utc_now,
)


RUNNER_VERSION = "2026-08-08.1"
DEFAULT_SYSTEM_PROMPT = (
    "Continue generating concise numbered observations until the token budget ends."
)
DEFAULT_USER_PROMPT = "List observations about local AI inference, starting at 1."


def build_request_body(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
    seed: int | None,
    ignore_eos: bool,
    reasoning_mode: str,
) -> dict[str, Any]:
    """Build the single request used unchanged for warm-up and measurements."""

    body: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "ignore_eos": ignore_eos,
        "stream": False,
    }
    if seed is not None:
        body["seed"] = seed
    if reasoning_mode in {"off", "on"}:
        body["chat_template_kwargs"] = {
            "enable_thinking": reasoning_mode == "on"
        }
    elif reasoning_mode != "auto":
        raise ValueError(f"unsupported reasoning mode: {reasoning_mode}")
    return body


def extract_llama_metrics(response: Any) -> dict[str, Any]:
    """Retain llama.cpp timing fields and normalize its headline measurements."""

    if not isinstance(response, Mapping):
        return {}
    timings = response.get("timings")
    timing_values = timings if isinstance(timings, Mapping) else {}
    metrics: dict[str, Any] = {}
    if timing_values:
        metrics["timings"] = dict(timing_values)
    aliases = {
        "prompt_per_second": "prompt_tokens_per_second",
        "predicted_per_second": "generation_tokens_per_second",
    }
    for source, destination in aliases.items():
        value = timing_values.get(source)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics[destination] = value

    for key in ("draft_n", "draft_n_accepted"):
        value = timing_values.get(key, response.get(key))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            metrics[key] = value
    draft_n = metrics.get("draft_n")
    draft_accepted = metrics.get("draft_n_accepted")
    if (
        isinstance(draft_n, (int, float))
        and draft_n > 0
        and isinstance(draft_accepted, (int, float))
    ):
        metrics["draft_acceptance_rate"] = draft_accepted / draft_n
    return metrics


def observed_completion_tokens(response: Any) -> int | None:
    """Read the generated-token count from usage, falling back to llama timings."""

    if not isinstance(response, Mapping):
        return None
    usage = response.get("usage")
    if isinstance(usage, Mapping):
        value = usage.get("completion_tokens")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    timings = response.get("timings")
    if isinstance(timings, Mapping):
        value = timings.get("predicted_n")
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def summarize_measurements(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Produce compact derived evidence from measured records only."""

    measured = [record for record in records if record.get("record_type") == "measurement"]
    successful = [record for record in measured if record.get("error") is None]
    latencies = [
        float(record["latency_ms"])
        for record in successful
        if isinstance(record.get("latency_ms"), (int, float))
    ]
    decode_rates = [
        float(record["server_metrics"]["generation_tokens_per_second"])
        for record in successful
        if isinstance(record.get("server_metrics"), Mapping)
        and isinstance(
            record["server_metrics"].get("generation_tokens_per_second"),
            (int, float),
        )
    ]
    drafted_total = sum(
        float(record["server_metrics"].get("draft_n", 0))
        for record in successful
        if isinstance(record.get("server_metrics"), Mapping)
        and isinstance(record["server_metrics"].get("draft_n"), (int, float))
    )
    accepted_total = sum(
        float(record["server_metrics"].get("draft_n_accepted", 0))
        for record in successful
        if isinstance(record.get("server_metrics"), Mapping)
        and isinstance(record["server_metrics"].get("draft_n_accepted"), (int, float))
    )

    summary: dict[str, Any] = {
        "requested": len(measured),
        "successful": len(successful),
        "failed": len(measured) - len(successful),
        "exact_completion_count": sum(
            record.get("completion_tokens_exact") is True for record in successful
        ),
        "unknown_completion_count": sum(
            record.get("completion_tokens_exact") is None for record in successful
        ),
    }
    if latencies:
        summary["end_to_end_latency_ms"] = {
            "mean": statistics.fmean(latencies),
            "median": statistics.median(latencies),
            "min": min(latencies),
            "max": max(latencies),
        }
    if decode_rates:
        summary["generation_tokens_per_second"] = {
            "mean": statistics.fmean(decode_rates),
            "median": statistics.median(decode_rates),
            "min": min(decode_rates),
            "max": max(decode_rates),
        }
    if drafted_total > 0:
        summary["draft"] = {
            "drafted_total": int(drafted_total),
            "accepted_total": int(accepted_total),
            "acceptance_ratio": accepted_total / drafted_total,
        }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run one warm-up and fixed-length measured requests against an "
            "OpenAI-compatible chat endpoint."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base-url", required=True, help="Server root, /v1 root, or endpoint")
    parser.add_argument("--model", required=True, help="Model identifier sent in every request")
    parser.add_argument(
        "--output",
        type=Path,
        help="Exact JSONL path; defaults to a unique file under --output-dir",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/results"),
        help="Directory used when --output is omitted",
    )
    parser.add_argument("--runs", type=int, default=5, help="Measured runs after one warm-up")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--ignore-eos",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Ask compatible servers to generate through EOS to the exact token cap",
    )
    parser.add_argument(
        "--reasoning-mode",
        choices=("auto", "off", "on"),
        default="off",
        help="auto omits controls; off/on sets chat_template_kwargs.enable_thinking",
    )
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--prompt", default=DEFAULT_USER_PROMPT)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing an API key; its value is never persisted",
    )
    parser.add_argument(
        "--require-api-key",
        action="store_true",
        help="Fail before requests when the selected key environment variable is empty",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Attach non-secret provider, runtime, hardware, or variant metadata",
    )
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.runs <= 0:
        parser.error("--runs must be positive")
    if args.max_tokens <= 0:
        parser.error("--max-tokens must be positive")
    if not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not args.system_prompt.strip() or not args.prompt.strip():
        parser.error("prompts cannot be empty")


def _record_exchange(
    *,
    record_type: str,
    run_id: str,
    run_index: int,
    client: OpenAICompatibleClient,
    body: Mapping[str, Any],
    api_key_present: bool,
    max_tokens: int,
) -> dict[str, Any]:
    exchange = client.complete(body)
    completion_tokens = observed_completion_tokens(exchange.response)
    exact = completion_tokens == max_tokens if completion_tokens is not None else None
    error = exchange.error
    status = "request_error" if error else "ok"
    if error is None and exact is False:
        status = "short_completion"
    elif error is None and exact is None and body.get("ignore_eos") is True:
        status = "completion_count_unavailable"
    return {
        "record_type": record_type,
        "run_id": run_id,
        "run": run_index,
        "recorded_at": utc_now(),
        "request": {
            "method": "POST",
            "url": sanitize_url(client.endpoint),
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "[REDACTED]" if api_key_present else "absent",
            },
            "body": dict(body),
        },
        "http_status": exchange.status_code,
        "response_headers": exchange.response_headers,
        "response": exchange.response,
        "raw_response": exchange.raw_response,
        "error": error,
        "status": status,
        "latency_ms": round(exchange.latency_ms, 3),
        "usage": normalize_usage(exchange.response),
        "server_metrics": extract_llama_metrics(exchange.response),
        "observed_completion_tokens": completion_tokens,
        "completion_tokens_exact": exact,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    try:
        custom_metadata = parse_metadata_pairs(args.metadata)
    except ValueError as exc:
        parser.error(str(exc))

    api_key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    if args.require_api_key and not api_key:
        parser.error(f"environment variable {args.api_key_env!r} is empty")

    client = OpenAICompatibleClient(args.base_url, api_key or None, args.timeout)
    body = build_request_body(
        model=args.model,
        system_prompt=args.system_prompt,
        user_prompt=args.prompt,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        seed=args.seed,
        ignore_eos=args.ignore_eos,
        reasoning_mode=args.reasoning_mode,
    )
    settings = {
        "warmup_runs": 1,
        "measured_runs": args.runs,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "seed": args.seed,
        "ignore_eos": args.ignore_eos,
        "stream": False,
        "reasoning_mode": args.reasoning_mode,
        "request_timeout_seconds": args.timeout,
    }
    repo_root = Path(__file__).resolve().parents[1]
    metadata = collect_environment_metadata(
        repo_root,
        endpoint=client.endpoint,
        model=args.model,
        settings=settings,
        custom=custom_metadata,
    )
    metadata["runner_version"] = RUNNER_VERSION
    metadata["api"]["authentication"] = "present" if api_key else "absent"

    run_id = f"{utc_now()[:10].replace('-', '')}-{uuid.uuid4().hex[:10]}"
    output_path = (
        args.output.resolve()
        if args.output is not None
        else (args.output_dir / f"fixed-generation-{run_id}.jsonl").resolve()
    )
    if output_path.exists():
        parser.error(f"refusing to append to existing output: {output_path}")

    secret_values = (api_key,)
    append_jsonl(
        output_path,
        sanitize_for_log(
            {
                "record_type": "run_start",
                "run_id": run_id,
                "started_at": utc_now(),
                "runner_version": RUNNER_VERSION,
                "request_count": args.runs + 1,
                "environment": metadata,
            },
            secret_values,
        ),
    )

    records: list[dict[str, Any]] = []
    schedule = [("warmup", 0)] + [("measurement", index) for index in range(1, args.runs + 1)]
    for position, (record_type, run_index) in enumerate(schedule, start=1):
        print(f"[{position}/{len(schedule)}] {record_type} {run_index} ...", flush=True)
        record = _record_exchange(
            record_type=record_type,
            run_id=run_id,
            run_index=run_index,
            client=client,
            body=body,
            api_key_present=bool(api_key),
            max_tokens=args.max_tokens,
        )
        clean_record = sanitize_for_log(record, secret_values)
        append_jsonl(output_path, clean_record)
        records.append(clean_record)
        print(
            f"    {clean_record['status'].upper()}: "
            f"{clean_record['latency_ms']:.3f} ms",
            flush=True,
        )

    summary = summarize_measurements(records)
    append_jsonl(
        output_path,
        {
            "record_type": "run_end",
            "run_id": run_id,
            "finished_at": utc_now(),
            "summary": summary,
        },
    )
    print(json.dumps(summary, sort_keys=True))
    print(f"JSONL: {output_path}")

    measured = [record for record in records if record["record_type"] == "measurement"]
    has_failure = any(record.get("error") is not None for record in measured)
    if args.ignore_eos:
        has_failure = has_failure or any(
            record.get("completion_tokens_exact") is not True for record in measured
        )
    return 1 if has_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
