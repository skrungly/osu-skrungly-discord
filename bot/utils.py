from enum import IntFlag

from discord.ext.commands import BadArgument, MemberConverter, MemberNotFound

from bot.constants import API_URL, DOMAIN, OLD_API_URL


class Mods(IntFlag):
    """represent and work with combinations of mods."""

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
    def speed(self):
        """return the speed modifier for a set of mods."""
        if self.DOUBLETIME in self:
            return 1.5

        if self.HALFTIME in self:
            return 0.75

        return 1.0


async def old_api_get(session, version, endpoint, params=None):
    """make a request to the game server's own API endpoints.

    this function will be removed soon. new code should use `api_get`.
    """
    url = f"{OLD_API_URL}/v{version}/{endpoint}"
    content = {}

    async with session.get(url, params=params) as response:
        if response.status == 200:
            content = await response.json()

        return response.status, content


async def fetch_difficulty(session, map_id, mode, mods):
    """fetch the difficulty of a map for a given mode and mods."""

    url = f"https://osu.{DOMAIN}/difficulty-rating"
    data_json = {
        "beatmap_id": map_id,
        "ruleset_id": mode % 4,
        "mods": [{"acronym": mod.acronym} for mod in mods]
    }

    async with session.post(url, json=data_json) as response:
        if response.status == 200:
            return float(await response.text())

    return 0.0


async def api_get(session, endpoint, params=None):
    """send a GET request to an endpoint on the API."""
    return await session.get(f"{API_URL}/{endpoint}", params=params)


async def resolve_player_info(session, ctx, user=None):
    """attempt to resolve player info from a command argument.

    args:
      session: an open aiohttp session with which to send the request.
      ctx: the context of the command.
      user: an optional user to fetch player info for. if a string is
        provided and can be converted to a discord Member instance,
        then their display name is used for the player query. if this
        fails, the given user string will be used as-is. if no user is
        specified, the author of the command is used instead.

    returns:
        a dict containing player data.

    raises:
        BadArgument: if the API returns a 404 for the requested user.
        RuntimeError: if the API returns any other non-200 response.
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

    err_msg = f"could not fetch info for player '{name}'!"
    if response.status == 404:
        if user:
            err_msg += " make sure you typed the name correctly."
        else:
            err_msg += " your discord nickname doesn't match any players."

        raise BadArgument(err_msg)

    err_msg += f" api returned status {response.status}. good luck! :D"
    raise RuntimeError(err_msg)
