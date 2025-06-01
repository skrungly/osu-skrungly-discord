from discord import Colour, Embed
from discord.ext import commands

from bot.utils import api_get, resolve_player_info


class Chatot(commands.Bot):
    def __init__(self, *args, http_session, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_session = http_session
        self.current_status = None

    async def on_command_error(self, ctx, err):
        await super().on_command_error(ctx, err)

        await ctx.reply(
            embed=Embed(
                title="oops! something went wrong.",
                color=Colour.brand_red(),
                description="".join(err.args)
            )
        )

    async def api_get(self, endpoint, params=None):
        """A wrapper around `bot.utils.api_get`."""
        return await api_get(self.http_session, endpoint, params)

    async def resolve_player_info(self, ctx, user=None):
        """A wrapper around `bot.utils.resolve_player_info`."""
        return await resolve_player_info(self.http_session, ctx, user)
