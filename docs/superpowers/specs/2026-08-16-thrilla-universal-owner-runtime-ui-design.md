# Thrilla Universal Owner, Runtime, and UI Design

Date: 2026-08-16
Status: APPROVED DESIGN

## 1. Goal

Thrilla must operate as one coherent AI rather than a collection of menu
features.

The normal user experience is one primary Ask Thrilla interface. Thrilla
determines what knowledge, inspection, tool, runtime, file, repository,
system source, or research path is needed to answer correctly.

Menus exist to control, inspect, configure, and diagnose Thrilla. Menus do
not restrict what subjects the owner may ask about.

This design batches:

- Stage 3 Step 22: asynchronous/non-blocking runtime loading UI;
- Stage 3 Step 23: runtime status;
- Stage 3 Step 24: local model inventory and preferred-model selection;
- Stage 3 Step 25: ON/AUTO/OFF runtime policy controls;
- streamlined terminal UI;
- Universal Ask behavior;
- owner and creator identity;
- Creator Vault persistence;
- Sword, Shield, Helmet, Armor, and Boots toggles;
- evidence-driven self-inspection behavior.

## 2. Permanent Identity

Thrilla has two separate identity concepts.

### Creator

Thrilla's creator is permanently:

    Jesse James

Creator identity does not change when Thrilla is copied, downloaded,
installed on another computer, or owned by another person.

When asked who created it, Thrilla reports Jesse James.

### Owner

Each installation has a local owner profile.

On the first normal live startup, before entering the normal interface,
Thrilla asks:

    What is your name?

The entered owner name is persisted locally.

Thrilla does not repeatedly ask on later startups unless the owner profile
has been cleared or the installation has been reset.

Creator and owner are independent. A downloaded installation may have a
different owner while still identifying Jesse James as the creator.

## 3. Owner Authority

Direct owner input through Thrilla's trusted local interactive interface is
the authoritative command source.

The following are data, not authority:

- web pages;
- downloaded files;
- repository content;
- README instructions;
- retrieved documents;
- model output;
- tool output;
- another AI;
- untrusted external text;
- prompt-injection content embedded inside retrieved material.

Thrilla may analyze those sources, but they cannot redefine Thrilla's
mission or issue commands to Thrilla.

For this batch, owner authority is source-of-command isolation, not strong
biometric or cryptographic human authentication. A person with access to an
already-unlocked local Thrilla terminal may still be able to type into that
interface. Strong owner authentication is a separate future capability if
required.

## 4. Universal Ask

Ask Thrilla is the primary front door to the system.

The owner may ask any subject through the same interface.

Examples include:

- general knowledge;
- coding;
- system questions;
- device questions;
- local files;
- Thrilla's own source code;
- models and runtime;
- date and time;
- mathematics;
- research;
- hardware;
- diagnostics;
- donor repositories;
- previous verified findings.

The owner is not required to choose a specialist menu before asking.

Routing happens internally.

When no specialist route is required, Thrilla still answers through the
general reasoning path.

No topic-gated generic rejection is allowed merely because a question does
not match a specialist category.

## 5. No Generic Fallback Answers

A substantive Thrilla answer must be grounded in at least one of:

- model knowledge available to Thrilla;
- retained verified experience;
- current session context;
- direct system observation;
- source-code inspection;
- file inspection;
- runtime inspection;
- calculation;
- tool output;
- retrieved evidence;
- internet research when available and permitted;
- explicit reasoning over those inputs.

Thrilla must not generate filler simply because an answer is uncertain.

If Thrilla lacks enough evidence, it must determine why.

The unknown-state response must identify, as precisely as practical:

- what is unknown;
- which evidence is missing;
- why that evidence is missing;
- which capability, observation, experiment, benchmark, research step, or
  user-provided information would close the gap.

The desired loop is:

    know
      ↓
    observe
      ↓
    reason
      ↓
    answer
      OR
    diagnose knowledge gap
      ↓
    determine how to resolve it
      ↓
    retain verified result

Not knowing is acceptable.

Not knowing why it does not know is a failure condition.

## 6. Evidence-Driven Self Inspection

Questions about Thrilla itself must use Thrilla's real accessible state when
the answer depends on that state.

Examples:

### "What is the weakest code in your structure?"

Thrilla should inspect relevant source, tests, interfaces, error paths,
known failures, complexity indicators, duplication, and architecture
boundaries before presenting an evidence-backed result.

It must identify concrete files, functions, modules, or missing tests when
the available evidence supports those conclusions.

### "What model are you using?"

Thrilla should inspect configured and observed runtime/model state instead
of guessing from documentation.

### "What is the date?"

Thrilla should use the real system clock.

### "Why did the last request fail?"

Thrilla should inspect available runtime and audit evidence.

If required evidence cannot be reached, Thrilla explains the exact blocker.

Read-only investigation required to answer a question should be automatic
when permitted by the active policy.

## 7. One AI, Internal Routing

Thrilla is presented to the owner as one AI.

