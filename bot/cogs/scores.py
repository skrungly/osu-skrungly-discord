import shutil
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from discord import ButtonStyle, Colour, Embed, File, User
from discord.ext import commands
from discord.ui import Button, View

from bot.replay import get_replay_screen, SKIN_FILES_PATH, SKIN_OSK_PATH
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

# limit skins to 256MB (uncompressed) to prevent silly things
SKIN_MAX_TOTAL_SIZE = 256 * 1024 * 1024


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

    async def _save_skin(self, ctx, osk_file):
        # ensure there is a unique place to put the skin and osk
        skin_folder = SKIN_FILES_PATH / str(ctx.author.id)
        archive_folder = SKIN_OSK_PATH / str(ctx.author.id)

        if skin_folder.exists():
            shutil.rmtree(skin_folder)

        if archive_folder.exists():
            shutil.rmtree(archive_folder)

        skin_folder.mkdir()
        archive_folder.mkdir()

        # we'll store the osk as-is in a user-identifiable folder
        await osk_file.save(archive_folder / osk_file.filename)

        # set up a buffer for the zip file to read from
        osk_buffer = BytesIO()
        await osk_file.save(osk_buffer)
        osk = ZipFile(osk_buffer)

        # extract the archive file-by-file
        total_size = 0
        for zipped_file in osk.infolist():
            if zipped_file.is_dir():
                continue

            total_size += zipped_file.file_size

            # do a quick check for decompression bombs
            if total_size > SKIN_MAX_TOTAL_SIZE:
                return Embed(
                    title="oops!",
                    description="skin exceeds maximum permitted size!",
                    color=Colour.brand_red()
                )

            # by renaming the filename for this ZipInfo,
            # we can force all skin elements to be in the
            # root of the skin folder, rather than in a
            # folder of the zipfile etc.
            zipped_file.filename = Path(zipped_file.filename).name

            await self.chatot.loop.run_in_executor(
                None,
                osk.extract,
                zipped_file,
                Path(skin_folder)
            )

        osk_buffer.close()
        osk.close()

        return Embed(
            title="skin saved successfully!",
            color=Colour.brand_green()
        )

    async def _get_skin(self, ctx, user_arg):
        if user_arg is not None:
            try:
                user = await commands.MemberConverter().convert(ctx, user_arg)
            except commands.MemberNotFound:
                return
        else:
            user = ctx.author

        archive_folder = SKIN_OSK_PATH / str(user.id)

        if archive_folder.exists():
            skin_path = list(archive_folder.iterdir())[0]
            return File(skin_path)  # there should just be the one file

    @commands.command()
    async def skin(self, ctx, user=None):
        attachments = ctx.message.attachments

        reply_file = None
        reply_embed = None

        async with ctx.typing():
            if attachments:
                if user is not None:
                    reply_embed = Embed(
                        title="please specify a skin or a user, not both!",
                        color=Colour.brand_red()
                    )

                elif len(attachments) > 1:
                    reply_embed = Embed(
                        title="please only provide one file for your skin!",
                        color=Colour.brand_red()
                    )

                else:
                    reply_embed = await self._save_skin(ctx, attachments[0])

            # if a skin wasn't attached, return a given user's skin instead
            else:
                reply_file = await self._get_skin(ctx, user)

                if not reply_file:
                    reply_embed = Embed(
                        title=f"user has not uploaded a skin yet!",
                        color=Colour.brand_red()
                    )

            await ctx.reply(embed=reply_embed, file=reply_file)


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
