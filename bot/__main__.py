import asyncio
import os
import traceback

from discord import Activity, ActivityType, Intents, Status
from discord.ext import commands, tasks

from bot.utils import old_api_get, send_error

intents = Intents.default()
intents.message_content = True

chatot = commands.Bot(
    command_prefix="!",
    intents=intents
)

chatot.current_status = None


@tasks.loop(seconds=20)
async def status_loop():
    api_status, response = await old_api_get(version=1, endpoint="get_player_count")

    bot_status = Status.idle
    activity_type = ActivityType.watching
    message = "osu! alone :("

    if api_status != 200:
        bot_status = Status.dnd
        activity_type = ActivityType.watching
        message = "the server fail"

    elif ppl_online := response["counts"]["online"]:
        bot_status = Status.online
        activity_type = ActivityType.playing
        message = (
            f"with {ppl_online} player{'s' if ppl_online > 1 else ''} online!"
        )

    activity = Activity(type=activity_type, name=message)

    if chatot.current_status != message:
        print("status update!", flush=True)
        await chatot.change_presence(activity=activity, status=bot_status)
        chatot.current_status = message


@chatot.listen()
async def on_ready():
    status_loop.start()
    print("ready!", flush=True)


@chatot.listen()
async def on_command_error(ctx, err):
    await send_error(
        ctx,
        "oops!",
        "```" + "\n".join(traceback.format_exception(err)) + "```"
    )


async def main():
    async with chatot:
        await chatot.load_extension("bot.cogs.scores")
        await chatot.load_extension("bot.cogs.skins")
        await chatot.start(os.environ["BOT_TOKEN"])


asyncio.run(main())
