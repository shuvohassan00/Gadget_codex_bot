#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
from telethon import TelegramClient
import config
from utils import LOGGER

CodeUtilBot = TelegramClient(
    session='codeutilbot',
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    connection_retries=None,
    retry_delay=1,
)

async def start_bot():
    LOGGER.info("Creating Telethonian Client From BOT_TOKEN")
    await CodeUtilBot.start(bot_token=config.BOT_TOKEN)
    LOGGER.info("Telethonian Client Created Successfully!")