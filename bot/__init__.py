import traceback

from discord.ext import commands

from bot.utils import api_get, resolve_player_info, send_error


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
        """A wrapper around `bot.utils.api_get`."""
        return await api_get(self.http_session, endpoint, params)

    async def resolve_player_info(self, ctx, user=None):
        """A wrapper around `bot.utils.resolve_player_info`."""
        return await resolve_player_info(self.http_session, ctx, user)