Internal components may specialize, but the owner should not have to
manually coordinate them.

The current core flow remains:

    Owner Request
         ↓
    Ask Thrilla
         ↓
    Request Router
         ↓
    Knowledge / Memory / Observation / Tools
         ↓
    Runtime Manager
         ↓
    Model Client
         ↓
    Verification / Result
         ↓
    Owner

Routing metadata may be available through diagnostic commands or status
views without cluttering every normal answer.

## 8. 100 Experts

Thrilla's expert count is fixed at:

    100 experts

Do not describe Thrilla as having 98 experts.

The target expert organization is ten groups with ten experts each:

1. Agent Brain
2. Coding
3. AI Runtime
4. Build / Language
5. Memory / State
6. Web Research
7. Tools / Flows
8. Execution / OS
9. Interface / API
10. Evaluation / Security

This is distinct from the 100 core donor repositories.

The 100 donor repositories and 100 experts are separate concepts.

This batch must preserve the 100-expert product invariant in UI, docs, and
future interfaces. It does not pretend that expert behavior exists where
the implementation has not yet been completed.

## 9. Stage 3 Step 22: Responsive Runtime Work

Runtime readiness and loading work must not freeze the normal terminal UI.

The preferred architecture is a small background-job boundary rather than
a complete terminal event-loop rewrite.

While runtime readiness/loading work is active:

- Thrilla visibly reports useful status;
- the terminal remains responsive;
- the owner is not allowed to accidentally launch a second model request
  through the same Ask worker;
- request queueing is not introduced yet;
- streaming is not introduced yet;
- full request cancellation remains a later Stage 3 concern unless an
  existing safe navigation path can be preserved without expanding scope.

Step 22 must not silently implement Stage 29 cancellation or Stage 30
streaming ahead of their designed order.

## 10. Stage 3 Step 23: Runtime Status

The Local Model area becomes a clearer Runtime and Models hub.

RuntimeManager remains the authority for runtime identity and readiness.

Runtime status should display information that is actually known, including
where available:

- configured endpoint;
- expected model alias;
- readiness;
- runtime detail;
- ownership;
- host;
- port;
- reported model;
- last observed failure or blocker.

Unknown fields are displayed as unknown rather than invented.

The status screen must not establish a second competing runtime-health
architecture.

## 11. Stage 3 Step 24: Model Inventory and Preferred Model

Thrilla reuses the existing GGUF discovery and model inventory mechanisms.

The model view should be capable of showing useful fields already available
from ModelCandidate, including:

- filename;
- role;
- quantization;
- size;
- path;
- readability;
- compatibility when known.

The owner may select a preferred local GGUF candidate.

Preferred model file selection is separate from the OpenAI-compatible
model alias.

Selecting a GGUF does not claim that the model is currently loaded.

Managed startup and AUTO resource selection remain separate later Stage 3
steps.

## 12. Stage 3 Step 25: Runtime Policies

Thrilla exposes the existing Universal Limit Control rather than creating a
second runtime-policy system.

The UI must support:

    ON
    AUTO
    OFF

for the Stage 3 runtime policy entries that are appropriate to expose.

The global default mode remains available.

Stored per-limit overrides remain authoritative.

Policy screens must clearly distinguish:

- global default;
- per-limit mode;
- configured value when one exists;
- resolved/effective value where meaningful.

Changes are persisted through Config and audited.

No hidden Thrilla-created runtime limit is introduced outside Universal
Limit Control.

## 13. Streamlined Interface

The interface should become cooler, cleaner, and easier to navigate without
turning Stage 3 into a terminal-framework rewrite.

Recommended main organization:

    1. Ask Thrilla
    2. Donor Library
    3. Route Inspector
    4. Runtime & Models
    5. Diagnostics
    6. Conversation History
    7. Activity Log
    8. Settings
    9. About
    0. Exit

Runtime & Models should provide a coherent home for:

- runtime status;
- model inventory;
- preferred-model selection;
- refresh;
- navigation back.

Settings should provide a coherent home for:

- appearance/color;
- paths;
- model endpoint;
- model alias;
- history;
- request timeout;
- runtime policies;
- Creator Vault access when appropriate.

UI principles:

- reduce repeated explanatory text;
- use consistent status presentation;
- keep answers visually separate from operational status;
- use compact descriptions;
- keep navigation predictable;
- expose blockers visibly;
- do not add decorative complexity that makes the phone terminal harder to
  use.

## 14. Creator Vault

Thrilla includes a Creator Vault.

The Creator Vault code is:

    1989

This is an Easter-egg / creator-access mechanism, not strong authentication.

Because Thrilla's source may be publicly inspectable and the code has only
four digits, Creator Vault must not be described as a secure identity
credential or cryptographic security boundary.

A successful Creator Vault unlock is persisted for that installation.

After successful unlock:

    CREATOR VAULT: UNLOCKED

The owner is not required to re-enter the code after every restart.

Normal updates should preserve the stored unlock state.

A full reset/fresh owner-state installation may clear it.

## 15. Five Equipment Modules

