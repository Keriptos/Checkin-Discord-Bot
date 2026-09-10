from postgrest import APIResponse, APIError
from postgrest.types import JSON
from discord import Member as DiscordMember
from supabase import AsyncClient, create_async_client
import asyncio
from dotenv import load_dotenv
from datetime import timezone, timedelta, datetime
import uuid
import os
import logging


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class SupaService:
    _db: AsyncClient | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def init_supabase(cls):
        """Make an async supabase client internally"""
        if cls._db is None:
            async with cls._lock:
                if cls._db is None:
                    SUPA_URL: str = os.environ.get("SUPABASE_URL")
                    SUPA_KEY: str = os.environ.get("SUPABASE_KEY")
                    cls._db = await create_async_client(SUPA_URL, SUPA_KEY)        

    @classmethod
    async def generate_user(cls, user: DiscordMember, sheet_format: str):
        try:
            await cls._db.table('users').insert({
                "id": uuid.uuid4(),
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
                "name": user.global_name,
                "sheet_format": sheet_format,
                "remind_at": None,
                "utc_hour": None,
                "utc_min": None,
                "discord_id": str(user.id)
            }).execute()
        except Exception as e:
            logger.error(f"Something went wrong in generating the user | {e}", exc_info=True)

    @classmethod
    async def get_supabase_user(cls, discord_id: str) -> JSON | None:    
        result = await cls._db.table('users').select('*').eq('discord_id', discord_id).execute()
        if result.data:
            return result.data[0]
        return None

    @classmethod
    async def generate_activity(cls, activity_name: str) -> APIResponse:
        try:
            await cls._db.table('activities').insert({'name': activity_name}).execute()
        except APIError as e:
            logger.error(f"Something went wrong, {e}", exc_info=True)

    @classmethod
    async def get_activity_id(cls, activity_name: str) -> str:
        try:
            result = await cls._db.table('activities').select('id').eq('name', activity_name).execute()
            if result.data:
                return result.data[0]['id']
            else:            
                raise LookupError(f"'{activity_name}' was not found in the database!")
        except APIError as e:
            logger.error(f"Something went wrong, {e}", exc_info=True)

    @classmethod
    async def make_checkin_record(cls, supa_user: JSON, activity_id: str) -> None:
        try: 
            await cls._db.table('checkins').insert({
                "user_id": supa_user['id'],
                "activity_id": activity_id,
                "start_time": datetime.now(timezone(timedelta(hours=supa_user['utc_hour'], minutes=supa_user['utc_min']))).isoformat(),
            }).execute()
        except APIError as e:
            logger.error(f"Something went wrong: {e}", exc_info=True)

    @classmethod
    async def check_out(cls, supa_user: JSON, activity_id: str): # Updates the checkin record
        try:
            await cls._db.table('checkins').update({
                "end_time": datetime.now(timezone(timedelta(hours=supa_user['utc_hour'], minutes=supa_user['utc_min']))).isoformat(),
            }).eq('user_id', supa_user['id']).eq('activity_id', activity_id).is_('end_time', "null").execute()
        except APIError as e:
            logger.error(f"Something went wrong: {e}", exc_info=True)

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
            created_at: datetime.isoformat,
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


async def main():
    await SupaService.init_supabase()
    supa_user = await SupaService.get_supabase_user(591939252061732900)
    activity_id = await SupaService.get_activity_id('Coding')
    # await SupaService.make_checkin_record(supa_user, activity_id)
    await SupaService.check_out(supa_user, activity_id)


if __name__ == "__main__":
    asyncio.run(main())