import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import PSFFPKG as app


class PSFFPKGTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {}, clear=True).start()
        self.output = io.StringIO()
        redirect = contextlib.redirect_stdout(self.output)
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def make_tool(self, directory, name=None):
        directory.mkdir(parents=True, exist_ok=True)
        tool = directory / (name or app.TOOL_EXE)
        tool.write_text("fake executable")
        tool.chmod(0o755)
        return tool

    def test_explicit_tool_overrides_environment(self):
        tool = self.make_tool(self.root / "release with spaces")
        os.environ["UFS2TOOL_PATH"] = "/missing/environment/tool"
        self.assertEqual(app.locate_tool(str(tool)), str(tool))
        self.assertEqual(app.locate_tool(str(tool.parent)), str(tool))

    def test_environment_tool_and_invalid_override(self):
        tool = self.make_tool(self.root / "release")
        os.environ["UFS2TOOL_PATH"] = str(tool.parent)
        self.assertEqual(app.locate_tool(), str(tool))
        with self.assertRaises(FileNotFoundError):
            app.locate_tool(str(self.root / "missing"))

    def test_sibling_tool_works_from_another_working_directory(self):
        tool = self.make_tool(self.root / "script directory")
        with mock.patch.object(app, "__file__", str(tool.parent / "PSFFPKG.py")):
            self.assertEqual(app.locate_tool(), str(tool))

    def test_tool_in_path(self):
        tool = self.make_tool(self.root / "bin", app.TOOL_EXE.lower())
        os.environ["PATH"] = str(tool.parent)
        with mock.patch.object(app, "__file__", str(self.root / "PSFFPKG.py")):
            # Default macOS volumes can return the same file with different casing.
            self.assertTrue(Path(app.locate_tool()).samefile(tool))

    @unittest.skipIf(os.name == "nt", "POSIX executable permissions")
    def test_nonexecutable_tool_has_actionable_error(self):
        tool = self.make_tool(self.root)
        tool.chmod(0o644)
        with self.assertRaisesRegex(PermissionError, "chmod"):
            app.locate_tool(str(tool))

    @unittest.skipIf(os.name == "nt", "macOS/POSIX privilege behavior")
    def test_posix_does_not_request_windows_elevation(self):
        with mock.patch.object(app, "is_admin", side_effect=AssertionError):
            self.assertTrue(app.elevate_if_needed())

    def test_help_does_not_request_elevation(self):
        with mock.patch.object(sys, "argv", ["PSFFPKG.py", "--help"]), \
             mock.patch.object(app, "elevate_if_needed") as elevate:
            with self.assertRaises(SystemExit) as result:
                app.main()
            self.assertEqual(result.exception.code, 0)
            elevate.assert_not_called()

    def test_interactive_path_preserves_apostrophes(self):
        path = str(self.root / "John's Game")
        with mock.patch("builtins.input", return_value=f'"{path}"'):
            self.assertEqual(app.prompt_path("path: "), path)

    def test_package_failure_and_interrupt_preserve_existing_file(self):
        source = self.root / "Game with spaces"
        source.mkdir()
        (source / "file").write_bytes(b"input")
        output = self.root / "output"
        output.mkdir()
        package = output / f"{source.name}.ffpkg"
        package.write_bytes(b"original package")
        for error in (subprocess.CalledProcessError(7, "tool"), KeyboardInterrupt()):
            with mock.patch.object(app.subprocess, "run", side_effect=error):
                with self.assertRaises(type(error)):
                    app.create_package(source, output, "/tool with spaces/UFS2Tool")
            self.assertEqual(package.read_bytes(), b"original package")
            self.assertEqual(list(output.iterdir()), [package])

    def test_package_success_replaces_existing_file(self):
        source = self.root / "Jogo de João"
        source.mkdir()
        output = self.root / "output"
        output.mkdir()
        package = output / f"{source.name}.ffpkg"
        package.write_bytes(b"old package")

        def create_image(command, check):
            self.assertTrue(check)
            self.assertEqual(command[-2], str(source))
            self.assertEqual(command[0], "/tool with spaces/UFS2Tool")
            Path(command[-1]).write_bytes(b"new image")

        with mock.patch.object(app.subprocess, "run", side_effect=create_image):
            self.assertEqual(app.create_package(source, output, "/tool with spaces/UFS2Tool"), package)
        self.assertEqual(package.read_bytes(), b"new image")
        self.assertEqual(list(output.iterdir()), [package])

    def test_output_cannot_be_inside_input(self):
        source = self.root / "game"
        source.mkdir()
        with mock.patch.object(app.subprocess, "run") as run:
            for output in (source, source / "packages"):
                with self.assertRaisesRegex(ValueError, "outside"):
                    app.create_package(source, output, "/tool")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
