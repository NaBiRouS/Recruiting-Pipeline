import os
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "http://127.0.0.1:4000"

API_TOKEN = os.getenv("API_TOKEN")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}