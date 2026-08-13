"""Canonical Thrilla donor catalog.

The catalog records source locations. It does not import or execute donor code.
"""

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class DonorSpec:
    phase: int
    category: int
    category_slug: str
    category_name: str
    slot: int
    repository: str
    folder: str
    priority: bool = False

    @property
    def relative_path(self) -> str:
        return f"{self.category_slug}/{self.slot:02d}-{self.folder}"


CategoryEntries = Sequence[Tuple[str, str]]


PHASE_ONE = (
    (
        "01-agent-brain",
        "Agent Brain / Reasoning / Orchestration",
        (
            ("NousResearch/hermes-agent", "hermes-agent"),
            ("OpenHands/software-agent-sdk", "openhands-sdk"),
            ("openclaw/openclaw", "openclaw"),
            ("langchain-ai/langgraph", "langgraph"),
            ("crewAIInc/crewAI", "crewai"),
            ("microsoft/autogen", "autogen"),
            ("agno-agi/agno", "agno"),
            ("microsoft/semantic-kernel", "semantic-kernel"),
            ("Significant-Gravitas/AutoGPT", "autogpt"),
            ("OpenHands/OpenHands", "openhands"),
        ),
    ),
    (
        "02-coding-self-repair",
        "Coding / Self-Repair / Repository Modification",
        (
            ("Aider-AI/aider", "aider"),
            ("cline/cline", "cline"),
            ("anomalyco/opencode", "opencode"),
            ("openai/codex", "codex"),
            ("SWE-agent/SWE-agent", "swe-agent"),
            ("continuedev/continue", "continue"),
            ("TabbyML/tabby", "tabby"),
            ("zed-industries/zed", "zed"),
            ("microsoft/vscode", "vscode"),
            ("The-PR-Agent/pr-agent", "pr-agent"),
        ),
    ),
    (
        "03-ai-runtime",
        "AI Models / Inference / Runtime",
        (
            ("ggml-org/llama.cpp", "llama.cpp"),
            ("pytorch/executorch", "executorch"),
            ("microsoft/onnxruntime", "onnxruntime"),
            ("ollama/ollama", "ollama"),
            ("vllm-project/vllm", "vllm"),
            ("huggingface/transformers", "transformers"),
            ("pytorch/pytorch", "pytorch"),
            ("mlc-ai/mlc-llm", "mlc-llm"),
            ("sgl-project/sglang", "sglang"),
            ("tensorflow/tensorflow", "tensorflow"),
        ),
    ),
    (
        "04-code-language-build",
        "Language Intelligence / Compilers / Build",
        (
            ("tree-sitter/tree-sitter", "tree-sitter"),
            ("llvm/llvm-project", "llvm-project"),
            ("python/cpython", "cpython"),
            ("rust-lang/rust", "rust"),
            ("golang/go", "go"),
            ("microsoft/TypeScript", "typescript"),
            ("openjdk/jdk", "openjdk"),
            ("Kitware/CMake", "cmake"),
            ("gradle/gradle", "gradle"),
            ("ninja-build/ninja", "ninja"),
        ),
    ),
    (
        "05-memory-knowledge-state",
        "Memory / RAG / Knowledge / State",
        (
            ("mem0ai/mem0", "mem0"),
            ("run-llama/llama_index", "llama-index"),
            ("deepset-ai/haystack", "haystack"),
            ("letta-ai/letta", "letta"),
            ("infiniflow/ragflow", "ragflow"),
            ("sqlite/sqlite", "sqlite"),
            ("qdrant/qdrant", "qdrant"),
            ("chroma-core/chroma", "chroma"),
            ("postgres/postgres", "postgresql"),
            ("redis/redis", "redis"),
        ),
    ),
    (
        "06-web-research",
        "Browser / Research / Historical Web",
        (
            ("browser-use/browser-use", "browser-use"),
            ("microsoft/playwright", "playwright"),
            ("ArchiveBox/ArchiveBox", "archivebox"),
            ("scrapy/scrapy", "scrapy"),
            ("puppeteer/puppeteer", "puppeteer"),
            ("SeleniumHQ/selenium", "selenium"),
            ("apify/crawlee", "crawlee"),
            ("projectdiscovery/katana", "katana"),
            ("curl/curl", "curl"),
            ("mitmproxy/mitmproxy", "mitmproxy"),
        ),
    ),
    (
        "07-tools-workflows",
        "Tools / Workflows / Automation",
        (
            ("activepieces/activepieces", "activepieces"),
            ("n8n-io/n8n", "n8n"),
            ("node-red/node-red", "node-red"),
            ("temporalio/temporal", "temporal"),
            ("langflow-ai/langflow", "langflow"),
            ("langgenius/dify", "dify"),
            ("windmill-labs/windmill", "windmill"),
            ("apache/airflow", "airflow"),
            ("PrefectHQ/prefect", "prefect"),
            ("triggerdotdev/trigger.dev", "trigger-dev"),
        ),
    ),
    (
        "08-execution-os",
        "Android / Windows Execution / OS / Sandbox",
        (
            ("termux/termux-packages", "termux-packages"),
            ("e2b-dev/E2B", "e2b"),
            ("podman-container-tools/podman", "podman"),
            ("moby/moby", "moby"),
            ("microsoft/WSL", "wsl"),
            ("termux/termux-app", "termux-app"),
            ("torvalds/linux", "linux"),
            ("mirror/busybox", "busybox"),
            ("PowerShell/PowerShell", "powershell"),
            ("microsoft/terminal", "windows-terminal"),
        ),
    ),
    (
        "09-interface-api",
        "Interface / API / Control Plane",
        (
            ("open-webui/open-webui", "open-webui"),
            ("Chainlit/chainlit", "chainlit"),
            ("lobehub/lobehub", "lobehub"),
            ("gradio-app/gradio", "gradio"),
            ("streamlit/streamlit", "streamlit"),
            ("fastapi/fastapi", "fastapi"),
            ("Textualize/textual", "textual"),
            ("tauri-apps/tauri", "tauri"),
            ("electron/electron", "electron"),
            ("pallets/flask", "flask"),
        ),
    ),
    (
        "10-evaluation-security",
        "Evaluation / Security / Observability",
        (
            ("langfuse/langfuse", "langfuse"),
            ("promptfoo/promptfoo", "promptfoo"),
            ("Arize-ai/phoenix", "phoenix"),
            ("pytest-dev/pytest", "pytest"),
            ("semgrep/semgrep", "semgrep"),
            ("aquasecurity/trivy", "trivy"),
            ("getsentry/sentry", "sentry"),
            ("prometheus/prometheus", "prometheus"),
            ("grafana/grafana", "grafana"),
            ("github/codeql", "codeql"),
        ),
    ),
)


