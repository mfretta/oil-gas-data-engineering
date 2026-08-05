from dotenv import load_dotenv
import os

load_dotenv()

DB = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

OPEN_METEO_URL = os.getenv("OPEN_METEO_URL")
EIA_API_key = os.getenv("EIA_API_KEY")

