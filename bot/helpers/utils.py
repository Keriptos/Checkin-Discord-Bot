import datetime
from bot.config_builder import ConfigDTO
import json
import os
from datetime import timedelta

CFG = ConfigDTO()

def lockedInTime(elapsed: timedelta) -> str:
    total_seconds = int(elapsed.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:  # show seconds, or "0 seconds" if everything is 0
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return " ".join(parts)

def loadJSON(file_path):    
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write('{}') # create empty file with an empty dict
    try:
        with open(file_path) as file: 
            return json.load(file)
    except json.JSONDecodeError:
        with open(file_path, 'w') as file:
            file.write('{}')  # Create an empty JSON file if it doesn't exist or is invalid and write in an empty dict
    return {}

def saveJSON(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent = 4)


def newUserSheetID(userID: int):
    """Hashed user sheetID I guess?"""
    newSheetID = userID % 1_000_000_000
    return newSheetID

def templateSheetLayout(username: str, format: str): # All index are 0-based
    FORMATS = { # These are the static table locations that are in "Template" sheet, don't use this after copying once
        "Yearly": (0, 34, 3, 17),    # yearly | 3 -> D column | 17 -> R column (exclusive)        
        "Semesterly_Standard": (35, 70, 3, 17),   # semester
        "Semesterly_Extended": (35, 70, 18, 38),  # semester (alternate) | 18 -> S column | 38 is AM column (exclusive)
        "Quarterly_Standard": (71, 106, 3, 17),  # quarter
        "Quarterly_Extended": (71, 106, 18, 35), # quarter (alternate) | 18 -> S column | 35 is AJ column (exclusive)
    }
    startRow, endRow, startCol, endCol = FORMATS[format]
    data = {
        username: {
            "startRowIndex": startRow,
            "endRowIndex": endRow,
            "startColumnIndex": startCol,
            "endColumnIndex": endCol,
        }
    }
    return data

def semesterly_standard_selector(col):
    return 0 if col % 2 == 1 else 1

def semesterly_extended_selector(col):
    if col % 3 == 2: return 0
    elif col % 3 == 0: return 1
    else: return 2

def quarterly_standard_selector(col):
    if col % 4 == 1: return 0
    elif col % 4 == 2: return 1
    elif col % 4 == 3: return 2
    else: return 3

def quarterly_extended_selector(col):
    return col % 5

def col_selector(col: int, userFormat: str) -> int:
    """Does not support yearly activity"""
    if userFormat == "Semesterly_Standard":
        return semesterly_standard_selector(col)
    elif userFormat == "Semestery_Extended":
        return semesterly_extended_selector(col)
    elif userFormat == "Quarterly_Standard":
        return quarterly_standard_selector(col)
    elif userFormat == "Quarterly_Extended":
        return quarterly_extended_selector(col)
    else:
        raise ValueError(f"Not supported for {userFormat} format")
    
def col_range_selector(userFormat: str):
    if userFormat == "Semesterly_Standard":
        return range(5,17)
    elif userFormat == "Semestery_Extended":
        return range(5,23)
    elif userFormat == "Quarterly_Standard":
        return range(5,17)
    elif userFormat == "Quarterly_Extended":
        return range(5,20)
    else:
        raise ValueError(f"Not supported for {userFormat} format")


def activity_rewrites(sheetID: int, user: dict, col_range: range, activityRow: int):
    rewrites: list = []
    userFormat = user['format']
    userActivities = user['activities']
    for col in col_range:
        selector = col_selector(col, userFormat)
        rewrites.append({
            "updateCells": {
                "rows": [{"values": [{"userEnteredValue": {"stringValue": f"{userActivities[selector]}"}}]}],
                "fields": "userEnteredValue",
                "range": {
                    "sheetId": sheetID,
                    "startRowIndex": activityRow,
                    "endRowIndex": activityRow + 1,
                    "startColumnIndex": col,
                    "endColumnIndex": col + 1,
                }
            }
        })
    return rewrites

if __name__ == "__main__":
    user = loadJSON(CFG.USERS_FILE)['461526727521206282']
    print(activity_rewrites(521206282, user, col_range_selector(user['format']), 3))