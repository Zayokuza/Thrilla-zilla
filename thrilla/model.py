"""Small OpenAI-compatible adapter for a local llama.cpp-style server."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional


SYSTEM_PROMPT = """You are Thrilla-zilla, a local-first AI workbench for Android and Windows.
Prioritize accuracy and user safety, then reliability, privacy, transparency,
accountability, fairness, adaptability, efficiency, and user-centered empathy.
State uncertainty plainly. Do not claim an action occurred without evidence."""


@dataclass(frozen=True)
class ModelStatus:
    online: bool
    detail: str
    model: str = ""


class ModelError(RuntimeError):
    pass


def _is_local_url(url: str) -> bool:
    hostname = (urllib.parse.urlparse(url).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost", "::1"}


class LocalModelClient:
    def __init__(self, url: str, model: str, timeout: float = 90.0) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("THRILLA_MODEL_API_KEY")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _allow_url(self) -> None:
        if _is_local_url(self.url):
            return
        if os.environ.get("THRILLA_ALLOW_REMOTE_MODEL") == "1":
            return
        raise ModelError(
            "Remote model URLs are blocked by default. Set "
            "THRILLA_ALLOW_REMOTE_MODEL=1 only if you accept sending prompts remotely."
        )

    def health(self, timeout: float = 1.0) -> ModelStatus:
        try:
            self._allow_url()
        except ModelError as error:
            return ModelStatus(False, str(error), self.model)
        parsed = urllib.parse.urlparse(self.url)
        models_url = urllib.parse.urlunparse(
            parsed._replace(path="/v1/models", params="", query="", fragment="")
        )
        request = urllib.request.Request(models_url, headers=self._headers())
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            names = [item.get("id", "") for item in payload.get("data", [])]
            model = names[0] if names else self.model
            return ModelStatus(True, "OpenAI-compatible endpoint responded.", model)
        except (OSError, ValueError, urllib.error.URLError) as error:
            return ModelStatus(False, f"Local model unavailable: {error}", self.model)

    def chat(self, messages: List[Dict[str, str]], route: str) -> str:
        self._allow_url()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT + f"\nActive route: {route}."},
                *messages,
            ],
            "temperature": 0.2,
            "stream": False,
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            content: Optional[str] = result["choices"][0]["message"]["content"]
            if not content:
                raise ModelError("Model returned an empty response.")
            return content
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ModelError(f"Unexpected model response: {error}") from error
        except (OSError, urllib.error.URLError) as error:
            raise ModelError(f"Model request failed: {error}") from error

