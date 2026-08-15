import importlib
import unittest


class RuntimeCommandTests(unittest.TestCase):

    def test_build_command_contains_structured_runtime_arguments(self):
        try:
            command = importlib.import_module(
                "thrilla.runtime.command"
            )
        except Exception as error:
            self.fail(
                "runtime command module must exist: {0}".format(
                    error
                )
            )

        config_type = getattr(
            command,
            "RuntimeCommandConfig",
            None,
        )
        builder = getattr(
            command,
            "build_llama_server_command",
            None,
        )

        self.assertTrue(
            callable(config_type),
            "RuntimeCommandConfig must exist",
        )
        self.assertTrue(
            callable(builder),
            "build_llama_server_command must exist",
        )

        config = config_type(
            executable="/usr/bin/llama-server",
            model="/models/primary.gguf",
            alias="thrilla-primary",
            host="127.0.0.1",
            port=8080,
            context_size=4096,
            parallel_slots=2,
        )

        self.assertEqual(
            [
                "/usr/bin/llama-server",
                "-m",
                "/models/primary.gguf",
                "-a",
                "thrilla-primary",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "-c",
                "4096",
                "-np",
                "2",
            ],
            builder(config),
        )

    def test_build_command_omits_optional_limits_when_unset(self):
        command = importlib.import_module(
            "thrilla.runtime.command"
        )

        config = command.RuntimeCommandConfig(
            executable="llama-server",
            model="/models/primary.gguf",
            alias="thrilla",
            host="127.0.0.1",
            port=8080,
            context_size=None,
            parallel_slots=None,
        )

        result = command.build_llama_server_command(
            config
        )

        self.assertNotIn("-c", result)
        self.assertNotIn("-np", result)

    def test_build_command_appends_device_specific_arguments(self):
        command = importlib.import_module(
            "thrilla.runtime.command"
        )

        config = command.RuntimeCommandConfig(
            executable="llama-server",
            model="/models/primary.gguf",
            alias="thrilla",
            host="127.0.0.1",
            port=8080,
            context_size=4096,
            parallel_slots=1,
            extra_args=(
                "--threads",
                "8",
                "--gpu-layers",
                "20",
            ),
        )

        result = command.build_llama_server_command(
            config
        )

        self.assertEqual(
            [
                "--threads",
                "8",
                "--gpu-layers",
                "20",
            ],
            result[-4:],
        )


if __name__ == "__main__":
    unittest.main()
