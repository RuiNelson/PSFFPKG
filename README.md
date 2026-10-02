# PSFFPKG - PS5 UFS2 Image Creator

**PSFFPKG** is a lightweight utility designed to automate the creation of `.ffpkg` (UFS2) images for the PlayStation 5. It serves as a wrapper for **SvenGDK's UFS2Tool**, streamlining the process of converting game dump directories into installable package files supported by the **ShadowMount** payload.

## 🚀 Features

- **Automated conversion:** Displays the input directory size and lets UFS2Tool calculate the image size, including filesystem overhead.
- **Automatic naming:** Saves the package as `GameDumpFolderName.ffpkg`.
- **Interactive and command-line modes:** Enter paths at the prompts or pass them as arguments for scripting.
- **Windows and macOS support:** Uses the native UFS2Tool executable for each platform.
- **Flexible tool location:** Finds UFS2Tool automatically or accepts a path through `--tool` or `UFS2TOOL_PATH`.
- **Safe replacement:** Replaces an existing package only after image creation succeeds and cleans up temporary files on failure or cancellation.

---

## ⚠️ Requirements

| Requirement | Windows | macOS |
| --- | --- | --- |
| PSFFPKG | `PSFFPKG.exe` from [releases](https://github.com/sinajet/PSFFPKG/releases) | `PSFFPKG.py` from this repository, with Python 3.8 or later |
| UFS2Tool | Windows release containing `UFS2Tool.exe` | macOS release containing `UFS2Tool`; prefer the self-contained version |
| Permissions | Administrator privileges; PSFFPKG requests elevation automatically | Image creation does not require `sudo` |

Download the matching [UFS2Tool release](https://github.com/SvenGDK/UFS2Tool/releases/) and keep the executable with all its accompanying files. On Apple Silicon, the macOS x64 release requires Rosetta 2. No additional Python packages are needed to run `PSFFPKG.py`.

### PlayStation 5

To use the generated packages, you need a **PlayStation 5** running compatible firmware and the **ShadowMount payload v1.4 or later** with UFS mounting support.

- [Download ShadowMount (adel-ailane)](https://github.com/adel-ailane/ShadowMount)

## Installation

### Windows

1. Download and extract the Windows **UFS2Tool** release.
2. Download **PSFFPKG.exe** from the [PSFFPKG releases](https://github.com/sinajet/PSFFPKG/releases).
3. Place `PSFFPKG.exe` in the extracted UFS2Tool folder so the tool is detected automatically:

```text
UFS2Tool/
├── PSFFPKG.exe
├── UFS2Tool.exe
└── ... (accompanying UFS2Tool files)
```

You can also keep UFS2Tool elsewhere and specify its location with `--tool`, as described below.

### macOS

1. Install Python 3.8 or later and check it with `python3 --version`.
2. Download and extract the macOS **UFS2Tool** release.
3. Download or clone this repository to get `PSFFPKG.py`.
4. Open Terminal in the folder containing `PSFFPKG.py`. Place UFS2Tool alongside the script for automatic detection, or specify its location with `--tool`:

```text
UFS2Tool/
├── PSFFPKG.py
├── UFS2Tool
└── ... (accompanying UFS2Tool files)
```

## Usage

### Interactive mode

**Windows:** Right-click `PSFFPKG.exe` and select **Run as Administrator**, or double-click it and accept the elevation prompt. To start it from PowerShell:

```powershell
.\PSFFPKG.exe
```

**macOS:** Run the script from Terminal:

```sh
python3 PSFFPKG.py
```

On either platform:

1. Enter the path to your **game dump folder**.
2. Enter an **output folder**, or press Enter to use the current working directory.
3. Wait for image creation to finish. The package is saved as `GameDumpFolderName.ffpkg`.

### Command-line mode

Pass the game dump folder as the first argument and the optional output folder as the second.

**Windows (PowerShell):**

```powershell
.\PSFFPKG.exe "C:\Games\GameDump" "D:\PS5_Packages"
```

**macOS (Terminal):**

```sh
python3 PSFFPKG.py "/path/to/GameDump" "/path/to/Packages"
```

If the output folder is omitted, the package is saved in the current working directory. Use `--help` to display the available arguments.

### UFS2Tool location

Both modes support `--tool`, which accepts either the executable or its extracted release folder.

**Windows (PowerShell):**

```powershell
.\PSFFPKG.exe "C:\Games\GameDump" "D:\PS5_Packages" --tool "C:\Tools\UFS2Tool\UFS2Tool.exe"
```

**macOS (Terminal):**

```sh
python3 PSFFPKG.py "/path/to/GameDump" "/path/to/Packages" --tool "/path/to/UFS2Tool"
```

To start interactive mode with a custom tool location, pass only `--tool` and its path.

PSFFPKG resolves UFS2Tool in this order:

1. The path provided with `--tool`.
2. The `UFS2TOOL_PATH` environment variable, if set.
3. The folder containing `PSFFPKG.exe` or `PSFFPKG.py`.
4. The system `PATH`.

### Paths and output files

- Quote paths containing spaces. Paths also support `~` for the home directory.
- Choose an output folder **outside the game dump folder**, including its subfolders. PSFFPKG rejects output locations inside the dump to prevent the generated image from becoming part of its own input.
- The output folder is created if it does not exist.
- An existing `.ffpkg` with the same name is replaced only after successful image creation. Temporary files are removed if creation fails or is cancelled.

## Troubleshooting

### Windows

- **Elevation fails:** Right-click `PSFFPKG.exe` and select **Run as Administrator**.
- **UFS2Tool is not found:** Keep `UFS2Tool.exe` beside `PSFFPKG.exe`, or provide its location with `--tool` or `UFS2TOOL_PATH`.

### macOS

- **UFS2Tool is not found:** Keep `UFS2Tool` beside `PSFFPKG.py`, or provide its location with `--tool` or `UFS2TOOL_PATH`.
- **Execution permission is missing:** Run `chmod +x "/path/to/UFS2Tool"`.
- **macOS blocks a trusted UFS2Tool download with a quarantine attribute:** Remove the attribute from the extracted release folder with `xattr -cr "/path/to/UFS2Tool-release"`.
- **Using the x64 release on Apple Silicon:** Make sure Rosetta is installed.

## How it works

PSFFPKG displays the total size of the input files, then calls UFS2Tool with `-D` to calculate the image size automatically and construct the UFS2 filesystem.

**Windows:**

```powershell
.\UFS2Tool.exe newfs -O 2 -b 32768 -f 4096 -D "Input_Dir" "Temp_Image.img"
```

**macOS:**

```sh
./UFS2Tool newfs -O 2 -b 32768 -f 4096 -D "Input_Dir" "Temp_Image.img"
```

After successful creation, PSFFPKG moves the temporary image to its final `.ffpkg` filename for use with ShadowMount. The filesystem parameters follow the methodology documented by **earthonion** in the [mkufs2 repository](https://github.com/earthonion/mkufs2).

## Credits & acknowledgments

- **[voidwhisper-ps](https://github.com/voidwhisper-ps):** For creating the ShadowMount payload and enabling UFS support on the PS5.
- **[SvenGDK](https://github.com/SvenGDK):** For developing UFS2Tool, which handles filesystem creation.
- **[earthonion](https://github.com/earthonion/mkufs2):** For the research and documentation on creating UFS2 images for FreeBSD/PS5.

## Disclaimer

This software is provided "as is", without warranty of any kind. Use it at your own risk. The author is not responsible for any damage to your console or data.
