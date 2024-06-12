# telegram_bot/config.py
from decouple import config

# Extracting configuration data from environment variables or .env file
HOST = config('HOST')
