#!/usr/bin/env python3
"""Dependency-free helpers for the Y OpenAI-compatible smoke suite.

This module deliberately uses only the Python standard library so it can run in
the same disposable container as a model server without changing that server's
Python environment.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import datetime as dt
import json
import os
import platform
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


SUITE_VERSION = "2026-08-08.3"
REDACTED = "[REDACTED]"
SECRET_KEY_PATTERN = re.compile(
    r"(?:api[-_]?key|authorization|password|passwd|secret|access[-_]?token|"
    r"refresh[-_]?token|(?:^|[-_])token(?:$|[-_])|bearer|credential|cookie)",
    re.IGNORECASE,
)
SAFE_TOKEN_METRIC_KEYS = frozenset(
    {
        "prompt_per_token_ms",
        "predicted_per_token_ms",
    }
)
SAFE_RESPONSE_HEADERS = {
    "content-type",
    "date",
    "server",
    "x-request-id",
    "request-id",
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
}


@dataclasses.dataclass(frozen=True)
class SmokeCase:
    """One stable smoke-suite case."""

    case_id: str
    category: str
    description: str
    messages: list[dict[str, Any]]
    grader: str
    expected: Any
    max_tokens: int = 256
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None


@dataclasses.dataclass
class ApiExchange:
    """The observable parts of one HTTP exchange, excluding credentials."""

    status_code: int | None
    response_headers: dict[str, str]
    response: Any
    raw_response: str | None
    error: str | None
    latency_ms: float


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds")


def normalize_chat_completions_url(base_url: str) -> str:
    """Turn a server root or /v1 root into a chat-completions endpoint."""

    value = base_url.strip().rstrip("/")
    if not value:
        raise ValueError("base URL cannot be empty")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an http:// or https:// URL")
    if parsed.path.endswith("/chat/completions"):
        return value
    if parsed.path.endswith("/v1"):
        return value + "/chat/completions"
    return value + "/v1/chat/completions"


def sanitize_url(value: str) -> str:
    """Redact credentials and secret-looking query parameters from a URL."""

    try:
        parsed = urllib.parse.urlsplit(value)
        hostname = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port is not None else ""
        netloc = hostname + port
        if parsed.username is not None or parsed.password is not None:
            netloc = f"{REDACTED}@{netloc}"
        query = []
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
            query.append((key, REDACTED if SECRET_KEY_PATTERN.search(key) else item))
        return urllib.parse.urlunsplit(
            (parsed.scheme, netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
        )
    except (TypeError, ValueError):
        return value


def sanitize_for_log(value: Any, secrets: Sequence[str] = ()) -> Any:
    """Recursively scrub credentials from an object before persistence."""

    live_secrets = tuple(secret for secret in secrets if secret)

    def scrub_string(text: str) -> str:
        result = text
        for secret in live_secrets:
            result = result.replace(secret, REDACTED)
        # Catch a bearer token in an exception even if it was not the selected key.
        result = re.sub(
            r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}",
            f"Bearer {REDACTED}",
            result,
        )
        return result

    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            safe_token_metric = (
                key_text in SAFE_TOKEN_METRIC_KEYS
                and isinstance(item, (int, float))
                and not isinstance(item, bool)
            )
            if not safe_token_metric and SECRET_KEY_PATTERN.search(key_text):
                clean[key_text] = REDACTED if item not in (None, "") else item
            else:
                clean[key_text] = sanitize_for_log(item, live_secrets)
        return clean
    if isinstance(value, (list, tuple)):
        return [sanitize_for_log(item, live_secrets) for item in value]
    if isinstance(value, str):
        return scrub_string(value)
    return value


def _needle_context(target_chars: int) -> tuple[str, str]:
    """Build a deterministic synthetic context and place one needle near 73%."""

    if target_chars < 4_096:
        raise ValueError("long-context size must be at least 4096 characters")
    needle = "Y-COMET-48271"
    line_template = (
        "Archive record {index:05d}: project={project}; zone={zone}; status=closed; "
        "reference={reference:08x}. This record is synthetic filler.\n"
    )
    projects = ("amber", "birch", "cobalt", "dune", "ember", "fjord", "garnet")
    zones = ("north", "south", "east", "west")
    lines: list[str] = []
    total = 0
    index = 0
    insertion_target = int(target_chars * 0.73)
    inserted = False
    while total < target_chars:
        if not inserted and total >= insertion_target:
            line = (
                "Archive exception: the recovery phrase for project ORBIT is "
                f"{needle}. Preserve capitalization exactly.\n"
            )
            inserted = True
        else:
            line = line_template.format(
                index=index,
                project=projects[index % len(projects)],
                zone=zones[(index * 3) % len(zones)],
                reference=(index * 2_654_435_761) & 0xFFFFFFFF,
            )
            index += 1
        lines.append(line)
        total += len(line)
    return "".join(lines), needle


def build_smoke_cases(long_context_chars: int = 65_536) -> list[SmokeCase]:
    """Return the fixed, versioned smoke suite."""

    context, needle = _needle_context(long_context_chars)
    return [
        SmokeCase(
            case_id="exact-arithmetic",
            category="reasoning",
            description="Exact arithmetic with a strict one-token-style answer.",
            messages=[
                {
                    "role": "system",
                    "content": "Follow the requested output format exactly. Do not explain.",
                },
                {
                    "role": "user",
                    "content": "Compute (37 * 19) - (84 / 7) + (5 ** 2). Reply with only the integer.",
                },
            ],
            grader="exact_text",
            expected="716",
            max_tokens=64,
        ),
        SmokeCase(
            case_id="code-executable",
            category="code",
            description="Generate a Python function that must pass executable tests.",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only one Python code block. Do not import modules and do not include "
                        "top-level executable statements."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Implement merge_intervals(intervals). Input is a list of [start, end] integer "
                        "pairs. Merge overlapping intervals, including intervals that touch at an "
                        "endpoint. Return a new sorted list and do not mutate the input."
                    ),
                },
            ],
            grader="python_tests",
            expected="merge_intervals",
            max_tokens=512,
        ),
        SmokeCase(
            case_id="structured-json",
            category="structured-output",
            description="Produce a strict JSON object with exact types and values.",
            messages=[
                {
                    "role": "system",
                    "content": "Return valid JSON only, without Markdown fences or commentary.",
                },
                {
                    "role": "user",
                    "content": (
                        "Return an object with exactly these fields and values: project is Y, priority "
                        "is the integer 3, tags is the array local then private, and approved is true."
                    ),
                },
            ],
            grader="json_exact",
            expected={
                "project": "Y",
                "priority": 3,
                "tags": ["local", "private"],
                "approved": True,
            },
            max_tokens=128,
        ),
        SmokeCase(
            case_id="tool-call-schema",
            category="tool-use",
            description="Emit an actual OpenAI-format tool call with schema-valid arguments.",
            messages=[
                {
                    "role": "system",
                    "content": "Use the supplied tool for inventory requests.",
                },
                {
                    "role": "user",
                    "content": "Check inventory for product YC-PM-128 in the us-west region.",
                },
            ],
            grader="tool_call_exact",
            expected={
                "name": "lookup_inventory",
                "arguments": {"product_id": "YC-PM-128", "region": "us-west"},
            },
            max_tokens=128,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_inventory",
                        "description": "Look up product inventory in one region.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "region": {
                                    "type": "string",
                                    "enum": ["us-east", "us-west", "eu-west"],
                                },
                            },
                            "required": ["product_id", "region"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            tool_choice="required",
        ),
        SmokeCase(
            case_id="instruction-following",
            category="instruction-following",
            description="Follow ordering, casing, delimiter, and wrapper constraints together.",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sort the supplied words alphabetically ignoring case, uppercase every word, "
                        "join them with |, wrap the result in <answer> and </answer>, and output nothing else."
                    ),
                },
                {"role": "user", "content": "fig, apple, Date, banana"},
            ],
            grader="exact_text",
            expected="<answer>APPLE|BANANA|DATE|FIG</answer>",
            max_tokens=96,
        ),
        SmokeCase(
            case_id="long-context-needle",
            category="long-context",
            description="Retrieve one exact needle from deterministic synthetic context.",
            messages=[
                {
                    "role": "system",
                    "content": "Answer from the archive only. Follow the exact output constraint.",
                },
                {
                    "role": "user",
                    "content": (
                        "Below is a synthetic archive. What is the recovery phrase for project ORBIT? "
                        "Return only the phrase, preserving capitalization.\n\n" + context
                    ),
                },
            ],
            grader="exact_text",
            expected=needle,
            max_tokens=96,
        ),
    ]


def build_request_body(
    case: SmokeCase,
    *,
    model: str,
    temperature: float,
    top_p: float,
    seed: int | None,
    reasoning_mode: str,
) -> dict[str, Any]:
    """Construct one OpenAI-compatible request without credentials."""

    body: dict[str, Any] = {
        "model": model,
        "messages": case.messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": case.max_tokens,
        "stream": False,
    }
    if seed is not None:
        body["seed"] = seed
    if reasoning_mode == "adaptive":
        body["chat_template_kwargs"] = {"enable_thinking": case.category == "reasoning"}
    elif reasoning_mode in {"off", "on"}:
        body["chat_template_kwargs"] = {"enable_thinking": reasoning_mode == "on"}
    elif reasoning_mode in {"low", "medium", "high"}:
        body["reasoning_effort"] = reasoning_mode
    elif reasoning_mode != "auto":
        raise ValueError(f"unsupported reasoning mode: {reasoning_mode}")
    if case.tools is not None:
        body["tools"] = case.tools
    if case.tool_choice is not None:
        body["tool_choice"] = case.tool_choice
    return body


class OpenAICompatibleClient:
    """Minimal non-streaming OpenAI-compatible HTTP client."""

    def __init__(self, base_url: str, api_key: str | None, timeout_seconds: float):
        self.endpoint = normalize_chat_completions_url(base_url)
        self.api_key = api_key or None
        self.timeout_seconds = timeout_seconds

    def complete(self, body: Mapping[str, Any]) -> ApiExchange:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
                elapsed = (time.perf_counter() - started) * 1_000
                raw_text = raw_bytes.decode("utf-8", errors="replace")
                parsed, raw_fallback = _parse_response_body(raw_text)
                return ApiExchange(
                    status_code=response.status,
                    response_headers=_safe_headers(response.headers.items()),
                    response=parsed,
                    raw_response=raw_fallback,
                    error=None,
                    latency_ms=elapsed,
                )
        except urllib.error.HTTPError as exc:
            elapsed = (time.perf_counter() - started) * 1_000
            raw_text = exc.read().decode("utf-8", errors="replace")
            parsed, raw_fallback = _parse_response_body(raw_text)
            return ApiExchange(
                status_code=exc.code,
                response_headers=_safe_headers(exc.headers.items() if exc.headers else []),
                response=parsed,
                raw_response=raw_fallback,
                error=f"HTTP {exc.code}: {exc.reason}",
                latency_ms=elapsed,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            elapsed = (time.perf_counter() - started) * 1_000
            return ApiExchange(
                status_code=None,
                response_headers={},
                response=None,
                raw_response=None,
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=elapsed,
            )


def _parse_response_body(raw_text: str) -> tuple[Any, str | None]:
    try:
        return json.loads(raw_text), None
    except json.JSONDecodeError:
        return None, raw_text


def _safe_headers(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    return {
        key.lower(): value
        for key, value in items
        if key.lower() in SAFE_RESPONSE_HEADERS
    }


def response_message(response: Any) -> dict[str, Any]:
    if not isinstance(response, Mapping):
        raise ValueError("response is not a JSON object")
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("response has no choices")
    choice = choices[0]
    if not isinstance(choice, Mapping) or not isinstance(choice.get("message"), Mapping):
        raise ValueError("first choice has no message")
    return dict(choice["message"])


def extract_text_content(response: Any) -> str:
    """Read string or OpenAI content-part text from the first message."""

    content = response_message(response).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        if parts:
            return "".join(parts)
    raise ValueError("first response message has no text content")


FENCE_PATTERN = re.compile(
    r"^\s*```(?:python|py|json)?\s*\n(?P<body>[\s\S]*?)\n```\s*$",
    re.IGNORECASE,
)
LEADING_THINK_CLOSER_PATTERN = re.compile(r"^\s*(?:</think>\s*)+")


def strip_leading_think_artifacts(text: str) -> str:
    """Remove only one or more stray leading ``</think>`` closers.

    Some reasoning chat templates emit a closing tag at the start of otherwise
    normal assistant content. The expression is deliberately anchored and
    case-sensitive so embedded, later, or merely similar text remains evidence.
    """

    return LEADING_THINK_CLOSER_PATTERN.sub("", text, count=1)


def normalize_assistant_response(response: Any) -> Any:
    """Return a copy with leading think closers removed from assistant content.

    The raw response passed by the caller is never mutated. In particular,
    ``reasoning_content`` is retained exactly as received.
    """

    if not isinstance(response, Mapping):
        return response
    normalized = copy.deepcopy(response)
    choices = normalized.get("choices")
    if not isinstance(choices, list):
        return normalized
    for choice in choices:
        if not isinstance(choice, Mapping):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = strip_leading_think_artifacts(content)
    return normalized


def strip_single_code_fence(text: str) -> str:
    match = FENCE_PATTERN.match(text)
    return match.group("body") if match else text.strip()


def parse_json_text(text: str) -> Any:
    return json.loads(strip_single_code_fence(text))


def _grade_exact_text(expected: str, response: Any) -> dict[str, Any]:
    actual = extract_text_content(response).strip()
    passed = actual == expected
    return {
        "passed": passed,
        "status": "pass" if passed else "fail",
        "reason": "exact match" if passed else f"expected {expected!r}, got {actual!r}",
        "observed": actual,
    }


def _grade_json_exact(expected: Any, response: Any) -> dict[str, Any]:
    actual = parse_json_text(extract_text_content(response))
    passed = actual == expected
    return {
        "passed": passed,
        "status": "pass" if passed else "fail",
        "reason": "exact JSON match" if passed else "JSON value or schema did not match",
        "observed": actual,
    }


def _grade_tool_call_exact(expected: Mapping[str, Any], response: Any) -> dict[str, Any]:
    message = response_message(response)
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        return {
            "passed": False,
            "status": "fail",
            "reason": f"expected exactly one tool call, got {0 if not isinstance(calls, list) else len(calls)}",
            "observed": calls,
        }
    call = calls[0]
    function = call.get("function") if isinstance(call, Mapping) else None
    if not isinstance(function, Mapping):
        raise ValueError("tool call has no function object")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    actual = {"name": function.get("name"), "arguments": arguments}
    passed = actual == dict(expected)
    return {
        "passed": passed,
        "status": "pass" if passed else "fail",
        "reason": "exact tool call match" if passed else "tool name or arguments did not match",
        "observed": actual,
    }


DISALLOWED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "exit",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "open",
    "quit",
    "setattr",
    "vars",
}


def validate_generated_python(source: str, expected_function: str) -> ast.Module:
    """Reject imports/top-level execution and obvious escape hatches.

    This reduces accidents; it is intentionally not described as a sandbox.
    """

    tree = ast.parse(source, filename="model_answer.py")
    function_nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    permitted_top_level = (ast.FunctionDef,)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(
            node.value.value, str
        ):
            continue
        if not isinstance(node, permitted_top_level):
            raise ValueError(f"disallowed top-level statement: {type(node).__name__}")
    if len(function_nodes) != 1 or function_nodes[0].name != expected_function:
        raise ValueError(f"answer must define exactly one function named {expected_function}")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise ValueError(f"disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("dunder names are disallowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attributes are disallowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in DISALLOWED_CALLS:
                raise ValueError(f"disallowed call: {node.func.id}")
    return tree


CODE_TEST_SUFFIX = r'''

def _y_smoke_run_tests():
    cases = [
        ([], []),
        ([[1, 3]], [[1, 3]]),
        ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]),
        ([[1, 2], [2, 4], [9, 9]], [[1, 4], [9, 9]]),
        ([[5, 7], [1, 10], [12, 13]], [[1, 10], [12, 13]]),
    ]
    for original, expected in cases:
        snapshot = [item[:] for item in original]
        actual = merge_intervals(original)
        assert actual == expected, (original, expected, actual)
        assert original == snapshot, "input was mutated"
    print("Y_SMOKE_CODE_TEST_OK")

_y_smoke_run_tests()
'''


def _resource_limits() -> None:
    """Best-effort Unix limits for the disposable code-test subprocess."""

    limits = (
        (resource.RLIMIT_CORE, 0, 0),
        (resource.RLIMIT_CPU, 4, 4),
        (resource.RLIMIT_FSIZE, 1_048_576, 1_048_576),
        (resource.RLIMIT_NOFILE, 32, 32),
    )
    for kind, soft, hard in limits:
        try:
            resource.setrlimit(kind, (soft, hard))
        except (OSError, ValueError):
            pass


def execute_python_tests(source: str, timeout_seconds: float = 5.0) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="y-smoke-code-") as temp_dir:
        path = Path(temp_dir) / "answer.py"
        path.write_text(source + CODE_TEST_SUFFIX, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(path)],
                cwd=temp_dir,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"},
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                preexec_fn=_resource_limits if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "passed": False,
                "status": "fail",
                "reason": f"generated code exceeded {timeout_seconds:g}s timeout",
                "stdout": (exc.stdout or "")[-2_000:],
                "stderr": (exc.stderr or "")[-2_000:],
            }
    passed = completed.returncode == 0 and "Y_SMOKE_CODE_TEST_OK" in completed.stdout
    return {
        "passed": passed,
        "status": "pass" if passed else "fail",
        "reason": "all executable tests passed" if passed else "executable tests failed",
        "return_code": completed.returncode,
        "stdout": completed.stdout[-2_000:],
        "stderr": completed.stderr[-2_000:],
    }


def _grade_python_tests(
    expected_function: str,
    response: Any,
    *,
    allow_code_execution: bool,
    code_timeout_seconds: float,
) -> dict[str, Any]:
    source = strip_single_code_fence(extract_text_content(response))
    if not allow_code_execution:
        return {
            "passed": False,
            "status": "not_run",
            "reason": "code execution disabled; rerun with --allow-code-execution in a disposable environment",
            "observed": {"syntax_checked": False},
        }
    validate_generated_python(source, expected_function)
    result = execute_python_tests(source, code_timeout_seconds)
    result["observed"] = {"syntax_checked": True, "source_chars": len(source)}
    return result


def grade_response(
    case: SmokeCase,
    response: Any,
    *,
    allow_code_execution: bool = False,
    code_timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    """Grade a response without allowing parser errors to abort the suite."""

    normalized_response = normalize_assistant_response(response)
    graders: dict[str, Callable[[], dict[str, Any]]] = {
        "exact_text": lambda: _grade_exact_text(case.expected, normalized_response),
        "json_exact": lambda: _grade_json_exact(case.expected, normalized_response),
        "tool_call_exact": lambda: _grade_tool_call_exact(case.expected, normalized_response),
        "python_tests": lambda: _grade_python_tests(
            case.expected,
            normalized_response,
            allow_code_execution=allow_code_execution,
            code_timeout_seconds=code_timeout_seconds,
        ),
    }
    try:
        grader = graders.get(case.grader)
        if grader is None:
            raise ValueError(f"unknown grader: {case.grader}")
        return grader()
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, SyntaxError) as exc:
        return {
            "passed": False,
            "status": "fail",
            "reason": f"grader error: {type(exc).__name__}: {exc}",
            "observed": None,
        }


def normalize_usage(response: Any) -> dict[str, Any]:
    if not isinstance(response, Mapping) or not isinstance(response.get("usage"), Mapping):
        return {}
    usage = dict(response["usage"])
    normalized: dict[str, Any] = {
        key: usage[key]
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if key in usage
    }
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping) and "reasoning_tokens" in details:
        normalized["reasoning_tokens"] = details["reasoning_tokens"]
    normalized["raw"] = usage
    return normalized


def extract_server_metrics(response: Any) -> dict[str, Any]:
    """Normalize optional llama.cpp timing/speculative-decoding evidence."""

    if not isinstance(response, Mapping):
        return {}
    metrics: dict[str, Any] = {}
    timings = response.get("timings")
    if isinstance(timings, Mapping):
        metrics["timings"] = dict(timings)
        prompt_per_second = timings.get("prompt_per_second")
        predicted_per_second = timings.get("predicted_per_second")
        if isinstance(prompt_per_second, (int, float)):
            metrics["prompt_tokens_per_second"] = prompt_per_second
        if isinstance(predicted_per_second, (int, float)):
            metrics["generation_tokens_per_second"] = predicted_per_second
    for key in ("draft_n", "draft_n_accepted", "tokens_cached"):
        if isinstance(response.get(key), (int, float)):
            metrics[key] = response[key]
    draft_n = metrics.get("draft_n")
    draft_accepted = metrics.get("draft_n_accepted")
    if isinstance(draft_n, (int, float)) and draft_n > 0 and isinstance(
        draft_accepted, (int, float)
    ):
        metrics["draft_acceptance_rate"] = draft_accepted / draft_n
    return metrics


def _run_command(command: Sequence[str], cwd: Path | None = None) -> str | None:
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def collect_environment_metadata(
    repo_root: Path,
    *,
    endpoint: str,
    model: str,
    settings: Mapping[str, Any],
    custom: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect safe client/GPU metadata without dumping the process environment."""

    gpu_rows: list[dict[str, Any]] = []
    gpu_output = _run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,uuid,driver_version,memory.total",
            "--format=csv,noheader,nounits",
        ]
    )
    if gpu_output:
        for row in gpu_output.splitlines():
            fields = [part.strip() for part in row.split(",")]
            if len(fields) == 4:
                gpu_rows.append(
                    {
                        "name": fields[0],
                        "uuid": fields[1],
                        "driver_version": fields[2],
                        "memory_total_mib": _int_or_text(fields[3]),
                    }
                )
    commit = _run_command(["git", "rev-parse", "HEAD"], cwd=repo_root)
    dirty_output = _run_command(["git", "status", "--porcelain"], cwd=repo_root)
    metadata = {
        "captured_at": utc_now(),
        "suite_version": SUITE_VERSION,
        "client": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "repository": {"commit": commit, "dirty": bool(dirty_output) if dirty_output is not None else None},
        "gpu": gpu_rows,
        "api": {"endpoint": sanitize_url(endpoint), "model": model},
        "settings": dict(settings),
        "custom": dict(custom or {}),
    }
    return metadata


