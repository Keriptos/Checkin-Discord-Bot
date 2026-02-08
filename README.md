This is a very customized project, woudln't work for most. You have to have a some sort of credentials file so that the program
can connect to Google Sheets.
[A video on how to set it up -->](https://youtu.be/zCEJurLGFRk)


## Local Data Files

This project requires the following local JSON files:

- credentials.json --> This is automatically generated from Google Sheets API
- users.json
- checkintimes.json
- sheetCache.json

These files are ignored by git and must be created locally.

Example structures:
- users_example.json
- checkintimes_example.json
- sheetCache_example.json

# Installation: 
pip install requirements.txt


# How to run?
python -m bot.main
