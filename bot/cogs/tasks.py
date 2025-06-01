from discord import Activity, ActivityType, Status
from discord.ext import commands, tasks

from bot.utils import old_api_get


class Tasks(commands.Cog):
    """management of scheduled and repeated tasks."""

    def __init__(self, chatot):
        self.chatot = chatot
        self.status_loop.start()

    @tasks.loop(seconds=20)
    async def status_loop(self):
        """update the bot status based on players online."""

        api_status, response = await old_api_get(
            self.chatot.http_session, version=1, endpoint="get_player_count"
        )

        bot_status = Status.idle
        activity_type = ActivityType.watching
        message = "osu! alone :("

        if api_status != 200:
            bot_status = Status.dnd
            activity_type = ActivityType.watching
            message = "the server fail"

        elif online := response["counts"]["online"]:
            bot_status = Status.online
            activity_type = ActivityType.playing
            message = (
                f"with {online} player{'s' if online > 1 else ''} online!"
            )

        activity = Activity(type=activity_type, name=message)

        if self.chatot.current_status != message:
            self.chatot.current_status = message
            await self.chatot.change_presence(
                activity=activity, status=bot_status
            )

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.chatot.wait_until_ready()


async def setup(chatot):
    await chatot.add_cog(Tasks(chatot))
