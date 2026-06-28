"""
Генератор тестовых данных (консольная версия).
Генерирует реалистичные имена, email, адреса, даты рождения и телефоны.
Сохраняет в CSV или JSON.
"""

import argparse
import csv
import json
import re
import random
import sys
from datetime import datetime

from faker import Faker
from transliterate import translit

# -------------------------- Конфигурация --------------------------
DEFAULT_COUNT = 10
DEFAULT_FORMAT = 'csv'
DEFAULT_FILENAME = 'data'

# -------------------------- Инициализация Faker --------------------------
fake = Faker('ru_RU')          # русские имена, адреса, телефоны

# -------------------------- Транслитерация --------------------------
def transliterate_russian(text: str) -> str:
    """Преобразует русский текст в латиницу (транслитерация)."""
    return translit(text, 'ru', reversed=True).lower()

# -------------------------- Вспомогательные функции для email --------------------------
def extract_city(address: str) -> str:
    """Извлекает название города из адреса (формат Faker для ru_RU)."""
    city = re.sub(r'^(г\.|город)\s*', '', address)
    city = city.split(',')[0].strip()
    city = re.sub(r'\s+(р-н|район|обл|область|край|респ|республика).*$', '', city)
    return city

def extract_name_parts(full_name: str) -> (str, str):
    """Возвращает (фамилия, имя) из полного имени."""
    parts = full_name.split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    return full_name, ''

def generate_email(name: str, phone: str, address: str, birth_date: str) -> str:
    """Формирует реалистичный email на основе имени, телефона, адреса и даты рождения."""
    surname, first_name = extract_name_parts(name)
    surname_lat = transliterate_russian(surname)
    first_name_lat = transliterate_russian(first_name)
    surname_lat = re.sub(r'[^a-z]', '', surname_lat)
    first_name_lat = re.sub(r'[^a-z]', '', first_name_lat)

    city = extract_city(address)
    city_lat = transliterate_russian(city)
    city_lat = re.sub(r'[^a-z]', '', city_lat)

    phone_digits = re.sub(r'\D', '', phone)
    phone_part = phone_digits[-4:] if len(phone_digits) >= 4 else phone_digits
    phone_part_long = phone_digits[-7:] if len(phone_digits) >= 7 else phone_digits

    try:
        dt = datetime.strptime(birth_date, '%Y-%m-%d')
        year = str(dt.year)
        year_short = year[-2:]
        day_month = f"{dt.day:02d}{dt.month:02d}"
        month_day = f"{dt.month:02d}{dt.day:02d}"
    except:
        year = '1990'
        year_short = '90'
        day_month = '0101'
        month_day = '0101'

    variants = [
        f"{surname_lat}_{first_name_lat}{year_short}",
        f"{first_name_lat}.{surname_lat}{year}",
        f"{surname_lat}{first_name_lat[:2]}{day_month}",
        f"{first_name_lat}{surname_lat[:2]}{month_day}",
        f"{surname_lat}_{city_lat}{year_short}",
        f"{first_name_lat}{city_lat}{year}",
        f"{surname_lat}{phone_part}",
        f"{first_name_lat}{phone_part_long}",
        f"{city_lat}_{surname_lat}{day_month}",
    ]
    if random.choice([True, False]):
        variants.append(f"{surname_lat}_{first_name_lat}{random.randint(10, 99)}")

    local_part = random.choice(variants)
    local_part = re.sub(r'[^a-zA-Z0-9._-]', '', local_part)
    local_part = local_part.strip('._-')

    if not local_part:
        local_part = f"user{random.randint(1000, 9999)}"

    domain = random.choice(['mail.ru', 'yandex.ru', 'gmail.com', 'bk.ru', 'list.ru'])
    return f"{local_part}@{domain}"

# -------------------------- Генерация одного человека --------------------------
def generate_person() -> dict:
    """Генерирует словарь с данными одного человека."""
    name = fake.name()
    phone = fake.phone_number()
    address = fake.address()
    birth_date = fake.date_of_birth(minimum_age=18, maximum_age=80)
    email = generate_email(name, phone, address, birth_date.strftime('%Y-%m-%d'))
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'address': address,
        'birth_date': birth_date.strftime('%Y-%m-%d')
    }

