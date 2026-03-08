# Discord Check-In Bot (Google Sheets Integration)

## ⚠️ Important Notes

This is a **highly customized project** and is **not intended to work out-of-the-box for most users yet**. It is slowly in development for accomodating more users in the future.

The bot runs hand in hand with **Google Sheets**, which means you **must provide your own Google API credentials** in order for the bot to function. Without proper credentials, the bot will fail to load features related to Sheets.

Follow this guide on how to setup the credentials:  
👉 https://youtu.be/zCEJurLGFRk

---

## 📁 Local Data & Credentials

This project depends on several **local JSON files** that are intentionally **ignored by Git** for security and data integrity reasons.

### Required local files

- credentials.json # Generated from Google Sheets API
- users.json
- checkintimes.json
- sheetCache.json

These files **must exist locally** before running the bot.

---

### 🧪 Example templates

Example files are provided to help you get started:
- users_example.json
- checkintimes_example.json
- sheetCache_example.json

To use them:
1. Copy the example file
2. Remove `_example` from the filename
3. Adjust values when necessary

---

## ⚙️  Configuration

File paths to the data files can be adjusted in:

- config.ini

If you change the variable names in config.ini, make sure to also rename it in *bot/config.py* file

---

## 📦 Installation

Using a virtual environment is strongly recommended.

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Bot
```bash 
python -m bot.main
```
