from pydantic_settings import BaseSettings


class Settings(BaseSettings):               # Settings is a subclass of BaseSettings
    """
    Reads environment variables from the .env file automatically.
    Each field name here must match the key in .env (case-insensitive).
    If a required field is missing, Pydantic raises a clear error at startup.
    """

    # Database
    DATABASE_URL: str

    # AI APIs
    OPENAI_API_KEY: str

    # App
    APP_ENV: str = "development"  # has a default, so it's optional in .env

    class Config:
        # Tells Pydantic where to find the .env file
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single shared instance.
# Every other file imports THIS object instead of re-reading .env themselves.
settings = Settings()
