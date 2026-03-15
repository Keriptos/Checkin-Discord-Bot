import os
import json
from pathlib import Path
from configparser import ConfigParser
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

# Read the config file
config = ConfigParser()
config.read(BASE_DIR / "config.ini")

class ConfigDTO:
    """Put the file configs into objects"""
    DISCORD_TOKEN   = os.getenv("TEST_BOT") # Token of test-bot.
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    GUILD_ID        = os.getenv("SERVER_ID")
    CREDS           = json.loads(os.getenv("CREDS"))
    CHECKIN_FILE    = BASE_DIR / config["Paths"]["checkin_file"]
    USERS_FILE      = BASE_DIR / config["Paths"]["users_file"]
    SHEET_CACHE     = BASE_DIR / config["Paths"]["sheet_cache"]


if __name__ == "__main__":
    cfg = ConfigDTO()
    print(cfg.CHECKIN_FILE)
    print(cfg.SHEET_CACHE)