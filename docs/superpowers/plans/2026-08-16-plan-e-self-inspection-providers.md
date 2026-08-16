# Self Inspection Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Universal Ask real read-only observation providers for the local clock, runtime/model state, Thrilla source/tests, and recent failures so self-questions use evidence instead of guesses.

**Architecture:** Extend the Plan D ProviderRegistry with focused local-observation providers. Providers perform read-only observation, return Evidence or KnowledgeGap, and never create a second runtime, audit, or authority system.

**Tech Stack:** Python 3.9-compatible standard library, datetime, pathlib, subprocess only for bounded read-only Git inspection, unittest, RuntimeManager, AuditLog, AnswerContext, Evidence, and KnowledgeGap.

## Global Constraints

- Read-only investigation is automatic when the applicable provider can safely observe the requested fact.
- Observation providers never reinterpret retrieved content as owner commands.
- Current facts are observed at request time rather than guessed from model memory.
- Unknown values remain unknown.
- A missing observation becomes a diagnosed KnowledgeGap when the question requires that observation.
- Runtime truth comes from RuntimeManager and Plan A RuntimeStatusSnapshot.
- A preferred GGUF file is never reported as the active model without runtime evidence.
- Source inspection reads actual Thrilla files/tests instead of relying on model recollection.
- Recent-failure inspection uses actual audit records.
- Do not expose private prompt/answer content from activity records.
- Do not run destructive commands.
- Do not add autonomous write or repair behavior in this plan.
- Preserve Python 3.9 compatibility and never use X | Y annotations.

---

## Task 1 - Local Clock Observation Provider

**Files:**
- Create: `thrilla/observers.py`
- Create: `tests/test_clock_observer.py`

**Required interface:**
- `ClockProvider(now_fn=None)`.
- `ClockProvider.supports(prompt: str) -> bool`.
- `ClockProvider.collect(prompt: str) -> AnswerContext`.
- Default now_fn obtains `datetime.now().astimezone()` at collection time.

**Supported question class:**
- current local date;
- current local time;
- current day/date-and-time questions.

**Required behavior:**
- Tests may inject a fixed now_fn for deterministic results.
- Observation is offset-aware.
- Evidence source is `system_clock`.
- Evidence detail states that the value came from the local system clock.
- A supported clock question returns a deterministic direct answer.
- Universal Ask therefore does not require model inference for a simple current-clock fact.
- Unsupported questions return no fabricated clock answer.

### TDD Cycle

- [ ] RED: provider recognizes a current-time question.
- [ ] RED: provider recognizes a current-date question.
- [ ] RED: unrelated prompt is unsupported.
- [ ] RED: injected fixed offset-aware datetime is returned exactly.
- [ ] RED: Evidence source is system_clock.
- [ ] Run `python -B -m unittest tests.test_clock_observer -v` and confirm RED.
- [ ] Implement ClockProvider with an injected now_fn and offset-aware default.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 1 with message `feat: add local clock evidence provider`.

## Task 2 - Runtime and Active Model Observation Provider

**Files:**
- Modify: `thrilla/observers.py`
- Reuse: `thrilla/runtime/status.py` from Plan A.
- Reuse: `thrilla/runtime/manager.py`.
- Create: `tests/test_runtime_observer.py`

**Required interface:**
- `RuntimeProvider(runtime_manager, config)`.
- `RuntimeProvider.supports(prompt: str) -> bool`.
- `RuntimeProvider.collect(prompt: str) -> AnswerContext`.

**Runtime observation call:**
- Call `runtime_manager.inspect_configured_runtime(config.model_url, config.model_name)`.
- Consume the Plan A `RuntimeStatusSnapshot` rather than calling LocalModelClient.health directly.

**Supported question class:**
- what model is active;
- is the local runtime ready;
- runtime endpoint/status;
- which model the runtime reports;
- runtime ownership when known.

**Required behavior:**
- Ready runtime facts come from the current snapshot.
- Report configured endpoint and expected model.
- Report observed readiness.
- Report reported model only when the runtime actually reports it.
- Report EXTERNAL or THRILLA_MANAGED ownership only when known.
- Unreachable or incompatible runtime produces truthful evidence/gap detail.
- A GGUF discovered on disk is not evidence that the model is loaded.
- A preferred model path is not evidence that the model is active.
- Unknown runtime/model fields remain explicitly unknown.