def _int_or_text(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def parse_metadata_pairs(pairs: Sequence[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"metadata must be KEY=VALUE: {pair!r}")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("metadata key cannot be empty")
        if SECRET_KEY_PATTERN.search(key):
            raise ValueError(f"refusing secret-looking metadata key: {key!r}")
        metadata[key] = value.strip()
    return metadata


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _markdown_cell(value: Any) -> str:
    text = "—" if value in (None, "") else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown_summary(
    *,
    run_id: str,
    metadata: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    jsonl_name: str,
) -> str:
    passed = sum(1 for result in results if result.get("passed") is True)
    not_run = sum(1 for result in results if result.get("status") == "not_run")
    failed = len(results) - passed - not_run
    latencies = [
        float(result["latency_ms"])
        for result in results
        if isinstance(result.get("latency_ms"), (int, float))
    ]
    total_prompt = sum(
        int(result.get("usage", {}).get("prompt_tokens", 0) or 0) for result in results
    )
    total_completion = sum(
        int(result.get("usage", {}).get("completion_tokens", 0) or 0) for result in results
    )
    api = metadata.get("api", {}) if isinstance(metadata.get("api"), Mapping) else {}
    settings = metadata.get("settings", {}) if isinstance(metadata.get("settings"), Mapping) else {}
    lines = [
        f"# OpenAI-compatible smoke report — `{run_id}`",
        "",
        "> This is a six-case integration smoke suite, not a standardized model-quality benchmark. "
        "Passing shows that basic prompting, output schemas and one tiny code task worked on this "
        "endpoint. It does not establish frontier quality or comparability with published benchmark scores.",
        "",
        "## Outcome",
        "",
        f"- Passed: **{passed}/{len(results)}**",
        f"- Failed: **{failed}**",
        f"- Not run: **{not_run}**",
        f"- Median end-to-end latency: **{statistics.median(latencies):.1f} ms**" if latencies else "- Median end-to-end latency: **unavailable**",
        f"- Reported usage: **{total_prompt} input / {total_completion} output tokens**",
        "",
        "## Configuration",
        "",
        f"- Model: `{_markdown_cell(api.get('model'))}`",
        f"- Endpoint: `{_markdown_cell(api.get('endpoint'))}`",
        f"- Suite: `{_markdown_cell(metadata.get('suite_version'))}`",
        f"- Temperature / top-p: `{_markdown_cell(settings.get('temperature'))}` / `{_markdown_cell(settings.get('top_p'))}`",
        f"- Seed: `{_markdown_cell(settings.get('seed'))}`",
        f"- Reasoning mode: `{_markdown_cell(settings.get('reasoning_mode'))}`",
        f"- Raw evidence: [`{jsonl_name}`]({jsonl_name})",
        "",
        "## Cases",
        "",
        "| Case | Category | Result | Latency | Input / output tokens | Server decode | Draft accepted | Detail |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        usage = result.get("usage", {})
        token_text = f"{usage.get('prompt_tokens', '—')} / {usage.get('completion_tokens', '—')}"
        latency = result.get("latency_ms")
        latency_text = f"{float(latency):.1f} ms" if isinstance(latency, (int, float)) else "—"
        server_metrics = result.get("server_metrics", {})
        decode_rate = server_metrics.get("generation_tokens_per_second")
        decode_text = f"{float(decode_rate):.2f} tok/s" if isinstance(decode_rate, (int, float)) else "—"
        draft_n = server_metrics.get("draft_n")
        draft_accepted = server_metrics.get("draft_n_accepted")
        draft_text = (
            f"{draft_accepted}/{draft_n}"
            if isinstance(draft_n, (int, float)) and isinstance(draft_accepted, (int, float))
            else "—"
        )
        lines.append(
            "| {case} | {category} | {status} | {latency} | {tokens} | {decode} | {draft} | {detail} |".format(
                case=_markdown_cell(result.get("case_id")),
                category=_markdown_cell(result.get("category")),
                status=_markdown_cell(str(result.get("status", "unknown")).upper()),
                latency=_markdown_cell(latency_text),
                tokens=_markdown_cell(token_text),
                decode=_markdown_cell(decode_text),
                draft=_markdown_cell(draft_text),
                detail=_markdown_cell(result.get("grade", {}).get("reason")),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Use this report to catch endpoint, chat-template, parser, tool-calling and gross runtime "
            "regressions. For a public performance claim, run a named standardized benchmark and the "
            "Y benchmark-policy measurements (warm/cold repetitions, TTFT, TPOT, throughput, memory, "
            "errors, power and thermals) on pinned hardware and artifacts.",
            "",
        ]
    )
    return "\n".join(lines)
