# Canonical requirements

## Product goal

Thrilla-zilla is intended to become one local-first AI workbench that can:

- answer general questions;
- study requested subjects;
- read and understand unfamiliar software repositories;
- write, repair, refactor, debug, explain, and test software;
- work with other AI codebases through documented interfaces;
- search current, cached, and historical web information;
- work with files, structured data, and local tools;
- execute bounded tasks on Android/Termux and Windows;
- measure whether changes help;
- improve its coding system through controlled, reversible engineering.

## Platform rule

Android/Termux and Windows are the release targets. A language, framework, build system, or repository belongs in the capability plan when it can materially contribute to software on those targets. macOS/iOS-only stacks are outside the current core scope.

## Language capability targets

### Maximum investment

- Python
- C
- C++
- Rust
- Kotlin
- TypeScript
- Gradle and the Android build ecosystem

Maximum means reading, writing, debugging, repairing, refactoring, architecture, optimization, testing, profiling, and understanding internals.

### Full professional capability

- Java
- JavaScript
- Go
- C#
- Bash and POSIX shell
- PowerShell
- SQL
- HTML and CSS

### Build and structured formats

- CMake, Make, Gradle, Maven, Ninja, Meson
- JSON, YAML, TOML, XML
- Dockerfiles
- protobuf and gRPC schemas
- WebAssembly/WAT
- Windows batch files
- JNI and Android NDK integration

### Additional practical capability

- Lua, PHP, Dart/Flutter, Groovy
- OpenCL and CUDA
- AArch64, x86, and x86-64 assembly comprehension
- ABI conventions, SIMD, and disassembly
- GLSL, Ruby, VB.NET, Scala, and Fortran

### Read and understand

- Perl
- R
- Solidity
- Julia
- Erlang and Elixir
- Haskell

Assembly capability primarily means tracing, understanding, debugging, and making targeted fixes—not rewriting large applications in assembly.

## Unknown-language behavior

An unfamiliar repository must trigger investigation instead of rejection:

```text
detect languages and frameworks
→ detect package and build systems
→ parse syntax/AST where possible
→ identify symbols, imports, and call relationships
→ identify cross-language interfaces
→ choose compiler/interpreter/linter/LSP/tests
→ validate understanding
→ edit only with evidence and rollback
```

## Memory requirements

Phone-first memory begins with:

```text
working memory
+ SQLite durable state
+ exact/full-text retrieval
+ lightweight semantic retrieval when justified
```

Every durable item needs relevance, timestamp, confidence, source, ownership, and scope. Larger machines may later use PostgreSQL, Qdrant, or Redis through optional adapters.

## Research requirements

Research should combine live, cached, and archived sources. Results need source URL, retrieval time, publication/event dates when available, clear attribution, and a distinction between sourced fact and inference. OSINT belongs inside the research system rather than becoming an unrelated agent architecture.

## Autonomy requirements

Autonomy means completing bounded tasks with minimal unnecessary interruption. It does not mean hidden actions or unlimited permissions. Every state-changing operation requires scope, target, reason, timeout, result, evidence, and recovery path.

## Evaluation requirements

Every material change should answer:

- Did it work?
- Did it break anything else?
- Did it become slower?
- Did RAM, CPU, storage, heat, or battery use rise?
- Did it introduce a vulnerability or privacy problem?
- Is it easier to maintain?
- Is the new implementation measurably better?
- Keep or rollback?

## Interface requirements

- simple `thrilla>` interaction;
- compact phone presentation;
- colored semantic output with plain fallback;
- arrow keys and numeric input;
- every action mapped to a validated handler;
- visible routing and limitations;
- clean Ctrl+C, cancellation, timeout, EOF, and crash behavior;
- no silent menu failures.

