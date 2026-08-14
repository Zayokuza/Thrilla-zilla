# Current status

Version: **0.1.0-alpha.2**
Date: **2026-08-13**
Stage: **Stages 1–2 complete; Stage 3 in progress**

## What is verified in the source workspace

- Stage 1 phone-interface stabilization is complete;
- Stage 2 atomic installation/update/rollback is complete;
- the complete Android/Termux regression suite passes 62 tests;
- atomic candidate staging, validation and activation are tested;
- current/previous release pointers are tested;
- failed activation automatically restores prior release state;
- explicit rollback is tested;
- stale/concurrent release locks are tested;
- release retention is tested;
- POSIX stable-launcher isolation is tested;
- Windows stable-launcher generation is tested;
- Termux and Windows installers use the atomic release manager;

- the project imports and compiles;
- every Python source and test file parses with Python 3.9 grammar;
- the dependency-free unit/regression suite passes;
- the Termux launcher and installer pass Bash syntax checks;
- a clean temporary Termux-style installation works;
- the archive can be extracted and retested;
- a real pseudo-terminal renders the colored compact menu;
- rapid numeric input followed by Enter dispatches correctly;
- Ctrl+C returns from a submenu or cleanly exits the main menu;
- model health/chat protocol works against a simulated OpenAI-compatible endpoint;
- remote model URLs are rejected unless explicitly enabled;
- the executable catalog contains exactly ten categories of ten core donors;
- the priority layer contains exactly 30 unique donors;
- the Phase-1 and Phase-2 entries have unique repository names and paths;
- Xray-core is registered as the first Phase-2 specialist.

Exact test totals are written to `BUILD-VERIFICATION.md`. Release-archive integrity is verified during packaging, and its SHA-256 is published with the downloadable artifact.

## What the supplied phone output verifies

- Thrilla launches in Termux;
- the colored menu renders on the phone;
- the runtime discovers 100/100 core donor repositories;
- the priority-30 screen reads the donor catalog and displays present repositories;
- the alpha.1 main menu exposed a Ctrl+C traceback while waiting for a key.

The Ctrl+C failure path is covered by new alpha.2 regression tests. It still requires final confirmation on the user's actual Termux installation after updating.

## What is not yet verified on the phone

- alpha.2 Ctrl+C behavior;
- a live response through the phone's actual `llama-server` and GGUF;
- automatic model startup, because it is not implemented yet;
- RAM, CPU, temperature, latency, storage, and battery measurements;
- Windows behavior on the target Windows machine;
- autonomous tools, coding, research, memory retrieval and sandboxing, because those later layers are not implemented yet.

## Capability status

| Capability | Status | Evidence or limitation |
|---|---|---|
| Colored interactive menu | Working | Source tests, pseudo-terminal test, and phone readout |
| Numeric and arrow navigation | Working in source | Phone confirmation still useful for alpha.2 |
| Ctrl+C clean exit/back | Fixed in alpha.2 | Regression-tested; phone confirmation pending |
| Deterministic routing | Working | Unit tests and CLI smoke tests |
| Donor catalog and scan | Working | 100/100 phone result |
| Read-only Git donor inspection | Implemented | Requires selected-repo phone testing |
| Local history and audit metadata | Implemented | Unit tested |
| Local-model HTTP client | Implemented | Protocol tested; live phone proof pending |
| Atomic install/update/rollback | Working | 62-test suite plus real Android/Termux install, update and rollback proof |
| Model discovery/lifecycle | Missing | Roadmap stage 3 |
| Agent Brain | Missing | Roadmap stage 4 |
| Safe tools and executor | Missing | Roadmap stages 5–8 |
| Repository intelligence | Missing | Roadmap stage 9 |
| Coding and repair | Missing | Roadmap stage 10 |
| SQLite retrieval memory | Missing | Roadmap stage 11 |
| Research/OSINT | Missing | Roadmap stage 12 |
| Evaluation/self-improvement | Missing | Roadmap stages 14–15 |
| Android/Windows adapters | Missing | Roadmap stage 16 |
| Phase-2 specialist 100 | Planned | Only Xray-core is canonical today |

## Repository and license status

The GitHub repository was verified empty immediately before preparing this initial publication. No Thrilla-zilla license has been selected. Donor projects retain their own licenses, and listing them does not imply reuse permission or endorsement.
