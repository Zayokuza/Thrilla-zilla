"""Interactive Thrilla application designed for a narrow phone terminal."""

import textwrap
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from . import __version__
from .audit import AuditLog
from .brain import AgentBrain, BrainError
from .answers import (
    KnowledgeGap,
    build_reasoning_messages,
)
from .catalog import CORE_DONORS, DonorSpec, phase_one_categories
from .colors import ColorMode, Palette
from .config import Config
from .limits import DEFAULT_LIMITS, LimitMode
from .diagnostics import Check, platform_name, run_checks
from .donors import DonorRegistry, DonorState
from .equipment import EQUIPMENT_NAMES, verify_creator_code
from .history import ConversationHistory
from .experts import (
    EXPERT_COUNT,
    EXPERT_GROUPS,
    EXPERTS_PER_GROUP,
    ExpertOrchestrator,
)
from .identity import CREATOR_NAME
from .model import LocalModelClient, ModelError
from .router import Route, route_request
from .runtime.discovery import build_model_inventory
from .runtime.manager import RuntimeBindingError, RuntimeManager
from .runtime.supervisor import RuntimeSupervisor
from .observers import (
    ClockProvider,
    MemoryProvider,
    RuntimeProvider,
    SelfProvider,
)
from .providers import ProviderRegistry
from .terminal import MenuItem, clear_screen, select_menu, terminal_width
from .tools import build_default_tool_executor


MAIN_MENU = (
    MenuItem("1", "Ask Thrilla"),
    MenuItem("2", "Donor Library"),
    MenuItem("3", "Route Inspector"),
    MenuItem("4", "Runtime & Models"),
    MenuItem("5", "Diagnostics"),
    MenuItem("6", "Conversation History"),
    MenuItem("7", "Activity Log"),
    MenuItem("8", "Settings"),
    MenuItem("9", "About"),
    MenuItem("0", "Exit"),
)

DONOR_MENU = (
    MenuItem("1", "Overview", "Phase progress and library location."),
    MenuItem("2", "Category Status", "Ready, incomplete and missing totals."),
    MenuItem("3", "Priority 30", "The first three donors in every category."),
    MenuItem("4", "Problems", "List missing or incomplete core donors."),
    MenuItem("5", "Inspect One Repository", "Read branch, commit, remote and cleanliness."),
    MenuItem("6", "Phase-2 Specialists", "Show collected specialist references."),
    MenuItem("0", "Back"),
)

RUNTIME_MENU = (
    MenuItem("1", "Runtime Status", "Inspect the configured runtime."),
    MenuItem("2", "Model Inventory", "Inspect discovered local GGUF models."),
    MenuItem("3", "Preferred Model", "View or choose the preferred GGUF."),
    MenuItem("4", "Refresh", "Refresh runtime and model state."),
    MenuItem("0", "Back"),
)


SETTINGS_MENU = (
    MenuItem("1", "Color Mode", "auto, always or never"),
    MenuItem("2", "Donor Root", "Location of Thrilla-codebases"),
    MenuItem("3", "Model URL", "Local OpenAI-compatible chat endpoint"),
    MenuItem("4", "Model Name", "Name sent with chat requests"),
    MenuItem("5", "Save Conversation History", "Local JSONL memory"),
    MenuItem("6", "Model Timeout", "Seconds before a request is cancelled"),
    MenuItem("7", "Runtime Policies", "Universal Limit Control modes and values"),
    MenuItem("8", "Creator Vault"),
    MenuItem("0", "Back"),
)


