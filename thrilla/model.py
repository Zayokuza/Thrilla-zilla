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


_REMOTE_POLICY_UNSET = object()


def _is_local_url(url: str) -> bool:
    hostname = (urllib.parse.urlparse(url).hostname or "").lower()
    return hostname in {"127.0.0.1", "localhost", "::1"}


class LocalModelClient:
    def __init__(
        self,
        url: str,
        model: str,
        timeout: Optional[float] = 90.0,
        remote_policy: object = _REMOTE_POLICY_UNSET,
    ) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout
        self.remote_policy = remote_policy

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("THRILLA_MODEL_API_KEY")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _allow_url(self) -> None:
        if _is_local_url(self.url):
            return

        if self.remote_policy is True:
            return

        if self.remote_policy is None:
            return

        if self.remote_policy is False:
            raise ModelError(
                "Remote model URLs are blocked by Thrilla Limit Control."
            )

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

    @staticmethod
    def _normalize_messages(
        messages: List[Dict[str, str]],
        route: str,
    ) -> List[Dict[str, str]]:
        """Build a strict alternating model conversation.

        Thrilla's durable history intentionally preserves failed
        and incomplete turns. Some local chat templates, including
        Gemma, reject those records when consecutive user messages
        or orphan assistant messages reach the inference endpoint.

        Keep durable history unchanged and normalize only the
        model-facing representation.
        """

        system_parts = [
            SYSTEM_PROMPT
            + f"\nActive route: {route}."
        ]
        dialogue: List[Dict[str, str]] = []

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if not isinstance(content, str):
                continue

            if role == "system":
                system_parts.append(content)
                continue

            if role in {"user", "assistant"}:
                dialogue.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

        current_user = None

        if (
            dialogue
            and dialogue[-1]["role"] == "user"
        ):
            current_user = dialogue.pop()

        completed: List[Dict[str, str]] = []
        pending_user = None

        for message in dialogue:
            if message["role"] == "user":
                pending_user = message
                continue

            if (
                message["role"] == "assistant"
                and pending_user is not None
            ):
                completed.extend(
                    (
                        pending_user,
                        message,
                    )
                )
                pending_user = None

        # Keep durable history intact, but bound only the model-facing
        # context. On this phone Gemma processes prompt tokens far more
        # slowly than it generates a tiny reply; sending 20+ historical
        # messages can consume the entire request timeout before generation.
        #
        # General chat gets up to the two most recent complete pairs, within
        # a tight character budget. Work routes keep a larger bounded window.
        if route == "general-chat":
            pair_limit = 2
            history_char_budget = 600
        else:
            pair_limit = 4
            history_char_budget = 4000

        pairs = [
            completed[index:index + 2]
            for index in range(0, len(completed), 2)
            if len(completed[index:index + 2]) == 2
        ]

        selected_pairs = []
        used_chars = 0

        for pair in reversed(pairs):
            pair_chars = sum(
                len(message["content"])
                for message in pair
            )
            if pair_chars > history_char_budget - used_chars:
                break
            selected_pairs.append(pair)
            used_chars += pair_chars
            if len(selected_pairs) >= pair_limit:
                break

        completed = [
            message
            for pair in reversed(selected_pairs)
            for message in pair
        ]

        if current_user is not None:
            completed.append(current_user)

        return [
            {
                "role": "system",
                "content": "\n\n".join(
                    system_parts
                ),
            },
            *completed,
        ]

    def chat(self, messages: List[Dict[str, str]], route: str) -> str:
        self._allow_url()
        payload = {
            "model": self.model,
            "messages": self._normalize_messages(
                messages,
                route,
            ),
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