def _phase_one_specs() -> Iterable[DonorSpec]:
    for category, (slug, name, entries) in enumerate(PHASE_ONE, start=1):
        for slot, (repository, folder) in enumerate(entries, start=1):
            yield DonorSpec(
                phase=1,
                category=category,
                category_slug=slug,
                category_name=name,
                slot=slot,
                repository=repository,
                folder=folder,
                priority=slot <= 3,
            )


CORE_DONORS: Tuple[DonorSpec, ...] = tuple(_phase_one_specs())

# Phase 2 is deliberately incomplete. Xray-core is the one verified specialist
# already collected; future candidates must be deduplicated against CORE_DONORS.
SPECIALIST_DONORS: Tuple[DonorSpec, ...] = (
    DonorSpec(
        phase=2,
        category=11,
        category_slug="11-networking-proxy",
        category_name="Networking / Proxy / Transport",
        slot=1,
        repository="XTLS/Xray-core",
        folder="xray-core",
        priority=True,
    ),
)

ALL_DONORS: Tuple[DonorSpec, ...] = CORE_DONORS + SPECIALIST_DONORS


def phase_one_categories() -> List[Tuple[int, str, str]]:
    return [
        (number, slug, name)
        for number, (slug, name, _entries) in enumerate(PHASE_ONE, start=1)
    ]

