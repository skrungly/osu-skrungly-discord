import shutil
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from discord import ButtonStyle, Colour, Embed, File
from discord.ext import commands
from discord.ui import Button, View

from bot.replay import get_replay_screen, SKINS_PATH, USED_SKIN_ELEMENTS
from bot.utils import (
    api_get,
    API_STRFTIME,
    API_URL,
    DOMAIN,
    fetch_difficulty,
    fetch_player,
    MAP_DL_MIRROR,
    Mods,
    send_error
)

# limit skin files to 16MB to prevent silly things
SKIN_MAX_FILE_SIZE = 16 * 1024 * 1024


class Scores(commands.Cog):
    def __init__(self, chatot):
        self.chatot = chatot

    async def _send_score(self, ctx, user, scope):
        player = (await fetch_player(ctx, user, scope="info")).get("info")

        if not player:
            return

        status, response = await api_get(
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

    @commands.command()
    async def skin(self, ctx):
        attached = ctx.message.attachments

        if not attached:
            await send_error(ctx, "please upload a skin with your command!")
            return

        elif len(attached) > 1:
            await send_error(ctx, "please only upload one file!")
            return

        skin_folder = SKINS_PATH / str(ctx.author.id)

        async with ctx.typing():
            # ensure there is a unique place to put the skin
            if skin_folder.exists():
                shutil.rmtree(skin_folder)

            skin_folder.mkdir()

            # set up a buffer for the zip file to read from
            osz_buffer = BytesIO()
            await attached[0].save(osz_buffer)
            osz = ZipFile(osz_buffer)

            # scan each file to find relevant skin elements
            valid_file = False
            skipped_files = False
            for zip_info in osz.infolist():
                if zip_info.is_dir():
                    continue

                skin_element = Path(zip_info.filename).stem
                if skin_element.endswith("@2x"):
                    skin_element = skin_element[:-3]

                if skin_element in USED_SKIN_ELEMENTS:
                    # do a quick check for decompression bombs
                    if zip_info.file_size > SKIN_MAX_FILE_SIZE:
                        skipped_files = True
                        continue

                    # by renaming the filename for this ZipInfo,
                    # we can force all skin elements to be in the
                    # root of the skin folder. if there are file
                    # clashes then that's the user's problem. :)
                    zip_info.filename = Path(zip_info.filename).name

                    # we have found at least one valid skin file,
                    # so we can confirm this to the user later.
                    valid_file = True
                    await self.chatot.loop.run_in_executor(
                        None,
                        osz.extract,
                        zip_info,
                        Path(skin_folder)
                    )

            if not valid_file:
                await send_error(
                    ctx,
                    title="could not find any valid skin elements!",
                    message=(
                        "upload your skin as a `.zip` or `.osk` file. "
                        "if it still doesn't work, make sure the skin "
                        "files are at the base of the zip archive. "
                    )
                )

                return

            if skipped_files:
                await send_error(
                    ctx,
                    title="skin file exceeds maximum permitted size",
                    message=(
                        "if this was an accident; don't worry. the large "
                        "file has been skipped, and the rest of the skin "
                        "should appear as normal.\n\n"
                        "if this was a zip bomb; nice try."
                    )
                )

        osz_buffer.close()
        osz.close()

        embed = Embed(
            title="custom skin has been set!",
            color=Colour.brand_green()
        )

        await ctx.reply(embed=embed)


class ScoreView(View):
    def __init__(self, mapset_id: int, replay_id: int):
        super().__init__()

        map_button = Button(
            label="map (.osz)",
            url=f"{MAP_DL_MIRROR}/{mapset_id}"
        )

        replay_button = Button(
            label="replay (.osr)",
            url=f"{API_URL}/v1/get_replay?id={replay_id}"
        )

        self.add_item(map_button)
        self.add_item(replay_button)


async def setup(chatot):
    await chatot.add_cog(Scores(chatot))
