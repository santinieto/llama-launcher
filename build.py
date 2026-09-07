from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parent

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "LocalLLMManager",
        "--distpath",
        str(base / "dist"),
        "--workpath",
        str(base / "build"),
        "--specpath",
        str(base),
        "--add-data",
        f"{base / 'config'};config",
        "--hidden-import",
        "app",
        "--hidden-import",
        "app.core",
        "--hidden-import",
        "app.gui",
        "--hidden-import",
        "app.models",
        str(base / "app" / "main.py"),
    ]

    print("Building LocalLLMManager...")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=str(base))

    if result.returncode == 0:
        dist_dir = base / "dist" / "LocalLLMManager"
        print()
        print(f"Build successful!")
        print(f"Output: {dist_dir}")
        print()
        print("To run:")
        print(f"  {dist_dir / 'LocalLLMManager.exe'}")
        print()
        print("Note: config/app.yaml is bundled inside the exe directory.")
        print("Models and llama.cpp stay external, referenced via config.")
    else:
        print()
        print(f"Build failed with return code {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
