#!/usr/bin/env python3
"""
Скрипт для настройки авторизации VCD IP Manager
Запустите этот файл в папке backend/
"""

import os
import secrets
from passlib.context import CryptContext
from pathlib import Path

def generate_password_hash(password):
    """Генерация хеша пароля"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)

def generate_secret_key():
    """Генерация секретного ключа"""
    return secrets.token_urlsafe(32)

def main():
    print("=" * 60)
    print("VCD IP Manager - Настройка авторизации")
    print("=" * 60)
    
    # Проверяем наличие .env файла
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ Файл .env не найден!")
        print("Создайте его из .env_example:")
        print("  cp .env_example .env")
        return
    
    print("\n📝 Настройка администратора:")
    print("-" * 40)
    
    # Запрашиваем имя пользователя
    username = input("Введите имя администратора (по умолчанию 'admin'): ").strip()
    if not username:
        username = "admin"
    
    # Запрашиваем пароль
    while True:
        password = input(f"Введите пароль для пользователя '{username}': ").strip()
        if len(password) < 6:
            print("⚠️  Пароль должен быть минимум 6 символов!")
            continue
        
        password_confirm = input("Подтвердите пароль: ").strip()
        if password != password_confirm:
            print("⚠️  Пароли не совпадают! Попробуйте еще раз.")
            continue
        break
    
    # Генерируем хеш пароля
    print("\n🔐 Генерация хеша пароля...")
    password_hash = generate_password_hash(password)
    
    # Генерируем секретный ключ
    print("🔑 Генерация секретного ключа...")
    secret_key = generate_secret_key()
    
    # Читаем существующий .env
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Проверяем, есть ли уже настройки авторизации
    auth_section = """
# ================== AUTHENTICATION ==================
# Секретный ключ для JWT токенов (НЕ ДЕЛИТЕСЬ ЭТИМ!)
SECRET_KEY={secret_key}

# Администратор системы
ADMIN_USERNAME={username}
ADMIN_PASSWORD_HASH={password_hash}

# Время жизни токена в минутах (24 часа = 1440 минут)
ACCESS_TOKEN_EXPIRE_MINUTES=1440
"""
    
    if "AUTHENTICATION" in env_content:
        print("\n⚠️  Настройки авторизации уже существуют в .env")
        overwrite = input("Перезаписать? (y/n): ").lower()
        if overwrite != 'y':
            print("Отменено.")
            return
        
        # Удаляем старую секцию
        lines = env_content.split('\n')
        new_lines = []
        skip = False
        for line in lines:
            if "AUTHENTICATION" in line:
                skip = True
            elif skip and line.strip() and not line.startswith('#') and '=' in line:
                continue
            elif skip and (line.startswith('# ===') or (not line.strip() and new_lines[-1].strip() == '')):
                skip = False
            if not skip:
                new_lines.append(line)
        env_content = '\n'.join(new_lines)
    
    # Добавляем новые настройки
    env_content = env_content.rstrip() + auth_section.format(
        secret_key=secret_key,
        username=username,
        password_hash=password_hash
    )
    
    # Сохраняем .env
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print("\n✅ Настройки авторизации успешно добавлены в .env!")
    print("\n" + "=" * 60)
    print("📋 Информация для входа:")
    print("-" * 40)
    print(f"Логин:  {username}")
    print(f"Пароль: {password}")
    print("\n⚠️  ВАЖНО: Запомните или сохраните пароль в безопасном месте!")
    print("=" * 60)
    
    # Проверяем наличие auth.py
    auth_path = Path("auth.py")
    if not auth_path.exists():
        print("\n⚠️  Файл auth.py не найден!")
        print("Создайте его с кодом из инструкции.")
    else:
        print("\n✅ Файл auth.py найден.")
    
    print("\n🚀 Теперь можно запускать приложение:")
    print("  python app.py")
    print("\nИ входить с указанными данными!")

if __name__ == "__main__":
    main()