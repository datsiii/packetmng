import argparse
import sys
import yaml
import hashlib
import zipfile
import os
import subprocess
import urllib.request


def load_manifest(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if 'manifest.yaml' not in zip_ref.namelist():
            raise FileNotFoundError("manifest.yaml not found in package")
        with zip_ref.open('manifest.yaml') as manifest_file:
            return yaml.safe_load(manifest_file)


def verify_sha256(zip_path, expected_hash):
    sha256 = hashlib.sha256()
    with open(zip_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest() == expected_hash


def extract_package(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted package to {extract_to}")


def install(package_name):
    print(f"Installing {package_name}...")
    zip_path = f"packages/{package_name}.zip"
    install_path = f"/usr/local/{package_name}"

    if not os.path.exists(zip_path):
        print("Package not found. Fetching...")
        fetch(package_name)

    manifest = load_manifest(zip_path)
    if not verify_sha256(zip_path, manifest['sha256']):
        print("SHA256 checksum mismatch! Aborting installation.")
        return

    if 'dependencies' in manifest:
        for dependency in manifest['dependencies']:
            print(f"Installing dependency: {dependency}")
            install(dependency)

    os.makedirs(install_path, exist_ok=True)
    extract_package(zip_path, install_path)
    print(f"Package {package_name} installed successfully.")


def build(package_name):
    print(f"Building {package_name}...")
    build_path = f"/usr/local/{package_name}"
    manifest = load_manifest(f"packages/{package_name}.zip")

    if 'entry_point' not in manifest:
        print("No entry point specified in manifest. Aborting build.")
        return

    entry_point = os.path.join(build_path, manifest['entry_point'])
    if not os.path.exists(entry_point):
        print("Entry point file not found. Aborting build.")
        return

    try:
        subprocess.run(["go", "build", "-o", os.path.join(build_path, package_name), entry_point], check=True)
        print(f"Package {package_name} built successfully.")
    except subprocess.CalledProcessError:
        print("Build failed.")


def update():
    print("Updating package cache...")
    os.makedirs("packages", exist_ok=True)
    urllib.request.urlretrieve("http://repository.example.com/package_list.yaml", "packages/package_list.yaml")
    print("Package cache updated.")


def fetch(package_name):
    print(f"Fetching {package_name}...")
    os.makedirs("packages", exist_ok=True)
    package_url = f"http://repository.example.com/{package_name}.zip"
    package_path = f"packages/{package_name}.zip"
    urllib.request.urlretrieve(package_url, package_path)
    print(f"Package {package_name} fetched successfully.")


def main():
    parser = argparse.ArgumentParser(description="Custom Package Manager")
    subparsers = parser.add_subparsers(dest="command")

    parser_install = subparsers.add_parser("install", help="Install a package")
    parser_install.add_argument("package", type=str, help="Package name")

    parser_build = subparsers.add_parser("build", help="Build a package")
    parser_build.add_argument("package", type=str, help="Package name")

    parser_update = subparsers.add_parser("update", help="Update package cache")

    parser_fetch = subparsers.add_parser("fetch", help="Fetch a package from repository")
    parser_fetch.add_argument("package", type=str, help="Package name")

    args = parser.parse_args()

    if args.command == "install":
        install(args.package)
    elif args.command == "build":
        build(args.package)
    elif args.command == "update":
        update()
    elif args.command == "fetch":
        fetch(args.package)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