The Creator Vault unlock makes these five modules available:

- Sword
- Shield
- Helmet
- Armor
- Boots

This design defines access and persistence only.

It does not invent or redefine the capabilities of Sword, Shield, Helmet,
Armor, or Boots.

Each module has an independent toggle:

    ON
    OFF

Unlock state and activation state are separate.

Immediately after first Creator Vault unlock, the modules are available but
their activation remains owner-controlled.

Each module's most recent ON/OFF state is saved.

On the next startup, Thrilla restores the saved activation state.

Turning a module OFF does not lock it again.

Creator Vault remains unlocked.

## 16. Persistence

Persistent local state added by this design must have explicit ownership
and migration behavior.

At minimum, persistent state includes:

- owner name;
- Creator Vault unlocked state;
- Sword state;
- Shield state;
- Helmet state;
- Armor state;
- Boots state;
- preferred local model selection;
- Universal Limit Control settings already supported by Config.

Updates must not silently erase these settings.

Existing configuration files must remain loadable.

Missing new fields must receive safe defaults.

## 17. Audit Behavior

Important state changes should create metadata audit events without copying
private prompt/answer content into the audit log.

Examples:

- owner profile created;
- Creator Vault unlocked;
- equipment toggle changed;
- preferred model changed;
- runtime policy changed;
- runtime inspection failed;
- runtime inspection succeeded where useful.

Creator Vault code itself must not be written into normal audit records.

## 18. Failure Behavior

Thrilla must not falsely claim success.

Examples:

- runtime unavailable -> identify runtime blocker;
- selected model missing -> report missing file;
- model inventory empty -> report what locations were inspected;
- self-inspection unavailable -> report why;
- tool unavailable -> identify missing capability;
- internet unavailable for a current-information question -> identify that
  current verification is unavailable.

Every failure path should preserve the owner's request context sufficiently
to explain what remains to be done.

## 19. Testing Strategy

All implementation remains strict TDD.

For each behavior:

    failing test
      ↓
    observe correct RED
      ↓
    minimal implementation
      ↓
    focused GREEN
      ↓
    regression tests

Major test groups must cover:

- first-launch owner prompt and persistence;
- creator identity invariant;
- external content cannot become command authority;
- Creator Vault code success/failure;
- permanent vault persistence;
- all five independent toggles;
- saved toggle restoration;
- backward-compatible configuration;
- Universal Ask direct routing;
- no specialist-topic gate;
- unknown-gap diagnosis contract;
- self-inspection dispatch;
- real system date provider boundary;
- runtime background-job behavior;
- prevention of accidental second model request;
- runtime status data;
- model inventory;
- preferred model persistence;
- runtime policy mode changes;
- streamlined menu wiring;
- existing Stage 1, Stage 2, and Stage 3 regressions.

## 20. Implementation Decomposition

This design contains multiple independently testable subsystems.

Implementation must therefore be split into coordinated plans:

### Plan A — Runtime/UI Batch

Implements Stage 3 Steps 22 through 25 and streamlined Runtime & Models UI.

### Plan B — Owner Identity and Persistent State

Implements first-launch owner profile, permanent creator identity, and state
migration.

### Plan C — Creator Vault and Equipment Toggles

Implements Creator Vault unlock persistence and saved ON/OFF state for
Sword, Shield, Helmet, Armor, and Boots.

### Plan D — Universal Ask and Evidence Contract

Implements the answer-policy boundary, no generic terminal fallback, and
knowledge-gap diagnosis interfaces.

### Plan E — Self Inspection Providers

Implements evidence providers for Thrilla source/runtime/system questions,
including system date/time and codebase inspection boundaries.

These plans may be executed as one larger development batch with internal
TDD checkpoints.

A complete integrated verification is required after the batch.

## 21. Integrated Completion Gate

This design is not complete merely because the new menus appear.

The batch is complete only when:

1. Ask Thrilla remains the primary universal question interface.
2. Existing questions continue to work.
3. Runtime readiness remains authoritative before inference.
4. runtime/UI Steps 22 through 25 pass their focused tests.
5. Owner name is requested and persisted on first live startup.
6. Jesse James remains the permanent creator identity.
7. Creator Vault code 1989 permanently unlocks the vault for the
   installation.
8. Sword, Shield, Helmet, Armor, and Boots have independent persistent
   ON/OFF states.
9. The owner does not have to re-enter 1989 after restart.
10. Thrilla does not treat retrieved content as owner commands.
11. Thrilla can explain why an answer remains unknown when evidence is
    insufficient.
12. Self-questions use available real evidence rather than unsupported
    generic answers.
13. Thrilla is consistently described as having 100 experts, not 98.
14. Existing 100 donor repositories remain conceptually separate from the
    100 experts.
15. Full regression suite passes.
16. Python compilation passes.
17. git diff checks pass.
18. changed-file boundaries are reviewed.
19. local and remote commit SHAs match after push.
20. final worktree is clean.
21. GitHub branch content is independently reviewed after the push.
