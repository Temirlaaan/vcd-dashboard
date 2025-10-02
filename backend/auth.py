# auth.py - Унифицированная система авторизации (JWT + Keycloak)
from datetime import datetime, timedelta
from typing import Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging

# Импортируем Keycloak модуль
try:
    from keycloak_auth import (
        KEYCLOAK_ENABLED, 
        keycloak_client, 
        get_current_keycloak_user,
        KeycloakUser
    )
except ImportError:
    KEYCLOAK_ENABLED = False
    keycloak_client = None
    get_current_keycloak_user = None
    KeycloakUser = None

load_dotenv()
logger = logging.getLogger(__name__)

# ============ КОНФИГУРАЦИЯ ============
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ============ МОДЕЛИ ============
class Token(BaseModel):
    access_token: str
    token_type: str
    auth_method: str = "jwt"  # jwt или keycloak

class TokenData(BaseModel):
    username: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    roles: list = []
    is_active: bool = True
    auth_method: str = "jwt"  # jwt или keycloak

# ============ ФУНКЦИИ JWT ============
def verify_password(plain_password, hashed_password):
    """Проверить пароль"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Получить хеш пароля"""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[User]:
    """Аутентификация пользователя через локальную БД"""
    if username != ADMIN_USERNAME:
        return None
    if not verify_password(password, ADMIN_PASSWORD_HASH):
        return None
    return User(username=username, auth_method="jwt")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создать JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_jwt_user(credentials: HTTPAuthorizationCredentials) -> User:
    """Получить пользователя из JWT токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    
    if token_data.username != ADMIN_USERNAME:
        raise credentials_exception
    
    return User(username=token_data.username, auth_method="jwt")

# ============ УНИФИЦИРОВАННАЯ АВТОРИЗАЦИЯ ============
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Union[User, 'KeycloakUser']:
    """
    Унифицированная функция для получения текущего пользователя.
    Автоматически определяет метод аутентификации (JWT или Keycloak)
    """
    token = credentials.credentials
    
    # Сначала пробуем Keycloak (если включен)
    if KEYCLOAK_ENABLED and keycloak_client:
        try:
            logger.debug("Trying Keycloak authentication...")
            keycloak_user = await get_current_keycloak_user(credentials)
            # Конвертируем в нашу модель User
            return User(
                username=keycloak_user.username,
                email=keycloak_user.email,
                first_name=keycloak_user.first_name,
                last_name=keycloak_user.last_name,
                roles=keycloak_user.roles,
                is_active=keycloak_user.is_active,
                auth_method="keycloak"
            )
        except HTTPException as e:
            # Если Keycloak не смог валидировать, пробуем JWT
            logger.debug(f"Keycloak auth failed: {e.detail}, trying JWT...")
    
    # Пробуем JWT аутентификацию
    try:
        logger.debug("Trying JWT authentication...")
        return await get_current_jwt_user(credentials)
    except HTTPException as jwt_error:
        # Если оба метода не сработали
        logger.error("Both authentication methods failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials with any authentication method",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency для защищенных роутов"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# ============ ПРОВЕРКА РОЛЕЙ ============
def require_role(required_role: str):
    """
    Decorator для проверки роли пользователя
    
    Example:
        @app.get("/admin")
        async def admin_route(user: User = Depends(require_role("admin"))):
            return {"message": "Admin access"}
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if required_role not in current_user.roles and current_user.username != ADMIN_USERNAME:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    return role_checker

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============
def generate_password_hash(password: str) -> str:
    """
    Генерация хеша пароля для использования в .env
    
    Usage:
        python -c "from auth import generate_password_hash; print(generate_password_hash('mypassword'))"
    """
    return get_password_hash(password)

# Логируем метод аутентификации при старте
if KEYCLOAK_ENABLED:
    logger.info("🔐 Authentication: Keycloak + JWT (fallback)")
else:
    logger.info("🔐 Authentication: JWT only")
