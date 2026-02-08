import os
from pathlib import Path
from configparser import ConfigParser
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# .env lives under the secrets folder
load_dotenv()
DISCORD_TOKEN = os.getenv("discordToken")
GOOGLE_SHEET_ID = os.getenv("googleSheetID")

# Read the config file
config = ConfigParser()
config.read(BASE_DIR / "config.ini")


CHECKIN_FILE = BASE_DIR / config["Paths"]["checkin_file"]
USERS_FILE   = BASE_DIR / config["Paths"]["users_file"]
SHEET_CACHE = BASE_DIR / config["Paths"]["sheet_cache"]
CREDS_PATH = BASE_DIR / config["Paths"]["credsPath"]
if __name__ == "__main__":
    print()