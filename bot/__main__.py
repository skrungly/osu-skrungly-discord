import asyncio
import os
import traceback

from discord import Game, Intents
from discord.ext.commands import Bot

from bot.utils import send_error

intents = Intents.default()
intents.message_content = True

chatot = Bot(
    command_prefix="!",
    activity=Game("with wigglytuff"),
    intents=intents
)


@chatot.event
async def on_ready():
    print("ready!", flush=True)


@chatot.event
async def on_command_error(ctx, err):
    await send_error(
        ctx,
        "oops!",
        "```" + "\n".join(traceback.format_exception(err)) + "```"
    )


async def main():
    async with chatot:
        await chatot.load_extension("bot.cogs.scores")
        await chatot.start(os.environ["BOT_TOKEN"])


asyncio.run(main())