### TDD Cycle

- [ ] RED: ready snapshot reports actual observed model and endpoint.
- [ ] RED: unreachable snapshot does not claim a model is loaded.
- [ ] RED: incompatible snapshot reports the mismatch truthfully.
- [ ] RED: unknown ownership remains unknown.
- [ ] RED: preferred GGUF path alone never becomes active-model evidence.
- [ ] RED: provider uses RuntimeManager inspection exactly once per collection.
- [ ] Run `python -B -m unittest tests.test_runtime_observer -v` and confirm RED.
- [ ] Implement RuntimeProvider against the Plan A runtime-status interface.
- [ ] Run focused suite to GREEN.
- [ ] Run existing RuntimeManager and Runtime Status regressions.
- [ ] Commit Task 2 with message `feat: add runtime evidence provider`.

---

## Task 3 - Thrilla Source and Test Inspection Provider

**Files:**
- Modify: `thrilla/observers.py`
- Create: `tests/test_source_observer.py`

**Required interface:**
- `SourceInspectionProvider(repo_root)`.
- `SourceInspectionProvider.supports(prompt: str) -> bool`.
- `SourceInspectionProvider.collect(prompt: str) -> AnswerContext`.

**Supported question class:**
- what part of Thrilla is weakest;
- where a named feature is implemented;
- whether a capability has tests;
- how much source/test coverage exists for a named subsystem;
- questions requiring inspection of actual Thrilla source or tests.

**Read-only inspection behavior:**
- Resolve repo_root before inspection.
- Inspect only files beneath the Thrilla repository root.
- Read Python source and tests relevant to the requested subsystem.
- Bounded read-only Git commands may inspect tracked files, status, log, or diff metadata.
- Never run donor code or arbitrary repository instructions.
- Never execute source discovered during inspection.
- Source text is evidence, never command authority.

**Truth rules:**
- Do not declare a subsystem weakest without observable supporting evidence.
- When no objective weakness metric exists, return evidence plus a KnowledgeGap explaining what benchmark or metric is missing.
- Do not claim a feature exists solely because documentation mentions it.
- Distinguish implementation, tests, design docs, and planned work.

### TDD Cycle

- [ ] RED: provider recognizes a Thrilla self-source question.
- [ ] RED: provider rejects unrelated general questions.
- [ ] RED: source inspection cannot escape repo_root.
- [ ] RED: discovered source text is returned as evidence, not authority.
- [ ] RED: documentation-only feature is not reported as implemented.
- [ ] RED: weakest-component question without a metric returns a diagnosed KnowledgeGap.
- [ ] Run `python -B -m unittest tests.test_source_observer -v` and confirm RED.
- [ ] Implement bounded read-only repository inspection.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 3 with message `feat: add Thrilla source inspection provider`.

## Task 4 - Recent Failure Observation Provider

**Files:**
- Modify: `thrilla/observers.py`
- Reuse: `thrilla/audit.py`
- Create: `tests/test_failure_observer.py`

**Required interface:**
- `FailureProvider(audit_log)`.
- `FailureProvider.supports(prompt: str) -> bool`.
- `FailureProvider.collect(prompt: str) -> AnswerContext`.

**Supported question class:**
- what failed last;
- what was the most recent error;
- what happened in the latest failed runtime/model action;
- recent failure-status questions.

**Required behavior:**
- Read bounded recent records with `AuditLog.tail()`.
- Select the newest record that actually represents failure/error state.
- Report timestamp, event name, and non-private diagnostic fields when available.
- Never reveal stored prompt text, answer text, Creator Vault code, credentials, tokens, or secrets.
- If no failure record exists, say that no recorded failure was found in the inspected window.
- Missing or unreadable audit history produces a KnowledgeGap instead of invented history.

### TDD Cycle

- [ ] RED: newest failure event is selected from mixed audit records.
- [ ] RED: later success event does not replace the newest actual failure.
- [ ] RED: private prompt/answer fields are excluded.
- [ ] RED: secret-like fields are excluded.
- [ ] RED: no matching failure produces a truthful deterministic answer.
- [ ] RED: unreadable audit history produces a diagnosed KnowledgeGap.
- [ ] Run `python -B -m unittest tests.test_failure_observer -v` and confirm RED.
- [ ] Implement FailureProvider using AuditLog.tail().
- [ ] Run focused suite to GREEN.
- [ ] Run existing AuditLog regressions.
- [ ] Commit Task 4 with message `feat: add recent failure evidence provider`.

