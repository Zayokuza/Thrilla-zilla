# Stage 3 — Local Model Runtime Manager

Status: **DETAILED IMPLEMENTATION MAP — CODE NOT STARTED**

Stage 3 turns Thrilla from a client that expects an already-running
OpenAI-compatible endpoint into a system capable of discovering,
selecting, starting, supervising and recovering its own local inference
runtime.

The first production target is Android/Termux using llama.cpp's
`llama-server`.

The design must also leave clean interfaces for Windows, ExecuTorch and
ONNX Runtime.

---

# 1. Current problem

Thrilla currently knows how to send requests to:

    http://127.0.0.1:8080/v1/chat/completions

but it does not own the lifecycle of the process listening there.

Current failure mode:

    Thrilla starts
        ↓
    User asks question
        ↓
    Router works
        ↓
    Model client calls localhost:8080
        ↓
    Nothing listening
        ↓
    Connection refused

Stage 3 closes that gap.

---

# 2. Target runtime flow

    User starts Thrilla
            │
            ▼
    Runtime Manager
            │
            ├── inspect configured runtime
            ├── locate llama-server
            ├── discover GGUF models
            ├── inspect device resources
            ├── evaluate Limit Control
            ├── select model/runtime configuration
            │
            ▼
    Runtime State Machine
            │
      STOPPED
            │
            ▼
      STARTING
            │
            ▼
      LOADING_MODEL
            │
            ▼
      HEALTH_CHECK
          ┌─┴─┐
          │   │
          ▼   ▼
        READY FAILED
          │      │
          │      ├── diagnose
          │      ├── retry when permitted
          │      └── report blocker
          │
          ▼
    Thrilla Model Client
          │
          ▼
    User Request

---

# 3. Main Stage-3 components

## 3.1 Runtime discovery

Responsibilities:

- locate `llama-server`;
- identify runtime version;
- locate GGUF files;
- distinguish full models from vocabulary/test GGUF files;
- inspect model size;
- inspect model metadata where possible;
- identify embedding models separately;
- identify planner/small models separately;
- identify chat/coding models;
- identify broken/unreadable candidates.

Initial known phone runtime:

    /data/data/com.termux/files/usr/bin/llama-server

Known useful model locations include:

    ~/models/
    ~/Zayo/models/
    configured Thrilla model directories

The donor llama.cpp source tree must NOT automatically be treated as a
model library because it contains vocabulary/test GGUF files.

---

## 3.2 Model inventory

Each discovered model becomes structured metadata:

    ModelCandidate
        path
        filename
        size_bytes
        architecture
        quantization
        role
        context_capability
        readable
        compatibility
        source
        last_verified
        score

Roles may include:

    primary
    coding
    planner
    embedding
    alternate
    unknown

No model gets silently deleted or overwritten.

---

## 3.3 Runtime selection

Thrilla selects from available candidates using:

1. user-selected model if explicitly configured;
2. task suitability;
3. available memory;
4. compatibility;
5. model role;
6. measured startup history;
7. measured response quality;
8. Universal Limit Control policy.

Selection must produce an explanation.

Example:

    Selected:
      gemma-3-4b-it-Q4_K_M.gguf

    Reason:
      compatible chat model
      fits current resource policy
      local file verified
      no larger model required for request

---

# 4. Universal Limit Control integration

Every Thrilla-created restriction introduced by Stage 3 MUST register
with the Universal Limit Control.

Modes:

    ON
    AUTO
    OFF

Global default:

    AUTO

Individual settings override the global setting.

Thrilla cannot silently change the user's chosen mode.

---

## Stage-3 limiter registry

At minimum:

    runtime.startup_timeout
    runtime.health_timeout
    runtime.shutdown_timeout
    runtime.restart_limit
    runtime.crash_retry_limit
    runtime.model_size
    runtime.context_size
    runtime.batch_size
    runtime.parallel_slots
    runtime.cpu_threads
    runtime.gpu_layers
    runtime.ram_budget
    runtime.process_count
    runtime.queue_depth
    runtime.request_timeout
    runtime.response_tokens
    runtime.model_switch_frequency
    runtime.keep_alive
    runtime.idle_shutdown

Existing limits to migrate into the same registry:

    model.request_timeout
    memory.history_turns
    network.remote_model
    donor.git_timeout

Future limits must register before use.

---

## ON semantics

Thrilla enforces the configured value.

Example:

    Context Limit: ON
    Value: 4096

Thrilla must not exceed 4096.

---

## AUTO semantics

