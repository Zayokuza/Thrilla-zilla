# Stage 3 Local Runtime Manager Design

Status: **APPROVED DESIGN — implementation next**

## Normative base

The detailed architecture and 35-step implementation sequence in:

    docs/STAGE3-LOCAL-MODEL-RUNTIME-MAP.md

remain the normative Stage-3 specification.

This document records the final implementation decisions approved before
coding begins.

## Completion target

Stage 3 will be completed to **100%**, not stopped around 50%.

Completion requires:

- full automated regression suite;
- real Android/Termux lifecycle proof;
- real Windows lifecycle proof.

Stage 3 is not complete until both target platforms pass.

## Architecture

Runtime lifecycle remains separate from the existing HTTP inference client.

    Ask Thrilla
        |
        v
    RuntimeManager.ensure_ready()
        |
        +-- Universal Limit Control
        +-- runtime discovery
        +-- GGUF discovery
        +-- model selection
        +-- endpoint/port inspection
        +-- ownership detection
        +-- process lifecycle
        +-- readiness
        +-- recovery
        |
        v
    LocalModelClient
        |
        v
    llama-server

Planned modules:

    thrilla/limits.py

    thrilla/runtime/
        __init__.py
        models.py
        state.py
        discovery.py
        policy.py
        command.py
        ports.py
        process.py
        health.py
        manager.py

## Universal Limit Control

Modes:

    ON
    AUTO
    OFF

Global default:

    AUTO

Every Thrilla-created restriction must register before use.

Existing limits will be migrated without silently changing current behavior.

External OS, hardware, model and kernel restrictions are reported as:

    EXTERNAL CONSTRAINT

They are not represented as user-toggleable Thrilla limits.

## Managed startup policy

For automatic local-runtime startup:

    AUTO
        lazily start when a request first requires inference

    ON
        proactively ensure a Thrilla-managed runtime is available

    OFF
        Thrilla does not automatically start a runtime

A compatible externally started local server may be reused.

Thrilla must never kill an externally owned server.

## Process ownership

Ownership is explicit:

    EXTERNAL
    THRILLA_MANAGED

Only a verified THRILLA_MANAGED process may be stopped or restarted by
Thrilla.

## Model discovery

Search user/configured model roots, including known phone locations such as:

    ~/models
    ~/Zayo/models

Do not automatically treat donor source trees as model libraries.

GGUF inventory distinguishes:

- chat/primary;
- coding;
- planner;
- embedding;
- alternate;
- unknown;
- test/vocabulary artifacts.

Test/vocabulary GGUF files must not become normal chat candidates.

## Readiness

A process existing is not sufficient for READY.

Required proof:

    service/process exists
        ->
    port accepts connections
        ->
    /v1/models responds
        ->
    expected model/alias is visible
        ->
    READY

Optional tiny inference proof may be used where appropriate.

## Integration

Before inference:

    RuntimeManager.ensure_ready()

On success, the model client receives the selected endpoint and model alias.

On failure, Thrilla reports the blocker and does not claim the request
completed.

## Runtime behavior

Stage 3 includes:

- deterministic llama-server command construction;
- port conflict detection;
- compatible external-server reuse;
- managed subprocess startup;
- startup log capture;
- readiness polling;
- clean managed shutdown;
- orphan reconciliation;
- runtime status UI;
- model-selection UI;
- ON/AUTO/OFF policy UI;
- AUTO resource selection;
- crash detection;
- controlled retry/recovery;
- request cancellation;
- streaming output.

## Android / Termux proof

The real phone must prove at minimum:

1. llama-server discovery;
2. GGUF discovery;
3. deterministic model selection;
4. automatic startup with no listener;
5. /v1/models readiness;
6. real local response to `hey`;
7. cancellation;
8. clean managed stop;
9. restart;
10. crash detection;
11. controlled recovery;
12. external-server detection without killing it;
13. repeated lifecycle operations;
14. failure injection;
15. memory-pressure behavior;
16. Stage-1 and Stage-2 regressions remain green.

## Windows proof

The same lifecycle contract must pass on the real Windows target.

Platform-specific process handling may differ, but runtime ownership,
readiness, policy and manager interfaces remain shared.

## Development process

Strict TDD:

    failing test
        ->
    confirm RED
        ->
    minimal implementation
        ->
    confirm GREEN
        ->
    full regression
        ->
    checkpoint commit

No production behavior is added without a failing test first.

## Implementation sequence

Follow the existing 35-step Stage-3 map in order.

The first implementation checkpoint is:

1. Universal Limit Control primitives;
2. existing-limit migration;
3. registry enforcement;
4. runtime state machine;
5. ModelCandidate.

No partial Stage-3 implementation will be labeled complete.
