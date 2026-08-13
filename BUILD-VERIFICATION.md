# Build verification — 0.1.0-alpha.2

Date: 2026-08-12

## Verified in the build workspace

- Python bytecode compilation: PASS
- Python 3.9 grammar parse: PASS
- Standard-library test suite: 29 tests PASS
- Bash syntax for launcher and Termux installer: PASS
- Clean temporary Termux-style installation: PASS
- Installed launcher version check: PASS
- Real pseudo-terminal launch: PASS
- Colored compact menu rendering: PASS
- Numeric option `5` plus Enter in one input packet: PASS
- Diagnostics screen dispatch from option `5`: PASS
- Ctrl+C from an interactive submenu returns to the main menu: PASS
- Ctrl+C from the interactive main menu exits without a traceback: PASS
- Ctrl+C from the non-interactive menu exits without a traceback: PASS
- Clean menu exit: PASS
- Mock OpenAI-compatible model health/chat exchange: PASS
- Remote-model default-deny check: PASS
- Core catalog shape: 10 categories × 10 donors PASS
- Priority catalog shape: 30 donors PASS
- Catalog duplicate check: PASS
- Xray-core Phase-2 registration: PASS
- Local Markdown link validation: PASS

## Requires the actual phone

- Scan the user's `~/Thrilla-codebases` tree and confirm 100/100 locally.
- Confirm Xray-core at `11-networking-proxy/01-xray-core` locally.
- Connect to the user's running `llama-server` and complete a live response.
- Confirm alpha.2 Ctrl+C behavior and the preferred Termux font, soft-keyboard height, colors, and arrow keys.
- Measure live RAM, CPU, temperature, latency, and battery impact.

The user-reported download result is 100/100 core repositories with zero clone failures, but the phone filesystem is not mounted in this build workspace. This document therefore does not relabel that report as a locally reproduced check.

## Not claimed by this alpha

This build does not yet claim autonomous tool execution, live research, repository editing, sandboxing, semantic retrieval, self-repair, or automatic keep/rollback evaluation. Those appear as staged work in `docs/ARCHITECTURE.md`.
