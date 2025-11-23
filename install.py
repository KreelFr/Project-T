#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safer installer for auto_changer.py
Usage: sudo python3 install.py
This script will:
 - copy auto_changer.py -> /usr/local/share/aut/auto_changer.py
 - create a small wrapper /usr/local/bin/aut
 - set executable bits
It will not install system packages or pip packages automatically.
"""

import os
import sys
import shutil
from pathlib import Path

SRC = Path.cwd()
SCRIPT = "auto_changer.py"
DEST_DIR = Path("/usr/local/share/aut")
WRAPPER = Path("/usr/local/bin/aut")

def is_root():
    return os.geteuid() == 0

def confirm(prompt):
    r = input(prompt + " [y/N] >> ").strip().lower()
    return r == "y"

def install():
    if not is_root():
        print("Installer must be run as root (sudo). Exiting.")
        sys.exit(1)

    src_file = SRC / SCRIPT
    if not src_file.exists():
        print(f"Could not find {SCRIPT} in current directory ({SRC}). Place {SCRIPT} here and retry.")
        sys.exit(1)

    if DEST_DIR.exists():
        print(f"{DEST_DIR} already exists.")
    else:
        print(f"Will create {DEST_DIR}")
        DEST_DIR.mkdir(parents=True, exist_ok=True)

    dst_file = DEST_DIR / SCRIPT
    print(f"Copying {src_file} -> {dst_file}")
    shutil.copy2(src_file, dst_file)
    dst_file.chmod(0o755)

    # create wrapper
    wrapper_content = f"#!/bin/sh\nexec python3 {dst_file} \"$@\"\n"
    print(f"Creating wrapper {WRAPPER}")
    with open(WRAPPER, "w", encoding="utf-8") as f:
        f.write(wrapper_content)
    WRAPPER.chmod(0o755)

    print("\nInstallation complete.")
    print("To run: aut --help")
    print("\nIMPORTANT: This tool does NOT auto-install system packages.")
    print("Make sure you have:")
    print("  - python3 and pip3")
    print("  - pip3 install requests")
    print("  - tor (if you plan to use tor mode)")
    print("  - openvpn (if you plan to use vpn mode)")
    print("\nIf you need help installing those, ask me and I will provide commands for your distro.")

def uninstall():
    if not is_root():
        print("Uninstaller must be run as root (sudo). Exiting.")
        sys.exit(1)

    if WRAPPER.exists():
        print(f"Removing wrapper {WRAPPER}")
        WRAPPER.unlink()
    if DEST_DIR.exists():
        print(f"Removing directory {DEST_DIR}")
        shutil.rmtree(DEST_DIR)
    print("Uninstalled.")

def main():
    print("AutoChanger installer.")
    print("Choose: (I)nstall, (U)ninstall, (Q)uit")
    c = input("Choice >> ").strip().lower()
    if c in ("i", "install"):
        if not is_root():
            print("You must run this script with sudo to install.")
            sys.exit(1)
        if confirm("Proceed with installation?"):
            install()
    elif c in ("u", "uninstall"):
        if not is_root():
            print("You must run this script with sudo to uninstall.")
            sys.exit(1)
        if confirm("Proceed with uninstall (this will remove /usr/local/share/aut and /usr/local/bin/aut)?"):
            uninstall()
    else:
        print("Exiting.")

if __name__ == "__main__":
    main()
