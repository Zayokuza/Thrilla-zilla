# Creator Vault and Equipment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and strict RED -> GREEN TDD.

**Goal:** Add permanent Creator Vault unlock and persistent ON/OFF controls for Sword, Shield, Helmet, Armor, and Boots.

**Architecture:** Keep vault/equipment logic in a focused equipment module and persistent installation state in Config. Unlock and activation are completely separate.

**Tech Stack:** Python 3.9-compatible standard library, unittest, existing Config and AuditLog.

## Global Constraints

- Creator Vault code is exactly `1989`.
- The code is an access/easter-egg mechanism, not strong authentication.
- Never write the entered Creator Vault code to AuditLog.
- Successful unlock is permanent for the installation.
- Updates must preserve unlock state.
- Sword, Shield, Helmet, Armor, and Boots each have independent ON/OFF state.
- All five default OFF before the owner explicitly activates them.
- Turning equipment OFF never relocks the Creator Vault.
- Do not define or invent equipment capabilities in this plan.

---

## Task 1 - Equipment Domain

**Files:**
- Create: `thrilla/equipment.py`
- Create: `tests/test_equipment.py`

**Required interface:**
- `EQUIPMENT_NAMES = ("sword", "shield", "helmet", "armor", "boots")`
- `verify_creator_code(value: str) -> bool`
- `normalized_equipment_state(raw) -> Dict[str, bool]`

**Required behavior:**
- `verify_creator_code("1989")` returns True.
- Any other value returns False.
- Normalized state always contains exactly all five known equipment names.
- Missing equipment defaults OFF.
- Unknown keys are ignored.
- Saved True/False values are preserved.

### TDD Cycle

- [ ] RED: 1989 succeeds.
- [ ] RED: incorrect code fails.
- [ ] RED: empty state produces five OFF entries.
- [ ] RED: mixed state preserves each independent toggle.
- [ ] RED: unknown equipment keys are discarded.
- [ ] Run `python -B -m unittest tests.test_equipment -v` and confirm RED.
- [ ] Implement the minimum equipment domain.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 1 with message `feat: add Creator Vault equipment domain`.

## Task 2 - Persistent Vault and Equipment State

**Files:**
- Modify: `thrilla/config.py`
- Create: `tests/test_creator_vault_config.py`

**Required Config fields:**
- `creator_vault_unlocked: bool = False`
- `equipment_states: Dict[str, bool]`

**Required behavior:**
- Existing config files without these fields continue to load.
- New installations begin locked.
- All five equipment toggles begin OFF.
- Unlock survives save, shutdown, and reload.
- Mixed equipment states survive save and reload exactly.
- Missing keys receive OFF defaults.
- Unknown saved keys do not become equipment modules.

### TDD Cycle

- [ ] RED: old config loads locked with five OFF states.
- [ ] RED: unlocked state survives reload.
- [ ] RED: Sword/Shield/Helmet/Armor/Boots mixed state survives reload.
- [ ] RED: missing and unknown keys normalize correctly.
- [ ] Run `python -B -m unittest tests.test_creator_vault_config -v` and confirm RED.
- [ ] Implement backward-compatible Config persistence.
- [ ] Run focused suite to GREEN.
- [ ] Run existing Config regressions.
- [ ] Commit Task 2 with message `feat: persist Creator Vault state`.

---

## Task 3 - Creator Vault UI and Permanent Unlock

**Files:**
- Modify: `thrilla/app.py`
- Reuse: `thrilla/equipment.py`
- Create: `tests/test_creator_vault_ui.py`

**Settings change:**
- Add `Creator Vault` entry.

**Locked behavior:**
- Show `CREATOR VAULT: LOCKED`.
- Ask for the Creator Vault code only inside the vault flow.
- Incorrect code leaves the vault locked.
- Correct code sets `creator_vault_unlocked=True` and saves immediately.
- Correct unlock writes `creator_vault_unlocked` audit metadata.
- The entered code itself is never included in audit fields.

**Unlocked behavior:**
- Show `CREATOR VAULT: UNLOCKED`.
- Do not ask for 1989 again after successful persisted unlock.
- Unlock survives normal restart and update.

