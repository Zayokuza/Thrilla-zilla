# Ordered build roadmap

This order follows technical dependencies. Later layers rely on the contracts and safety behavior established earlier.

## 1. Stabilize the phone interface

Fix Ctrl+C, terminal restoration, resizing, rapid number-plus-Enter input, keyboard-height layout, wrapping, and every menu route. The rest of the system is inaccessible if the control surface is unreliable.

## 2. Add atomic installation and updates

Install into dated release directories, run tests before activation, switch one launcher only after success, preserve the prior release, and support rollback. This protects the working phone installation while Thrilla is changing quickly.

## 3. Build the local-model runtime manager

Discover configured GGUF files, start and stop `llama-server`, check readiness, stream tokens, cancel generation, recover crashes, and enforce configurable context/RAM limits. The current client cannot start its own model.

Primary donors: llama.cpp, ExecuTorch, and ONNX Runtime. llama.cpp is the primary local LLM runtime; ExecuTorch and ONNX Runtime should be evaluated for efficient mobile models, embeddings, classifiers, and other bounded inference tasks rather than treated as duplicate chat servers.

## 4. Create the bounded Agent Brain

Implement:

```text
request → understand → plan → act → observe → critic → finish/retry
```

Every run needs step, tool, token, time, and retry budgets plus cancellation. This turns model text into a controlled agent process.

Primary donors: Hermes Agent, OpenHands SDK, and OpenClaw.

## 5. Define the structured tool contract

Every tool needs a stable name, input schema, permission class, timeout, cancellation path, structured result, evidence, and structured failure. This prevents silent tool failures and lets the critic evaluate real outcomes.

## 6. Add safety and permission controls

Define allowed roots, read/write/network/device scopes, secret redaction, high-risk action gates, destructive-action previews, and policy-visible denials. Autonomy is useful only when actions remain attributable and recoverable.

## 7. Implement the essential tools

Start with file operations, literal/regex search, Git inspection and patching, argv-based commands, process control, compilation, linting, testing, storage, RAM, CPU, battery, and platform information.

## 8. Add checkpoints and rollback

Before every state-changing action, capture affected files and Git state. After changes, validate. If evaluation fails or execution is cancelled, restore the checkpoint and verify restoration.

## 9. Build repository intelligence

Detect languages, frameworks, packages, build systems, entry points, symbols, imports, tests, generated files, and cross-language boundaries. Begin with deterministic repository maps and Tree-sitter parsing.

Primary donors: Tree-sitter, LLVM, and CPython.

## 10. Build the coding and repair agent

Implement:

```text
inspect → plan → checkpoint → edit → compile/lint → test → critic → keep/rollback
```

Primary donors: Aider, Cline, and OpenCode.

## 11. Add SQLite memory and retrieval

Store session turns, project facts, tasks, decisions, source, confidence, ownership, scope, and timestamps. Use SQLite plus full-text search first. Add lightweight semantic retrieval only after exact retrieval and migrations are stable.

Primary donors: Mem0, LlamaIndex, and Haystack. SQLite is the intended phone-first durable store.

## 12. Add research and OSINT

Support direct HTTP, browser-rendered pages, cached responses, archived versions, timestamps, citations, source comparison, cancellation, and network/privacy controls.

Primary donors: Browser Use, Playwright, and ArchiveBox.

## 13. Add workflows and integrations

Create reusable action graphs, triggers, retries, schedules, secrets references, and human-visible run state.

Primary donors: Activepieces, n8n, and Node-RED.

## 14. Add evaluation, security, and full auditing

Record who, what, why, when, where, duration, inputs, results, evidence, failures, and grades. Measure correctness, tests, speed, RAM, CPU, complexity, security, privacy, maintainability, and tool reliability.

Primary donors: Langfuse, Promptfoo, and Phoenix, followed by the remaining Category-10 projects.

## 15. Add controlled self-improvement

Allow Thrilla to identify weaknesses and propose changes, but require checkpoints, implementation limits, compilation, tests, before/after benchmarks, security review, critic evaluation, and automatic rollback of regressions.

## 16. Add Android and Windows adapters

Android/Termux support includes storage permissions, intents, notifications, optional Termux:API, process lifecycle, and thermal/battery awareness. Windows support includes PowerShell, CMD/Cygwin paths, services/processes, and safe filesystem behavior.

Primary donors: Termux Packages, E2B, and Podman, followed by the rest of Category 8.

## 17. Finish interface and API surfaces

Keep the phone terminal interface dependable, then add an optional local API and richer UI without changing the core contracts.

Primary donors: Open WebUI, Chainlit, and LobeHub.

## 18. Study donors under provenance control

Inspect the priority 30 first, tied to the active implementation layer. Record commits, files, licenses, concepts, provenance, tests, and benchmarks. Never use repository count as a substitute for integration quality.

## 19. Complete target-device proof

Run cold install, donor scan, model lifecycle, conversation, files, coding/rollback, research/citations, cancellation, resource, restart, Android, and Windows tests. Only measured end-to-end success advances the project toward 1.0.

## 20. Build Phase 2

Finalize a duplicate-free specialist library after the core works. Phase 2 expands what Thrilla can study; it is not a blocker for the core agent.

