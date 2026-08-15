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


if __name__ == "__main__":
    unittest.main()
