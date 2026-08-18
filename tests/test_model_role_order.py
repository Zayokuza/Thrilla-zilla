import json
import unittest
from unittest.mock import patch

from thrilla.model import LocalModelClient


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ModelRoleOrderTests(unittest.TestCase):
    def test_model_payload_normalizes_malformed_history(self):
        client = LocalModelClient(
            "http://127.0.0.1:8080/v1/chat/completions",
            "local-model",
        )

        messages = [
            {
                "role": "assistant",
                "content": "orphan assistant",
            },
            {
                "role": "user",
                "content": "failed request",
            },
            {
                "role": "user",
                "content": "recovered request",
            },
            {
                "role": "assistant",
                "content": "recovered answer",
            },
            {
                "role": "system",
                "content": "reference evidence",
            },
            {
                "role": "user",
                "content": "current request",
            },
        ]

        response = Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": "ok",
                        }
                    }
                ]
            }
        )

        with patch(
            "urllib.request.urlopen",
            return_value=response,
        ) as opened:
            answer = client.chat(
                messages,
                "general-chat",
            )

        self.assertEqual(answer, "ok")

        request = opened.call_args.args[0]
        payload = json.loads(
            request.data.decode("utf-8")
        )

        sent = payload["messages"]

        self.assertEqual(
            [message["role"] for message in sent],
            [
                "system",
                "user",
                "assistant",
                "user",
            ],
        )

        self.assertIn(
            "reference evidence",
            sent[0]["content"],
        )

        self.assertIn(
            "Active route: general-chat",
            sent[0]["content"],
        )

        self.assertEqual(
            sent[1]["content"],
            "recovered request",
        )

        self.assertEqual(
            sent[2]["content"],
            "recovered answer",
        )

        self.assertEqual(
            sent[3]["content"],
            "current request",
        )


if __name__ == "__main__":
    unittest.main()
