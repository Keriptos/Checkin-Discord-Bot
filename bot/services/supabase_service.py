from postgrest import APIResponse, APIError
from discord import Member as DiscordMember
from dotenv import load_dotenv
import supabase
import uuid
import os
import logging
import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPA_URL: str = os.environ.get("SUPABASE_URL")
SUPA_KEY: str = os.environ.get("SUPABASE_KEY")
try:    
    db: supabase.Client = supabase.create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    print(f"Error connecting to Supabase: {e}")

VALID_UTC_ = {
    (-12,0), (-11,0),(-10,0),(-9,30),(-9,0),(-8,0),(-7,0),(-6,0),(-5,0), # 9 items
    (-4,0),(-3,30),(-3,0),(-2,0),(-1,0),(0,0),(1,0),(2,0),(3,0),(3,30), # 10 items
    (4,0),(4,30),(5,0),(5,30),(5,45),(6,0),(6,30),(7,0),(8,0),(8,45), # 10 items
    (9,0),(9,30),(10,0),(10,30),(11,0),(12,0),(12,45),(13,0),(14,0) # 9 items
}

class SupaUserData:
    def __init__(self,
            id: uuid.uuid4,
            name: str, 
            created_at: datetime.date.isoformat,
            sheet_format: str,            
            remind_at: int | None = None,
            utc_hour: int | None = None,
            utc_min: int | None = None,
            discord_id: str | None = None):

        self.id = id
        self.created_at = created_at
        self.name = name
        self.sheet_format = sheet_format
        self.remind_at = remind_at
        self.utc_hour = utc_hour
        self.utc_min = utc_min
        self.discord_id = discord_id
    
    def _validate_time(self):
        self.timezone = (self.utc_hour, self.utc_min)
        if self.timezone not in VALID_UTC_:
            raise ValueError(f"Invalid timezone: {self.timezone[0]}:{self.timezone[1]}.")

# def generate_user(user: DiscordMember, sheet_format: str):
#     result = db.table('users').insert({
#         "id": uuid.uuid4(),
#         "created_at": datetime.date.today().isoformat(),
#         "name": user.global_name,
#         "sheet_format": sheet_format,
#         "remind_at": None,
#         "utc_hour": None,
#         "utc_min": None,
#         "discord_id": str(user.id)        
#     }).execute()
    

def get_supabase_user_id(discord_id: str) -> str | None:
    result = db.table('users').select('id').eq('discord_id', discord_id).execute()
    if result.data:
        return result.data[0]['id']
    return None

def generate_activity(activity_name: str) -> APIResponse:
    try:
        db.table('activities').insert({'name': activity_name}).execute()    
    except APIError as e:
        logger.error(f"Something went wrong, {e}", exc_info=True)

def get_activity_id(activity_name: str) -> str:
    try:
        result = db.table('activities').select('id').eq('name', activity_name).execute()
        if result.data:
            return result.data[0]['id']
        else:            
            raise LookupError(f"'{activity_name}' was not found in the database!")
    except APIError as e:
        logger.error(f"Something went wrong, {e}", exc_info=True)

def make_checkin_record(supa_user_id: str, activity_id: str) -> None:
    try: 
        db.table('checkins').insert({            
            "user_id": supa_user_id,
            "activity_id": activity_id,
            "start_time": datetime.datetime.now().isoformat(),            
        }).execute()
    except APIError as e:
        logger.error(f"Something went wrong: {e}", exc_info=True)

def check_out(supa_user_id: str, activity_id: str): # Updates the checkin record
    try:
        db.table('checkins').update({
            "end_time": datetime.datetime.now().isoformat(),
        }).eq('user_id', supa_user_id).eq('activity_id', activity_id).is_('end_time', "null").execute()
    except APIError as e:
        logger.error(f"Something went wrong: {e}", exc_info=True)


def main():
    user_id = get_supabase_user_id(591939252061732900)
    activity_id = get_activity_id("Coding")
    check_out(user_id, activity_id)
    # print(user_id)
    # check_out(user_id)
    # get_activity_id("Studying")
    # result = (
    #     db.table('checkins')
    #     .select('*')
    #     .eq('user_id', user_id)
    #     .is_('end_time', "null")
    #     .execute())
    # print(result)

    

if __name__ == "__main__":
    main()