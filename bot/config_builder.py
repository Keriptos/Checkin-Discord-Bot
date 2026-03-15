import os
import json
from pathlib import Path
from configparser import ConfigParser
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Handles the environment file
load_dotenv()
DISCORD_TOKEN = os.getenv("TEST_BOT") # Token of test-bot.
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GUILD_ID = os.getenv("SERVER_ID")
CREDS = json.loads(os.getenv("CREDS"))

# Read the config file
config = ConfigParser()
config.read(BASE_DIR / "config.ini")


CHECKIN_FILE = BASE_DIR / config["Paths"]["checkin_file"]
USERS_FILE   = BASE_DIR / config["Paths"]["users_file"]
SHEET_CACHE = BASE_DIR / config["Paths"]["sheet_cache"]


if __name__ == "__main__":
    print(CREDS)
    print(USERS_FILE)
    print(SHEET_CACHE)    