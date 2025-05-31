from enum import IntFlag
from typing import Optional

from aiohttp import ClientSession
from discord import Colour, Embed
from discord.ext.commands import MemberConverter
from discord.ext.commands.errors import MemberNotFound

from bot.constants import API_URL, DOMAIN, OLD_API_URL


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


async def old_api_get(version: int, endpoint: str, params: Optional[dict] = None):
    url = f"{OLD_API_URL}/v{version}/{endpoint}"
    content = {}

    async with ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                content = await response.json()

            return response.status, content


async def fetch_difficulty(map_id: int, mode: int, mods: Mods):
    url = f"https://osu.{DOMAIN}/difficulty-rating"
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


async def api_get(session, endpoint, params=None):
    """Send a GET request to an endpoint on the API."""
    return await session.get(f"{API_URL}/{endpoint}", params=params)


async def resolve_player_info(session, ctx, user=None):
    """Attempt to resolve player info from a command argument.

    Args:
      session:
        An open session with which to perform the request.
      ctx:
        The context of the command.
      user:
        An optional user to fetch player info about. If a string is
        provided and can be converted to a discord Member instance,
        then their display name is used for the player query. If this
        fails, the given user string will be used as-is. If no user is
        specified, the author of the command is used instead.

    Returns:
        A dict containing player data if successful, else None.
    """

    if user:
        try:  # attempt to match a discord member to use their name
            member = await MemberConverter().convert(ctx, user)
        except MemberNotFound:
            name = user
        else:  # if the conversion was successful:
            name = member.display_name
    else:
        name = ctx.author.display_name

    async with await api_get(session, f"/players/{name}") as response:
        player_info = await response.json()

    if response.status == 200:
        return player_info

    elif response.status == 404:
        if user:
            err_msg = "make sure you typed the username correctly!"
        else:
            err_msg = "your discord nickname doesn't match any players."
    else:
        err_msg = "something really broke. good luck!"

    err_title = f"could not get info for player *{name}*"
    await send_error(ctx, err_title, err_msg)
