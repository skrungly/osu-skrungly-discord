import os
from typing import Optional

from aiohttp import ClientSession
from aiohttp.web import HTTPNotFound
from discord import Colour, Embed
from discord.ext.commands import Context, Converter, MemberConverter
from discord.ext.commands.errors import MemberNotFound

DOMAIN = os.environ["DOMAIN"]
MAP_DL_MIRROR = os.environ["MAP_DL_MIRROR"]

API_URL = f"https://api.{DOMAIN}"
API_STRFTIME = f"%Y-%m-%dT%H:%M:%S"


async def api_get(version: int, endpoint: str, params: Optional[dict] = None):
    url = f"{API_URL}/v{version}/{endpoint}"
    content = {}

    async with ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                content = await response.json()

            return response.status, content


async def send_error(ctx, title, message=None):
    embed = Embed(
        title=title,
        color=Colour.brand_red(),
        description=message
    )

    await ctx.reply(embed=embed)


async def fetch_player(ctx, user, scope="all"):
    if user:
        # attempt to match a discord member to use their name
        try:
            member = await MemberConverter().convert(ctx, user)
            name = member.display_name

        # otherwise, just use the name as given
        except MemberNotFound:
            name = user

    # if no name was specified, default to self
    else:
        name = ctx.author.display_name

    status, response = await api_get(
        version=1,
        endpoint="get_player_info",
        params={"name": name, "scope": scope}
    )

    err_msg = None

    if status == 404:
        if user:
            err_msg = "make sure you typed the username correctly!"
        else:
            err_msg = "your discord nickname doesn't match any osu! players."

    elif status != 200:
        err_msg = "something really broke. time to annoy kingsley!"

    if err_msg:
        err_title = f"could not get info for player *{name}*"
        await send_error(ctx, err_title, err_msg)
        return response

    return response["player"]
