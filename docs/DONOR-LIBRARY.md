# Donor library

The donor library is a collection of source trees for architectural study. It is not a dependency lockfile and does not make the listed software part of Thrilla-zilla.

Phone-reported Phase-1 status: **100/100 Git repositories, zero clone failures, approximately 23 GB**.

The ★ marker identifies the priority 30: the first three repositories in each core category.

## 1. Agent Brain / Reasoning / Orchestration

Folder: `~/Thrilla-codebases/01-agent-brain`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `NousResearch/hermes-agent` | `01-hermes-agent` |
| 02 | ★ | `OpenHands/software-agent-sdk` | `02-openhands-sdk` |
| 03 | ★ | `openclaw/openclaw` | `03-openclaw` |
| 04 |  | `langchain-ai/langgraph` | `04-langgraph` |
| 05 |  | `crewAIInc/crewAI` | `05-crewai` |
| 06 |  | `microsoft/autogen` | `06-autogen` |
| 07 |  | `agno-agi/agno` | `07-agno` |
| 08 |  | `microsoft/semantic-kernel` | `08-semantic-kernel` |
| 09 |  | `Significant-Gravitas/AutoGPT` | `09-autogpt` |
| 10 |  | `OpenHands/OpenHands` | `10-openhands` |

Purpose: reasoning loops, delegation, tools, planning, state machines, checkpoints, and autonomous execution.

## 2. Coding / Self-Repair / Repository Modification

Folder: `~/Thrilla-codebases/02-coding-self-repair`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `Aider-AI/aider` | `01-aider` |
| 02 | ★ | `cline/cline` | `02-cline` |
| 03 | ★ | `anomalyco/opencode` | `03-opencode` |
| 04 |  | `openai/codex` | `04-codex` |
| 05 |  | `SWE-agent/SWE-agent` | `05-swe-agent` |
| 06 |  | `continuedev/continue` | `06-continue` |
| 07 |  | `TabbyML/tabby` | `07-tabby` |
| 08 |  | `zed-industries/zed` | `08-zed` |
| 09 |  | `microsoft/vscode` | `09-vscode` |
| 10 |  | `The-PR-Agent/pr-agent` | `10-pr-agent` |

Purpose: repository understanding, code modification, autonomous coding, repair, testing, diff review, and editor integration.

Corrections preserved in the canonical plan:

- archived `RooCodeInc/Roo-Code` was removed;
- `qodo-ai/pr-agent` was corrected to `The-PR-Agent/pr-agent`;
- `openai/codex` was added as a current replacement.

## 3. AI Models / Inference / Runtime

Folder: `~/Thrilla-codebases/03-ai-runtime`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `ggml-org/llama.cpp` | `01-llama.cpp` |
| 02 | ★ | `pytorch/executorch` | `02-executorch` |
| 03 | ★ | `microsoft/onnxruntime` | `03-onnxruntime` |
| 04 |  | `ollama/ollama` | `04-ollama` |
| 05 |  | `vllm-project/vllm` | `05-vllm` |
| 06 |  | `huggingface/transformers` | `06-transformers` |
| 07 |  | `pytorch/pytorch` | `07-pytorch` |
| 08 |  | `mlc-ai/mlc-llm` | `08-mlc-llm` |
| 09 |  | `sgl-project/sglang` | `09-sglang` |
| 10 |  | `tensorflow/tensorflow` | `10-tensorflow` |

Purpose: local GGUF LLM execution, Android/mobile edge inference, cross-framework inference, serving, model APIs, batching, quantization, and acceleration.

## 4. Language Intelligence / Compilers / Build

Folder: `~/Thrilla-codebases/04-code-language-build`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `tree-sitter/tree-sitter` | `01-tree-sitter` |
| 02 | ★ | `llvm/llvm-project` | `02-llvm-project` |
| 03 | ★ | `python/cpython` | `03-cpython` |
| 04 |  | `rust-lang/rust` | `04-rust` |
| 05 |  | `golang/go` | `05-go` |
| 06 |  | `microsoft/TypeScript` | `06-typescript` |
| 07 |  | `openjdk/jdk` | `07-openjdk` |
| 08 |  | `Kitware/CMake` | `08-cmake` |
| 09 |  | `gradle/gradle` | `09-gradle` |
| 10 |  | `ninja-build/ninja` | `10-ninja` |

