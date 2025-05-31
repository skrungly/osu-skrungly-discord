from discord import Embed, Colour
from discord.ext import commands

from bot.constants import DOMAIN, NEW_API_URL
from bot.utils import fetch_player, send_error


class Skins(commands.Cog):
    @commands.command()
    async def skin(self, ctx, user=None):
        if ctx.message.attachments:
            profile_link = f"https://osu.{DOMAIN}"

            author_info = await fetch_player(ctx, None, scope="info")
            if author_info:
                profile_link += f"/u/{author_info['info']['name']}"

            await send_error(
                ctx, "uploading new skins is currently unsupported :(", (
                    "user-uploaded skins are no longer being stored here on "
                    "the discord bot. you should soon be able to manage your "
                    f"skin from [your profile]({profile_link}) instead!"
                )
            )

            return

        player_info = await fetch_player(ctx, user, scope="info")
        if not player_info:
            return  # error already sent by fetch_player

        skin_link = f"{NEW_API_URL}/players/{player_info['info']['name']}/skin"

        embed = Embed(
            title="skin request successful!",
            description=f"click [here]({skin_link}) to download it.",
            color=Colour.brand_green()
        )

        await ctx.reply(embed=embed)


async def setup(chatot):
    await chatot.add_cog(Skins(chatot))
