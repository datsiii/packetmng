import json
import os
import shutil
import zipfile
import hcl
import hashlib
import requests
import datetime
import subprocess

CACHE_DIR = "./cache"


def compute_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_manifest(manifest_path):
    with open(manifest_path, "r") as f:
        return hcl.load(f)


def download_file(url, dest_path):
    print(f"Скачивание: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Файл загружен: {dest_path}")


def check_go_installed():
    try:
        result = subprocess.run(["go", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Найден компилятор Go: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        return False
    return False


def install_go(go_info):
    go_url = go_info["source"]
    go_sha256 = go_info["sha256"]
    go_archive = "/tmp/go.tar.gz"

    download_file(go_url, go_archive)

    if os.path.exists("/usr/local/go"):
        shutil.rmtree("/usr/local/go")

    os.system(f"tar -C /usr/local -xzf {go_archive}")
    os.environ["PATH"] += os.pathsep + "/usr/local/go/bin"
    print("Компилятор Go установлен!")


def build_go_project(project_path, entry_point, output_binary):
    os.chdir(project_path)
    os.makedirs("bin", exist_ok=True)
    binary_path = f"bin/{output_binary}"
    build_cmd = f"go build -o {binary_path} {entry_point}"
    result = subprocess.run(build_cmd, shell=True)

    if result.returncode != 0:
        raise RuntimeError("Ошибка сборки!")

    print(f"Сборка завершена. Бинарник: {binary_path}")
    return os.path.join(project_path, binary_path)


def create_manifest(binary_path, entry_point, dependencies):
    manifest_content = f"""
    name = "my-go-app"
    version = "1.0.0"
    entry_point = "{entry_point}"
    date = "{datetime.datetime.now().isoformat()}"
    output_binary = "{os.path.basename(binary_path)}"
    sha256 = "{compute_sha256(binary_path)}"
    supported_os = ["linux"]
    supported_architectures = ["amd64"]
    dependencies = [
        {{"name" = "{dependencies[0]['name']}", "version" = "{dependencies[0]['version']}", "source" = "{dependencies[0]['source']}", "sha256" = "{dependencies[0]['sha256']}"}}    
    ]
    """

    with open("manifest.hcl", "w") as f:
        f.write(manifest_content.strip())

    print("Файл manifest.hcl создан!")


def create_zip_package(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, source_dir))
    print(f"Архив создан: {output_zip}")


def run_binary(binary_path):
    os.chdir('..')
    print(f"Запуск: {binary_path}")
    subprocess.run([binary_path])


def fetch_repository(repo_url, package_name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    repo_cache_path = os.path.join(CACHE_DIR, package_name)

    if os.path.exists(repo_cache_path):
        print(f" Репозиторий {package_name} уже загружен в кэш.")
        return repo_cache_path

    zip_path = os.path.join(CACHE_DIR, f"{package_name}.zip")
    download_file(repo_url, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(repo_cache_path)

    print(f"Репозиторий {package_name} загружен и распакован в кэш.")
    return repo_cache_path


def main(zip_path):
    extracted_path = "./extracted"

    if os.path.exists(zip_path):
        shutil.rmtree(extracted_path, ignore_errors=True)
        os.makedirs(extracted_path)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extracted_path)

        print(f"Архив {zip_path} распакован в {extracted_path}")

    manifest_path = os.path.join(extracted_path, "manifest.hcl")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError("Файл manifest.hcl не найден!")

    manifest = load_manifest(manifest_path)
    print(f"Манифест загружен: {manifest}")

    if not check_go_installed():
        install_go(manifest["dependencies"][0])

    repo_cache_path = fetch_repository(manifest["dependencies"][0]["source"], manifest["dependencies"][0]["name"])
    print(f"Используем кэшированный репозиторий: {repo_cache_path}")

    binary_path = build_go_project(extracted_path, manifest["entry_point"], manifest["output_binary"])

    computed_sha256 = compute_sha256(binary_path)
    if computed_sha256 != manifest["sha256"]:
        print("Контрольная сумма не совпадает!")
    else:
        print("Контрольная сумма совпадает.")

    create_manifest(binary_path, manifest["entry_point"], manifest["dependencies"])

    output_zip = "package.zip"
    create_zip_package(extracted_path, output_zip)

    run_binary(binary_path)


if __name__ == "__main__":
    zip_file = "test-package.zip"
    main(zip_file)
