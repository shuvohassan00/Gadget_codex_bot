#Copyright @ISmartCoder
#Updates Channel @abirxdhackz
from telethon import events, Button
from bot import CodeUtilBot
import config
import asyncio
from utils import LOGGER
import re

prefixes = ''.join(re.escape(p) for p in config.COMMAND_PREFIXES)
start_pattern = re.compile(rf'^[{prefixes}]start(?:\s+.+)?$', re.IGNORECASE)

@CodeUtilBot.on(events.NewMessage(pattern=start_pattern))
async def start_handler(event):
    sender = await event.get_sender()
    name = (sender.first_name or "User").strip()

    msg = await CodeUtilBot.send_message(
        event.chat_id,
        "**Starting Code Util Bot ⚙️....**"
    )

    await asyncio.sleep(0.2)
    await msg.edit("**Generating Session Keys...**")

    await asyncio.sleep(0.2)

    text = (
        f"**Hi {name}! Welcome To This Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**CodeUtil ⚙️** is your ultimate toolkit on Telegram, packed with free hosts. Simplify your servers with ease!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Don't forget to [join](https://{config.UPDATE_CHANNEL_URL}) for updates!"
    )

    buttons = [
        [Button.inline("⚙ Main Menu", b"main_menu")],
        [Button.inline("ℹ️ About Me", b"about"), Button.inline("📄 Policy & Terms", b"policy")],
    ]

    await msg.edit(
        text,
        link_preview=False,
        buttons=buttons
    )