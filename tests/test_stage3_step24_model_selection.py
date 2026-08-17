"""Stage 3 Step 24 preferred GGUF model selection RED tests."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from thrilla.config import Config
import thrilla.app as app_module


class PreferredModelConfigTests(unittest.TestCase):
    def test_new_config_defaults_to_empty_preferred_model_path(self):
        config = Config.defaults()
        self.assertEqual(config.preferred_model_path, "")

    def test_old_config_without_preferred_model_path_still_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            payload = {
                "donor_root": str(Path(tmp) / "donors"),
                "state_root": tmp,
                "model_name": "local-model",
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            config = Config.load(path)
            self.assertEqual(config.preferred_model_path, "")

    def test_preferred_model_path_survives_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            config = Config(
                donor_root=str(Path(tmp) / "donors"),
                state_root=tmp,
            )
            config.preferred_model_path = "/models/code-model.Q4_K_M.gguf"
            config.save(path)
            loaded = Config.load(path)
            self.assertEqual(
                loaded.preferred_model_path,
                "/models/code-model.Q4_K_M.gguf",
            )


class PreferredModelUITests(unittest.TestCase):
    def make_app(self, preferred=""):
        app = object.__new__(app_module.ThrillaApp)
        app.config = SimpleNamespace(
            preferred_model_path=preferred,
            model_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="local-model",
        )
        app._header = Mock()
        app._status = Mock()
        app._pause = Mock()
        app._prompt = Mock(return_value="")
        app.audit = Mock()
        app.runtime_manager = Mock()
        return app

    def test_preferred_model_screen_exists(self):
        app = self.make_app()
        self.assertTrue(hasattr(app, "preferred_model_screen"))

    def test_preferred_path_does_not_claim_model_is_active(self):
        app = self.make_app("/models/preferred.gguf")
        app.preferred_model_screen()
        labels = [call.args[0] for call in app._status.call_args_list]
        self.assertNotIn("Active model", labels)

    def test_missing_preferred_file_is_reported_as_missing(self):
        app = self.make_app("/definitely/missing/preferred.gguf")
        app.preferred_model_screen()
        rendered = " ".join(
            str(arg)
            for call in app._status.call_args_list
            for arg in call.args
        ).lower()
        self.assertIn("missing", rendered)


class PreferredModelSelectionTests(unittest.TestCase):
    def make_app(self):
        config = SimpleNamespace(
            preferred_model_path="",
            model_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="local-model",
            state_root="/tmp/thrilla-state",
            save=Mock(),
        )
        app = object.__new__(app_module.ThrillaApp)
        app.config = config
        app._header = Mock()
        app._status = Mock()
        app._pause = Mock()
        app._prompt = Mock(return_value="")
        app.audit = Mock()
        app.runtime_manager = Mock()
        app.message = ""
        return app

    def test_inventory_renders_candidate_metadata(self):
        app = self.make_app()
        candidate = SimpleNamespace(
            path="/models/coder.Q4_K_M.gguf",
            filename="coder.Q4_K_M.gguf",
            size_bytes=1048576,
            role=SimpleNamespace(value="coding"),
            quantization="Q4_K_M",
            readable=True,
            compatibility="unknown",
        )
        app._model_inventory = Mock(return_value=[candidate])

        app.model_inventory_screen()

        rendered = " ".join(
            str(arg)
            for call in app._status.call_args_list
            for arg in call.args
        )
        self.assertIn("coder.Q4_K_M.gguf", rendered)
        self.assertIn("coding", rendered)
        self.assertIn("Q4_K_M", rendered)
        self.assertIn("/models/coder.Q4_K_M.gguf", rendered)

    def test_selecting_existing_gguf_persists_without_changing_model_alias(self):
        app = self.make_app()

        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "chosen.Q4_K_M.gguf"
            model.write_bytes(b"GGUF")
            app._prompt.return_value = str(model)

            original_alias = app.config.model_name
            app.preferred_model_screen()

            self.assertEqual(
                app.config.preferred_model_path,
                str(model.resolve()),
            )
            self.assertEqual(app.config.model_name, original_alias)
            app.config.save.assert_called_once()
            app.runtime_manager.ready_binding.assert_not_called()


if __name__ == "__main__":
    unittest.main()
