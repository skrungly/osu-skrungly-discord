from discord import Embed, Colour
from discord.ext import commands
from discord.ext.commands.errors import BadArgument

from bot.constants import DOMAIN, API_URL


class Skins(commands.Cog):
    """commands related to user-uploaded skins!"""

    def __init__(self, chatot):
        self.chatot = chatot

    @commands.command()
    async def skin(self, ctx, user=None):
        """get a download link for a user-uploaded skin."""

        if ctx.message.attachments:
            profile_link = f"https://osu.{DOMAIN}"

            try:
                author_info = await self.chatot.resolve_player_info(ctx)
            except RuntimeError:
                pass  # no such player? just link the site anyways.
            else:
                profile_link += f"/u/{author_info['name']}"

            raise BadArgument(
                "user-uploaded skins are no longer being stored here on "
                "the discord bot. you should soon be able to manage your "
                f"skin from [your profile]({profile_link}) instead!"
            )

        player_info = await self.chatot.resolve_player_info(ctx, user)
        skin_link = f"{API_URL}/players/{player_info['name']}/skin"

        embed = Embed(
            title="skin request successful!",
            description=f"click [here]({skin_link}) to download it.",
            color=Colour.brand_green()
        )

        await ctx.reply(embed=embed)


async def setup(chatot):
    await chatot.add_cog(Skins(chatot))
