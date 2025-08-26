from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

password = input("Enter admin password: ")
hashed = pwd_context.hash(password)
print(f"\nPassword hash:\n{hashed}")
print(f"\nAdd this to your .env file:")
print(f"ADMIN_PASSWORD_HASH={hashed}")