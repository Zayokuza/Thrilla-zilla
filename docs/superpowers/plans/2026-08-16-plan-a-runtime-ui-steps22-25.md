# Runtime/UI Steps 22-25 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and strict RED -> GREEN TDD.

**Goal:** Implement Stage 3 Steps 22-25 and streamline Runtime & Models.

**Architecture:** RuntimeManager remains authoritative. Add nonblocking runtime jobs, runtime status, model inventory/selection, and existing Universal Limit Control UI.

**Tech Stack:** Python 3.9-compatible standard library and unittest.

## Global Constraints

- No X | Y type syntax.
- Never kill external runtimes.
- Preserve Step 21 readiness-before-inference.
- No streaming, cancellation, or request queue in this batch.
- Runtime limits stay inside Universal Limit Control.

## Task 1 - Step 22 Background Runtime Job

**Files:**
- Create: `thrilla/runtime/jobs.py`
- Create: `tests/test_stage3_step22_jobs.py`

**Required behavior:**
- One background worker at a time.
- Starting must return without waiting for the worker to finish.
- A second active start raises RuntimeError.
- Successful result is retained.
- Worker failure is retained as FAILED state and error text.

### TDD Cycle

- [ ] Write failing tests for all required behaviors.
- [ ] Run `python -B -m unittest tests.test_stage3_step22_jobs -v` and confirm RED.
- [ ] Implement the minimum thread-and-lock solution.
- [ ] Run the focused suite and confirm GREEN.
- [ ] Run runtime regression tests.
- [ ] Commit only the Task 1 files.

---

## Task 2 - Step 23 Runtime Status Snapshot

**Files:**
- Create: `thrilla/runtime/status.py`
- Modify: `thrilla/runtime/manager.py`
- Create: `tests/test_stage3_step23_runtime_status.py`

**Required behavior:**
- RuntimeManager remains the runtime status authority.
- Status reports configured endpoint and expected model.
- Ready server reports ready=True.
- Unreachable or incompatible server reports ready=False with detail.
- Host, port, ownership, reported models, and error are shown only when actually known.
- Runtime health timeout comes from the existing configured RuntimeManager value.
- Do not use LocalModelClient.health() as a competing authority.

**Required interface:**
- `RuntimeStatusSnapshot` is immutable.
- `RuntimeManager.inspect_configured_runtime(model_url, expected_model)` returns the snapshot.

### TDD Cycle

- [ ] RED: compatible server produces ready status.
- [ ] RED: unreachable server produces truthful failed status.
- [ ] RED: model mismatch is visible.
- [ ] RED: configured health timeout is propagated.
- [ ] Implement by reusing existing runtime inspection.
- [ ] Focused GREEN.
- [ ] Run existing runtime-manager regressions.
- [ ] Commit only Task 2 files.

## Task 3 - Runtime & Models Hub

**Files:**
- Modify: `thrilla/app.py`
- Create: `tests/test_stage3_step23_runtime_ui.py`

**Main menu change:**
- Item 4 becomes `Runtime & Models`.

**Runtime submenu:**
- 1. Runtime Status
- 2. Model Inventory
- 3. Preferred Model
- 4. Refresh
- 0. Back

**Required behavior:**
- Runtime Status uses RuntimeManager inspection.
- Navigation never triggers model inference.
- Runtime/status text stays visually separate from chat answers.
- Unknown values display as unknown rather than being invented.
- A GGUF file existing on disk is not described as active unless runtime evidence says it is.

### TDD Cycle

- [ ] RED: main menu exposes Runtime & Models.
- [ ] RED: runtime submenu has expected entries.
- [ ] RED: Runtime Status uses RuntimeManager.
- [ ] RED: navigation bypasses model chat.
- [ ] Implement minimal hub wiring.
- [ ] Focused GREEN.
- [ ] Run existing app/navigation regressions.
- [ ] Commit only Task 3 files.

---

## Task 4 - Step 24 Preferred GGUF Model Selection

**Files:**
- Modify: `thrilla/config.py`
- Modify: `thrilla/app.py`
- Reuse: `thrilla/runtime/discovery.py`
- Create: `tests/test_stage3_step24_model_selection.py`

**Config interface:**
- Add `preferred_model_path: str = ""`.
- Existing configuration files without this field must still load.
- Save/load must preserve the selected path.

**Required behavior:**
- Reuse existing GGUF discovery and ModelCandidate inventory.
- Show filename, role, quantization, size, and path.
- Show readability and compatibility when known.
- Preferred GGUF path remains separate from the OpenAI-compatible `model_name` alias.
- Selecting a GGUF means preferred, not active.
- Thrilla must not report the selected file as loaded without runtime evidence.
- A preferred path that no longer exists must be reported as missing.

