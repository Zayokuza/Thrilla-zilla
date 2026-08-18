# Stage 3 Coding + Rollback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Thrilla a bounded autonomous repository-repair path that inspects candidate files, asks the local model for structured edits, checkpoints targets, verifies changes, critic-reviews the result, and automatically rolls back failures.

**Architecture:** `thrilla/checkpoints.py` owns durable file snapshots outside the repository. `thrilla/coding.py` owns repository inspection, model-plan parsing, bounded text writes, deterministic verification, critic review, and rollback. `thrilla/app.py` exposes `/repair <goal>` plus narrow natural-language self-repair intent.

**Tech Stack:** Python 3 standard library, unittest, git CLI, existing Thrilla local model/runtime.

**Spec:** Active six-stage Thrilla v1 roadmap; Stage 3 = coding + rollback.

## Global Constraints

- Preserve Stages 1-2 behavior.
- Never edit `.git`.
- Model output proposes text edits only; it never chooses verification commands.
- Checkpoint every target before write.
- Use `shell=False` for verification.
- Roll back automatically on verification or critic failure.
- Do not auto-commit model-generated repairs.
- Installer commits Stage 3 only after all regression tests pass.

---

### Task 1: Durable checkpoints

**Files:** Create `thrilla/checkpoints.py`; test `tests/test_checkpoints.py`.

- [ ] Write failing checkpoint tests.
- [ ] Confirm RED.
- [ ] Implement targeted snapshots under `state_root/checkpoints/coding`.
- [ ] Verify existing files restore and new files are removed.

### Task 2: Verified coding workflow

**Files:** Create `thrilla/coding.py`; test `tests/test_coding_workflow.py`.

- [ ] Write failing success, rollback, and model-boundary tests.
- [ ] Confirm RED.
- [ ] Implement repository path validation and edit budgets.
- [ ] Implement atomic text writes after checkpoint creation.
- [ ] Run fixed verification with `shell=False`.
- [ ] Critic-review verification plus `git diff --check`.
- [ ] Roll back on failure.
- [ ] Restrict model edits to inspected candidate files.

### Task 3: App integration

**Files:** Modify `thrilla/app.py`; test `tests/test_stage3_app_integration.py` and `tests/test_stage3_command_surface.py`.

- [ ] Confirm app tests fail before integration.
- [ ] Instantiate coding agent in constructor and refresh.
- [ ] Add `/repair <goal>` and narrow “fix yourself” handling.
- [ ] Audit outcome and surface checkpoint/rollback state.
- [ ] Update stale About capability text.

### Task 4: Acceptance

- [ ] Run focused Stage-3 tests.
- [ ] Prove failed temp-repo edit rolls back.
- [ ] Run compileall.
- [ ] Run full unittest discovery.
- [ ] Run `git diff --check`.
- [ ] Commit only after all checks pass.
