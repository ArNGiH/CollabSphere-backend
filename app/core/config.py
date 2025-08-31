from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer,HTTPBearer


class Settings(BaseSettings):
    DATABASE_URL:str
    SECRET_KEY:str
    JWT_ALGORITHM:str
    ACCESS_TOKEN_EXPIRE_MINUTES:int
    s3_bucket_name:str
    SMTP_HOST:str
    SMTP_PORT:int
    SMTP_USER:str
    SMTP_PASS:str
    FRONTEND_RESET_URL:str
    openai_api_key: str

    class Config:
        env_file=".env"

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme = HTTPBearer()
settings=Settings()