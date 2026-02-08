# Google Sheets Imports
import gspread 
from google.oauth2.service_account import Credentials

# Other Imports
import time


g_sheet = None
def sheetInitialization():
    from dotenv import load_dotenv
    import os
    commandStartTime = time.perf_counter()
    global g_sheet
    if g_sheet is None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file("credentials.json", scopes = scopes)
        client = gspread.authorize(creds)

        load_dotenv(".env")
        sheetID = os.getenv("googleSheetID")
        g_sheet = client.open_by_key(sheetID)
        commandEndTime = time.perf_counter()
        print(f"Initialized sheet client in {commandEndTime - commandStartTime:.4f} seconds")            
    return g_sheet


def main():
    sheetInitialization()



if __name__ == "__main__":
    main()
