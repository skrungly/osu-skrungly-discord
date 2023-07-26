import os
from enum import IntFlag
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


class Mods(IntFlag):
    NOFAIL = "NF"
    EASY = "EZ"
    TOUCH_SCREEN = "TS"
    HIDDEN = "HD"
    HARDROCK = "HR"
    SUDDENDEATH = "SD"
    DOUBLETIME = "DT"
    RELAX = "RX"
    HALFTIME = "HT"
    NIGHTCORE = "NC"
    FLASHLIGHT = "FL"
    AUTOPLAY = "AT"
    SPUNOUT = "SO"
    RELAX2 = "AP"
    PERFECT = "PF"
    KEY4 = "4K"
    KEY5 = "5K"
    KEY6 = "6K"
    KEY7 = "7K"
    KEY8 = "8K"
    FADEIN = "FI"
    RANDOM = "RD"
    CINEMA = "CM"
    TARGET = "TP"
    KEY9 = "9K"
    KEYCOOP = "CP"
    KEY1 = "1K"
    KEY3 = "3K"
    KEY2 = "2K"
    SCOREV2 = "V2"
    MIRROR = "MR"

    def __new__(cls, acronym):
        # a little bit jank but... it's fiiiiine.
        value = 1 << len(cls._member_names_)
        member = int.__new__(cls, value)
        member._value_ = value
        member.acronym = acronym
        return member

    @property
    def skin_name(self):
        if len(self) != 1:
            raise ValueError("expected single mod for skin element")

        return f"selection-mod-{self.name.lower()}"

    @property
    def speed(self):
        if self.DOUBLETIME in self:
            return 1.5

        elif self.HALFTIME in self:
            return 0.75

        return 1.0


async def api_get(version: int, endpoint: str, params: Optional[dict] = None):
    url = f"{API_URL}/v{version}/{endpoint}"
    content = {}

    async with ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                content = await response.json()

            return response.status, content


async def fetch_difficulty(map_id: int, mode: int, mods: Mods):
    url = f"https://osu.{DOMAIN}/difficulty-rating"
    difficulty = 0.0
    data_json = {
        "beatmap_id": map_id,
        "ruleset_id": mode % 4,
        "mods": [{"acronym": mod.acronym} for mod in mods]
    }

    async with ClientSession() as session:
        async with session.post(url, json=data_json) as response:
            if response.status == 200:
                return float(await response.text())

    return 0.0


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
