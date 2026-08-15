# Stage 3 Step 21 — Ask Runtime Readiness Design

## Status

APPROVED DESIGN

Step 21 connects Ask Thrilla to the Runtime Manager readiness boundary
before inference.

This step does not yet implement automatic managed-runtime startup,
model selection, asynchronous loading UI, streaming, cancellation,
resource selection, crash recovery, or model switching.

Those remain later Stage-3 steps.

## Goal

An Ask Thrilla request must not call model inference until the configured
runtime has been inspected and proven reusable for the expected model.

Current direct flow:

    Ask Thrilla
        |
        v
    LocalModelClient.chat()
        |
        v
    connection succeeds or fails

Step-21 flow:

    Ask Thrilla
        |
        v
    RuntimeManager
        |
        v
    inspect configured host/port
        |
        v
    GET /v1/models
        |
        v
    expected model present?
       / \
     yes  no
      |    |
      v    v
    bind   explicit blocker
      |    |
      v    X no chat call
    LocalModelClient.chat()

## Architecture

`ThrillaApp` owns one `RuntimeManager` created from the active Config.

`RuntimeManager` remains responsible for converting verified runtime
identity into a `RuntimeClientBinding`.

`LocalModelClient` remains the HTTP inference adapter and must not absorb
process-management or readiness-policy responsibilities.

The application must not duplicate `/v1/models` probing logic.

## Configured runtime inspection

Step 21 operates only on the currently configured model endpoint.

The configured chat URL is parsed into:

    host
    port

The manager inspects that local runtime using the existing runtime-health
primitives.

The expected model comes from the configured Thrilla model name.

A compatible external service may be reused if the existing-server
inspection proves it reusable.

Step 21 does not yet start a missing runtime.

Managed automatic startup remains later lifecycle integration work.

## Ask behavior

Before each real model inference request:

1. route the user request as currently implemented;
2. prepare conversation history as currently implemented;
3. ask RuntimeManager for a ready client binding;
4. if readiness succeeds, call `binding.client.chat(...)`;
5. if readiness fails, report the runtime blocker;
6. do not call model inference after readiness failure;
7. do not falsely log the user request as completed.

Navigation commands such as `/back`, `/help`, `/route`, and `/clear`
must continue to work without runtime readiness checks.

## Failure behavior

A runtime-readiness failure must be visible.

The request must not be represented as completed.

At minimum, the failure message must identify that the configured local
runtime is not ready or reusable and retain the diagnostic detail
returned by runtime inspection.

Step 21 does not implement retry or recovery.

## Runtime policy boundary

No new hardcoded runtime limit is introduced.

Existing model request timeout and remote-model policy continue flowing
through Universal Limit Control into RuntimeManager and LocalModelClient.

Step 21 must not silently alter the user's ON/AUTO/OFF choices.

## Scope exclusions

Explicitly excluded from Step 21:

- automatic llama-server spawning;
- automatic GGUF selection;
- resource-based AUTO model selection;
- non-blocking loading UI;
- runtime status screen;
- model selection screen;
- runtime policy settings UI;
- crash retry;
- request cancellation;
- streaming;
- real-device lifecycle proof.

These belong to later numbered Stage-3 steps.

## Testing requirements

Tests must prove:

1. ThrillaApp constructs and retains RuntimeManager from Config.
2. Ask requests obtain a runtime client through RuntimeManager.
3. successful readiness uses the returned binding client for inference.
4. readiness failure prevents `chat()` from being called.
5. readiness failure does not produce a completed-request audit event.
6. navigation-only Ask commands do not trigger runtime readiness.
7. existing Stage-1 Ask behavior and model-client tests remain green.

Tests must follow strict RED -> GREEN sequencing.

## Completion condition

Step 21 is complete only when Ask Thrilla cannot enter model inference
without passing through RuntimeManager readiness/binding first.

This does not make Stage 3 complete.
