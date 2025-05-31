from datetime import datetime
from io import BytesIO

from discord import Colour, Embed, File
from discord.ext import commands
from discord.ui import Button, View

from bot.constants import API_STRFTIME, DOMAIN, MAP_DL_MIRROR
from bot.replay import get_replay_screen
from bot.utils import (
    old_api_get,
    fetch_difficulty,
    fetch_player,
    Mods,
    send_error
)

# limit skins to 256MB (uncompressed) to prevent silly things
SKIN_MAX_TOTAL_SIZE = 256 * 1024 * 1024
SKIN_DOWNLOAD_URL = f"https://assets.{DOMAIN}/skins"


class Scores(commands.Cog):
    def __init__(self, chatot):
        self.chatot = chatot

    async def _send_score(self, ctx, user, scope):
        player = (await fetch_player(ctx, user, scope="info")).get("info")

        if not player:
            return

        status, response = await old_api_get(
            version=1,
            endpoint="get_player_scores",
            params={
                "id": player["id"],
                "limit": 1,
                "include_failed": "False",
                "scope": scope
            }
        )

        if status != 200:
            return await send_error(
                ctx,
                f"something went wrong fetching {scope} score!",
                "this is definitely an issue to get kingsley to sort out."
            )

        if not response["scores"]:
            return await send_error(
                ctx,
                f"couldn't find any scores for player {player['name']}!",
                "if this seems wrong, it seriously is. let kingsley know!"
            )

        score = response["scores"][0]
        beatmap = score["beatmap"]
        mods = Mods(score["mods"])

        difficulty = await fetch_difficulty(
            beatmap["id"],
            score["mode"],
            mods,
        )

        # api returns a string, so parse back into a usable format
        score["play_time"] = datetime.strptime(
            score["play_time"],
            API_STRFTIME
        )

        async with ctx.typing():
            # TODO: should probs make this properly non-blocking
            replay_img = await get_replay_screen(
                score,
                beatmap,
                player["name"],
                str(ctx.author.id)
            )

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

        with BytesIO() as img_binary:
            replay_img.save(img_binary, "PNG")
            img_binary.seek(0)

            filename = f"result{score['id']}.png"
            msg_file = File(fp=img_binary, filename=filename)
            embed.set_image(url=f"attachment://{filename}")

            await ctx.reply(file=msg_file, embed=embed, view=view)

    @commands.group(invoke_without_command=True)
    async def score(self, ctx, user=None):
        await ctx.invoke(self.chatot.get_command("score last"), user)

    @score.command()
    async def last(self, ctx, user=None):
        await self._send_score(ctx, user, scope="recent")

    @score.command()
    async def top(self, ctx, user=None):
        await self._send_score(ctx, user, scope="best")


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
