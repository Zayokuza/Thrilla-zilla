import importlib
import unittest


class RuntimeStateMachineTests(unittest.TestCase):
    def test_state_transition_records_required_metadata(self):
        state = importlib.import_module("thrilla.runtime.state")

        self.assertTrue(
            hasattr(state, "StateTransition"),
            "runtime.state must define StateTransition",
        )

        transition = state.StateTransition(
            previous=state.RuntimeState.STOPPED,
            next=state.RuntimeState.STARTING,
            timestamp="2026-08-13T21:33:00-05:00",
            actor="RuntimeManager",
            reason="inference requested",
            model="/models/example.gguf",
            pid=12345,
            elapsed=0.25,
            result="started",
        )

        self.assertEqual(state.RuntimeState.STOPPED, transition.previous)
        self.assertEqual(state.RuntimeState.STARTING, transition.next)
        self.assertEqual(
            "2026-08-13T21:33:00-05:00",
            transition.timestamp,
        )
        self.assertEqual("RuntimeManager", transition.actor)
        self.assertEqual("inference requested", transition.reason)
        self.assertEqual("/models/example.gguf", transition.model)
        self.assertEqual(12345, transition.pid)
        self.assertEqual(0.25, transition.elapsed)
        self.assertEqual("started", transition.result)

    def test_state_machine_records_legal_transition(self):
        state = importlib.import_module("thrilla.runtime.state")

        self.assertTrue(
            hasattr(state, "RuntimeStateMachine"),
            "runtime.state must define RuntimeStateMachine",
        )

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.STOPPED,
        )

        transition = machine.transition(
            state.RuntimeState.STARTING,
            actor="RuntimeManager",
            reason="inference requested",
            model="/models/example.gguf",
            pid=12345,
            elapsed=0.25,
            result="starting",
        )

        self.assertEqual(state.RuntimeState.STARTING, machine.current)
        self.assertEqual(1, len(machine.history))

        self.assertIs(transition, machine.history[0])
        self.assertEqual(state.RuntimeState.STOPPED, transition.previous)
        self.assertEqual(state.RuntimeState.STARTING, transition.next)
        self.assertTrue(transition.timestamp)
        self.assertEqual("RuntimeManager", transition.actor)
        self.assertEqual("inference requested", transition.reason)
        self.assertEqual("/models/example.gguf", transition.model)
        self.assertEqual(12345, transition.pid)
        self.assertEqual(0.25, transition.elapsed)
        self.assertEqual("starting", transition.result)

    def test_state_machine_rejects_illegal_transition_without_mutation(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.STOPPED,
        )

        try:
            machine.transition(
                state.RuntimeState.READY,
                actor="RuntimeManager",
                reason="invalid direct readiness jump",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.0,
                result="ready",
            )
        except Exception as error:
            self.assertIn("STOPPED", str(error).upper())
            self.assertIn("READY", str(error).upper())
        else:
            self.fail(
                "STOPPED -> READY must fail visibly as an illegal transition"
            )

        self.assertEqual(state.RuntimeState.STOPPED, machine.current)
        self.assertEqual([], machine.history)

    def test_state_machine_allows_starting_to_loading_model(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.STARTING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.LOADING_MODEL,
                actor="RuntimeManager",
                reason="llama-server process started",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.75,
                result="loading",
            )
        except Exception as error:
            self.fail(
                "STARTING -> LOADING_MODEL must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.LOADING_MODEL,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.STARTING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.LOADING_MODEL,
            transition.next,
        )

    def test_state_machine_allows_loading_model_to_health_checking(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.LOADING_MODEL,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.HEALTH_CHECKING,
                actor="RuntimeManager",
                reason="model load completed",
                model="/models/example.gguf",
                pid=12345,
                elapsed=1.25,
                result="checking",
            )
        except Exception as error:
            self.fail(
                "LOADING_MODEL -> HEALTH_CHECKING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.HEALTH_CHECKING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.LOADING_MODEL,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.HEALTH_CHECKING,
            transition.next,
        )

    def test_state_machine_allows_health_checking_to_ready(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.HEALTH_CHECKING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.READY,
                actor="RuntimeManager",
                reason="runtime readiness checks passed",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.20,
                result="ready",
            )
        except Exception as error:
            self.fail(
                "HEALTH_CHECKING -> READY must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.READY,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.HEALTH_CHECKING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.READY,
            transition.next,
        )

    def test_state_machine_allows_ready_to_busy(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.READY,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.BUSY,
                actor="RuntimeManager",
                reason="inference request started",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.0,
                result="busy",
            )
        except Exception as error:
            self.fail(
                "READY -> BUSY must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.BUSY,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.READY,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.BUSY,
            transition.next,
        )

    def test_state_machine_allows_busy_to_ready(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.BUSY,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.READY,
                actor="RuntimeManager",
                reason="inference request completed",
                model="/models/example.gguf",
                pid=12345,
                elapsed=2.50,
                result="ready",
            )
        except Exception as error:
            self.fail(
                "BUSY -> READY must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.READY,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.BUSY,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.READY,
            transition.next,
        )

    def test_state_machine_allows_ready_to_stopping(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.READY,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.STOPPING,
                actor="RuntimeManager",
                reason="managed runtime shutdown requested",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.0,
                result="stopping",
            )
        except Exception as error:
            self.fail(
                "READY -> STOPPING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.STOPPING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.READY,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.STOPPING,
            transition.next,
        )

    def test_state_machine_allows_stopping_to_stopped(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.STOPPING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.STOPPED,
                actor="RuntimeManager",
                reason="managed runtime exited cleanly",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.50,
                result="stopped",
            )
        except Exception as error:
            self.fail(
                "STOPPING -> STOPPED must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.STOPPED,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.STOPPING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.STOPPED,
            transition.next,
        )

    def test_state_machine_allows_unknown_to_discovering(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.UNKNOWN,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.DISCOVERING,
                actor="RuntimeManager",
                reason="runtime discovery started",
                model="",
                pid=0,
                elapsed=0.0,
                result="discovering",
            )
        except Exception as error:
            self.fail(
                "UNKNOWN -> DISCOVERING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.DISCOVERING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.UNKNOWN,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.DISCOVERING,
            transition.next,
        )

    def test_state_machine_allows_discovering_to_selecting(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.DISCOVERING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.SELECTING,
                actor="RuntimeManager",
                reason="runtime and model discovery completed",
                model="",
                pid=0,
                elapsed=0.25,
                result="selecting",
            )
        except Exception as error:
            self.fail(
                "DISCOVERING -> SELECTING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.SELECTING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.DISCOVERING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.SELECTING,
            transition.next,
        )

    def test_state_machine_allows_selecting_to_starting(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.SELECTING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.STARTING,
                actor="RuntimeManager",
                reason="model selected for managed startup",
                model="/models/example.gguf",
                pid=0,
                elapsed=0.10,
                result="starting",
            )
        except Exception as error:
            self.fail(
                "SELECTING -> STARTING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.STARTING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.SELECTING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.STARTING,
            transition.next,
        )

    def test_state_machine_allows_starting_to_failed(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.STARTING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.FAILED,
                actor="RuntimeManager",
                reason="managed runtime failed to start",
                model="/models/example.gguf",
                pid=0,
                elapsed=1.25,
                result="startup_failed",
            )
        except Exception as error:
            self.fail(
                "STARTING -> FAILED must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.FAILED,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.STARTING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.FAILED,
            transition.next,
        )
        self.assertEqual(
            "managed runtime failed to start",
            transition.reason,
        )
        self.assertEqual(
            "startup_failed",
            transition.result,
        )

    def test_state_machine_allows_loading_model_to_failed(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.LOADING_MODEL,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.FAILED,
                actor="RuntimeManager",
                reason="model load failed",
                model="/models/example.gguf",
                pid=12345,
                elapsed=1.75,
                result="load_failed",
            )
        except Exception as error:
            self.fail(
                "LOADING_MODEL -> FAILED must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.FAILED,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.LOADING_MODEL,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.FAILED,
            transition.next,
        )

    def test_state_machine_allows_health_checking_to_failed(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.HEALTH_CHECKING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.FAILED,
                actor="RuntimeManager",
                reason="runtime readiness check failed",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.75,
                result="health_failed",
            )
        except Exception as error:
            self.fail(
                "HEALTH_CHECKING -> FAILED must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.FAILED,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.HEALTH_CHECKING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.FAILED,
            transition.next,
        )

    def test_state_machine_allows_crashed_to_recovering(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.CRASHED,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.RECOVERING,
                actor="RuntimeManager",
                reason="unexpected managed runtime exit detected",
                model="/models/example.gguf",
                pid=12345,
                elapsed=0.0,
                result="recovery_started",
            )
        except Exception as error:
            self.fail(
                "CRASHED -> RECOVERING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.RECOVERING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.CRASHED,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.RECOVERING,
            transition.next,
        )
        self.assertEqual(
            "recovery_started",
            transition.result,
        )

    def test_state_machine_allows_recovering_to_starting(self):
        state = importlib.import_module("thrilla.runtime.state")

        machine = state.RuntimeStateMachine(
            initial=state.RuntimeState.RECOVERING,
        )

        try:
            transition = machine.transition(
                state.RuntimeState.STARTING,
                actor="RuntimeManager",
                reason="recovery retry starting managed runtime",
                model="/models/example.gguf",
                pid=0,
                elapsed=0.25,
                result="restart_started",
            )
        except Exception as error:
            self.fail(
                "RECOVERING -> STARTING must be legal: {0}".format(
                    error
                )
            )

        self.assertEqual(
            state.RuntimeState.STARTING,
            machine.current,
        )
        self.assertEqual(1, len(machine.history))
        self.assertIs(transition, machine.history[0])
        self.assertEqual(
            state.RuntimeState.RECOVERING,
            transition.previous,
        )
        self.assertEqual(
            state.RuntimeState.STARTING,
            transition.next,
        )
        self.assertEqual(
            "restart_started",
            transition.result,
        )


if __name__ == "__main__":
    unittest.main()
