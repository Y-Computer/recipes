"""Offline tests for the fixed-generation performance runner."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_fixed_generation as runner  # noqa: E402


def successful_exchange(*, tokens: int = 4, latency_ms: float = 12.5) -> SimpleNamespace:
    return SimpleNamespace(
        status_code=200,
        response_headers={"content-type": "application/json"},
        response={
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": "1. test"}}
            ],
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": tokens,
                "total_tokens": 7 + tokens,
            },
            "timings": {
                "prompt_n": 7,
                "prompt_ms": 3.5,
                "prompt_per_second": 2_000.0,
                "predicted_n": tokens,
                "predicted_ms": 8.0,
                "predicted_per_second": 500.0,
                "draft_n": 6,
                "draft_n_accepted": 3,
            },
        },
        raw_response=None,
        error=None,
        latency_ms=latency_ms,
    )


class FakeClient:
    exchanges: list[SimpleNamespace] = []
    bodies: list[dict] = []

    def __init__(self, base_url: str, api_key: str | None, timeout_seconds: float):
        self.endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def complete(self, body: dict) -> SimpleNamespace:
        self.bodies.append(dict(body))
        return self.exchanges.pop(0)


class RequestTests(unittest.TestCase):
    def test_request_is_fixed_length_non_streaming_and_deterministic(self) -> None:
        body = runner.build_request_body(
            model="deepseek",
            system_prompt="system",
            user_prompt="user",
            max_tokens=256,
            temperature=0,
            seed=42,
            ignore_eos=True,
            reasoning_mode="off",
        )
        self.assertEqual(body["model"], "deepseek")
        self.assertEqual(body["max_tokens"], 256)
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["seed"], 42)
        self.assertIs(body["ignore_eos"], True)
        self.assertIs(body["stream"], False)
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual([message["role"] for message in body["messages"]], ["system", "user"])

    def test_auto_reasoning_and_missing_seed_are_omitted(self) -> None:
        body = runner.build_request_body(
            model="model",
            system_prompt="system",
            user_prompt="user",
            max_tokens=8,
            temperature=0,
            seed=None,
            ignore_eos=False,
            reasoning_mode="auto",
        )
        self.assertNotIn("seed", body)
        self.assertNotIn("chat_template_kwargs", body)
        self.assertIs(body["ignore_eos"], False)


class MetricsTests(unittest.TestCase):
    def test_llama_timings_and_draft_acceptance_are_retained(self) -> None:
        response = successful_exchange().response
        metrics = runner.extract_llama_metrics(response)
        self.assertEqual(metrics["timings"]["predicted_n"], 4)
        self.assertEqual(metrics["prompt_tokens_per_second"], 2_000.0)
        self.assertEqual(metrics["generation_tokens_per_second"], 500.0)
        self.assertEqual(metrics["draft_n"], 6)
        self.assertEqual(metrics["draft_n_accepted"], 3)
        self.assertEqual(metrics["draft_acceptance_rate"], 0.5)
        self.assertEqual(runner.observed_completion_tokens(response), 4)

    def test_completion_count_falls_back_to_llama_timings(self) -> None:
        self.assertEqual(
            runner.observed_completion_tokens({"timings": {"predicted_n": 12}}),
            12,
        )
        top_level = runner.extract_llama_metrics(
            {"draft_n": 8, "draft_n_accepted": 2}
        )
        self.assertEqual(top_level["draft_acceptance_rate"], 0.25)
        self.assertIsNone(runner.observed_completion_tokens({"choices": []}))


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeClient.exchanges = []
        FakeClient.bodies = []

    @staticmethod
    def _metadata(*args: object, **kwargs: object) -> dict:
        return {"api": {}, "settings": kwargs.get("settings", {}), "custom": {}}

    def test_main_writes_warmup_measurements_and_summary(self) -> None:
        FakeClient.exchanges = [
            successful_exchange(latency_ms=10),
            successful_exchange(latency_ms=11),
            successful_exchange(latency_ms=13),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "fixed.jsonl"
            with (
                mock.patch.object(runner, "OpenAICompatibleClient", FakeClient),
                mock.patch.object(runner, "collect_environment_metadata", self._metadata),
            ):
                result = runner.main(
                    [
                        "--base-url",
                        "http://127.0.0.1:8080",
                        "--model",
                        "deepseek",
                        "--output",
                        str(output),
                        "--runs",
                        "2",
                        "--max-tokens",
                        "4",
                    ]
                )

            self.assertEqual(result, 0)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(
                [record["record_type"] for record in records],
                ["run_start", "warmup", "measurement", "measurement", "run_end"],
            )
            exchanges = records[1:-1]
            self.assertEqual([record["run"] for record in exchanges], [0, 1, 2])
            for record in exchanges:
                self.assertIsNone(record["error"])
                self.assertEqual(record["request"]["body"]["max_tokens"], 4)
                self.assertIs(record["request"]["body"]["stream"], False)
                self.assertIs(record["completion_tokens_exact"], True)
                self.assertEqual(
                    record["server_metrics"]["generation_tokens_per_second"], 500.0
                )
            self.assertEqual(records[-1]["summary"]["successful"], 2)
            self.assertEqual(records[-1]["summary"]["exact_completion_count"], 2)
            self.assertEqual(records[-1]["summary"]["draft"]["accepted_total"], 6)
            self.assertEqual(len(FakeClient.bodies), 3)
            self.assertTrue(all(body == FakeClient.bodies[0] for body in FakeClient.bodies))

    def test_measurement_error_is_persisted_and_returns_nonzero(self) -> None:
        failure = SimpleNamespace(
            status_code=503,
            response_headers={"content-type": "application/json"},
            response={"error": {"message": "busy"}},
            raw_response=None,
            error="HTTP 503: Service Unavailable",
            latency_ms=3.0,
        )
        FakeClient.exchanges = [successful_exchange(), failure]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "failure.jsonl"
            with (
                mock.patch.object(runner, "OpenAICompatibleClient", FakeClient),
                mock.patch.object(runner, "collect_environment_metadata", self._metadata),
            ):
                result = runner.main(
                    [
                        "--base-url",
                        "http://127.0.0.1:8080/v1",
                        "--model",
                        "deepseek",
                        "--output",
                        str(output),
                        "--runs",
                        "1",
                        "--max-tokens",
                        "4",
                    ]
                )

            self.assertEqual(result, 1)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            measurement = records[2]
            self.assertEqual(measurement["status"], "request_error")
            self.assertEqual(measurement["error"], "HTTP 503: Service Unavailable")
            self.assertEqual(measurement["response"], {"error": {"message": "busy"}})
            self.assertEqual(records[-1]["summary"]["failed"], 1)

    def test_short_completion_fails_only_when_ignore_eos_is_enabled(self) -> None:
        for extra_args, expected in (([], 1), (["--no-ignore-eos"], 0)):
            with self.subTest(extra_args=extra_args):
                FakeClient.exchanges = [
                    successful_exchange(tokens=3),
                    successful_exchange(tokens=3),
                ]
                FakeClient.bodies = []
                with tempfile.TemporaryDirectory() as temp_dir:
                    output = Path(temp_dir) / "short.jsonl"
                    with (
                        mock.patch.object(runner, "OpenAICompatibleClient", FakeClient),
                        mock.patch.object(
                            runner, "collect_environment_metadata", self._metadata
                        ),
                    ):
                        result = runner.main(
                            [
                                "--base-url",
                                "http://127.0.0.1:8080",
                                "--model",
                                "deepseek",
                                "--output",
                                str(output),
                                "--runs",
                                "1",
                                "--max-tokens",
                                "4",
                                *extra_args,
                            ]
                        )
                    self.assertEqual(result, expected)

    def test_unknown_completion_count_fails_exact_length_run(self) -> None:
        unknown = successful_exchange()
        unknown.response.pop("usage")
        unknown.response.pop("timings")
        FakeClient.exchanges = [successful_exchange(), unknown]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "unknown.jsonl"
            with (
                mock.patch.object(runner, "OpenAICompatibleClient", FakeClient),
                mock.patch.object(runner, "collect_environment_metadata", self._metadata),
            ):
                result = runner.main(
                    [
                        "--base-url",
                        "http://127.0.0.1:8080",
                        "--model",
                        "deepseek",
                        "--output",
                        str(output),
                        "--runs",
                        "1",
                        "--max-tokens",
                        "4",
                    ]
                )
            self.assertEqual(result, 1)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(records[2]["status"], "completion_count_unavailable")
            self.assertIsNone(records[2]["completion_tokens_exact"])


if __name__ == "__main__":
    unittest.main()
