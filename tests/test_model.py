import json
import unittest
from unittest.mock import patch

from thrilla.model import LocalModelClient, ModelError


class ModelTests(unittest.TestCase):
    def test_remote_endpoint_requires_explicit_opt_in(self):
        client = LocalModelClient("https://example.com/v1/chat/completions", "test")
        status = client.health()
        self.assertFalse(status.online)
        self.assertIn("blocked", status.detail.lower())
        with self.assertRaises(ModelError):
            client.chat([{"role": "user", "content": "hello"}], "general-chat")

    def test_local_health_and_chat_response(self):
        class Response:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_arguments):
                return False

            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        client = LocalModelClient("http://127.0.0.1:8080/v1/chat/completions", "local")
        with patch("urllib.request.urlopen", return_value=Response({"data": [{"id": "phone-model"}]})):
            status = client.health()
        self.assertTrue(status.online)
        self.assertEqual("phone-model", status.model)

        response = Response({"choices": [{"message": {"content": "working"}}]})
        with patch("urllib.request.urlopen", return_value=response) as opened:
            answer = client.chat([{"role": "user", "content": "hello"}], "coding")
        self.assertEqual("working", answer)
        sent = json.loads(opened.call_args.args[0].data.decode("utf-8"))
        self.assertEqual("local", sent["model"])
        self.assertIn("Active route: coding", sent["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
