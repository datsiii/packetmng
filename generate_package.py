import os
import yaml
import hashlib
import sys
import zipfile
from datetime import datetime

def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def create_manifest(package_name, source_dir):
    manifest = {
        "name": package_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "dependencies": ["go"],
        "sha256": "",
        "os": ["linux"],
        "arch": ["x86_64"],
        "entry": "main.go"
    }
    manifest_path = os.path.join(source_dir, "manifest.yaml")
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)
    return manifest_path

def create_package(package_name, source_dir, output_zip):
    # Создаем временный manifest.yaml
    manifest_path = create_manifest(package_name, source_dir)

    # Создаем архив БЕЗ manifest.yaml
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file == "manifest.yaml":
                    continue  # Пропускаем временный манифест
                file_path = os.path.join(root, file)
                # Добавляем файлы в корень архива
                zipf.write(file_path, arcname=os.path.basename(file_path))

    # Вычисляем хеш архива без manifest.yaml
    sha256 = calculate_sha256(output_zip)

    # Обновляем manifest.yaml с актуальным хешем
    with open(manifest_path, "r") as f:
        manifest = yaml.safe_load(f)
    manifest["sha256"] = sha256
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f)

    # Добавляем обновленный manifest.yaml в архив
    with zipfile.ZipFile(output_zip, "a", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(manifest_path, arcname="manifest.yaml")

    print(f"✅ Пакет {package_name} создан: {output_zip}")
    print(f"SHA256: {sha256}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("❌ Использование: python3 generate_manifest.py <папка_с_кодом> <выходной_zip>")
        sys.exit(1)
    source_dir = sys.argv[1]
    output_zip = sys.argv[2]
    package_name = os.path.basename(source_dir)
    create_package(package_name, source_dir, output_zip)