from datetime import datetime
from io import BytesIO

from discord import Colour, Embed, File
from discord.ext import commands
from discord.ui import Button, View

from bot.constants import API_STRFTIME, DOMAIN, MAP_DL_MIRROR
from bot.utils import (
    fetch_difficulty,
    fetch_player,
    Mods,
    send_error
)


class Scores(commands.Cog):
    def __init__(self, chatot):
        self.chatot = chatot

    @commands.command()
    async def score(self, ctx, user=None):
        player = (await fetch_player(ctx, user, scope="info")).get("info")
        if not player:
            return

        info_response = await self.chatot.api_get(
            endpoint=f"/players/{player['id']}/scores",
            params={
                "sort": "recent",
                "limit": 1
            }
        )

        async with info_response:
            if info_response.status != 200:
                await send_error(ctx, "unable to fetch scores.")
                return

            scores = await info_response.json()

        if not scores:
            await send_error(
                ctx,
                f"couldn't find any scores for player {player['name']}!",
                "if this seems wrong, it seriously is. let kingsley know!"
            )
            return

        score = scores[0]
        beatmap = score["beatmap"]
        mods = Mods(score["mods"])

        # api returns a string, so parse back into a usable format
        score["play_time"] = datetime.strptime(
            score["play_time"], API_STRFTIME
        )

        difficulty = await fetch_difficulty(
            beatmap["id"],
            score["mode"],
            mods,
        )

        async with ctx.typing():
            img_response = await self.chatot.api_get(
                endpoint=f"/scores/{score['id']}/screen"
            )

            async with img_response:
                if info_response.status != 200:
                    await send_error(ctx, "score screenshot not available.")

                img_buffer = BytesIO(await img_response.read())
                img_buffer.seek(0)

        embed = Embed(
            title="{artist} - {title} [{version}]".format(**beatmap),
            url=f"https://osu.{DOMAIN}/beatmapsets/{beatmap['set_id']}",
            colour=Colour.blue(),
            timestamp=score["play_time"]
        )

        embed.set_author(
            name=player["name"],
            url=f"https://osu.{DOMAIN}/u/{player['name']}",
            icon_url=f"https://a.{DOMAIN}/{player['id']}"
        )

        adjusted_bpm = beatmap['bpm'] * mods.speed
        adjusted_length = int(beatmap["total_length"] / mods.speed)
        duration_str = f"{adjusted_length // 60}:{adjusted_length % 60:02}"

        embed.add_field(name="performance", value=f"{score['pp']}pp")
        embed.add_field(name="star rating", value=f"{difficulty:.02f}*")
        embed.add_field(name="\u200b", value="\u200b")  # empty field!

        embed.add_field(name="duration", value=duration_str)
        embed.add_field(name="max combo", value=f"{beatmap['max_combo']}x")
        embed.add_field(name="speed", value=f"{adjusted_bpm:g} bpm")

        embed.set_footer(text="osu!skrungly")

        view = ScoreView(beatmap["set_id"], score["id"])

        filename = f"result{score['id']}.png"
        msg_file = File(fp=img_buffer, filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        await ctx.reply(file=msg_file, embed=embed, view=view)


class ScoreView(View):
    def __init__(self, mapset_id: int, replay_id: int):
        super().__init__()

        map_button = Button(
            label="map (.osz)",
            url=f"{MAP_DL_MIRROR}/{mapset_id}"
        )

        replay_button = Button(
            label="replay (.osr)",
            url=f"https://api.{DOMAIN}/v1/get_replay?id={replay_id}"
        )

        self.add_item(map_button)
        self.add_item(replay_button)


async def setup(chatot):
    await chatot.add_cog(Scores(chatot))
