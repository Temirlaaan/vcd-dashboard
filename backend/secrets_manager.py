# import os
# import json
# import logging
# from typing import Dict, Optional
# from pathlib import Path
# from cryptography.fernet import Fernet
# import hashlib

# logger = logging.getLogger(__name__)

# class SecretsManager:
#     """Менеджер для безопасной работы с секретами"""
    
#     def __init__(self):
#         self.secrets_path = os.getenv('SECRETS_PATH', '/run/secrets')
#         self.secrets_file = 'vcd_credentials'
#         self._secrets_cache = None
#         self._encryption_key = self._get_or_create_key()
    
#     def _get_or_create_key(self) -> bytes:
#         """Получить или создать ключ шифрования"""
#         key_path = Path('/app/cache/.encryption_key')
#         key_path.parent.mkdir(parents=True, exist_ok=True)
        
#         if key_path.exists():
#             with open(key_path, 'rb') as f:
#                 return f.read()
#         else:
#             key = Fernet.generate_key()
#             with open(key_path, 'wb') as f:
#                 f.write(key)
#             os.chmod(key_path, 0o600)
#             return key
    
#     def _decrypt_token(self, encrypted_token: str) -> str:
#         """Расшифровать токен"""
#         try:
#             f = Fernet(self._encryption_key)
#             return f.decrypt(encrypted_token.encode()).decode()
#         except:
#             # Если не зашифрован, вернуть как есть (для обратной совместимости)
#             return encrypted_token
    
#     def load_secrets(self) -> Dict:
#         """Загрузить секреты из Docker secrets или переменных окружения"""
#         if self._secrets_cache:
#             return self._secrets_cache
        
#         secrets = {}
        
#         # Попытка загрузить из Docker secrets
#         secrets_file_path = Path(self.secrets_path) / self.secrets_file
#         if secrets_file_path.exists():
#             try:
#                 with open(secrets_file_path, 'r') as f:
#                     raw_secrets = json.load(f)
                    
#                 # Расшифровываем токены
#                 for cloud, config in raw_secrets.items():
#                     if 'api_token' in config:
#                         config['api_token'] = self._decrypt_token(config['api_token'])
#                     secrets[cloud] = config
                    
#                 logger.info("Secrets loaded from Docker secrets")
#             except Exception as e:
#                 logger.error(f"Failed to load secrets from file: {e}")
        
#         # Fallback на переменные окружения (для разработки)
#         if not secrets:
#             env_mapping = {
#                 'vcd': {
#                     'url': os.getenv('VCD_URL'),
#                     'api_version': os.getenv('VCD_API_VERSION', '38.0'),
#                     'api_token': os.getenv('VCD_API_TOKEN')
#                 },
#                 'vcd01': {
#                     'url': os.getenv('VCD_URL_VCD01'),
#                     'api_version': os.getenv('VCD_API_VERSION_VCD01', '37.0'),
#                     'api_token': os.getenv('VCD_API_TOKEN_VCD01')
#                 },
#                 'vcd02': {
#                     'url': os.getenv('VCD_URL_VCD02'),
#                     'api_version': os.getenv('VCD_API_VERSION_VCD02', '37.0'),
#                     'api_token': os.getenv('VCD_API_TOKEN_VCD02')
#                 }
#             }
            
#             for cloud, config in env_mapping.items():
#                 if config['url'] and config['api_token']:
#                     secrets[cloud] = config
            
#             if secrets:
#                 logger.info("Secrets loaded from environment variables")
        
#         self._secrets_cache = secrets
#         return secrets
    
#     def get_cloud_credentials(self, cloud_name: str) -> Optional[Dict]:
#         """Получить credentials для конкретного облака"""
#         secrets = self.load_secrets()
#         return secrets.get(cloud_name)
    
#     def validate_token(self, token: str) -> bool:
#         """Валидация токена"""
#         if not token:
#             return False
        
#         # Проверка формата токена
#         if len(token) < 20:
#             return False
        
#         # Можно добавить дополнительные проверки
#         return True
    
#     def rotate_tokens(self):
#         """Ротация токенов (для будущей реализации)"""
#         # TODO: Implement token rotation logic
#         pass

# # Вспомогательный скрипт для шифрования токенов
# def encrypt_tokens(input_file: str, output_file: str):
#     """Зашифровать токены в файле credentials"""
#     key = Fernet.generate_key()
#     f = Fernet(key)
    
#     with open(input_file, 'r') as file:
#         data = json.load(file)
    
#     # Шифруем токены
#     for cloud, config in data.items():
#         if 'api_token' in config:
#             encrypted = f.encrypt(config['api_token'].encode()).decode()
#             config['api_token'] = encrypted
    
#     with open(output_file, 'w') as file:
#         json.dump(data, file, indent=2)
    
#     print(f"Encryption key: {key.decode()}")
#     print(f"Encrypted credentials saved to: {output_file}")

# if __name__ == "__main__":
#     # Пример использования для шифрования
#     import sys
#     if len(sys.argv) == 3:
#         encrypt_tokens(sys.argv[1], sys.argv[2])