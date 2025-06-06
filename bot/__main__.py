import asyncio
import logging

import aiohttp
from discord import Intents

from bot import Chatot
from bot.constants import BOT_TOKEN

logging.basicConfig(level=logging.INFO)


async def main():
    """set up and start the discord bot instance."""

    intents = Intents.default()
    intents.message_content = True

    async with aiohttp.ClientSession() as http_session:
        chatot = Chatot(
            command_prefix="!",
            intents=intents,
            http_session=http_session,
        )

        async with chatot:
            await chatot.load_extension("bot.cogs.scores")
            await chatot.load_extension("bot.cogs.skins")
            await chatot.load_extension("bot.cogs.tasks")

            await chatot.start(BOT_TOKEN)


asyncio.run(main())
