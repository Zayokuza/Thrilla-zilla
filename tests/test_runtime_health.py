import importlib
import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer


class _ModelsHandler(BaseHTTPRequestHandler):
    payload = {
        "data": [
            {
                "id": "thrilla-test-model",
            }
        ]
    }
    status = 200

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return

        body = json.dumps(
            self.payload
        ).encode("utf-8")

        self.send_response(
            self.status
        )
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@contextmanager
def _http_server(payload, status=200):
    handler = type(
        "ConfiguredModelsHandler",
        (_ModelsHandler,),
        {
            "payload": payload,
            "status": status,
        },
    )

    server = HTTPServer(
        (
            "127.0.0.1",
            0,
        ),
        handler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
    )
    thread.start()

    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


class _SequenceModelsHandler(BaseHTTPRequestHandler):
    payloads = ()
    request_count = 0

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_response(404)
            self.end_headers()
            return

        index = min(
            type(self).request_count,
            len(type(self).payloads) - 1,
        )

        payload = type(self).payloads[index]
        type(self).request_count += 1

        body = json.dumps(
            payload
        ).encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@contextmanager
def _sequence_http_server(payloads):
    handler = type(
        "ConfiguredSequenceModelsHandler",
        (_SequenceModelsHandler,),
        {
            "payloads": tuple(payloads),
            "request_count": 0,
        },
    )

    server = HTTPServer(
        (
            "127.0.0.1",
            0,
        ),
        handler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
    )
    thread.start()

    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