Purpose: parsing, syntax trees, compilers, interpreters, language semantics, symbols, build discovery, and unfamiliar-source understanding.

FreeCAD was considered here, then moved to Phase 2. Ninja was selected for the core because arbitrary-project build understanding is foundational.

## 5. Memory / RAG / Knowledge / State

Folder: `~/Thrilla-codebases/05-memory-knowledge-state`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `mem0ai/mem0` | `01-mem0` |
| 02 | ★ | `run-llama/llama_index` | `02-llama-index` |
| 03 | ★ | `deepset-ai/haystack` | `03-haystack` |
| 04 |  | `letta-ai/letta` | `04-letta` |
| 05 |  | `infiniflow/ragflow` | `05-ragflow` |
| 06 |  | `sqlite/sqlite` | `06-sqlite` |
| 07 |  | `qdrant/qdrant` | `07-qdrant` |
| 08 |  | `chroma-core/chroma` | `08-chroma` |
| 09 |  | `postgres/postgres` | `09-postgresql` |
| 10 |  | `redis/redis` | `10-redis` |

Purpose: working memory, durable state, exact and semantic retrieval, RAG, source metadata, vector stores, databases, and caching.

Phone-first implementation target: SQLite plus exact/full-text retrieval, followed by lightweight vector retrieval when justified. PostgreSQL, Qdrant, and Redis are possible larger-machine adapters.

## 6. Browser / Research / Crawling / Historical Web

Folder: `~/Thrilla-codebases/06-web-research`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `browser-use/browser-use` | `01-browser-use` |
| 02 | ★ | `microsoft/playwright` | `02-playwright` |
| 03 | ★ | `ArchiveBox/ArchiveBox` | `03-archivebox` |
| 04 |  | `scrapy/scrapy` | `04-scrapy` |
| 05 |  | `puppeteer/puppeteer` | `05-puppeteer` |
| 06 |  | `SeleniumHQ/selenium` | `06-selenium` |
| 07 |  | `apify/crawlee` | `07-crawlee` |
| 08 |  | `projectdiscovery/katana` | `08-katana` |
| 09 |  | `curl/curl` | `09-curl` |
| 10 |  | `mitmproxy/mitmproxy` | `10-mitmproxy` |

Purpose: live web access, browser automation, crawling, network retrieval, caching, historical information, and research recovery.

## 7. Tools / Workflows / Automation

Folder: `~/Thrilla-codebases/07-tools-workflows`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `activepieces/activepieces` | `01-activepieces` |
| 02 | ★ | `n8n-io/n8n` | `02-n8n` |
| 03 | ★ | `node-red/node-red` | `03-node-red` |
| 04 |  | `temporalio/temporal` | `04-temporal` |
| 05 |  | `langflow-ai/langflow` | `05-langflow` |
| 06 |  | `langgenius/dify` | `06-dify` |
| 07 |  | `windmill-labs/windmill` | `07-windmill` |
| 08 |  | `apache/airflow` | `08-airflow` |
| 09 |  | `PrefectHQ/prefect` | `09-prefect` |
| 10 |  | `triggerdotdev/trigger.dev` | `10-trigger-dev` |

Purpose: tool orchestration, integration catalogs, automation graphs, retries, schedules, durable workflows, and run visibility.

## 8. Android / Windows Execution / OS / Sandbox

Folder: `~/Thrilla-codebases/08-execution-os`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `termux/termux-packages` | `01-termux-packages` |
| 02 | ★ | `e2b-dev/E2B` | `02-e2b` |
| 03 | ★ | `podman-container-tools/podman` | `03-podman` |
| 04 |  | `moby/moby` | `04-moby` |
| 05 |  | `microsoft/WSL` | `05-wsl` |
| 06 |  | `termux/termux-app` | `06-termux-app` |
| 07 |  | `torvalds/linux` | `07-linux` |
| 08 |  | `mirror/busybox` | `08-busybox` |
| 09 |  | `PowerShell/PowerShell` | `09-powershell` |
| 10 |  | `microsoft/terminal` | `10-windows-terminal` |

