import importlib
import importlib.util
import unittest


class LimitControlBootstrapTests(unittest.TestCase):
    def test_limit_control_module_exists(self):
        spec = importlib.util.find_spec("thrilla.limits")

        self.assertIsNotNone(
            spec,
            "Stage 3 requires thrilla.limits before runtime limits are added.",
        )

    def test_limit_mode_defines_on_auto_off(self):
        limits = importlib.import_module("thrilla.limits")
        limit_mode = getattr(limits, "LimitMode", None)

        self.assertIsNotNone(
            limit_mode,
            "Universal Limit Control requires a LimitMode enum.",
        )
        self.assertEqual("on", limit_mode.ON.value)
        self.assertEqual("auto", limit_mode.AUTO.value)
        self.assertEqual("off", limit_mode.OFF.value)

    def test_default_registry_contains_managed_startup(self):
        limits = importlib.import_module("thrilla.limits")
        registry = getattr(limits, "DEFAULT_LIMITS", None)

        self.assertIsNotNone(
            registry,
            "Universal Limit Control requires a default limit registry.",
        )

        spec = registry.get("runtime.managed_startup")

        self.assertEqual("runtime.managed_startup", spec.name)
        self.assertEqual(limits.LimitMode.AUTO, spec.default_mode)

    def test_default_registry_contains_every_required_limit(self):
        limits = importlib.import_module("thrilla.limits")

        required = {
            "runtime.managed_startup",
            "runtime.startup_timeout",
            "runtime.health_timeout",
            "runtime.shutdown_timeout",
            "runtime.restart_limit",
            "runtime.crash_retry_limit",
            "runtime.model_size",
            "runtime.context_size",
            "runtime.batch_size",
            "runtime.parallel_slots",
            "runtime.cpu_threads",
            "runtime.gpu_layers",
            "runtime.ram_budget",
            "runtime.process_count",
            "runtime.queue_depth",
            "runtime.request_timeout",
            "runtime.response_tokens",
            "runtime.model_switch_frequency",
            "runtime.keep_alive",
            "runtime.idle_shutdown",
            "model.request_timeout",
            "memory.history_turns",
            "network.remote_model",
            "network.public_read",
            "network.write_actions",
            "network.fetch_timeout",
            "network.fetch_bytes",
            "network.redirects",
            "network.research_workers",
            "network.cache_entries",
            "network.cache_age_seconds",
            "donor.git_timeout",
        }

        names_method = getattr(limits.DEFAULT_LIMITS, "names", None)
        actual = set(names_method()) if names_method is not None else set()

        self.assertEqual(required, actual)

    def test_registry_rejects_duplicate_limit_names(self):
        limits = importlib.import_module("thrilla.limits")

        duplicate_specs = (
            limits.LimitSpec(
                name="runtime.example",
                default_mode=limits.LimitMode.AUTO,
            ),
            limits.LimitSpec(
                name="runtime.example",
                default_mode=limits.LimitMode.ON,
            ),
        )

        with self.assertRaises(ValueError):
            limits.LimitRegistry(duplicate_specs)

    def test_limit_specs_expose_default_value_and_description(self):
        limits = importlib.import_module("thrilla.limits")
        spec = limits.DEFAULT_LIMITS.get("runtime.managed_startup")

        self.assertTrue(
            hasattr(spec, "default_value"),
            "LimitSpec requires default_value.",
        )
        self.assertTrue(
            hasattr(spec, "description"),
            "LimitSpec requires a human-readable description.",
        )

    def test_existing_limit_defaults_are_preserved(self):
        limits = importlib.import_module("thrilla.limits")

        expected = {
            "model.request_timeout": 90.0,
            "memory.history_turns": 12,
            "network.remote_model": False,
            "donor.git_timeout": 4.0,
        }

        actual = {
            name: getattr(
                limits.DEFAULT_LIMITS.get(name),
                "default_value",
                object(),
            )
            for name in expected
        }

        self.assertEqual(expected, actual)

    def test_resolve_implements_on_auto_off(self):
        limits = importlib.import_module("thrilla.limits")
        resolve = getattr(limits.DEFAULT_LIMITS, "resolve", None)

        if not callable(resolve):
            self.fail("LimitRegistry requires resolve().")

        on = resolve(
            "model.request_timeout",
            mode=limits.LimitMode.ON,
            configured_value=120.0,
            auto_value=75.0,
        )
        self.assertEqual(limits.LimitMode.ON, on.mode)
        self.assertEqual(120.0, on.value)
        self.assertEqual("configured", on.source)
        self.assertTrue(on.explanation)

        auto = resolve(
            "model.request_timeout",
            mode=limits.LimitMode.AUTO,
            configured_value=120.0,
            auto_value=75.0,
        )
        self.assertEqual(limits.LimitMode.AUTO, auto.mode)
        self.assertEqual(75.0, auto.value)
        self.assertEqual("auto", auto.source)
        self.assertTrue(auto.explanation)

        off = resolve(
            "model.request_timeout",
            mode=limits.LimitMode.OFF,
            configured_value=120.0,
            auto_value=75.0,
        )
        self.assertEqual(limits.LimitMode.OFF, off.mode)
        self.assertIsNone(off.value)
        self.assertEqual("off", off.source)
        self.assertTrue(off.explanation)


if __name__ == "__main__":
    unittest.main()
