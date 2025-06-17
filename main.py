import requests
from tqdm import tqdm
import json

# Чтение токена из файла
with open('ya_token.txt', 'r') as file:
    token = file.read().strip()

# Имя файла для сохранения результатов
RESULTS_FILE = 'photos_dog.json'

# смотрим какие есть фото в photos_dog.json
def load_results():
    try:
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# сохраняем названия фото в photos_dog.json
def save_results(data):
    with open(RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# проверка на дубли в файле photos_dog.json
def is_duplicate(results, filename):
    return any(entry['file_name'] == filename for entry in results)

# проверка дублей на Яндекс диске
def check_file_exists(ya_path):
    url = 'https://cloud-api.yandex.net/v1/disk/resources'
    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': ya_path}

    response = requests.get(url, headers=headers, params=params)
    return response.status_code == 200

# создаем папку на Яндекс диске
def create_ya_folder(folder_name):
    url = 'https://cloud-api.yandex.net/v1/disk/resources'
    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': f'/{folder_name}'}

    response = requests.put(url, headers=headers, params=params)

    if response.status_code == 201:
        print(f"Папка '{folder_name}' успешно создана")
        return True
    elif response.status_code == 409:
        print(f"Папка '{folder_name}' уже существует")
        return True
    else:
        print(f"Ошибка при создании папки '{folder_name}': {response.status_code}, возможно не прописан token")
        return False

# читаем имя файла из URL
def extract_filename_from_url(url):
    parts = url.split('/')
    return parts[-1] if parts else 'image.jpg'

# загружаем файл на Яндекс диск
def upload_to_ya_disk(file_url, ya_path, results):
    filename = ya_path.split('/')[-1]

# Проверяем дубликаты в photos_dog.json и на Яндекс диске
    if is_duplicate(results, filename) or check_file_exists(ya_path):
        print(f"Файл {filename} уже существует, пропускаем")
        return False

    upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
    headers = {'Authorization': f'OAuth {token}'}
    params = {
        'url': file_url,
        'path': ya_path,
        'disable_redirects': True
    }

    response = requests.post(upload_url, headers=headers, params=params)
    if response.status_code == 202:
        print(f"Успешно загружено: {filename}")
        return True
    else:
        print(f"Ошибка загрузки {filename}: {response.status_code}")
        return False

# получаем инфу о  породе и подпородах
def get_breed_info(breed_name):
    response = requests.get(f'https://dog.ceo/api/breed/{breed_name}/list')
    if response.status_code == 200:
        return response.json().get('message', [])
    return None

# получаем случайное изображение
def get_dog_image(breed, sub_breed=None):
    if sub_breed:
        url = f'https://dog.ceo/api/breed/{breed}/{sub_breed}/images/random'
    else:
        url = f'https://dog.ceo/api/breed/{breed}/images/random'

    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('message')
    return None

# загружаем изобржения для указаной породы
def download_breed_images(breed_name):
    breed_folder = f"dog_geo/{breed_name}"
    if not create_ya_folder(breed_folder):
        return False

    sub_breeds = get_breed_info(breed_name)
    total_images = len(sub_breeds) if sub_breeds else 1

    results = load_results()

    with tqdm(total=total_images, desc=f"Загрузка {breed_name}", unit="img") as pbar:
        if sub_breeds:
            for sub_breed in sub_breeds:
                image_url = get_dog_image(breed_name, sub_breed)
                if image_url:
                    original_filename = extract_filename_from_url(image_url)
                    filename = f"{breed_name}_{sub_breed}_{original_filename}"
                    ya_path = f"/{breed_folder}/{filename}"

                    if upload_to_ya_disk(image_url, ya_path, results):
                        results.append({"file_name": filename})
                        save_results(results)
                pbar.update(1)
        else:
            image_url = get_dog_image(breed_name)
            if image_url:
                original_filename = extract_filename_from_url(image_url)
                filename = f"{breed_name}_{original_filename}"
                ya_path = f"/{breed_folder}/{filename}"

                if upload_to_ya_disk(image_url, ya_path, results):
                    results.append({"file_name": filename})
                    save_results(results)
            pbar.update(1)
    return True

# возвращаем список всех пород
def list_all_breeds():
    response = requests.get('https://dog.ceo/api/breeds/list/all')
    if response.status_code == 200:
        return list(response.json().get('message', {}).keys())
    return []

# выводим список пород таблицей с 8 колонками
def print_breeds_table(breeds, columns=8, width=150):
    max_length = max(len(breed) for breed in breeds) + 2
    columns = min(columns, width // max_length)
    rows = [breeds[i:i + columns] for i in range(0, len(breeds), columns)]

    print("\nДоступные породы собак:")
    print("=" * width)
    for row in rows:
        formatted_row = " | ".join(breed.ljust(max_length) for breed in row)
        print(formatted_row)
    print("=" * width)


def main():
    if not create_ya_folder('dog_geo'):
        print("Не удалось создать основную папку для пород")
        return

    all_breeds = list_all_breeds()
    all_breeds.sort()

    print_breeds_table(all_breeds)

    while True:
        breed_name = input("\nВведите название породы (или '0' для выхода): ").strip().lower()

        if breed_name == '0':
            break

        if breed_name not in all_breeds:
            print(f"Порода '{breed_name}' не найдена. Попробуйте еще раз.")
            continue

        download_breed_images(breed_name)


if __name__ == "__main__":
    main()
