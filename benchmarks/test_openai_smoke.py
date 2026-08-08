"""Offline unit tests for smoke-suite parsers and graders."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from openai_smoke_lib import (  # noqa: E402
    SmokeCase,
    build_request_body,
    build_smoke_cases,
    extract_text_content,
    extract_server_metrics,
    grade_response,
    normalize_chat_completions_url,
    normalize_assistant_response,
    parse_json_text,
    parse_metadata_pairs,
    sanitize_for_log,
    sanitize_url,
    strip_leading_think_artifacts,
    strip_single_code_fence,
    validate_generated_python,
)


def text_response(text: str) -> dict:
    return {
        "id": "test",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    }


class ParserTests(unittest.TestCase):
    def test_normalize_base_urls(self) -> None:
        self.assertEqual(
            normalize_chat_completions_url("http://127.0.0.1:8000"),
            "http://127.0.0.1:8000/v1/chat/completions",
        )
        self.assertEqual(
            normalize_chat_completions_url("https://example.test/v1/"),
            "https://example.test/v1/chat/completions",
        )
        exact = "https://example.test/openai/v1/chat/completions"
        self.assertEqual(normalize_chat_completions_url(exact), exact)

    def test_url_and_nested_secret_redaction(self) -> None:
        secret = "rpa_this_is_a_test_key"
        url = f"https://user:{secret}@example.test/v1?token={secret}&mode=test"
        safe_url = sanitize_url(url)
        self.assertNotIn(secret, safe_url)
        self.assertIn("mode=test", safe_url)
        clean = sanitize_for_log(
            {
                "authorization": f"Bearer {secret}",
                "prompt_tokens": 12,
                "nested": [f"failure echoed {secret}", {"value": "safe"}],
            },
            (secret,),
        )
        self.assertEqual(clean["authorization"], "[REDACTED]")
        self.assertEqual(clean["prompt_tokens"], 12)
        self.assertNotIn(secret, json.dumps(clean))

    def test_timing_metric_allowlist_does_not_weaken_token_redaction(self) -> None:
        clean = sanitize_for_log(
            {
                "timings": {
                    "prompt_per_token_ms": 1.25,
                    "predicted_per_token_ms": 42.5,
                },
                "token": "plain-secret",
                "auth_token": "auth-secret",
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
                "prompt_per_token_ms": "not-a-number",
            }
        )
        self.assertEqual(clean["timings"]["prompt_per_token_ms"], 1.25)
        self.assertEqual(clean["timings"]["predicted_per_token_ms"], 42.5)
        self.assertEqual(clean["token"], "[REDACTED]")
        self.assertEqual(clean["auth_token"], "[REDACTED]")
        self.assertEqual(clean["access_token"], "[REDACTED]")
        self.assertEqual(clean["refresh_token"], "[REDACTED]")
        self.assertEqual(clean["prompt_per_token_ms"], "[REDACTED]")

    def test_content_parts_and_fences(self) -> None:
        response = {
            "choices": [
                {
                    "message": {
                        "content": [
                            {"type": "text", "text": "hello "},
                            {"type": "text", "text": "world"},
                        ]
                    }
                }
            ]
        }
        self.assertEqual(extract_text_content(response), "hello world")
        self.assertEqual(strip_single_code_fence("```python\nx = 1\n```"), "x = 1")
        self.assertEqual(parse_json_text('```json\n{"ok": true}\n```'), {"ok": True})

    def test_metadata_rejects_secret_looking_keys(self) -> None:
        self.assertEqual(parse_metadata_pairs(["provider=runpod", "gpu=B200"]), {"provider": "runpod", "gpu": "B200"})
        with self.assertRaises(ValueError):
            parse_metadata_pairs(["api_key=nope"])

    def test_extracts_llama_server_metrics(self) -> None:
        metrics = extract_server_metrics(
            {
                "timings": {"prompt_per_second": 123.4, "predicted_per_second": 17.5},
                "draft_n": 20,
                "draft_n_accepted": 15,
            }
        )
        self.assertEqual(metrics["generation_tokens_per_second"], 17.5)
        self.assertEqual(metrics["draft_acceptance_rate"], 0.75)

    def test_strips_only_leading_think_closers(self) -> None:
        self.assertEqual(
            strip_leading_think_artifacts(" \n </think>\t</think> \n 716"),
            "716",
        )
        embedded = "The literal </think> tag stays here."
        self.assertEqual(strip_leading_think_artifacts(embedded), embedded)
        later = "<think>private work</think>\n716"
        self.assertEqual(strip_leading_think_artifacts(later), later)

    def test_response_normalizer_preserves_raw_and_reasoning_content(self) -> None:
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "\n</think>  answer with </think> later",
                        "reasoning_content": "reasoning </think> remains exact",
                    }
                }
            ]
        }
        normalized = normalize_assistant_response(response)
        message = normalized["choices"][0]["message"]
        self.assertEqual(message["content"], "answer with </think> later")
        self.assertEqual(message["reasoning_content"], "reasoning </think> remains exact")
        self.assertEqual(response["choices"][0]["message"]["content"], "\n</think>  answer with </think> later")


class GraderTests(unittest.TestCase):
    def test_exact_and_json_graders(self) -> None:
        exact = SmokeCase("exact", "test", "", [], "exact_text", "716")
        self.assertTrue(grade_response(exact, text_response("716\n"))["passed"])
        self.assertFalse(grade_response(exact, text_response("The answer is 716"))["passed"])
        self.assertTrue(grade_response(exact, text_response(" \n</think>\n716"))["passed"])

        structured = SmokeCase(
            "json", "test", "", [], "json_exact", {"ok": True, "count": 3}
        )
        self.assertTrue(
            grade_response(structured, text_response('{"ok":true,"count":3}'))["passed"]
        )
        malformed = grade_response(structured, text_response("not json"))
        self.assertFalse(malformed["passed"])
        self.assertIn("grader error", malformed["reason"])

    def test_tool_call_grader(self) -> None:
        case = SmokeCase(
            "tool",
            "test",
            "",
            [],
            "tool_call_exact",
            {"name": "lookup", "arguments": {"item": "Y"}},
        )
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "lookup",
                                    "arguments": '{"item":"Y"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        self.assertTrue(grade_response(case, response)["passed"])

    def test_generated_code_passes_and_failures_are_detected(self) -> None:
        case = SmokeCase("code", "test", "", [], "python_tests", "merge_intervals")
        passing = text_response(
            """```python
def merge_intervals(intervals):
    result = []
    for start, end in sorted([item[:] for item in intervals]):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result
```"""
        )
        result = grade_response(case, passing, allow_code_execution=True)
        self.assertTrue(result["passed"], result)

        failing = text_response("```python\ndef merge_intervals(intervals):\n    return []\n```")
        self.assertFalse(grade_response(case, failing, allow_code_execution=True)["passed"])
        not_run = grade_response(case, passing, allow_code_execution=False)
        self.assertEqual(not_run["status"], "not_run")

    def test_generated_code_rejects_imports_and_dynamic_execution(self) -> None:
        with self.assertRaises(ValueError):
            validate_generated_python("import os\ndef merge_intervals(x): return x", "merge_intervals")
        with self.assertRaises(ValueError):
            validate_generated_python(
                "def merge_intervals(x): return eval('x')", "merge_intervals"
            )

    def test_request_reasoning_modes_and_suite_shape(self) -> None:
        cases = build_smoke_cases(4_096)
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({case.case_id for case in cases}), 6)
        body = build_request_body(
            cases[0],
            model="model",
            temperature=1,
            top_p=0.95,
            seed=0,
            reasoning_mode="off",
        )
        self.assertEqual(body["seed"], 0)
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        body = build_request_body(
            cases[0],
            model="model",
            temperature=1,
            top_p=0.95,
            seed=None,
            reasoning_mode="high",
        )
        self.assertEqual(body["reasoning_effort"], "high")

    def test_adaptive_reasoning_routes_by_fixed_case_category(self) -> None:
        cases = build_smoke_cases(4_096)
        expected = {
            "exact-arithmetic": True,
            "code-executable": False,
            "structured-json": False,
            "tool-call-schema": False,
            "instruction-following": False,
            "long-context-needle": False,
        }
        self.assertEqual({case.case_id for case in cases}, set(expected))
        for case in cases:
            with self.subTest(case_id=case.case_id, category=case.category):
                body = build_request_body(
                    case,
                    model="model",
                    temperature=1,
                    top_p=0.95,
                    seed=0,
                    reasoning_mode="adaptive",
                )
                self.assertEqual(
                    body["chat_template_kwargs"],
                    {"enable_thinking": expected[case.case_id]},
                )


if __name__ == "__main__":
    unittest.main()