### TDD Cycle

- [ ] RED: old config loads with an empty preferred-model path.
- [ ] RED: preferred-model path survives save and reload.
- [ ] RED: inventory exposes existing ModelCandidate metadata.
- [ ] RED: choosing a preferred GGUF does not claim the runtime loaded it.
- [ ] RED: missing preferred file is reported truthfully.
- [ ] Run `python -B -m unittest tests.test_stage3_step24_model_selection -v` and confirm RED.
- [ ] Implement the minimum config and UI changes.
- [ ] Run the focused suite to GREEN.
- [ ] Run config and discovery regressions.
- [ ] Commit only Task 4 changes with message `feat: add preferred local model selection`.

## Task 5 - Step 25 Runtime Policies

**Files:**
- Modify: `thrilla/app.py`
- Modify: `thrilla/config.py` only if a focused persistence helper is required.
- Reuse: `thrilla/limits.py`
- Create: `tests/test_stage3_step25_policy_ui.py`

**Settings change:**
- Add `Runtime Policies`.

**Required behavior:**
- Use `DEFAULT_LIMITS.names()` as the registered limit source.
- Display the global default mode.
- Display per-limit overrides.
- Display configured values where present.
- Display resolved/effective values where meaningful.
- Allow ON, AUTO, and OFF.
- Persist mode changes through Config.
- Audit policy changes using limit name and mode.
- Do not create hidden limits outside Universal Limit Control.

### TDD Cycle

- [ ] RED: global default mode is displayed.
- [ ] RED: existing per-limit override is displayed.
- [ ] RED: ON persists.
- [ ] RED: AUTO persists.
- [ ] RED: OFF persists.
- [ ] RED: audit event records limit name and mode without prompt content.
- [ ] Run `python -B -m unittest tests.test_stage3_step25_policy_ui -v` and confirm RED.
- [ ] Implement using existing Limit Control.
- [ ] Run the focused suite to GREEN.
- [ ] Run limit/config regression tests.
- [ ] Commit only Task 5 changes with message `feat: expose runtime limit policies`.

---

## Task 6 - Streamlined Terminal UI

**Files:**
- Modify: `thrilla/app.py`
- Create: `tests/test_streamlined_ui.py`

**Target main menu:**
- 1. Ask Thrilla
- 2. Donor Library
- 3. Route Inspector
- 4. Runtime & Models
- 5. Diagnostics
- 6. Conversation History
- 7. Activity Log
- 8. Settings
- 9. About
- 0. Exit

**Required behavior:**
- Preserve direct Ask entry.
- Preserve familiar numeric navigation.
- Reduce repeated explanatory text.
- Keep operational status visually separate from AI answers.
- Runtime & Models must be reachable from the main menu.
- Runtime Policies must be reachable from Settings.
- Existing commands and navigation behavior must continue to work.
- Do not introduce a new terminal UI framework.

### TDD Cycle

- [ ] RED: expected main-menu labels and numeric keys.
- [ ] RED: every menu option maps to the correct handler.
- [ ] RED: Ask remains direct entry.
- [ ] RED: Runtime & Models is reachable.
- [ ] RED: Runtime Policies is reachable.
- [ ] Run `python -B -m unittest tests.test_streamlined_ui -v` and confirm RED.
- [ ] Implement minimal UI cleanup.
- [ ] Run focused suite to GREEN.
- [ ] Run existing CLI and app regressions.
- [ ] Commit only Task 6 changes with message `feat: streamline runtime terminal interface`.

## Plan A Verification Gate

- [ ] Run all Step 22-25 focused tests together.
- [ ] Run existing runtime tests.
- [ ] Run existing config and Limit Control tests.
- [ ] Run existing CLI/app tests.
- [ ] Run the full test suite.
- [ ] Run `python -m compileall -f -q thrilla tests`.
- [ ] Run `git diff --check`.
- [ ] Review changed-file boundaries.
- [ ] Confirm no production Python uses X | Y syntax.
- [ ] Confirm Step 21 readiness-before-inference still works.
- [ ] Confirm no streaming, cancellation, or request queue was added.
- [ ] Confirm external runtime ownership behavior remains unchanged.

## Plan A Completion

Plan A is complete only when Steps 22, 23, 24, and 25 work together, the streamlined menus pass regression tests, the full suite passes, compilation passes, and the worktree contains only reviewed changes.
