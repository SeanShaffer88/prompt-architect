import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from prompt_architect import cli, record

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "specs" / "classification-routing.json"
SUITE = REPO_ROOT / "benchmarks" / "suites" / "classification-routing.json"


class FakeModel(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible chat-completions endpoint."""

    responses: list = []
    status = 200
    seen_requests: list = []

    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        FakeModel.seen_requests.append(
            {"auth": self.headers.get("Authorization"), "body": body, "path": self.path}
        )
        if FakeModel.status != 200:
            self.send_response(FakeModel.status)
            self.end_headers()
            self.wfile.write(b'{"error": "boom"}')
            return
        content = FakeModel.responses.pop(0) if FakeModel.responses else "{}"
        payload = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence the test server
        pass


class FakeServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}/v1"
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


def good_response(label="billing", confidence="high", evidence="charged twice for October"):
    return json.dumps({"label": label, "confidence": confidence, "evidence": evidence})


# One correct response per suite case, in T1..T6 order. Used to prove that a
# captured run can be graded end-to-end.
SUITE_RESPONSES = [
    good_response("billing", "high", "charged twice for October"),
    good_response("unclear", "low", ""),
    good_response("unclear", "low", "asdkjhqwe zxcv"),
    good_response("billing", "high", "charged twice for October"),
    good_response("unclear", "low", "can't get into my account"),
    good_response("bug", "high", "export button does nothing"),
]


class RecordTests(unittest.TestCase):
    def setUp(self):
        FakeModel.responses = []
        FakeModel.seen_requests = []
        FakeModel.status = 200

    def test_captures_one_output_per_case(self):
        with FakeServer() as server, TemporaryDirectory() as tmp:
            FakeModel.responses = [good_response() for _ in range(6)]
            out = Path(tmp) / "run.json"
            result = record.record(
                spec_path=SPEC, suite_path=SUITE, variant="v3", model="test-model-2026-11-08",
                base_url=server.base_url, api_key="dummy-key", out_path=out,
            )
            run = json.loads(out.read_text())

        self.assertEqual(result.cases, 6)
        self.assertEqual(run["suite"], "classification-routing")
        self.assertEqual(run["variant"], "v3")
        self.assertEqual(run["model"], "test-model-2026-11-08")
        self.assertEqual(run["provenance"]["kind"], "captured")
        self.assertEqual(len(run["outputs"]), 6)
        self.assertEqual(set(run["outputs"]), {"T1", "T2", "T3", "T4", "T5", "T6"})

    def test_sends_prompt_as_system_and_case_as_user(self):
        with FakeServer() as server, TemporaryDirectory() as tmp:
            FakeModel.responses = [good_response() for _ in range(6)]
            record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                          base_url=server.base_url, api_key="dummy-key",
                          out_path=Path(tmp) / "run.json")

        first = FakeModel.seen_requests[0]
        self.assertTrue(first["path"].endswith("/v1/chat/completions"))
        self.assertEqual(first["auth"], "Bearer dummy-key")
        self.assertEqual(first["body"]["messages"][0]["role"], "system")
        self.assertIn("### Role", first["body"]["messages"][0]["content"])
        self.assertIn("### Fallback Protocol", first["body"]["messages"][0]["content"])
        self.assertEqual(first["body"]["messages"][1]["role"], "user")
        self.assertEqual(first["body"]["temperature"], 0.0)

    def test_api_key_is_never_written_to_the_run_file(self):
        with FakeServer() as server, TemporaryDirectory() as tmp:
            FakeModel.responses = [good_response() for _ in range(6)]
            out = Path(tmp) / "run.json"
            record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                          base_url=server.base_url, api_key="super-secret-key",
                          out_path=out)
            text = out.read_text()
        self.assertNotIn("super-secret-key", text)

    def test_http_error_raises_and_writes_nothing(self):
        with FakeServer() as server, TemporaryDirectory() as tmp:
            FakeModel.status = 500
            out = Path(tmp) / "run.json"
            with self.assertRaises(record.RecordError):
                record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                              base_url=server.base_url, api_key="dummy", out_path=out)
            self.assertFalse(out.exists())

    def test_unreachable_endpoint_raises(self):
        with TemporaryDirectory() as tmp, self.assertRaises(record.RecordError):
            record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                          base_url="http://127.0.0.1:9/v1", api_key="dummy",
                          out_path=Path(tmp) / "run.json", timeout=2)

    def test_missing_key_is_an_error(self):
        with self.assertRaises(record.RecordError):
            record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                          api_key=None, out_path="/tmp/never.json")

    def test_captured_run_can_be_graded(self):
        with FakeServer() as server, TemporaryDirectory() as tmp:
            FakeModel.responses = list(SUITE_RESPONSES)
            out = Path(tmp) / "run.json"
            record.record(spec_path=SPEC, suite_path=SUITE, variant="v3", model="test",
                          base_url=server.base_url, api_key="dummy", out_path=out)
            code, output = run_cli("eval", str(SUITE), "--run", str(out), "--expect-pass")
        self.assertEqual(code, 0, output)


def run_cli(*args):
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        code = cli.main(list(args))
    return code, buffer.getvalue()


class RecordCliTests(unittest.TestCase):
    def test_dry_run_needs_no_key(self):
        code, output = run_cli("record", "--spec", str(SPEC), "--suite", str(SUITE),
                               "--model", "test", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("### Role", output)

    def test_missing_key_exits_2(self):
        import os
        os.environ.pop("OPENAI_API_KEY", None)
        code, _ = run_cli("record", "--spec", str(SPEC), "--suite", str(SUITE),
                          "--model", "test", "--api-key-env", "DEFINITELY_NOT_SET")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
