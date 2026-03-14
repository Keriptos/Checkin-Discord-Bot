import datetime
import json
import os
from datetime import timedelta

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