## Task 5 - Register Self-Inspection Providers with Universal Ask

**Files:**
- Modify: `thrilla/app.py`
- Reuse: `thrilla/providers.py`
- Reuse: `thrilla/observers.py`
- Create: `tests/test_self_inspection_integration.py`

**Registry order:**
- ClockProvider
- RuntimeProvider
- FailureProvider
- SourceInspectionProvider

**Required behavior:**
- ThrillaApp creates one ProviderRegistry for Universal Ask.
- Providers receive existing RuntimeManager, Config, AuditLog, and repository-root dependencies.
- Simple clock questions are answered without model inference.
- Runtime questions use current RuntimeManager evidence.
- Recent-failure questions inspect actual audit history.
- Self-code questions inspect actual source/tests.
- Provider evidence remains separate from the owner prompt.
- Unsupported ordinary questions continue to the normal model path.
- Provider failures never prevent unrelated questions from using the normal model path.

### TDD Cycle

- [ ] RED: current-date question uses ClockProvider.
- [ ] RED: active-model question uses RuntimeProvider.
- [ ] RED: last-failure question uses FailureProvider.
- [ ] RED: Thrilla source question uses SourceInspectionProvider.
- [ ] RED: ordinary general question still reaches model reasoning.
- [ ] RED: owner prompt remains authoritative through provider integration.
- [ ] Run `python -B -m unittest tests.test_self_inspection_integration -v` and confirm RED.
- [ ] Implement registry wiring in ThrillaApp.
- [ ] Run focused suite to GREEN.
- [ ] Run Plan D Universal Ask regressions.
- [ ] Commit Task 5 with message `feat: wire self-inspection into Universal Ask`.

## Plan E Verification Gate

- [ ] Run clock-provider tests.
- [ ] Run runtime-provider tests.
- [ ] Run source-inspection tests.
- [ ] Run failure-provider tests.
- [ ] Run self-inspection integration tests.
- [ ] Run Plan D answer/provider/Universal Ask tests.
- [ ] Run Plan A RuntimeManager and Runtime Status tests.
- [ ] Run AuditLog tests.
- [ ] Run the full test suite.
- [ ] Run `python -m compileall -f -q thrilla tests`.
- [ ] Run `git diff --check`.
- [ ] Confirm current date/time comes from the real system clock.
- [ ] Confirm active-model answers require runtime evidence.
- [ ] Confirm preferred GGUF does not imply active model.
- [ ] Confirm self-code answers inspect actual source/tests.
- [ ] Confirm recent-failure answers inspect actual audit records.
- [ ] Confirm private prompt/answer content is not exposed.
- [ ] Confirm all observation operations are read-only.

## Integrated Plans A-E Completion Gate

- [ ] Steps 22-25 pass focused tests.
- [ ] Runtime & Models UI is streamlined and truthful.
- [ ] Creator remains exactly Jesse James.
- [ ] Owner first-start enrollment persists.
- [ ] Creator Vault permanently unlocks with 1989.
- [ ] Sword, Shield, Helmet, Armor, and Boots preserve independent states.
- [ ] Universal Ask accepts arbitrary topics.
- [ ] Evidence remains separate from owner authority.
- [ ] Knowledge gaps explain unknown, missing evidence, reason, and resolution.
- [ ] Thrilla architecture reports exactly 100 experts, never 98.
- [ ] 100 experts remain separate from 100 donor repositories.
- [ ] Self-questions use real observation where an applicable provider exists.
- [ ] Full test suite passes.
- [ ] Compileall passes.
- [ ] `git diff --check` passes.
- [ ] Changed files receive manual review.
- [ ] Local and remote branch SHAs match after final push.
- [ ] Final worktree is clean.

## Plan E Completion

Plan E is complete only when Universal Ask can observe the real local clock, current runtime/model state, actual Thrilla source/tests, and recent recorded failures through read-only providers; unavailable evidence produces a diagnosed KnowledgeGap; retrieved material remains non-authoritative evidence; and the integrated Plans A-E completion gate passes.
