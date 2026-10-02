#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import argparse
import tempfile
import shutil
import ctypes
import shlex
import time
from pathlib import Path

TOOL_EXE = "UFS2Tool.exe" if os.name == "nt" else "UFS2Tool"


def is_admin():
    """Check administrator privileges on Windows only."""
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def elevate_if_needed():
    """Request Windows elevation; ordinary image files need no sudo on macOS."""
    if os.name != "nt" or is_admin():
        return True

    print("[INFO] Administrator privileges required. Requesting elevation...")
    # Preserve spaces and quotes in paths when restarting through UAC.
    arguments = sys.argv[1:] if getattr(sys, "frozen", False) else [
        str(Path(sys.argv[0]).resolve()), *sys.argv[1:]
    ]
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, subprocess.list2cmdline(arguments),
        os.getcwd(), 1
    )
    if ret <= 32:
        print("[ERROR] Failed to elevate. Please run as Administrator manually.")
        sys.exit(1)
    sys.exit(0)


def validate_tool(path):
    """Return an absolute executable path, or explain why it cannot run."""
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"UFS2Tool executable not found: {path}")
    if os.name != "nt" and not os.access(path, os.X_OK):
        raise PermissionError(
            f"UFS2Tool is not executable. Run: chmod +x {shlex.quote(str(path))}"
        )
    return str(path)


def locate_tool(tool=None):
    """Find a native UFS2Tool, accepting an explicit executable or directory."""
    names = (TOOL_EXE, TOOL_EXE.lower())
    configured = tool if tool is not None else os.environ.get("UFS2TOOL_PATH")
    if configured is not None:
        path = Path(configured).expanduser()
        if path.is_dir():
            for name in names:
                candidate = path / name
                if candidate.is_file():
                    return validate_tool(candidate)
            raise FileNotFoundError(f"{TOOL_EXE} not found in {path}")
        return validate_tool(path)

    script_dir = Path(
        sys.executable if getattr(sys, "frozen", False) else __file__
    ).resolve().parent
    for name in names:
        candidate = script_dir / name
        if candidate.is_file():
            return validate_tool(candidate)
    for name in names:
        candidate = shutil.which(name)
        if candidate:
            return validate_tool(candidate)

    raise FileNotFoundError(
        f"{TOOL_EXE} not found. Use --tool /path/to/{TOOL_EXE}, set "
        "UFS2TOOL_PATH, or place the tool next to the script or in PATH."
    )


def calculate_directory_size_bytes(path):
    """Calculate the total size of files in a directory."""
    return sum(entry.stat().st_size for entry in Path(path).rglob("*") if entry.is_file())


def run_newfs_with_D(tool_path, input_dir, output_image):
    """Create a UFS2 image, streaming UFS2Tool's output to the console."""
    cmd = [
        tool_path, "newfs", "-O", "2", "-b", "32768", "-f", "4096",
        "-D", str(input_dir), str(output_image)
    ]
    display_cmd = subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)
    print(f"[INFO] Executing command: {display_cmd}", flush=True)
    print("[INFO] Creating UFS2 image... (this may take a while)", flush=True)
    print("-" * 50, flush=True)
    subprocess.run(cmd, check=True)
    print("-" * 50)
    print("[INFO] Image creation completed successfully.")
    return output_image


def prompt_path(prompt):
    """Accept pasted paths without removing apostrophes inside file names."""
    value = input(prompt).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return str(Path(value).expanduser()) if value else ""


def interactive_input():
    """Get input and output paths in interactive mode."""
    print("=== Create UFS2 image and convert to ffpkg ===")
    while True:
        in_dir = prompt_path("Enter the game dump folder path: ")
        if not in_dir:
            print("❌ Path cannot be empty.")
        elif not Path(in_dir).is_dir():
            print("❌ Directory is not valid.")
        else:
            break
    out_dir = prompt_path("Enter output folder path (default: current directory): ")
    return in_dir, out_dir or os.getcwd()


def create_package(input_dir, output_dir, tool_path):
    input_dir = Path(input_dir).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory '{input_dir}' does not exist.")
    # The tool copies everything in the input tree, including any temporary image.
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("Choose an output folder outside the game dump folder.")
    output_dir.mkdir(parents=True, exist_ok=True)

    folder_name = input_dir.name or "output"
    final_path = output_dir / f"{folder_name}.ffpkg"
    bytes_size = calculate_directory_size_bytes(input_dir)
    print(f"[INFO] Actual file size: {bytes_size:,} bytes")
    print("[INFO] Image size is calculated automatically by UFS2Tool.")
    print(f"[INFO] Final file: {final_path}")

    with tempfile.NamedTemporaryFile(
        dir=output_dir, prefix=f"{folder_name}_", suffix=".tmp", delete=False
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        run_newfs_with_D(tool_path, input_dir, temp_path)
        os.replace(temp_path, final_path)
        print(f"✅ UFS2 image successfully created and renamed to ffpkg:\n   {final_path}")
    finally:
        # Also clean up on a failed subprocess or Ctrl+C; preserve any old package.
        temp_path.unlink(missing_ok=True)
    return final_path


def main():
    parser = argparse.ArgumentParser(
        description="Create a UFS2 image from a directory and convert to ffpkg"
    )
    parser.add_argument("input_dir", nargs="?", help="Path to the game dump folder")
    parser.add_argument(
        "output_dir", nargs="?", default=os.getcwd(),
        help="Path to output folder (default: current directory)"
    )
    parser.add_argument(
        "--tool", metavar="PATH",
        help="Path to the UFS2Tool executable or release folder "
             "(default: UFS2TOOL_PATH, script folder, then PATH)"
    )
    args = parser.parse_args()
    elevate_if_needed()
    interactive = args.input_dir is None
    try:
        tool_path = locate_tool(args.tool)
        print(f"[INFO] Using UFS2Tool: {tool_path}")
        if interactive:
            input_dir, output_dir = interactive_input()
        else:
            input_dir, output_dir = args.input_dir, args.output_dir
        create_package(input_dir, output_dir, tool_path)
    except subprocess.CalledProcessError as error:
        print(f"❌ UFS2Tool execution failed (exit code {error.returncode}).")
        return 1
    except (OSError, ValueError) as error:
        print(f"❌ {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Cancelled.")
        return 130

    if os.name == "nt" and interactive:
        print("\n[INFO] Window will close automatically in 5 seconds...")
        time.sleep(5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
