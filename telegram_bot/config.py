from dotenv import load_dotenv
import os

load_dotenv()

# Токены и другие конфигурационные параметры
TOKEN = os.getenv('BOT_TOKEN')
HOST = os.getenv('HOST')
SPECKLE_TOKEN = os.getenv('SPECKLE_TOKEN')