Purpose: execution environments, isolation, resource control, Android/Termux integration, Windows compatibility, shell behavior, and operating-system interfaces.

Corrections preserved in the canonical plan:

- Podman repository corrected to `podman-container-tools/podman`;
- invalid `busybox/busybox` corrected to `mirror/busybox`.

## 9. Interface / API / Control Plane

Folder: `~/Thrilla-codebases/09-interface-api`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `open-webui/open-webui` | `01-open-webui` |
| 02 | ★ | `Chainlit/chainlit` | `02-chainlit` |
| 03 | ★ | `lobehub/lobehub` | `03-lobehub` |
| 04 |  | `gradio-app/gradio` | `04-gradio` |
| 05 |  | `streamlit/streamlit` | `05-streamlit` |
| 06 |  | `fastapi/fastapi` | `06-fastapi` |
| 07 |  | `Textualize/textual` | `07-textual` |
| 08 |  | `tauri-apps/tauri` | `08-tauri` |
| 09 |  | `electron/electron` | `09-electron` |
| 10 |  | `pallets/flask` | `10-flask` |

Purpose: chat and control surfaces, local APIs, terminal UIs, web UIs, desktop shells, streaming interaction, and configuration.

The former repository name `lobehub/lobe-chat` was corrected to `lobehub/lobehub`.

## 10. Evaluation / Testing / Security / Observability

Folder: `~/Thrilla-codebases/10-evaluation-security`

| Slot | Priority | Repository | Local folder |
|---:|:---:|---|---|
| 01 | ★ | `langfuse/langfuse` | `01-langfuse` |
| 02 | ★ | `promptfoo/promptfoo` | `02-promptfoo` |
| 03 | ★ | `Arize-ai/phoenix` | `03-phoenix` |
| 04 |  | `pytest-dev/pytest` | `04-pytest` |
| 05 |  | `semgrep/semgrep` | `05-semgrep` |
| 06 |  | `aquasecurity/trivy` | `06-trivy` |
| 07 |  | `getsentry/sentry` | `07-sentry` |
| 08 |  | `prometheus/prometheus` | `08-prometheus` |
| 09 |  | `grafana/grafana` | `09-grafana` |
| 10 |  | `github/codeql` | `10-codeql` |

Purpose: traces, evaluation, regression detection, unit and integration testing, static analysis, vulnerability detection, runtime errors, metrics, dashboards, and code security.

## Phase 2 — specialist/reference library

Phase 1 teaches Thrilla how to become the core system. Phase 2 is intended to teach broader engineering domains:

1. graphics, 2D/3D, CAD, and game engines;
2. audio, video, multimedia, codecs, and streaming;
3. networking, protocols, proxies, and packet systems;
4. security, reverse engineering, and defensive tooling;
5. databases, storage engines, and search internals;
6. Android applications and framework internals;
7. Windows applications and platform internals;
8. scientific, mathematical, and numerical computing;
9. embedded systems, firmware, hardware, and IoT;
10. large real-world applications and distributed systems.

The conceptual target is ten disciplines with ten repositories each, with no Phase-1 duplicate.

### Verified collected entry

| Category | Slot | Repository | Local path | Phone-reported verification |
|---|---:|---|---|---|
| Networking / proxy / transport | 01 | `XTLS/Xray-core` | `11-networking-proxy/01-xray-core` | `main`, commit `7d214f8`, clean, 8.7 MB |

Its study scope includes Go networking, TCP/UDP, proxy routing, VLESS, XTLS, REALITY, TLS/uTLS, QUIC, DNS, WireGuard, gRPC/protobuf, transport abstraction, connection handling, and Android/Windows networking.

### Previously discussed candidates

Blender, Godot, GIMP, FreeCAD, OBS Studio, Kubernetes, a usable Chromium source tree, Nmap, Wireshark, large Android projects, AUTOMATIC1111/stable-diffusion-webui, Chatwoot, and UI/UX reference projects were discussed as possibilities.

PyTorch and PostgreSQL must not be duplicated because both already exist in Phase 1. Every Phase-2 selection still requires current-repository verification, ranking, license review, device/storage consideration, and duplicate checking before it becomes canonical.