Thrilla chooses the runtime value from live conditions.

Inputs can include:

- available RAM;
- model size;
- model metadata;
- current workload;
- thermal condition when measurable;
- previous startup success;
- latency history;
- task complexity;
- other active Thrilla processes.

AUTO decisions must be logged.

---

## OFF semantics

Thrilla does not impose that particular software limit.

Example:

    Context Limit: OFF

means Thrilla does not artificially cap context.

External physical/runtime limits can still exist.

---

# 5. External constraints

External constraints are NOT Thrilla limits.

Examples:

- Android killing a process;
- Linux memory exhaustion;
- llama.cpp model capability;
- physical RAM;
- storage capacity;
- OS permissions;
- unsupported instruction set;
- kernel limits.

They must be reported as:

    EXTERNAL CONSTRAINT

and never falsely represented as user-configurable Thrilla switches.

---

# 6. Runtime state machine

Required states:

    UNKNOWN
    STOPPED
    DISCOVERING
    SELECTING
    STARTING
    LOADING_MODEL
    HEALTH_CHECKING
    READY
    BUSY
    STOPPING
    FAILED
    CRASHED
    RECOVERING

Every transition records:

    previous state
    next state
    timestamp
    actor
    reason
    model
    PID when applicable
    elapsed time
    result

Illegal transitions must fail visibly.

---

# 7. Process ownership

Thrilla must know whether a llama-server process is:

    EXTERNAL

or:

    THRILLA_MANAGED

Thrilla must never kill an unrelated externally-started server just
because it occupies the configured port.

A managed process record should contain:

    pid
    executable
    command
    model
    port
    start_time
    owner_token
    log_path

---

# 8. Port handling

Default endpoint may remain localhost:8080.

Before starting:

1. inspect whether port is listening;
2. query `/v1/models`;
3. determine whether it is compatible;
4. determine whether it is Thrilla-managed;
5. reuse compatible service where allowed;
6. otherwise select another permitted port or report conflict.

No blind process killing.

---

# 9. Command construction

Runtime arguments must come from structured configuration rather than a
hardcoded shell string.

Conceptual command:

    llama-server
      -m <model>
      -a <alias>
      --host <host>
      --port <port>
      -c <context>
      -np <parallelism>
      <device-specific options>

The command builder must be separately testable.

---

# 10. Health checks

Health sequence:

    process exists
        ↓
    port accepting connections
        ↓
    GET /v1/models
        ↓
    expected model visible
        ↓
    optional tiny inference probe
        ↓
    READY

A process merely existing does not equal READY.

---

# 11. Startup behavior

Initial Stage-3 behavior:

    Thrilla starts
        ↓
    Runtime status checked
        ↓
    if READY:
        reuse
    else:
        discover runtime/model
        ↓
        start managed runtime
        ↓
        wait for health
        ↓
        READY or explicit failure

Normal UI must remain responsive while loading.

---

# 12. Failure handling

Failure categories:

    executable missing
    model missing
    invalid GGUF
    incompatible model
    port occupied
    startup timeout
    process crash
    memory failure
    HTTP health failure
    model API failure
    unexpected exit
    permission failure

Failures must identify:

    what failed
    why
    where
    attempted recovery
    remaining options

No false "completed" result.

---

# 13. Crash recovery

When a Thrilla-managed runtime dies:

    CRASHED
       ↓
    inspect cause
       ↓
    evaluate retry policy
       ↓
    RECOVERING
       ↓
    restart same config
       OR
    select lighter config/model
       OR
    report external blocker

Retries themselves belong to Limit Control.

---

# 14. Logging

Runtime logs must include:

    who
    why
    what
    when
    where
    how long

Additional runtime fields:

    PID
    model
    model size
    endpoint
    context
    threads
    parallel slots
    startup duration
    generation latency
    exit status
    peak resource observations when available

---

# 15. Streaming

Current model requests are non-streaming.

Stage 3 eventually adds:

    stream = true

with:

- token-by-token display;
- clean cancellation;
- terminal restoration;
- partial-output handling;
- audit metadata;
- no false completion after cancellation.

Streaming comes after reliable lifecycle control.

---

# 16. Cancellation

User cancellation must propagate:

    UI
     ↓
    model request
     ↓
    HTTP operation
     ↓
    generation

Stopping a request must not necessarily stop the resident model server.

Separate:

    cancel request

from:

    stop runtime

---

# 17. Model switching

