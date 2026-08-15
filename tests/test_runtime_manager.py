import importlib
import unittest


class RuntimeManagerTests(unittest.TestCase):

    def test_runtime_manager_defines_client_binding_boundary(self):
        try:
            manager = importlib.import_module(
                "thrilla.runtime.manager"
            )
        except Exception as error:
            self.fail(
                "runtime manager module must exist: {0}".format(
                    error
                )
            )

        manager_type = getattr(
            manager,
            "RuntimeManager",
            None,
        )

        binding_type = getattr(
            manager,
            "RuntimeClientBinding",
            None,
        )

        error_type = getattr(
            manager,
            "RuntimeBindingError",
            None,
        )

        self.assertTrue(
            callable(manager_type),
            "RuntimeManager must exist",
        )

        self.assertTrue(
            callable(binding_type),
            "RuntimeClientBinding must exist",
        )

        self.assertTrue(
            callable(error_type),
            "RuntimeBindingError must exist",
        )

    def test_manager_binds_reusable_external_server_to_local_model_client(self):
        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        runtime = manager.RuntimeManager()

        binder = getattr(
            runtime,
            "bind_external",
            None,
        )

        self.assertTrue(
            callable(binder),
            "bind_external must exist",
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("external-model",),
            expected_model="external-model",
            model_match=True,
            reusable=True,
            detail="models endpoint responded",
        )

        binding = binder(
            inspection
        )

        self.assertIsInstance(
            binding,
            manager.RuntimeClientBinding,
        )

        self.assertEqual(
            process.ProcessOwnership.EXTERNAL,
            binding.ownership,
        )

        self.assertEqual(
            "127.0.0.1",
            binding.host,
        )

        self.assertEqual(
            8080,
            binding.port,
        )

        self.assertEqual(
            "external-model",
            binding.model,
        )

        self.assertEqual(
            "http://127.0.0.1:8080/v1/chat/completions",
            binding.client.url,
        )

        self.assertEqual(
            "external-model",
            binding.client.model,
        )

    def test_manager_refuses_nonreusable_external_server(self):
        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )

        runtime = manager.RuntimeManager()

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("wrong-model",),
            expected_model="expected-model",
            model_match=False,
            reusable=False,
            detail="expected model not available",
        )

        with self.assertRaises(
            manager.RuntimeBindingError,
            msg=(
                "nonreusable external runtime "
                "must not become inference client"
            ),
        ):
            runtime.bind_external(
                inspection
            )

    def test_manager_binds_managed_record_with_explicit_model_id(self):
        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        runtime = manager.RuntimeManager()

        binder = getattr(
            runtime,
            "bind_managed",
            None,
        )

        self.assertTrue(
            callable(binder),
            "bind_managed must exist",
        )

        record = process.RuntimeProcessRecord(
            ownership=process.ProcessOwnership.THRILLA_MANAGED,
            pid=12345,
            executable="/usr/bin/llama-server",
            command=(
                "/usr/bin/llama-server",
                "-m",
                "/models/primary.gguf",
            ),
            model="/models/primary.gguf",
            port=8123,
            start_time="2026-08-15T12:00:00-05:00",
            owner_token="owner-token",
            log_path="/tmp/runtime.log",
        )

        binding = binder(
            record=record,
            host="127.0.0.1",
            model_id="thrilla-primary",
        )

        self.assertEqual(
            process.ProcessOwnership.THRILLA_MANAGED,
            binding.ownership,
        )

        self.assertEqual(
            8123,
            binding.port,
        )

        self.assertEqual(
            "thrilla-primary",
            binding.model,
        )

        self.assertEqual(
            "thrilla-primary",
            binding.client.model,
        )

        self.assertEqual(
            "http://127.0.0.1:8123/v1/chat/completions",
            binding.client.url,
        )

        self.assertNotEqual(
            record.model,
            binding.client.model,
            (
                "client model identifier must remain "
                "separate from GGUF path metadata"
            ),
        )

    def test_manager_refuses_external_record_as_managed_binding(self):
        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        process = importlib.import_module(
            "thrilla.runtime.process"
        )

        runtime = manager.RuntimeManager()

        record = process.RuntimeProcessRecord(
            ownership=process.ProcessOwnership.EXTERNAL,
            pid=12345,
            executable="/usr/bin/llama-server",
            command=(
                "/usr/bin/llama-server",
            ),
            model="external-model",
            port=8124,
            start_time="",
            owner_token="",
            log_path="",
        )

        with self.assertRaises(
            manager.RuntimeBindingError,
            msg=(
                "external record must not be "
                "reclassified as managed"
            ),
        ):
            runtime.bind_managed(
                record=record,
                host="127.0.0.1",
                model_id="external-model",
            )

    def test_manager_from_config_preserves_model_client_limit_policy(self):
        manager = importlib.import_module(
            "thrilla.runtime.manager"
        )
        health = importlib.import_module(
            "thrilla.runtime.health"
        )
        config_module = importlib.import_module(
            "thrilla.config"
        )

        factory = getattr(
            manager.RuntimeManager,
            "from_config",
            None,
        )

        self.assertTrue(
            callable(factory),
            "RuntimeManager.from_config must exist",
        )

        config = config_module.Config(
            donor_root="/tmp/donors",
            state_root="/tmp/state",
            limit_default_mode="on",
            limit_values={
                "model.request_timeout": 12.5,
                "network.remote_model": False,
            },
        )

        runtime = factory(
            config
        )

        inspection = health.ExistingServerInspection(
            host="127.0.0.1",
            port=8080,
            listening=True,
            bindable=False,
            openai_compatible=True,
            models=("policy-model",),
            expected_model="policy-model",
            model_match=True,
            reusable=True,
            detail="ready",
        )

        binding = runtime.bind_external(
            inspection
        )

        self.assertEqual(
            12.5,
            binding.client.timeout,
        )

        self.assertIs(
            False,
            binding.client.remote_policy,
        )


if __name__ == "__main__":
    unittest.main()
