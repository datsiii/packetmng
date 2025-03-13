import os
import yaml
import zipfile
import hashlib
import subprocess
import shutil
from pathlib import Path

CACHE_DIR = Path.home() / ".mypkg_cache"
REPO_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "repo"  # Абсолютный путь
INSTALL_DIR = Path("/usr/local/mypkg")

def sha256sum(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_package(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Извлекаем файлы напрямую в extract_to (без вложенных папок)
        for file in zip_ref.namelist():
            zip_ref.extract(file, extract_to)

def load_manifest(package_dir):
    manifest_path = package_dir / "manifest.yaml"
    with open(manifest_path, 'r') as f:
        return yaml.safe_load(f)

def check_sha256(zip_path, expected_hash):
    return sha256sum(zip_path) == expected_hash

def install_package(pkg_name):
    zip_path = REPO_DIR / f"{pkg_name}.zip"
    if not zip_path.exists():
        print(f"❌ Файл {zip_path} не найден!")
        return

    extract_dir = CACHE_DIR / pkg_name
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Распаковываем архив
    extract_package(zip_path, extract_dir)

    # Проверяем хеш
    manifest = load_manifest(extract_dir)
    if not check_sha256(zip_path, manifest['sha256']):
        print("❌ SHA256 mismatch!")
        shutil.rmtree(extract_dir)
        return

    # Устанавливаем зависимости
    if 'go' in manifest['dependencies']:
        install_go()

    # Переносим в целевую директорию
    target_dir = INSTALL_DIR / pkg_name
    shutil.rmtree(target_dir, ignore_errors=True)
    shutil.copytree(extract_dir, target_dir)
    print(f"✅ Пакет {pkg_name} установлен!")

def install_go():
    if (INSTALL_DIR / "go").exists():
        return
    fetch_package("go")
    install_package("go")

def fetch_package(pkg_name):
    zip_path = REPO_DIR / f"{pkg_name}.zip"
    if not zip_path.exists():
        print(f"❌ Пакет {pkg_name} не найден в репозитории!")
        return
    CACHE_DIR.mkdir(exist_ok=True)
    shutil.copy(zip_path, CACHE_DIR)

def build_package(pkg_name):
    pkg_dir = INSTALL_DIR / pkg_name
    if not pkg_dir.exists():
        print(f"❌ Пакет {pkg_name} не установлен!")
        return
    subprocess.run(["go", "build", "-o", str(pkg_dir / "output"), str(pkg_dir / "main.go")])

def main():
    import sys
    if len(sys.argv) < 3:
        print("❌ Использование: python3 package_manager.py <команда> <пакет>")
        return
    command, package = sys.argv[1], sys.argv[2]
    if command == "install":
        install_package(package)
    elif command == "build":
        build_package(package)
    elif command == "fetch":
        fetch_package(package)
    else:
        print(f"❌ Неизвестная команда: {command}")

if __name__ == "__main__":
    main()