Future sequence:

    request arrives
       ↓
    current model suitable?
       ├── yes → reuse
       └── no
            ↓
       alternate worthwhile?
            ↓
       switching permitted?
            ↓
       checkpoint runtime state
            ↓
       stop managed model
            ↓
       start selected model
            ↓
       health proof
            ↓
       continue

Switching cannot silently discard a working runtime without recovery
information.

---

# 18. Runtime persistence

Possible policy states:

    RESIDENT
    IDLE-SHUTDOWN
    PER-REQUEST
    USER-MANAGED

Default should ultimately be controlled through the runtime policy and
Limit Control rather than hardcoded.

---

# 19. Android/Termux requirements

Must verify:

- executable discovery under `$PREFIX/bin`;
- process spawning;
- process groups;
- signal handling;
- Android background behavior;
- Termux session death behavior;
- storage paths;
- memory pressure;
- terminal cancellation;
- localhost networking;
- clean shutdown;
- orphan detection.

---

# 20. Windows requirements

Use the same runtime interface but platform-specific process control.

Must verify:

- executable discovery;
- subprocess creation;
- process termination;
- console behavior;
- port detection;
- path quoting;
- model paths;
- log paths;
- startup persistence.

Do not duplicate the entire runtime manager.

---

# 21. Runtime interfaces

Planned module boundary:

    thrilla/runtime/
        __init__.py
        models.py
        discovery.py
        policy.py
        command.py
        process.py
        health.py
        manager.py
        state.py

Potential separate universal policy module:

    thrilla/limits.py

The model HTTP adapter remains focused on inference communication rather
than process management.

---

# 22. Linear implementation order

Implementation MUST proceed in this order.

## Step 1
Create Universal Limit Control primitives.

No runtime hard limits before this exists.

## Step 2
Register existing Thrilla-imposed limits.

Do not silently change existing behavior yet.

## Step 3
Add tests that detect unregistered runtime limit definitions.

## Step 4
Create runtime state types and legal transition tests.

## Step 5
Create `ModelCandidate`.

## Step 6
Implement llama-server executable discovery.

## Step 7
Implement GGUF discovery.

## Step 8
Filter vocabulary/test GGUF files from normal chat candidates.

## Step 9
Implement model inventory reporting.

## Step 10
Implement deterministic runtime command builder.

Do not spawn anything yet.

## Step 11
Implement port inspection.

## Step 12
Implement compatible existing-server detection.

## Step 13
Implement managed-process metadata.

## Step 14
Implement process spawn behind tests.

## Step 15
Implement startup log capture.

## Step 16
Implement `/v1/models` readiness polling.

## Step 17
Implement startup failure classification.

## Step 18
Implement clean managed-process shutdown.

## Step 19
Implement orphan detection.

## Step 20
Connect Runtime Manager to existing LocalModelClient.

## Step 21
Make Ask Thrilla request runtime readiness before inference.

## Step 22
Add asynchronous/non-blocking model loading UI.

## Step 23
Add runtime status screen.

## Step 24
Add model selection screen.

## Step 25
Expose ON/AUTO/OFF runtime policies.

## Step 26
Implement AUTO resource selection.

## Step 27
Add crash detection.

## Step 28
Add controlled recovery/retry.

## Step 29
Add request cancellation.

## Step 30
Add streaming responses.

## Step 31
Run real-phone llama.cpp lifecycle proof.

## Step 32
Run repeated start/stop/restart tests.

## Step 33
Run memory-pressure tests.

## Step 34
Run failure-injection tests.

## Step 35
Run Windows proof.

Only after these pass should Stage 3 be described as complete.

---

# 23. First live target

The first real proof should automate what is currently manual:

    Thrilla starts
       ↓
    sees localhost:8080 is unavailable
       ↓
    finds llama-server
       ↓
    discovers verified chat GGUF
       ↓
    selects permitted runtime configuration
       ↓
    starts llama-server
       ↓
    waits for /v1/models
       ↓
    marks READY
       ↓
    user types:
        hey
       ↓
    actual local-model answer returned

No second Termux session should ultimately be required.

---

# 24. Stage-3 completion definition

Stage 3 is complete only when Thrilla can:

- discover a valid local model;
- discover its inference runtime;
- start it;
- prove readiness;
- answer through it;
- cancel a request;
- recover from runtime failure;
- stop its own managed runtime;
- distinguish external from managed servers;
- obey ON/AUTO/OFF user policy;
- report external constraints accurately;
- leave the terminal usable after every failure path;
- pass automated tests;
- pass real Android/Termux verification;
- pass Windows verification.

Until then, Stage 3 remains in progress.
