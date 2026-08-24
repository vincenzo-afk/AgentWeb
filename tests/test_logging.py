from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentweb.api import create_server
from agentweb.structured_logging import StructuredLogger


class StructuredLoggerTests(unittest.TestCase):
    def test_emit_writes_correlated_redacted_json_record(self) -> None:
        stream = io.StringIO()
        logger = StructuredLogger(stream=stream, clock=lambda: 1_700_000_000)
        record = logger.emit(
            "warn",
            "api",
            "request token=secret-value",
            request_id="req_123",
            extra={
                "method": "GET",
                "target": "https://example.com/path?api_key=private-value",
                "body": "full page body must not survive",
                "status_code": 401,
            },
        )
        parsed = json.loads(stream.getvalue())
        self.assertEqual(parsed, record)
        self.assertEqual(parsed["level"], "warn")
        self.assertEqual(parsed["component"], "api")
        self.assertEqual(parsed["request_id"], "req_123")
        self.assertEqual(parsed["timestamp"], "2023-11-14T22:13:20Z")
        serialized = stream.getvalue()
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("private-value", serialized)
        self.assertNotIn("full page body", serialized)

    def test_invalid_level_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            StructuredLogger(stream=io.StringIO()).emit("trace", "test", "message")
        with self.assertRaises(ValueError):
            StructuredLogger(stream=io.StringIO(), min_level="trace")

    def test_min_level_filters_lower_severity_records(self) -> None:
        stream = io.StringIO()
        logger = StructuredLogger(stream=stream, min_level="warn")
        logger.info("test", "hidden")
        logger.warn("test", "visible")
        lines = stream.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["level"], "warn")

    def test_api_request_logs_request_id_and_redacts_query_secret(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        os.environ["LOG_LEVEL"] = "warn"
        server = create_server("127.0.0.1", 0, str(Path(temp_dir.name) / "logging.sqlite3"))
        stream = io.StringIO()
        server.logger = StructuredLogger(stream=stream, min_level="warn")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = Request(f"http://127.0.0.1:{server.server_port}/v1/health?api_key=private-value")
            with urlopen(request, timeout=3) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(stream.getvalue(), "")
            delete_request = Request(
                f"http://127.0.0.1:{server.server_port}/v1/observe/nonexistent",
                method="DELETE",
            )
            with self.assertRaises(HTTPError) as error:
                urlopen(delete_request, timeout=3)
            self.assertEqual(error.exception.code, 404)
            records = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(records), 1)
            delete_record = records[0]
            self.assertTrue(delete_record["request_id"].startswith("req_"))
            self.assertEqual(delete_record["details"]["status_code"], 404)
            self.assertEqual(delete_record["level"], "warn")
            self.assertNotIn("private-value", stream.getvalue())
        finally:
            os.environ.pop("LOG_LEVEL", None)
            os.environ.pop("AGENTWEB_QUIET", None)
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
