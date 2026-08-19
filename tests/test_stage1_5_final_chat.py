import json
import unittest
from unittest.mock import patch
from thrilla.model import LocalModelClient

class Response:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self):
        return json.dumps({"choices":[{"message":{"content":"ok"}}]}).encode()

class StageOneToFiveFinalChatTests(unittest.TestCase):
    def payload(self, route, prompt="hey"):
        client=LocalModelClient("http://127.0.0.1:8080/v1/chat/completions","local-model",timeout=5)
        with patch("urllib.request.urlopen", return_value=Response()) as opened:
            self.assertEqual("ok", client.chat([{"role":"user","content":prompt}], route))
        return json.loads(opened.call_args.args[0].data.decode())

    def test_general_chat_has_small_output_budget(self):
        p=self.payload("general-chat")
        self.assertIn("max_tokens",p)
        self.assertGreater(p["max_tokens"],0)
        self.assertLessEqual(p["max_tokens"],192)

    def test_work_routes_keep_larger_output_budget(self):
        g=self.payload("general-chat")
        c=self.payload("coding","explain code")
        s=self.payload("deep-search","research this")
        self.assertGreater(c["max_tokens"],g["max_tokens"])
        self.assertGreater(s["max_tokens"],g["max_tokens"])

    def test_general_chat_requests_natural_conversation(self):
        p=self.payload("general-chat")
        system=p["messages"][0]["content"].lower()
        self.assertIn("casual conversation",system)
        self.assertIn("do not recite",system)
        self.assertIn("greeting",system)

if __name__ == "__main__": unittest.main()
