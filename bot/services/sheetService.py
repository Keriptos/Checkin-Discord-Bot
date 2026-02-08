# Google Sheets Imports
import gspread 
from google.oauth2.service_account import Credentials

# Other Imports
import time
from bot.config import CREDS_PATH, GOOGLE_SHEET_ID


g_sheet = None
def sheetInitialization():
    commandStartTime = time.perf_counter()
    global g_sheet
    if g_sheet is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes = scopes)
        client = gspread.authorize(creds)
        g_sheet = client.open_by_key(GOOGLE_SHEET_ID)
        commandEndTime = time.perf_counter()
        print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")            
    return g_sheet


def main():
    g_sheet = sheetInitialization()
    print(g_sheet)



if __name__ == "__main__":
    main()