class ThrillaApp:
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config.load()
        try:
            mode = ColorMode(self.config.color_mode)
        except ValueError:
            mode = ColorMode.AUTO
        self.palette = Palette(mode)
        self.audit = AuditLog(self.config.state_path)
        self.history = ConversationHistory(self.config.state_path)
        self.registry = DonorRegistry(self.config.donor_path)
        self.runtime_manager = RuntimeManager.from_config(self.config)
        self.runtime_supervisor = RuntimeSupervisor(
            self.config,
            self.runtime_manager,
        )
        self.brain = AgentBrain(max_attempts=2)
        self.expert_orchestrator = ExpertOrchestrator()
        self.tool_executor = self._tool_executor()
        self.provider_registry = self._provider_registry()
        self.model = self._model_client()
        self.message = ""

    def _provider_registry(self) -> ProviderRegistry:
        """Build Thrilla's ordered local observation providers."""

        repo_root = str(
            Path(__file__).resolve().parent.parent
        )

        return ProviderRegistry(
            (
                ClockProvider(),
                RuntimeProvider(
                    inspect_fn=(
                        self.runtime_manager
                        .inspect_configured_runtime
                    ),
                    model_url=self.config.model_url,
                    expected_model=self.config.model_name,
                ),
                SelfProvider(
                    repo_root=repo_root,
                    version=__version__,
                ),
                MemoryProvider(
                    records_fn=self.history.records,
                ),
            )
        )

    def _tool_executor(self):
        repo_root = Path(__file__).resolve().parent.parent

        return build_default_tool_executor(
            repo_root=repo_root,
            state_root=self.config.state_path,
            donor_root=self.config.donor_path,
        )

    def _model_client(self) -> LocalModelClient:
        timeout = self.config.resolve_limit(
            "model.request_timeout"
        ).value
        remote_policy = self.config.resolve_limit(
            "network.remote_model"
        ).value

        return LocalModelClient(
            self.config.model_url,
            self.config.model_name,
            timeout,
            remote_policy=remote_policy,
        )

    def _refresh(self) -> None:
        try:
            mode = ColorMode(self.config.color_mode)
        except ValueError:
            mode = ColorMode.AUTO
        self.palette = Palette(mode)
        self.registry = DonorRegistry(self.config.donor_path)
        self.runtime_manager = RuntimeManager.from_config(self.config)
        self.runtime_supervisor = RuntimeSupervisor(
            self.config,
            self.runtime_manager,
        )
        self.expert_orchestrator = ExpertOrchestrator()
        self.tool_executor = self._tool_executor()
        self.provider_registry = self._provider_registry()
        self.model = self._model_client()

    def _title(self) -> str:
        ready, total = self.registry.progress(1)
        return f"THRILLA-ZILLA  v{__version__}  •  donors {ready}/{total}"

    def _header(self, title: str) -> None:
        clear_screen()
        width = min(terminal_width(), 62)
        print(self.palette.brand(title))
        print(self.palette.muted("─" * width))

    def _pause(self) -> None:
        try:
            input(self.palette.muted("\nPress Enter to continue… "))
        except EOFError:
            pass

    def _prompt(self, label: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        try:
            value = self._input_line(f"{label}{suffix}: ").strip()
        except EOFError:
            return default
        return value or default

    def _input_line(self, label: str) -> str:
        """Keep the user's label and typed text cyan until Enter is pressed."""
        if not self.palette.enabled:
            return input(label)
        try:
            return input(self.palette.start("prompt") + label)
        finally:
            sys.stdout.write(self.palette.reset_code)
            sys.stdout.flush()

    def _status(self, label: str, value: str, level: str = "normal") -> None:
        marker = {"pass": "✓", "warn": "!", "fail": "✗", "normal": "•"}.get(level, "•")
        painter = {
            "pass": self.palette.success,
            "warn": self.palette.warning,
            "fail": self.palette.error,
        }.get(level, self.palette.accent)
        print(f"{painter(marker)} {label}: {value}")

    def main_handlers(self) -> Dict[str, Callable[[], None]]:
        """Return the complete handler map for MAIN_MENU."""
        return {
            "1": self.ask,
            "2": self.donor_library,
            "3": self.route_inspector,
            "4": self.runtime_models,
            "5": self.diagnostics_screen,
            "6": self.history_screen,
            "7": self.audit_screen,
            "8": self.settings,
            "9": self.about,
        }

    def runtime_handlers(self) -> Dict[str, Callable[[], None]]:
        """Return the complete handler map for RUNTIME_MENU."""
        return {
            "1": self.runtime_status_screen,
            "2": self.model_inventory_screen,
            "3": self.preferred_model_screen,
            "4": self.refresh_runtime_models,
        }

    def donor_handlers(self) -> Dict[str, Callable[[], None]]:
        """Return the complete handler map for DONOR_MENU."""
        return {
            "1": self.donor_overview,
            "2": self.donor_categories,
            "3": self.priority_donors,
            "4": self.donor_problems,
            "5": self.inspect_donor,
            "6": self.specialist_donors,
        }

    def settings_handlers(self) -> Dict[str, Callable[[], None]]:
        """Return the complete handler map for SETTINGS_MENU."""
        return {
            "1": self.setting_color,
            "2": self.setting_donor_root,
            "3": self.setting_model_url,
            "4": self.setting_model_name,
            "5": self.setting_history,
            "6": self.setting_timeout,
            "7": self.runtime_policies_screen,
            "8": self.creator_vault_screen,
        }

    def ensure_owner_profile(self) -> None:
        """Enroll the local installation owner once."""
        if self.config.owner_name.strip():
            return

        while not self.config.owner_name.strip():
            try:
                owner_name = self._input_line("What is your name?").strip()
            except (EOFError, OSError):
                return

            if not owner_name:
                continue

            self.config.owner_name = owner_name
            self.config.save()
            self.audit.write("owner_profile_created")

    def run(self) -> int:
        self.audit.write("app_started", version=__version__, platform=platform_name())
        self.ensure_owner_profile()
        handlers = self.main_handlers()
        try:
            while True:
                footer = self.message or "↑/↓ move  •  Enter select  •  numbers work too"
                self.message = ""
                choice = select_menu(self._title(), MAIN_MENU, self.palette, footer=footer)
                if choice == "0":
                    break
                handler = handlers.get(choice)
                if handler is None:
                    self.message = self.palette.error(f"Menu action {choice} is unavailable.")
                    continue
                try:
                    handler()
                except KeyboardInterrupt:
                    self.message = self.palette.warning("Cancelled; no changes were made.")
                except Exception as error:
                    self.audit.write("ui_error", action=choice, error=type(error).__name__)
                    self._header("THRILLA ERROR")
                    print(self.palette.error(f"{type(error).__name__}: {error}"))
                    self._pause()
        finally:
            self.audit.write("app_stopped")
        print(self.palette.muted("Thrilla stopped cleanly."))
        return 0

    @staticmethod
    def _format_knowledge_gap(
        gap: KnowledgeGap,
    ) -> str:
        """Render one structured evidence failure."""

        lines = [
            "Knowledge gap: {}".format(
                gap.unknown
            ),
            "",
            "Missing evidence:",
        ]

        lines.extend(
            "- {}".format(item)
            for item in gap.missing_evidence
        )

        lines.extend(
            [
                "",
                "Why:",
                gap.reason,
                "",
                "How to resolve:",
            ]
        )

        lines.extend(
            "- {}".format(item)
            for item in gap.resolution
        )

        return "\n".join(lines)

    @staticmethod
    def _reasoning_messages(
        previous,
        owner_prompt: str,
        evidence,
    ):
        """Preserve history, then isolate evidence from owner input."""

        return (
            list(previous)
            + build_reasoning_messages(
                owner_prompt,
                evidence,
            )
        )

    def _resolve_ask_answer(
        self,
        prompt: str,
        previous,
        route: str,
    ) -> str:
        """Resolve providers before optional model inference."""

        context = (
            self.provider_registry.collect(
                prompt
            )
        )

        if context.direct_answer is not None:
            return context.direct_answer

        if context.gap is not None:
            return self._format_knowledge_gap(
                context.gap
            )

        messages = self._reasoning_messages(
            previous,
            prompt,
            context.evidence,
        )

        expert_context = self.expert_orchestrator.context_for(
            prompt,
            route,
            limit=3,
        )

        messages.insert(
            len(previous),
            {
                "role": "system",
                "content": expert_context,
            },
        )

        # Keep the supervisor bound to the current manager. Tests and
        # adapters may replace runtime_manager after app construction;
        # retaining the constructor-time manager would bypass that
        # replacement and can accidentally reach a live runtime.
        self.runtime_supervisor.manager = self.runtime_manager

        result = self.brain.run_answer(
            prompt,
            lambda: self.runtime_supervisor.chat(
                messages,
                route,
            ),
        )

        return result.answer

    def ask(self) -> None:
        self._header("ASK THRILLA")
        print(self.palette.muted("Cyan = you  •  green = Thrilla  •  /help for commands"))
        print(self.palette.muted("Requests route to chat, coding, search, files/data, device or system."))
        while True:
            try:
                prompt = self._input_line("\nyou> ").strip()
            except EOFError:
                return
            if not prompt:
                continue
            command = prompt.lower().strip()

            if command in {
                "/back",
                "/exit",
                "/quit",
                "back",
                "exit",
                "quit",
                "0",
                "go back",
                "start over",
                "main menu",
                "menu",
                "home",
            }:
                return
            if command == "/help":
                print(self.palette.accent("/route  /model  /clear  /back"))
                continue
            if command == "/route":
                print(self.palette.accent("Routing is automatic and shown before every response."))
                continue
            if command == "/model":
                status = self.model.health()
                level = "pass" if status.online else "warn"
                self._status("Model", status.detail, level)
                continue
            if command == "/clear":
                cleared = self.history.clear()
                print(self.palette.success("Conversation history cleared." if cleared else "History is already empty."))
                self.audit.write("history_cleared", existed=cleared)
                continue

            decision = route_request(prompt)
            print(self.palette.muted(
                f"route: {decision.route.value}  •  confidence: {decision.confidence:.0%}  •  {decision.explanation}"
            ))
            history_turns = self.config.resolve_limit(
                "memory.history_turns"
            ).value
            previous = (
                self.history.messages(history_turns)
                if self.config.save_history
                else []
            )
            if self.config.save_history:
                self.history.append("user", prompt, decision.route.value)
            try:
                print(self.palette.muted("Thrilla is thinking…"))
                answer = self._resolve_ask_answer(
                    prompt,
                    previous,
                    decision.route.value,
                )
            except (
                BrainError,
                ModelError,
                RuntimeBindingError,
            ) as error:
                self.audit.write(
                    "model_request_failed",
                    route=decision.route.value,
                    prompt_chars=len(prompt),
                    error=type(error).__name__,
                )
                print(self.palette.error(str(error)))
                print(self.palette.warning(
                    "Start llama-server or change Settings → Model URL. The request was not claimed as completed."
                ))
                continue
            if self.config.save_history:
                self.history.append("assistant", answer, decision.route.value)
            self.audit.write(
                "model_request_completed",
                route=decision.route.value,
                prompt_chars=len(prompt),
                answer_chars=len(answer),
            )
            print("\n" + self.palette.answer("thrilla> ") + self.palette.answer(answer))

    def donor_library(self) -> None:
        handlers = self.donor_handlers()
        while True:
            choice = select_menu("DONOR LIBRARY", DONOR_MENU, self.palette)
            if choice == "0":
                return
            handlers[choice]()

    def donor_overview(self) -> None:
        self._header("DONOR LIBRARY / OVERVIEW")
        ready, total = self.registry.progress(1)
        priority_ready, priority_total = self.registry.priority_progress()
        specialist_ready, specialist_total = self.registry.progress(2)
        self._status("Root", str(self.registry.root))
        self._status("Phase 1 core", f"{ready}/{total}", "pass" if ready == total else "warn")
        self._status("Priority layer", f"{priority_ready}/{priority_total}", "pass" if priority_ready == priority_total else "warn")
        self._status("Phase 2 registered", f"{specialist_ready}/{specialist_total}", "pass" if specialist_ready == specialist_total else "warn")
        print("\n" + self.palette.warning("Donors are read-only study sources. They are not imported or executed automatically."))
        self._pause()

    def donor_categories(self) -> None:
        self._header("DONOR LIBRARY / CATEGORIES")
        counts = self.registry.category_counts()
        for number, _slug, name in phase_one_categories():
            values = counts.get(number, {})
            ready = values.get("ready", 0)
            problems = values.get("missing", 0) + values.get("incomplete", 0)
            level = "pass" if ready == 10 else "warn"
            self._status(f"{number:02d} {name}", f"{ready}/10" + (f" • {problems} problem(s)" if problems else ""), level)
        self._pause()

    def _print_donor_states(self, states: Sequence[DonorState], include_path: bool = False) -> None:
        current = None
        for state in states:
            if state.spec.category != current:
                current = state.spec.category
                print("\n" + self.palette.brand(f"{current:02d} {state.spec.category_name}"))
            marker = "✓" if state.present else "✗"
            painter = self.palette.success if state.present else self.palette.error
            label = f"{marker} {state.spec.slot:02d} {state.spec.repository}"
            print(painter(label))
            if include_path:
                print("   " + self.palette.muted(str(state.path)))

    def priority_donors(self) -> None:
        self._header("DONOR LIBRARY / PRIORITY 30")
        states = tuple(self.registry.inspect(spec) for spec in CORE_DONORS if spec.priority)
        self._print_donor_states(states)
        ready = sum(item.present for item in states)
        print("\n" + self.palette.accent(f"Ready: {ready}/{len(states)}"))
        self._pause()

    def donor_problems(self) -> None:
        self._header("DONOR LIBRARY / PROBLEMS")
        problems = tuple(state for state in self.registry.scan(1) if not state.present)
        if not problems:
            print(self.palette.success("All 100 core repositories are present."))
        else:
            self._print_donor_states(problems, include_path=True)
        self._pause()

    def inspect_donor(self) -> None:
        self._header("DONOR LIBRARY / INSPECT")
        query = self._prompt("Repository number (1-100), name, or owner/name")
        if not query:
            return
        specs = self._find_specs(query, CORE_DONORS)
        if not specs:
            print(self.palette.error("No matching core donor."))
            self._pause()
            return
        if len(specs) > 1:
            print(self.palette.warning("Multiple matches; be more specific:"))
            for spec in specs[:20]:
                print(f"  {(spec.category - 1) * 10 + spec.slot:03d} {spec.repository}")
            self._pause()
            return
        spec = specs[0]
        state = self.registry.inspect(spec)
        git_timeout = self.config.resolve_limit(
            "donor.git_timeout"
        ).value
        details = self.registry.verify_git(
            spec,
            timeout=git_timeout,
        )
        self._status("Repository", spec.repository)
        self._status("Path", str(state.path), "pass" if state.present else "fail")
        self._status("State", state.state, "pass" if state.present else "fail")
        if details.error:
            self._status("Git", details.error, "fail")
        else:
            self._status("Branch", details.branch)
            self._status("Commit", details.commit)
            self._status("Working tree", "clean" if details.clean else "modified", "pass" if details.clean else "warn")
            self._status("Remote", details.remote)
        self.audit.write("donor_inspected", repository=spec.repository, state=state.state)
        self._pause()

    def _find_specs(self, query: str, specs: Iterable[DonorSpec]) -> List[DonorSpec]:
        normalized = query.strip().lower()
        if normalized.isdigit():
            index = int(normalized) - 1
            sequence = list(specs)
            return [sequence[index]] if 0 <= index < len(sequence) else []
        return [
            spec for spec in specs
            if normalized in spec.repository.lower() or normalized == spec.folder.lower()
        ]

    def specialist_donors(self) -> None:
        self._header("DONOR LIBRARY / PHASE 2")
        states = self.registry.scan(2)
        self._print_donor_states(states, include_path=True)
        print("\n" + self.palette.warning("Only verified collected specialists are registered. The Phase-2 100 is not yet finalized."))
        self._pause()

    def route_inspector(self) -> None:
        self._header("ROUTE INSPECTOR")
        request = self._prompt("Request")
        if not request:
            return
        decision = route_request(request)
        self._status("Route", decision.route.value, "pass")
        self._status("Confidence", f"{decision.confidence:.0%}")
        self._status("Why", decision.explanation)
        self.audit.write("route_inspected", route=decision.route.value, prompt_chars=len(request))
        self._pause()

    def runtime_models(self) -> None:
        handlers = self.runtime_handlers()
        while True:
            choice = select_menu(
                "RUNTIME & MODELS",
                RUNTIME_MENU,
                self.palette,
            )
            if choice == "0":
                return
            handler = handlers.get(choice)
            if handler is not None:
                handler()

    def runtime_status_screen(self) -> None:
        self._header("RUNTIME & MODELS / STATUS")
        snapshot = self.runtime_manager.inspect_configured_runtime(
            self.config.model_url,
            self.config.model_name,
        )

        self._status("Endpoint", snapshot.configured_endpoint)
        self._status("Expected model", snapshot.expected_model or "unknown")
        self._status(
            "Runtime",
            "READY" if snapshot.ready else "NOT READY",
            "pass" if snapshot.ready else "warn",
        )
        self._status("Detail", snapshot.detail or "unknown")
        self._status("Host", snapshot.host or "unknown")
        self._status(
            "Port",
            str(snapshot.port) if snapshot.port is not None else "unknown",
        )

        ownership = snapshot.ownership
        ownership_text = (
            getattr(ownership, "value", str(ownership))
            if ownership is not None
            else "unknown"
        )
        self._status("Ownership", ownership_text)

        reported = (
            ", ".join(snapshot.reported_models)
            if snapshot.reported_models
            else "unknown"
        )
        self._status("Reported model", reported)

        if snapshot.error:
            self._status("Error", snapshot.error, "warn")

        self._pause()

    def _model_search_roots(self):
        roots = []

        preferred = getattr(
            self.config,
            "preferred_model_path",
            "",
        )
        if preferred:
            roots.append(
                Path(preferred).expanduser().parent
            )

        state_root = getattr(
            self.config,
            "state_root",
            "",
        )
        if state_root:
            roots.append(
                Path(state_root).expanduser() / "models"
            )

        roots.append(Path.home() / "models")

        unique = []
        seen = set()

        for root in roots:
            resolved = str(root)
            if resolved not in seen:
                seen.add(resolved)
                unique.append(resolved)

        return tuple(unique)

    def _model_inventory(self):
        return build_model_inventory(
            self._model_search_roots()
        )

    def model_inventory_screen(self) -> None:
        self._header("RUNTIME & MODELS / INVENTORY")

        inventory = self._model_inventory()

        if not inventory:
            print(self.palette.muted(
                "No local GGUF models were found in the configured search roots."
            ))
            self._pause()
            return

        for number, candidate in enumerate(
            inventory,
            start=1,
        ):
            role = getattr(
                candidate.role,
                "value",
                str(candidate.role),
            )

            size_mb = (
                candidate.size_bytes / 1048576.0
            )

            self._status(
                "{0}. {1}".format(
                    number,
                    candidate.filename,
                ),
                "{0} | {1} | {2:.1f} MiB".format(
                    role,
                    candidate.quantization,
                    size_mb,
                ),
            )
            self._status(
                "Path",
                candidate.path,
            )
            self._status(
                "Readable",
                "yes"
                if candidate.readable
                else "no",
                "pass"
                if candidate.readable
                else "warn",
            )
            self._status(
                "Compatibility",
                candidate.compatibility
                or "unknown",
            )

        self._pause()

    def preferred_model_screen(self) -> None:
        self._header(
            "RUNTIME & MODELS / PREFERRED MODEL"
        )

        preferred = getattr(
            self.config,
            "preferred_model_path",
            "",
        )

        if preferred:
            preferred_path = Path(
                preferred
            ).expanduser()

            exists = preferred_path.is_file()

            self._status(
                "Preferred",
                str(preferred_path),
                "pass" if exists else "warn",
            )
            self._status(
                "Preferred file",
                "available" if exists else "missing",
                "pass" if exists else "warn",
            )
        else:
            self._status(
                "Preferred",
                "not selected",
            )

        inventory = self._model_inventory()

        for number, candidate in enumerate(
            inventory,
            start=1,
        ):
            role = getattr(
                candidate.role,
                "value",
                str(candidate.role),
            )
            self._status(
                "{0}. {1}".format(
                    number,
                    candidate.filename,
                ),
                "{0} | {1}".format(
                    role,
                    candidate.quantization,
                ),
            )

        choice = self._prompt(
            "Preferred model number or GGUF path"
        )

        if not choice:
            self._pause()
            return

        selected = None

        if choice.isdigit():
            index = int(choice) - 1

            if 0 <= index < len(inventory):
                selected = Path(
                    inventory[index].path
                )
        else:
            selected = Path(
                choice
            ).expanduser()

        if (
            selected is None
            or not selected.is_file()
            or selected.suffix.lower() != ".gguf"
        ):
            self._status(
                "Selection",
                "missing or invalid GGUF",
                "warn",
            )
            self._pause()
            return

        selected = selected.resolve()

        self.config.preferred_model_path = str(
            selected
        )

        self.config.save()

        self.audit.write(
            "preferred_model_changed",
            preferred_model_path=str(selected),
        )

        self._status(
            "Preferred",
            str(selected),
            "pass",
        )
        self._status(
            "Runtime state",
            "selection saved; loaded state requires runtime evidence",
        )

        self._pause()

    def refresh_runtime_models(self) -> None:
        self.runtime_manager = RuntimeManager.from_config(self.config)
        self.message = self.palette.success(
            "Runtime and model state refreshed."
        )

    def model_screen(self) -> None:
        self._header("LOCAL MODEL")
        self._status("Endpoint", self.config.model_url)
        self._status("Configured model", self.config.model_name)
        status = self.model.health(timeout=2.0)
        self._status("Connection", status.detail, "pass" if status.online else "warn")
        if status.online:
            self._status("Reported model", status.model or "not reported", "pass")
        else:
            print("\n" + self.palette.warning("The menu and donor tools still work without a model."))
            print(self.palette.muted("Configure Settings → Model URL after starting llama-server."))
        self.audit.write("model_checked", online=status.online)
        self._pause()

    def diagnostics_screen(self) -> None:
        self._header("DIAGNOSTICS")
        checks = run_checks(self.config)
        for check in checks:
            self._status(check.name, check.detail, check.level)
        failures = sum(check.level == "fail" for check in checks)
        warnings = sum(check.level == "warn" for check in checks)
        print("\n" + (
            self.palette.success("Core checks passed.") if not failures
            else self.palette.error(f"{failures} required check(s) failed.")
        ))
        if warnings:
            print(self.palette.warning(f"{warnings} optional or incomplete check(s) need attention."))
        self.audit.write("diagnostics_completed", failures=failures, warnings=warnings)
        self._pause()

    def history_screen(self) -> None:
        self._header("CONVERSATION HISTORY")
        records = self.history.records(limit=20)
        if not records:
            print(self.palette.muted("No saved conversation history."))
        for record in records:
            role = record["role"]
            label = "you>" if role == "user" else "thrilla>"
            painter = self.palette.prompt if role == "user" else self.palette.answer
            print("\n" + painter(label))
            print(painter(record["content"]))
        print("\n" + self.palette.muted(f"Stored locally at {self.history.path}"))
        answer = self._prompt("Type CLEAR to preserve-and-clear, or Enter to go back")
        if answer == "CLEAR":
            cleared = self.history.clear()
            self.audit.write("history_cleared", existed=cleared)
            print(self.palette.success("History moved aside and active history cleared." if cleared else "History was already empty."))
            self._pause()

    def audit_screen(self) -> None:
        self._header("ACTIVITY LOG")
        records = self.audit.tail(20)
        if not records:
            print(self.palette.muted("No activity events."))
        for record in records:
            timestamp = str(record.pop("timestamp", ""))[:19].replace("T", " ")
            event = record.pop("event", "unknown")
            details = "  ".join(f"{key}={value}" for key, value in record.items())
            print(self.palette.accent(f"{timestamp}  {event}"))
            if details:
                print("  " + self.palette.muted(details))
        print("\n" + self.palette.muted("Prompts and answers are not copied into this metadata log."))
        self._pause()

    def settings(self) -> None:
        handlers = self.settings_handlers()
        while True:
            choice = select_menu("SETTINGS", SETTINGS_MENU, self.palette)
            if choice == "0":
                return
            handlers[choice]()

    def set_runtime_policy_mode(self, name: str, mode: str) -> None:
        if name not in DEFAULT_LIMITS.names():
            raise ValueError("unknown runtime policy: {0}".format(name))

        normalized = LimitMode(mode).value
        self.config.limit_modes[name] = normalized
        self.config.save()

        self.audit.write(
            "runtime_policy_changed",
            limit_name=name,
            mode=normalized,
        )

    def runtime_policies_screen(self) -> None:
        self._header("SETTINGS / RUNTIME POLICIES")

        self._status(
            "Global default",
            self.config.limit_default_mode.upper(),
        )

        names = DEFAULT_LIMITS.names()

        for number, name in enumerate(names, start=1):
            mode = self.config.limit_modes.get(
                name,
                self.config.limit_default_mode,
            )
            configured = self.config.limit_values.get(
                name,
                "not set",
            )
            decision = self.config.resolve_limit(name)

            effective = (
                "none"
                if decision.value is None
                else str(decision.value)
            )

            self._status(
                "{0}. {1}".format(number, name),
                "{0} | configured={1} | effective={2}".format(
                    mode.upper(),
                    configured,
                    effective,
                ),
            )

        choice = self._prompt(
            "Limit number/name to change, or Enter to go back"
        )

        if not choice:
            self._pause()
            return

        if choice.isdigit():
            index = int(choice) - 1
            name = names[index] if 0 <= index < len(names) else ""
        else:
            name = choice

        if name not in names:
            self._status("Policy", "unknown limit", "warn")
            self._pause()
            return

        mode = self._prompt(
            "Mode for {0} (on/auto/off)".format(name)
        ).lower()

        if mode not in {
            LimitMode.ON.value,
            LimitMode.AUTO.value,
            LimitMode.OFF.value,
        }:
            self._status("Mode", "must be on, auto or off", "warn")
            self._pause()
            return

        self.set_runtime_policy_mode(name, mode)

        self._status(
            "Saved",
            "{0} = {1}".format(name, mode.upper()),
            "pass",
        )
        self._pause()

    def _save_setting(self, field: str, old_value: object) -> None:
        path = self.config.save()
        self._refresh()
        self.audit.write("setting_changed", field=field, old=str(old_value), config=str(path))
        self.message = self.palette.success(f"Saved {field}.")

    def setting_color(self) -> None:
        value = self._prompt("Color mode (auto/always/never)", self.config.color_mode).lower()
        if value not in {mode.value for mode in ColorMode}:
            self.message = self.palette.error("Color mode must be auto, always or never.")
            return
        old = self.config.color_mode
        self.config.color_mode = value
        self._save_setting("color_mode", old)

    def setting_donor_root(self) -> None:
        value = self._prompt("Donor root", self.config.donor_root)
        old = self.config.donor_root
        self.config.donor_root = str(Path(value).expanduser())
        self._save_setting("donor_root", old)

    def setting_model_url(self) -> None:
        value = self._prompt("Model URL", self.config.model_url)
        if not value.startswith(("http://", "https://")):
            self.message = self.palette.error("Model URL must begin with http:// or https://.")
            return
        old = self.config.model_url
        self.config.model_url = value
        self._save_setting("model_url", old)

    def setting_model_name(self) -> None:
        value = self._prompt("Model name", self.config.model_name)
        old = self.config.model_name
        self.config.model_name = value
        self._save_setting("model_name", old)

    def setting_history(self) -> None:
        default = "yes" if self.config.save_history else "no"
        value = self._prompt("Save local conversation history? (yes/no)", default).lower()
        if value not in {"yes", "y", "no", "n"}:
            self.message = self.palette.error("Enter yes or no.")
            return
        old = self.config.save_history
        self.config.save_history = value in {"yes", "y"}
        self._save_setting("save_history", old)

    def setting_timeout(self) -> None:
        value = self._prompt("Model timeout in seconds", str(self.config.request_timeout))
        try:
            timeout = float(value)
            if not 1 <= timeout <= 3600:
                raise ValueError
        except ValueError:
            self.message = self.palette.error("Timeout must be between 1 and 3600 seconds.")
            return
        old = self.config.request_timeout
        self.config.request_timeout = timeout
        self._save_setting("request_timeout", old)

    def creator_vault_menu_items(self):
        """Return the five independent equipment toggles."""

        items = []

        for index, name in enumerate(
            EQUIPMENT_NAMES,
            start=1,
        ):
            state = self.config.equipment_states.get(
                name,
                False,
            )

            items.append(
                MenuItem(
                    str(index),
                    "{} - {}".format(
                        name.title(),
                        "ON" if state else "OFF",
                    ),
                )
            )

        items.append(
            MenuItem("0", "Back")
        )

        return tuple(items)

    def toggle_equipment(self, name: str) -> bool:
        """Toggle one Creator Vault module only."""

        if not self.config.creator_vault_unlocked:
            return False

        if name not in EQUIPMENT_NAMES:
            raise ValueError(
                "unknown Creator Vault equipment: {}".format(
                    name
                )
            )

        new_state = not self.config.equipment_states.get(
            name,
            False,
        )

        self.config.equipment_states[name] = new_state
        self.config.save()

        self.audit.write(
            "equipment_toggle_changed",
            equipment=name,
            state=new_state,
        )

        return new_state

    def creator_vault_screen(self) -> None:
        """Unlock the vault and control persistent equipment."""

        if not self.config.creator_vault_unlocked:
            self._header("CREATOR VAULT: LOCKED")

            try:
                code = self._input_line(
                    "Creator Vault code: "
                )
            except EOFError:
                return

            if not verify_creator_code(code):
                print(
                    self.palette.error(
                        "Creator Vault code was not accepted."
                    )
                )
                self._pause()
                return

            self.config.creator_vault_unlocked = True
            self.config.save()
            self.audit.write(
                "creator_vault_unlocked"
            )

        self._header(
            "CREATOR VAULT: UNLOCKED"
        )

        while True:
            choice = select_menu(
                "CREATOR VAULT: UNLOCKED",
                self.creator_vault_menu_items(),
                self.palette,
            )

            if choice == "0":
                return

            if not choice.isdigit():
                continue

            index = int(choice) - 1

            if not 0 <= index < len(EQUIPMENT_NAMES):
                continue

            self.toggle_equipment(
                EQUIPMENT_NAMES[index]
            )


    def about(self) -> None:
        self._header("ABOUT THRILLA-ZILLA")
        self._status("Creator", CREATOR_NAME)
        if self.config.owner_name.strip():
            self._status("Owner", self.config.owner_name.strip())
        print(self.palette.brand(f"Version {__version__}"))
        print(self.palette.muted("Phone-first • local-first • Android/Termux + Windows"))
        print()
        paragraphs = (
            "This alpha is the native Thrilla control shell: interactive UI, transparent routing, local model adapter, durable local history, donor inventory, diagnostics and audit metadata.",
            "Thrilla defines exactly {} experts across {} groups of {}. These 100 experts are separate from the 100 donor repositories. The donors remain external read-only study sources. Expert runtime orchestration is not yet implemented; this records the architecture without claiming active expert execution.".format(EXPERT_COUNT, len(EXPERT_GROUPS), EXPERTS_PER_GROUP),
            "Current boundary: autonomous tool execution, web research, repository editing, memory retrieval and self-repair gates are not yet implemented. The UI reports that boundary instead of pretending those actions happened.",
        )
        for paragraph in paragraphs:
            print(textwrap.fill(paragraph, width=min(terminal_width(), 68)) + "\n")
        print(self.palette.accent("Behavior priority:"))
        print("accuracy + safety → reliability → privacy → transparency → accountability")
        self._pause()


def checks_as_dicts(checks: Sequence[Check]) -> List[Dict[str, str]]:
    return [asdict(check) for check in checks]