### TDD Cycle

- [ ] RED: locked screen is shown before unlock.
- [ ] RED: wrong code leaves vault locked.
- [ ] RED: 1989 unlocks and persists.
- [ ] RED: audit event exists without the code value.
- [ ] RED: already-unlocked installation does not request the code again.
- [ ] Run `python -B -m unittest tests.test_creator_vault_ui -v` and confirm RED.
- [ ] Implement the minimum vault UI flow.
- [ ] Run focused suite to GREEN.
- [ ] Run existing Settings regressions.
- [ ] Commit Task 3 with message `feat: add permanent Creator Vault unlock`.

## Task 4 - Five Independent Equipment Toggles

**Files:**
- Modify: `thrilla/app.py`
- Reuse: `thrilla/equipment.py`
- Extend: `tests/test_creator_vault_ui.py`

**Unlocked equipment menu:**
- Sword - ON/OFF
- Shield - ON/OFF
- Helmet - ON/OFF
- Armor - ON/OFF
- Boots - ON/OFF

**Required behavior:**
- Equipment controls are unavailable while the vault is locked.
- Each toggle changes only its selected module.
- Toggling one module never changes another.
- Turning a module OFF does not lock it.
- Each change saves Config immediately.
- Each change writes an `equipment_toggle_changed` audit event containing equipment name and new state.
- No equipment capability behavior is implemented in this plan.

### TDD Cycle

- [ ] RED: locked vault cannot toggle equipment.
- [ ] RED: Sword toggles independently.
- [ ] RED: Shield toggles independently.
- [ ] RED: Helmet toggles independently.
- [ ] RED: Armor toggles independently.
- [ ] RED: Boots toggles independently.
- [ ] RED: mixed states remain independent.
- [ ] RED: toggle audit records name and state only.
- [ ] Implement minimal equipment controls.
- [ ] Run focused suite to GREEN.
- [ ] Commit Task 4 with message `feat: add Creator Vault equipment toggles`.

## Task 5 - Restart and Update Restoration

**Files:**
- Extend: `tests/test_creator_vault_config.py`
- Extend: `tests/test_creator_vault_ui.py`

**Required behavior:**
- Save an unlocked installation with a mixed five-module pattern.
- Reload Config into a fresh ThrillaApp instance.
- Vault remains unlocked.
- Every equipment toggle restores its exact previous value.
- No module is automatically switched ON after unlock.
- No module is automatically switched OFF after restart.

### TDD Cycle

- [ ] RED: save mixed state Sword ON, Shield OFF, Helmet ON, Armor OFF, Boots ON.
- [ ] RED: fresh reload restores that exact pattern.
- [ ] RED: restart never asks for 1989 again after unlock.
- [ ] RED: turning every module OFF still leaves vault unlocked.
- [ ] Implement only restoration changes required by failing tests.
- [ ] Run focused suite to GREEN.
- [ ] Run Config and app regressions.
- [ ] Commit Task 5 with message `feat: restore Creator Vault equipment state`.

## Plan C Verification Gate

- [ ] Run equipment-domain tests.
- [ ] Run vault Config migration tests.
- [ ] Run vault UI tests.
- [ ] Run restart/restoration tests.
- [ ] Run existing Config tests.
- [ ] Run existing Settings/app tests.
- [ ] Run the full test suite.
- [ ] Run `python -m compileall -f -q thrilla tests`.
- [ ] Run `git diff --check`.
- [ ] Confirm code 1989 is never written to normal audit records.
- [ ] Confirm all five modules exist: Sword, Shield, Helmet, Armor, Boots.
- [ ] Confirm all five have independent persistent ON/OFF state.
- [ ] Confirm permanent unlock and toggle state are separate.
- [ ] Confirm this plan does not invent module capabilities.

## Plan C Completion

Plan C is complete only when code 1989 permanently unlocks the Creator Vault for the installation, Sword/Shield/Helmet/Armor/Boots each have independent persistent ON/OFF state, restart restores the exact last state, OFF never relocks the vault, audit logs exclude the entered code, and all regressions pass.