class RuntimeHealthTests(unittest.TestCase):

    def test_probe_models_endpoint_reads_model_ids(self):
        try:
            health = importlib.import_module(
                "thrilla.runtime.health"
            )
        except Exception as error:
            self.fail(
                "runtime health module must exist: {0}".format(
                    error
                )
            )

        probe_type = getattr(
            health,
            "ModelsEndpointProbe",
            None,
        )
        probe = getattr(
            health,
            "probe_models_endpoint",
            None,
        )

        self.assertTrue(
            callable(probe_type),
            "ModelsEndpointProbe must exist",
        )
        self.assertTrue(
            callable(probe),
            "probe_models_endpoint must exist",
        )

        payload = {
            "object": "list",
            "data": [
                {
                    "id": "model-a",
                },
                {
                    "id": "model-b",
                },
            ],
        }

        with _http_server(payload) as server:
            port = server.server_address[1]

            result = probe(
                "127.0.0.1",
                port,
                timeout=0.5,
            )

        self.assertIsInstance(
            result,
            probe_type,
        )
        self.assertTrue(
            result.reachable,
        )
        self.assertTrue(
            result.openai_compatible,
        )
        self.assertEqual(
            (
                "model-a",
                "model-b",
            ),
            result.models,
        )

    def test_probe_models_endpoint_rejects_wrong_json_shape(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        with _http_server(
            {
                "hello": "world",
            }
        ) as server:
            result = health.probe_models_endpoint(
                "127.0.0.1",
                server.server_address[1],
                timeout=0.5,
            )

        self.assertTrue(
            result.reachable,
        )

        self.assertFalse(
            result.openai_compatible,
            "wrong JSON shape must not be OpenAI compatible",
        )

    def test_probe_models_endpoint_checks_expected_model(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        payload = {
            "data": [
                {
                    "id": "loaded-model",
                }
            ]
        }

        with _http_server(payload) as server:
            port = server.server_address[1]

            match = health.probe_models_endpoint(
                "127.0.0.1",
                port,
                timeout=0.5,
                expected_model="loaded-model",
            )

            mismatch = health.probe_models_endpoint(
                "127.0.0.1",
                port,
                timeout=0.5,
                expected_model="different-model",
            )

        self.assertEqual(
            "loaded-model",
            match.expected_model,
        )
        self.assertTrue(
            match.model_match,
        )

        self.assertEqual(
            "different-model",
            mismatch.expected_model,
        )
        self.assertFalse(
            mismatch.model_match,
        )

    def test_inspect_existing_server_marks_compatible_listener_reusable(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        inspector = getattr(
            health,
            "inspect_existing_server",
            None,
        )

        inspection_type = getattr(
            health,
            "ExistingServerInspection",
            None,
        )

        self.assertTrue(
            callable(inspector),
            "inspect_existing_server must exist",
        )
        self.assertTrue(
            callable(inspection_type),
            "ExistingServerInspection must exist",
        )

        payload = {
            "object": "list",
            "data": [
                {
                    "id": "thrilla-primary",
                }
            ],
        }

        with _http_server(payload) as server:
            port = server.server_address[1]

            result = inspector(
                "127.0.0.1",
                port,
                timeout=0.5,
                expected_model="thrilla-primary",
            )

        self.assertIsInstance(
            result,
            inspection_type,
        )
        self.assertTrue(
            result.listening,
        )
        self.assertFalse(
            result.bindable,
        )
        self.assertTrue(
            result.openai_compatible,
        )
        self.assertTrue(
            result.model_match,
        )
        self.assertTrue(
            result.reusable,
        )
        self.assertEqual(
            (
                "thrilla-primary",
            ),
            result.models,
        )

    def test_wait_for_model_readiness_accepts_expected_model(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        waiter = getattr(
            health,
            "wait_for_model_readiness",
            None,
        )

        result_type = getattr(
            health,
            "ReadinessResult",
            None,
        )

        self.assertTrue(
            callable(waiter),
            "wait_for_model_readiness must exist",
        )

        self.assertTrue(
            callable(result_type),
            "ReadinessResult must exist",
        )

        payload = {
            "object": "list",
            "data": [
                {
                    "id": "thrilla-ready-model",
                }
            ],
        }

        with _http_server(payload) as server:
            result = waiter(
                host="127.0.0.1",
                port=server.server_address[1],
                expected_model="thrilla-ready-model",
                startup_timeout=0.5,
                probe_timeout=0.2,
                poll_interval=0.01,
            )

        self.assertIsInstance(
            result,
            result_type,
        )

        self.assertTrue(
            result.ready,
        )

        self.assertEqual(
            (
                "thrilla-ready-model",
            ),
            result.models,
        )

        self.assertEqual(
            1,
            result.attempts,
        )

    def test_wait_for_model_readiness_polls_until_model_appears(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        payloads = (
            {
                "object": "list",
                "data": [],
            },
            {
                "object": "list",
                "data": [
                    {
                        "id": "delayed-model",
                    }
                ],
            },
        )

        with _sequence_http_server(payloads) as server:
            result = health.wait_for_model_readiness(
                host="127.0.0.1",
                port=server.server_address[1],
                expected_model="delayed-model",
                startup_timeout=0.5,
                probe_timeout=0.2,
                poll_interval=0.01,
            )

        self.assertTrue(
            result.ready,
            "readiness must poll until expected model appears",
        )

        self.assertGreaterEqual(
            result.attempts,
            2,
        )

        self.assertIn(
            "delayed-model",
            result.models,
        )

    def test_wait_for_model_readiness_reports_timeout(self):
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        payload = {
            "object": "list",
            "data": [
                {
                    "id": "wrong-model",
                }
            ],
        }

        with _http_server(payload) as server:
            result = health.wait_for_model_readiness(
                host="127.0.0.1",
                port=server.server_address[1],
                expected_model="expected-model",
                startup_timeout=0.05,
                probe_timeout=0.02,
                poll_interval=0.01,
            )

        self.assertFalse(
            result.ready,
        )

        self.assertTrue(
            result.timed_out,
            "readiness timeout must be reported",
        )

        self.assertGreaterEqual(
            result.attempts,
            1,
        )

        self.assertEqual(
            (
                "wrong-model",
            ),
            result.models,
        )


if __name__ == "__main__":
    unittest.main()
