import os
import yaml
import zipfile
import hashlib
import subprocess
import shutil
from pathlib import Path

CACHE_DIR = Path.home() / ".mypkg_cache"
REPO_DIR = Path("./repo")
INSTALL_DIR = Path("/usr/local/mypkg")


def sha256sum(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_package(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def load_manifest(package_dir):
    manifest_path = package_dir / "manifest.yaml"
    with open(manifest_path, 'r') as f:
        return yaml.safe_load(f)


def check_sha256(package_dir, expected_hash):
    zip_path = package_dir.with_suffix(".zip")
    return sha256sum(zip_path) == expected_hash


def install_package(pkg_name):
    zip_path = REPO_DIR / f"{pkg_name}.zip"
    extract_dir = CACHE_DIR / pkg_name
    extract_package(zip_path, extract_dir)
    manifest = load_manifest(extract_dir)
    if not check_sha256(zip_path, manifest['sha256']):
        print("SHA256 mismatch!")
        return
    if 'go' in manifest['dependencies']:
        install_go()
    shutil.move(str(extract_dir), str(INSTALL_DIR / pkg_name))


def install_go():
    if (INSTALL_DIR / "go").exists():
        return
    fetch_package("go")
    install_package("go")


def fetch_package(pkg_name):
    zip_path = REPO_DIR / f"{pkg_name}.zip"
    if not zip_path.exists():
        print(f"Package {pkg_name} not found in repository!")
        return
    shutil.copy(zip_path, CACHE_DIR)


def build_package(pkg_name):
    pkg_dir = INSTALL_DIR / pkg_name
    if not pkg_dir.exists():
        print(f"Package {pkg_name} is not installed!")
        return
    subprocess.run(["go", "build", "-o", str(pkg_dir / "output"), str(pkg_dir / "main.go")])


def update_cache():
    CACHE_DIR.mkdir(exist_ok=True)
    for pkg in REPO_DIR.glob("*.zip"):
        shutil.copy(pkg, CACHE_DIR)


def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: mypkg <command> <package>")
        return
    command, package = sys.argv[1], sys.argv[2]
    if command == "install":
        install_package(package)
    elif command == "build":
        build_package(package)
    elif command == "fetch":
        fetch_package(package)
    elif command == "update":
        update_cache()
    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
