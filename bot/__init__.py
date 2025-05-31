import traceback

from discord.ext import commands

from bot.constants import API_URL
from bot.utils import send_error


class Chatot(commands.Bot):
    def __init__(self, *args, http_session, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_session = http_session
        self.current_status = None

    async def on_command_error(self, ctx, err):
        # TODO: this produces an unfriendly wall of error text. maybe
        # we should make a private dev channel for these messages?
        msg_block = '\n'.join(traceback.format_exception(err))
        await send_error(ctx, "oops! something broke.", f"```{msg_block}```")

    async def api_get(self, endpoint, params=None):
        """Send a GET request to an endpoint on the API."""
        return await self.http_session.get(f"{API_URL}/{endpoint}", params=params)
