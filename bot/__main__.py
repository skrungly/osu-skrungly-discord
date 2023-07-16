import asyncio
import json
import os
import shutil
import traceback
from io import BytesIO
from zipfile import ZipFile

import aiomysql
from discord import Colour, Embed, File, Game, Intents
from discord.ext.commands import Bot, Context

from .replay import get_replay_screen, SKINS_PATH, USED_SKIN_ELEMENTS

intents = Intents.default()
intents.message_content = True

chatot = Bot(
    command_prefix="!",
    activity=Game("with wigglytuff"),
    intents=intents
)


async def send_error(ctx, title, message=None):
    embed = Embed(
        title=title,
        color=Colour.brand_red(),
        description=message
    )

    await ctx.reply(embed=embed)


@chatot.event
async def on_command_error(ctx, err):
    await send_error(
        ctx,
        "oops!",
        "```" + "\n".join(traceback.format_exception(err)) + "```"
    )


@chatot.event
async def on_ready():
    chatot.db = await aiomysql.connect(
        host="mysql",
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        db=os.environ["MYSQL_DATABASE"],
        cursorclass=aiomysql.cursors.DictCursor,
        loop=chatot.loop
    )

    print("ready!", flush=True)


async def fetch_user(ctx, username):
    async with chatot.db.cursor() as cursor:
        await cursor.execute(
            "SELECT * FROM users WHERE name=(%s)",
            (username,)
        )

        user_data = await cursor.fetchone()

    if not user_data:
        await send_error(
            ctx,
            title=f"could not find user *{username}*",
            message=(
                "specify a user with `!last [user]`, or link your "
                "account by setting your nickname in this server "
                "to match your osu!skrungly username :)"
            )
        )

        return

    return user_data


async def query_score(query, args):
    async with chatot.db.cursor() as cursor:
        await cursor.execute(query, args)
        score = await cursor.fetchone()

        await cursor.execute(
            "SELECT * FROM maps WHERE md5=(%s)",
            (score['map_md5'],)
        )

        beatmap = await cursor.fetchone()
        await chatot.db.commit()

    return score, beatmap


async def upload_results(ctx, score, beatmap, user):
    async with chatot.db.cursor() as cursor:
        await cursor.execute(
            "SELECT COUNT(1) FROM scores "
            "WHERE map_md5 = (%s) AND score > (%s) AND status = 2 ",
            (score["map_md5"], score["score"])
        )

        rank = list((await cursor.fetchone()).values())[0]
        await chatot.db.commit()

    async with ctx.typing():
        replay_img = await get_replay_screen(
            score,
            beatmap,
            user["name"],
            str(ctx.author.id)
        )

    embed = Embed(
        title=f"{beatmap['artist']} - {beatmap['title']} [{beatmap['version']}]",
        url=f"https://osu.ppy.sh/beatmapsets/{beatmap['set_id']}",
        colour=Colour.blue(),
        timestamp=score["play_time"]
    )

    embed.set_author(
        name=user["name"],
        url=f"https://osu.skrungly.com/u/{user['name']}",
        icon_url=f"https://a.skrungly.com/{user['id']}"
    )

    embed.set_footer(text=f"{score['pp']}pp | achieved #{rank + 1} @ osu!skrungly")

    with BytesIO() as img_binary:
        replay_img.save(img_binary, "PNG")
        img_binary.seek(0)

        filename=f"result{score['id']}.png"
        msg_file = File(fp=img_binary, filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        await ctx.reply(file=msg_file, embed=embed)


@chatot.command()
async def last(ctx, *args):
    embed = Embed(
        title="the `!last` command has been renamed",
        color=Colour.brand_green(),
        description="you can now use `!score last`, or just `!score` for short."
    )

    await ctx.reply(embed=embed)


@chatot.group(invoke_without_command=True)
async def score(ctx, *args):
    await ctx.invoke(chatot.get_command("score last"), *args)


@score.command()
async def last(ctx, username=None):
    username = username or ctx.author.display_name
    user_data = await fetch_user(ctx, username)

    if not user_data:
        return

    score, beatmap = await query_score(
        "SELECT * FROM scores "
        "WHERE userid = (%s) AND status != 0 "
        "ORDER BY play_time DESC "
        "LIMIT 1",
        (user_data["id"],)
    )

    await upload_results(ctx, score, beatmap, user_data)


@score.command()
async def top(ctx, username=None):
    username = username or ctx.author.display_name
    user_data = await fetch_user(ctx, username)

    if not user_data:
        return

    score, beatmap = await query_score(
        "SELECT * FROM scores "
        "WHERE userid = (%s) AND status = 2 AND map_md5 in ("
        "    SELECT md5 FROM maps WHERE status = 2 OR status = 3"
        ") ORDER BY pp DESC "
        "LIMIT 1",
        (user_data["id"],)
    )

    await upload_results(ctx, score, beatmap, user_data)


@chatot.command()
async def skin(ctx):
    attached = ctx.message.attachments

    if not attached:
        await send_error(ctx, "please upload a skin alongside your command!")
        return

    elif len(attached) > 1:
        await send_error(ctx, "please only upload one file!")
        return

    skin_folder = SKINS_PATH / str(ctx.author.id)

    async with ctx.typing():
        if skin_folder.exists():
            shutil.rmtree(skin_folder)

        skin_folder.mkdir()

        osz_buffer = BytesIO()
        await attached[0].save(osz_buffer)
        osz = ZipFile(osz_buffer)
        valid_file = False

        for element in USED_SKIN_ELEMENTS:
            try:
                await chatot.loop.run_in_executor(
                    None,
                    osz.extract,
                    f"{element}.png",
                    skin_folder
                )
                valid_file = True
            except KeyError:
                pass

            try:
                await chatot.loop.run_in_executor(
                    None,
                    osz.extract,
                    f"{element}@2x.png",
                    skin_folder
                )
                valid_file = True
            except KeyError:
                pass

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

    osz_buffer.close()
    osz.close()

    embed = Embed(
        title="custom skin has been set!",
        color=Colour.brand_green()
    )

    await ctx.reply(embed=embed)


async def main():
    async with chatot:
        await chatot.start(os.environ["BOT_TOKEN"])


asyncio.run(main())
