"""Regression tests for native wheel artifact selection."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HOOK_PATH = Path(__file__).resolve().parents[1] / "hatch_build.py"
SPEC = importlib.util.spec_from_file_location("wheel_build_hook", HOOK_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WheelBuildTests(unittest.TestCase):
    def initialize_hook(self, root, suffix, version="standard"):
        hook = MODULE.CustomHook(str(root), {}, {}, {}, "standard", "wheel")
        build_data = {}
        with patch.object(MODULE.sysconfig, "get_config_var", return_value=suffix):
            hook.initialize(version, build_data)
        return build_data

    def test_selects_only_current_interpreter_extension(self):
        for suffix in (".cpython-312-x86_64-linux-gnu.so", ".cp312-win_amd64.pyd"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = root / "package"
                package.mkdir()
                current = package / f"pocketsocket_server{suffix}"
                current.touch()
                (package / "pocketsocket_server.cpython-310-x86_64-linux-gnu.so").touch()
                (package / "pocketsocket_server.cp311-win_amd64.pyd").touch()
                data = self.initialize_hook(root, suffix)
                self.assertEqual(data["force_include"], {str(current): current.name})
                self.assertTrue(data["infer_tag"])
                self.assertFalse(data["pure_python"])

    def test_missing_current_extension_fails_even_with_stale_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package").mkdir()
            (root / "package" / "pocketsocket_server.so").touch()
            with self.assertRaisesRegex(RuntimeError, "Missing native extension"):
                self.initialize_hook(root, ".cp312-win_amd64.pyd")

    def test_missing_extension_suffix_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "native extension suffix"):
                self.initialize_hook(Path(directory), None)

    def test_editable_bootstrap_allows_building_extension_after_install(self):
        with tempfile.TemporaryDirectory() as directory:
            data = self.initialize_hook(Path(directory), ".so", version="editable")
            self.assertNotIn("force_include", data)


if __name__ == "__main__":
    unittest.main()