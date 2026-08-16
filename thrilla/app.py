"""Interactive Thrilla application designed for a narrow phone terminal."""

import textwrap
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from . import __version__
from .audit import AuditLog
from .catalog import CORE_DONORS, DonorSpec, phase_one_categories
from .colors import ColorMode, Palette
from .config import Config
from .diagnostics import Check, platform_name, run_checks
from .donors import DonorRegistry, DonorState
from .history import ConversationHistory
from .model import LocalModelClient, ModelError
from .router import Route, route_request
from .runtime.manager import RuntimeBindingError, RuntimeManager
from .terminal import MenuItem, clear_screen, select_menu, terminal_width


MAIN_MENU = (
    MenuItem("1", "Ask Thrilla", "Chat; requests are routed automatically."),
    MenuItem("2", "Donor Library", "Inspect the 100 core and specialist sources."),
    MenuItem("3", "Route Inspector", "See where a request will be sent and why."),
    MenuItem("4", "Local Model", "Check the local OpenAI-compatible endpoint."),
    MenuItem("5", "Diagnostics", "Verify Python, Git, donors, storage and model."),
    MenuItem("6", "Conversation History", "Review or clear locally saved chat."),
    MenuItem("7", "Activity Log", "Review metadata-only operational events."),
    MenuItem("8", "Settings", "Colors, paths, model and local history."),
    MenuItem("9", "About", "Version, principles and current capabilities."),
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

SETTINGS_MENU = (
    MenuItem("1", "Color Mode", "auto, always or never"),
    MenuItem("2", "Donor Root", "Location of Thrilla-codebases"),
    MenuItem("3", "Model URL", "Local OpenAI-compatible chat endpoint"),
    MenuItem("4", "Model Name", "Name sent with chat requests"),
    MenuItem("5", "Save Conversation History", "Local JSONL memory"),
    MenuItem("6", "Model Timeout", "Seconds before a request is cancelled"),
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
        self.model = self._model_client()
        self.message = ""

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
            "4": self.model_screen,
            "5": self.diagnostics_screen,
            "6": self.history_screen,
            "7": self.audit_screen,
            "8": self.settings,
            "9": self.about,
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
        }

    def run(self) -> int:
        self.audit.write("app_started", version=__version__, platform=platform_name())
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
            messages = [*previous, {"role": "user", "content": prompt}]
            if self.config.save_history:
                self.history.append("user", prompt, decision.route.value)
            try:
                print(self.palette.muted("Thrilla is thinking…"))
                binding = self.runtime_manager.ready_binding(
                    self.config.model_url,
                    self.config.model_name,
                )
                answer = binding.client.chat(
                    messages,
                    decision.route.value,
                )
            except (ModelError, RuntimeBindingError) as error:
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

    def about(self) -> None:
        self._header("ABOUT THRILLA-ZILLA")
        print(self.palette.brand(f"Version {__version__}"))
        print(self.palette.muted("Phone-first • local-first • Android/Termux + Windows"))
        print()
        paragraphs = (
            "This alpha is the native Thrilla control shell: interactive UI, transparent routing, local model adapter, durable local history, donor inventory, diagnostics and audit metadata.",
            "The 100 repositories are external study sources—not one giant dependency tree. Any borrowed mechanism must pass license review, isolated tests, integration tests and keep-or-rollback evaluation.",
            "Current boundary: autonomous tool execution, web research, repository editing, memory retrieval and self-repair gates are not yet implemented. The UI reports that boundary instead of pretending those actions happened.",
        )
        for paragraph in paragraphs:
            print(textwrap.fill(paragraph, width=min(terminal_width(), 68)) + "\n")
        print(self.palette.accent("Behavior priority:"))
        print("accuracy + safety → reliability → privacy → transparency → accountability")
        self._pause()


def checks_as_dicts(checks: Sequence[Check]) -> List[Dict[str, str]]:
    return [asdict(check) for check in checks]
