import os
import zipfile
import subprocess
import hashlib
import shutil
import requests
import yaml


# -----------------------------
# 1. Распаковка архива и чтение манифеста
# -----------------------------
def unzip_package(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Архив {zip_path} распакован в {extract_to}")


def load_manifest(manifest_path):
    with open(manifest_path, 'r') as file:
        manifest = yaml.safe_load(file)
    print("Манифест загружен:")
    print(manifest)
    return manifest


def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# -----------------------------
# 2. Проверка компилятора Go и его скачивание
# -----------------------------
def check_go_compiler():
    try:
        output = subprocess.check_output(["go", "version"], stderr=subprocess.STDOUT)
        print("Найден компилятор Go:", output.decode().strip())
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Компилятор Go не найден в системе.")
        return False


def download_go_compiler(url, download_path):
    print(f"Скачиваем компилятор Go с {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(download_path, "wb") as f:
            f.write(response.content)
        print(f"Скачивание завершено. Файл сохранён в {download_path}")
        # Распаковка архива и установка зависит от формата архива
        # Здесь можно добавить логику распаковки и установки
    else:
        raise Exception("Ошибка скачивания компилятора Go")


# -----------------------------
# 3. Сборка исходного кода (целевого приложения)
# -----------------------------
def build_application(source_dir, entry_point, output_name):
    output_path = os.path.join(source_dir, "bin", output_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Запуск сборки из {source_dir} с точкой входа {entry_point}")
    try:
        subprocess.check_call(["go", "build", "-o", output_path, entry_point], cwd=source_dir)
        print(f"Сборка завершена успешно. Бинарный файл: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print("Ошибка при сборке:", e)
        return None


# -----------------------------
# 4. Выгрузка пакета из репозитория и кеширование зависимостей
# -----------------------------
class PackageManager:
    def __init__(self, cache_dir="~/.pkg_cache"):
        self.cache_dir = os.path.expanduser(cache_dir)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        print(f"Локальный кэш находится в {self.cache_dir}")

    def fetch_package(self, url, package_name):
        """
        Выгружает (скачивает) пакет по URL и сохраняет в кэш, если он еще не сохранен.
        """
        local_zip = os.path.join(self.cache_dir, package_name + ".zip")
        if os.path.exists(local_zip):
            print(f"Пакет {package_name} уже есть в кэше.")
            return local_zip
        print(f"Скачивание пакета {package_name} с {url}")
        r = requests.get(url)
        if r.status_code == 200:
            with open(local_zip, "wb") as f:
                f.write(r.content)
            print("Скачивание завершено.")
            return local_zip
        else:
            raise Exception("Ошибка скачивания пакета")

    def cache_dependency(self, dep_name, package_path):
        """
        Кеширует зависимость, копируя архив в локальный кэш.
        """
        dest_path = os.path.join(self.cache_dir, dep_name + ".zip")
        if os.path.exists(dest_path):
            print(f"Зависимость {dep_name} уже закеширована.")
        else:
            shutil.copy(package_path, dest_path)
            print(f"Зависимость {dep_name} добавлена в локальный кэш.")
        return dest_path

    def update_cache(self):
        """
        Обновляет локальный кэш зависимостей. Можно реализовать, например, сравнение версий
        или контрольных сумм для каждой зависимости.
        """
        # Для простоты выводим сообщение. Логику можно расширить.
        print(
            "Обновление локального кэша не реализовано полностью. Здесь можно добавить проверку обновлений зависимостей.")

    def install_dependency(self, dep_name, target_dir="/usr/local"):
        """
        Устанавливает зависимость в систему, распаковывая архив из кэша.
        Например, установка компилятора Go в /usr/local/go.
        """
        package_zip = os.path.join(self.cache_dir, dep_name + ".zip")
        if not os.path.exists(package_zip):
            print(f"Зависимость {dep_name} не найдена в кэше. Скачайте её.")
            return False
        install_dir = os.path.join(target_dir, dep_name)
        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        os.makedirs(install_dir, exist_ok=True)
        with zipfile.ZipFile(package_zip, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
        print(f"Зависимость {dep_name} установлена в {install_dir}")
        return True


# -----------------------------
# 5. Запуск итогового приложения
# -----------------------------
def run_application(binary_path):
    print(f"Запуск приложения: {binary_path}")
    try:
        subprocess.check_call([binary_path])
    except subprocess.CalledProcessError as e:
        print("Ошибка при запуске приложения:", e)


# -----------------------------
# Пример рабочего сценария
# -----------------------------
if __name__ == "__main__":
    # Пути и URL-ы для примера
    test_package_zip = "test-package.zip"  # Архив с исходным кодом и манифестом
    extract_dir = "./extracted"

    # 1. Распаковка архива и загрузка манифеста
    unzip_package(test_package_zip, extract_dir)
    manifest_path = os.path.join(extract_dir, "manifest.yaml")
    manifest = load_manifest(manifest_path)

    # 2. Проверка компилятора Go
    if not check_go_compiler():
        # Если компилятор не найден, скачиваем его (пример URL и путь для скачивания)
        go_download_url = "https://golang.org/dl/go1.17.linux-amd64.tar.gz"
        go_archive_path = os.path.join(extract_dir, "go.tar.gz")
        download_go_compiler(go_download_url, go_archive_path)
        # Здесь дополнительно можно распаковать архив и настроить PATH

    # 3. Сборка приложения
    # Предполагаем, что в манифесте есть точка входа, например, "main.go"
    binary_path = build_application(extract_dir, manifest.get("entry_point", "main.go"), manifest["name"])
    if binary_path:
        # 4. Проверка SHA256 (например, для бинарного файла)
        computed_sha256 = compute_sha256(binary_path)
        if computed_sha256 == manifest.get("sha256"):
            print("Контрольная сумма совпадает!")
        else:
            print("Контрольная сумма не совпадает! Возможно, что-то пошло не так.")

    # 5. Работа с зависимостями через локальный кэш
    pm = PackageManager()

    # Выгрузка пакета зависимости (например, компилятора Go) из репозитория
    # Здесь url и имя указываются для примера; в реальной ситуации данные будут из манифеста или конфигурации
    dep_url = "https://example.com/go-compiler.zip"
    dep_name = "go-compiler"
    try:
        dep_package = pm.fetch_package(dep_url, dep_name)
        pm.cache_dependency(dep_name, dep_package)
        pm.install_dependency(dep_name, target_dir="/usr/local")
    except Exception as e:
        print("Ошибка при работе с зависимостью:", e)

    # Обновление кэша (опционально)
    pm.update_cache()

    # 6. Запуск итогового приложения
    run_application(binary_path)
