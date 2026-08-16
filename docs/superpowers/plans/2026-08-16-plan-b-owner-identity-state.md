# Owner Identity and Persistent State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and strict RED -> GREEN TDD.

**Goal:** Give every Thrilla installation a persistent owner while permanently identifying Jesse James as Thrilla creator.

**Architecture:** Immutable creator identity lives in a focused identity module. Mutable installation-owner state is persisted through Config. First live startup asks for the owner only when no owner is stored.

**Tech Stack:** Python 3.9-compatible standard library, dataclasses, unittest, existing Config and AuditLog.

## Global Constraints

- Creator is always exactly `Jesse James`.
- Creator and owner are separate concepts.
- Existing configuration files remain loadable.
- Missing new fields receive safe defaults.
- Direct local Thrilla UI input is the authoritative command source.
- Owner name alone is not described as cryptographic authentication.
- Do not duplicate creator-name string literals throughout the UI.

---

## Task 1 - Identity Domain

**Files:**
- Create: `thrilla/identity.py`
- Create: `tests/test_identity.py`

**Required interface:**
- `CREATOR_NAME = "Jesse James"`
- Immutable `ThrillaIdentity` with `creator` and `owner` fields.
- `identity_for(owner_name)` always uses the permanent creator constant.

**Required behavior:**
- Caller cannot replace the creator through installation owner state.
- Empty owner is valid before first-start enrollment.
- Different installation owners never alter creator identity.

### TDD Cycle

- [ ] RED: identity_for("Alice") reports creator Jesse James and owner Alice.
- [ ] RED: identity_for("Bob") still reports creator Jesse James.
- [ ] RED: creator identity is sourced from one permanent constant.
- [ ] Run `python -B -m unittest tests.test_identity -v` and observe correct RED.
- [ ] Implement the minimal immutable identity module.
- [ ] Run focused suite to GREEN.
- [ ] Commit only `thrilla/identity.py` and `tests/test_identity.py` with message `feat: add Thrilla creator identity`.

## Task 2 - Owner Config Migration

**Files:**
- Modify: `thrilla/config.py`
- Create: `tests/test_owner_config.py`
- Extend existing config regression tests where needed.

**Required interface:**
- Add `owner_name: str = ""` to Config.

**Required behavior:**
- Old configuration with no owner_name loads successfully.
- New installation defaults to empty owner_name.
- Save and reload preserve the owner exactly.
- Adding owner state must not alter existing runtime, model, history, or Limit Control settings.

### TDD Cycle

- [ ] RED: old config JSON without owner_name loads with empty owner.
- [ ] RED: owner_name survives save and reload.
- [ ] RED: existing config fields survive migration unchanged.
- [ ] Run `python -B -m unittest tests.test_owner_config -v` and observe correct RED.
- [ ] Implement the minimum backward-compatible Config change.
- [ ] Run focused suite to GREEN.
- [ ] Run existing config regressions.
- [ ] Commit Task 2 with message `feat: persist Thrilla owner identity`.

---

## Task 3 - First Live Startup Owner Enrollment

**Files:**
- Modify: `thrilla/app.py`
- Create: `tests/test_owner_startup.py`

**Required interface:**
- Add `ThrillaApp.ensure_owner_profile()`.
- `run()` calls it before the first normal main-menu render.

**Required behavior:**
- If owner_name is empty, Thrilla asks exactly `What is your name?`.
- Leading/trailing whitespace is removed before saving.
- Empty input is rejected and the prompt repeats.
- A stored owner skips enrollment on later launches.
- Successful enrollment saves Config immediately.
- Successful enrollment writes `owner_profile_created` to AuditLog.
- Enrollment must not expose or modify unrelated configuration.

### TDD Cycle

- [ ] RED: missing owner causes first-start name prompt.
- [ ] RED: empty name repeats the prompt.
- [ ] RED: valid name is trimmed and persisted.
- [ ] RED: stored owner bypasses the prompt on the next startup.
- [ ] RED: successful enrollment records owner_profile_created.
- [ ] Run `python -B -m unittest tests.test_owner_startup -v` and confirm RED.
- [ ] Implement the minimum enrollment flow.
- [ ] Run focused suite to GREEN.
- [ ] Run existing app startup regressions.
- [ ] Commit Task 3 with message `feat: add first-start owner enrollment`.

## Task 4 - Creator and About Invariant

**Files:**
- Modify: `thrilla/app.py`
- Reuse: `thrilla/identity.py`
- Create: `tests/test_creator_identity_ui.py`

**Required behavior:**
- About identifies the creator as Jesse James.
- About may show the local owner separately when one exists.
- Changing owner_name never changes creator identity.
- UI reads creator identity from `CREATOR_NAME` rather than duplicating independent literals.
- Thrilla must not describe owner-name enrollment as secure authentication.

### TDD Cycle

- [ ] RED: About reports creator Jesse James.
- [ ] RED: owner and creator can have different names.
- [ ] RED: changing owner does not alter creator output.
- [ ] Implement the minimum UI integration.
- [ ] Run focused suite to GREEN.
- [ ] Run About/app regressions.
- [ ] Commit Task 4 with message `feat: expose creator and owner identity`.

## Task 5 - Owner Authority Boundary

**Files:**
- Reuse: `thrilla/identity.py`
- Modify or create the narrow request-context boundary used by Universal Ask in Plan D.
- Create: `tests/test_owner_authority_identity.py`

**Required behavior:**
- Direct text entered through Thrilla trusted local UI is tagged as owner input.
- Retrieved web, file, repository, model, tool, and external-AI content is never tagged as owner authority.
- This plan defines source identity only; enforcement in answer construction is completed in Plan D.

### TDD Cycle

- [ ] RED: direct UI request is classified as owner input.
- [ ] RED: retrieved content is classified as non-authoritative evidence.
- [ ] Implement the minimum source classification boundary.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 5 with message `feat: classify owner command authority`.

## Plan B Verification Gate

- [ ] Run identity tests.
- [ ] Run owner-config migration tests.
- [ ] Run first-start enrollment tests.
- [ ] Run creator/About tests.
- [ ] Run owner-authority source tests.
- [ ] Run all existing Config tests.
- [ ] Run existing app and CLI tests.
- [ ] Run the full test suite.
- [ ] Run `python -m compileall -f -q thrilla tests`.
- [ ] Run `git diff --check`.
- [ ] Confirm old Config files still load.
- [ ] Confirm creator remains exactly Jesse James.
- [ ] Confirm owner enrollment happens only when owner_name is empty.

## Plan B Completion

Plan B is complete only when creator identity is immutable, installation owner state is backward-compatible and persistent, first live startup enrolls the owner once, About distinguishes creator from owner, authority source classification is test-covered, and all regressions pass.
