#!/usr/bin/env python3
"""
Скрипт для проверки работы авторизации
Запустите в папке backend/
"""

import requests
import json
from dotenv import load_dotenv
import os

# Загружаем .env
load_dotenv()

def test_backend():
    print("=" * 60)
    print("Тестирование Backend авторизации")
    print("=" * 60)
    
    # Проверяем переменные окружения
    print("\n1. Проверка .env файла:")
    print("-" * 40)
    
    username = os.getenv("ADMIN_USERNAME")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH")
    secret_key = os.getenv("SECRET_KEY")
    
    if not username:
        print("❌ ADMIN_USERNAME не найден в .env")
        return
    else:
        print(f"✅ ADMIN_USERNAME: {username}")
    
    if not password_hash:
        print("❌ ADMIN_PASSWORD_HASH не найден в .env")
        return
    else:
        print(f"✅ ADMIN_PASSWORD_HASH: {password_hash[:20]}...")
    
    if not secret_key:
        print("❌ SECRET_KEY не найден в .env")
        return
    else:
        print(f"✅ SECRET_KEY: {secret_key[:20]}...")
    
    # Проверяем доступность backend
    print("\n2. Проверка доступности Backend:")
    print("-" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        # Проверяем health endpoint
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend доступен на {base_url}")
            print(f"   Ответ: {response.json()}")
        else:
            print(f"⚠️  Backend отвечает с кодом: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Backend НЕ ЗАПУЩЕН или не доступен на {base_url}")
        print("\n🔧 Решение:")
        print("   1. Откройте новый терминал")
        print("   2. Перейдите в папку backend/")
        print("   3. Запустите: python app.py")
        return
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return
    
    # Тестируем авторизацию
    print("\n3. Тест авторизации:")
    print("-" * 40)
    
    # Запрашиваем пароль для теста
    test_password = input(f"Введите пароль для пользователя '{username}': ")
    
    # Пробуем залогиниться
    login_data = {
        "username": username,
        "password": test_password
    }
    
    try:
        print(f"\n📤 Отправка запроса на {base_url}/api/login")
        print(f"   Данные: username={username}, password=***")
        
        response = requests.post(
            f"{base_url}/api/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        print(f"\n📥 Ответ сервера:")
        print(f"   Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ АВТОРИЗАЦИЯ УСПЕШНА!")
            print(f"   Токен получен: {data['access_token'][:50]}...")
            
            # Проверяем защищенный endpoint
            print("\n4. Проверка доступа к защищенным данным:")
            print("-" * 40)
            
            headers = {"Authorization": f"Bearer {data['access_token']}"}
            verify_response = requests.get(f"{base_url}/api/verify", headers=headers)
            
            if verify_response.status_code == 200:
                print("✅ Токен работает, доступ к API подтвержден!")
                print(f"   Данные: {verify_response.json()}")
            else:
                print("❌ Токен не работает")
                
        elif response.status_code == 401:
            print("❌ НЕВЕРНЫЙ ЛОГИН ИЛИ ПАРОЛЬ")
            error_detail = response.json().get('detail', 'Unknown error')
            print(f"   Ошибка: {error_detail}")
            print("\n🔧 Возможные причины:")
            print("   1. Неправильный пароль")
            print("   2. Хеш пароля в .env не соответствует введенному паролю")
            print("   3. Попробуйте заново сгенерировать хеш через setup_auth.py")
            
        elif response.status_code == 422:
            print("❌ ОШИБКА ВАЛИДАЦИИ ДАННЫХ")
            print(f"   Детали: {response.json()}")
            print("\n🔧 Проверьте формат отправляемых данных")
            
        else:
            print(f"❌ Неожиданный ответ: {response.status_code}")
            print(f"   Тело ответа: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Не удается подключиться к backend")
        print("   Убедитесь, что backend запущен (python app.py)")
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
    
    print("\n" + "=" * 60)
    print("Тест завершен")
    print("=" * 60)

if __name__ == "__main__":
    test_backend()