# Stage 3 — Step 21: Ask Runtime Readiness

## Objective

Make Thrilla's Ask / Chat path consume the runtime lifecycle established by the RuntimeManager instead of independently using the application's legacy model client.

Step 21 must prove that Thrilla will only perform inference through a runtime endpoint that has passed runtime readiness inspection.

## Required Behavior

### 1. ThrillaApp owns RuntimeManager

ThrillaApp must construct and retain a RuntimeManager using application configuration.

Required configuration:

- request_timeout comes from Config.request_timeout
- remote_policy remains disabled unless explicitly introduced by a later design step

Expected ownership:

    app.runtime_manager

### 2. RuntimeManager provides a ready binding

RuntimeManager must expose a readiness operation:

    ready_binding(model_url, model_name)

The operation must:

1. Parse the configured model endpoint.
2. Inspect the target host and port.
3. Confirm that an existing server is reusable.
4. Confirm OpenAI-compatible model discovery.
5. Confirm the expected configured model is available.
6. Return a binding containing the runtime client used for inference.

A runtime that is unreachable, incompatible, bound to the wrong model, or otherwise not reusable must not be treated as ready.

### 3. Ask uses the runtime binding

Ask / Chat must not perform inference directly through the legacy:

    app.model

For an actual model request, Ask must first request:

    app.runtime_manager.ready_binding(
        config.model_url,
        config.model_name,
    )

Inference must then use:

    binding.client

This makes RuntimeManager the authority over the model transport consumed by Ask.

### 4. Navigation occurs before readiness

Plain navigation commands must continue to work without attempting runtime readiness or model inference.

Examples include:

- back
- exit
- quit
- 0
- go back
- start over
- main menu
- menu
- home

Navigation must be recognized before requesting a runtime binding.

### 5. Readiness failure blocks inference

If RuntimeManager cannot provide a ready runtime binding:

- Ask must handle the failure without crashing the interactive menu.
- No model client may be invoked.
- No fallback to app.model is allowed.
- Audit must record:

    model_request_failed

- Audit must not record:

    model_request_completed

The failure should remain visible to the operator with enough detail to diagnose why the runtime was rejected.

## Non-Goals

Step 21 does not:

- automatically launch a missing model runtime
- introduce remote inference
- silently switch models
- bypass runtime inspection
- add new model-selection policy
- redesign the Ask interface
- remove legacy model construction unless later cleanup proves it unused elsewhere

## Compatibility Rule

Existing navigation behavior must remain intact.

Runtime readiness is required only after the input has been determined to be an inference request.

## Verification

Run focused Step 21 tests first, then the complete suite.

Focused tests must cover:

- ThrillaApp RuntimeManager construction
- configured request timeout propagation
- remote policy default
- ready endpoint binding
- correct expected-model inspection
- Ask inference through binding.client
- legacy direct client not used
- readiness failure handling
- failure audit behavior
- navigation without runtime/model calls

Then run the full test suite and confirm no regression in Stages 1–3.

## Completion Gate

Step 21 is complete only when:

1. RuntimeManager is the authority for Ask model readiness.
2. Ask inference uses only the client returned by the ready binding.
3. Runtime failure cannot fall back to the legacy client.
4. Runtime failure is audited correctly.
5. Navigation does not trigger runtime readiness.
6. Focused tests pass.
7. Full regression suite passes.