def generate_data(count: int) -> list:
    """Генерирует список словарей с данными count записей."""
    return [generate_person() for _ in range(count)]

# -------------------------- Валидация --------------------------
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return True
    if len(digits) == 10:
        return True
    return False

def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_record(record: dict) -> dict:
    errors = []
    if not record.get('name', '').strip():
        errors.append("Имя пустое")
    if not validate_email(record.get('email', '')):
        errors.append(f"Некорректный email: {record.get('email')}")
    if not validate_phone(record.get('phone', '')):
        errors.append(f"Некорректный телефон: {record.get('phone')}")
    if not record.get('address', '').strip():
        errors.append("Адрес пустой")
    if not validate_date(record.get('birth_date', '')):
        errors.append(f"Некорректная дата: {record.get('birth_date')}")
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def validate_data(data: list) -> tuple:
    valid_count = 0
    invalid_count = 0
    errors_list = []
    for i, record in enumerate(data):
        res = validate_record(record)
        if res['valid']:
            valid_count += 1
        else:
            invalid_count += 1
            errors_list.append((i, res['errors']))
    return valid_count, invalid_count, errors_list

# -------------------------- Сохранение в файлы --------------------------
def save_csv(data: list, filename: str) -> None:
    if not data:
        return
    fieldnames = data[0].keys()
    with open(f"{filename}.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def save_json(data: list, filename: str) -> None:
    with open(f"{filename}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -------------------------- Интерактивный ввод (если нет аргументов) --------------------------
def interactive_input():
    """Запрашивает параметры у пользователя в интерактивном режиме."""
    print("=== Генератор тестовых данных ===")
    while True:
        try:
            count = int(input(f"Количество записей (по умолчанию {DEFAULT_COUNT}): ") or DEFAULT_COUNT)
            if count > 0:
                break
            print("Введите положительное число.")
        except ValueError:
            print("Ошибка: введите целое число.")
    fmt = input(f"Формат сохранения (csv/json, по умолчанию {DEFAULT_FORMAT}): ").strip().lower()
    if fmt not in ('csv', 'json'):
        fmt = DEFAULT_FORMAT
    filename = input(f"Имя файла без расширения (по умолчанию {DEFAULT_FILENAME}): ").strip()
    if not filename:
        filename = DEFAULT_FILENAME
    return count, fmt, filename

# -------------------------- Основная функция CLI --------------------------
def main():
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description="Генератор тестовых данных")
    parser.add_argument('-n', '--count', type=int, help="Количество записей")
    parser.add_argument('-f', '--format', choices=['csv', 'json'], help="Формат сохранения")
    parser.add_argument('-o', '--output', help="Имя файла без расширения")
    args = parser.parse_args()

    # Если аргументы не заданы – переходим в интерактивный режим
    if args.count is None and args.format is None and args.output is None:
        count, fmt, filename = interactive_input()
    else:
        # Используем переданные аргументы, подставляя значения по умолчанию для отсутствующих
        count = args.count if args.count is not None else DEFAULT_COUNT
        fmt = args.format if args.format is not None else DEFAULT_FORMAT
        filename = args.output if args.output is not None else DEFAULT_FILENAME

    print(f"Генерация {count} записей...")
    data = generate_data(count)

    # Валидация и вывод статистики
    valid, invalid, errors = validate_data(data)
    print(f"Валидных записей: {valid}, невалидных: {invalid}")
    if invalid > 0:
        print("Ошибки валидации:")
        for idx, errs in errors:
            print(f"  Запись #{idx+1}: {', '.join(errs)}")

    # Сохранение
    if fmt == 'csv':
        save_csv(data, filename)
        print(f"Данные сохранены в {filename}.csv")
    else:
        save_json(data, filename)
        print(f"Данные сохранены в {filename}.json")

if __name__ == '__main__':
    main()