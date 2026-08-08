#!/usr/bin/env python3
"""Run the fixed Y smoke suite against an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path
from typing import Any

from openai_smoke_lib import (
    SUITE_VERSION,
    OpenAICompatibleClient,
    append_jsonl,
    build_request_body,
    build_smoke_cases,
    collect_environment_metadata,
    extract_server_metrics,
    grade_response,
    normalize_usage,
    parse_metadata_pairs,
    render_markdown_summary,
    sanitize_for_log,
    sanitize_url,
    utc_now,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a dependency-free smoke suite against an OpenAI-compatible chat endpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base-url", help="Server root, /v1 root, or full chat-completions URL")
    parser.add_argument("--model", help="Exact model identifier exposed by the server")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/results"),
        help="Directory for JSONL evidence and Markdown summary",
    )
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing the API key; the value is never persisted",
    )
    parser.add_argument(
        "--require-api-key",
        action="store_true",
        help="Fail before requests if the selected API-key environment variable is empty",
    )
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed; servers may ignore it or reject unsupported seed fields",
    )
    parser.add_argument(
        "--reasoning-mode",
        choices=("auto", "adaptive", "off", "on", "low", "medium", "high"),
        default="auto",
        help=(
            "auto omits reasoning controls; adaptive enables thinking only for the reasoning case; "
            "off/on sends chat_template_kwargs.enable_thinking; low/medium/high sends reasoning_effort"
        ),
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="Per-request timeout in seconds")
    parser.add_argument(
        "--code-timeout", type=float, default=5.0, help="Generated-code subprocess timeout"
    )
    parser.add_argument(
        "--allow-code-execution",
        action="store_true",
        help="Run model-generated Python; use only inside a disposable, isolated environment",
    )
    parser.add_argument(
        "--long-context-chars",
        type=int,
        default=65_536,
        help="Approximate synthetic archive size for the needle case",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="CASE_ID",
        help="Run only a named fixed case; repeat for multiple cases",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Attach non-secret environment metadata such as provider=runpod",
    )
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--list-cases", action="store_true", help="Print fixed case IDs and exit")
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.list_cases:
        return
    if not args.base_url:
        parser.error("--base-url is required unless --list-cases is used")
    if not args.model:
        parser.error("--model is required unless --list-cases is used")
    if not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2")
    if not 0 < args.top_p <= 1:
        parser.error("--top-p must be greater than 0 and at most 1")
    if args.timeout <= 0 or args.code_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.long_context_chars < 4_096:
        parser.error("--long-context-chars must be at least 4096")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    cases = build_smoke_cases(args.long_context_chars)
    if args.list_cases:
        for case in cases:
            print(f"{case.case_id}\t{case.category}\t{case.description}")
        return 0

    available = {case.case_id for case in cases}
    unknown = sorted(set(args.only) - available)
    if unknown:
        parser.error(f"unknown --only case(s): {', '.join(unknown)}")
    if args.only:
        selected = set(args.only)
        cases = [case for case in cases if case.case_id in selected]

    try:
        custom_metadata = parse_metadata_pairs(args.metadata)
    except ValueError as exc:
        parser.error(str(exc))
    api_key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    if args.require_api_key and not api_key:
        parser.error(f"environment variable {args.api_key_env!r} is empty")

    client = OpenAICompatibleClient(args.base_url, api_key or None, args.timeout)
    settings = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "seed": args.seed,
        "reasoning_mode": args.reasoning_mode,
        "long_context_chars": args.long_context_chars,
        "code_execution": args.allow_code_execution,
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
    metadata["api"]["authentication"] = "present" if api_key else "absent"

    run_id = f"{utc_now()[:10].replace('-', '')}-{uuid.uuid4().hex[:10]}"
    output_dir = args.output_dir.resolve()
    jsonl_path = output_dir / f"smoke-{run_id}.jsonl"
    summary_path = output_dir / f"smoke-{run_id}.md"
    secret_values = (api_key,)
    append_jsonl(
        jsonl_path,
        sanitize_for_log(
            {
                "record_type": "run_start",
                "run_id": run_id,
                "started_at": utc_now(),
                "suite_version": SUITE_VERSION,
                "case_count": len(cases),
                "environment": metadata,
            },
            secret_values,
        ),
    )

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.case_id} ...", flush=True)
        body = build_request_body(
            case,
            model=args.model,
            temperature=args.temperature,
            top_p=args.top_p,
            seed=args.seed,
            reasoning_mode=args.reasoning_mode,
        )
        exchange = client.complete(body)
        if exchange.error:
            grade = {
                "passed": False,
                "status": "request_error",
                "reason": exchange.error,
                "observed": None,
            }
        else:
            grade = grade_response(
                case,
                exchange.response,
                allow_code_execution=args.allow_code_execution,
                code_timeout_seconds=args.code_timeout,
            )
        record = {
            "record_type": "case_result",
            "run_id": run_id,
            "recorded_at": utc_now(),
            "suite_version": SUITE_VERSION,
            "case_id": case.case_id,
            "category": case.category,
            "description": case.description,
            "request": {
                "method": "POST",
                "url": sanitize_url(client.endpoint),
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "[REDACTED]" if api_key else "absent",
                },
                "body": body,
            },
            "http_status": exchange.status_code,
            "response_headers": exchange.response_headers,
            "response": exchange.response,
            "raw_response": exchange.raw_response,
            "latency_ms": round(exchange.latency_ms, 3),
            "usage": normalize_usage(exchange.response),
            "server_metrics": extract_server_metrics(exchange.response),
            "passed": grade.get("passed") is True,
            "status": grade.get("status", "fail"),
            "grade": grade,
            "environment": metadata,
        }
        clean_record = sanitize_for_log(record, secret_values)
        append_jsonl(jsonl_path, clean_record)
        results.append(clean_record)
        print(f"    {str(clean_record['status']).upper()}: {clean_record['grade']['reason']}")
        if args.fail_fast and not clean_record["passed"]:
            break

    counts = {
        "passed": sum(1 for result in results if result["passed"]),
        "failed": sum(1 for result in results if result["status"] not in {"pass", "not_run"}),
        "not_run": sum(1 for result in results if result["status"] == "not_run"),
        "executed": len(results),
    }
    append_jsonl(
        jsonl_path,
        {
            "record_type": "run_end",
            "run_id": run_id,
            "finished_at": utc_now(),
            "counts": counts,
        },
    )
    summary = render_markdown_summary(
        run_id=run_id,
        metadata=metadata,
        results=results,
        jsonl_name=jsonl_path.name,
    )
    summary_path.write_text(summary, encoding="utf-8")
    print(json.dumps(counts, sort_keys=True))
    print(f"JSONL: {jsonl_path}")
    print(f"Summary: {summary_path}")
    return 0 if counts["passed"] == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
