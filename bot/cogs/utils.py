from discord.ext import commands


class Utilities(commands.Cog):
    """just a bunch of helpful commands!"""

    def __init__(self, chatot):
        self.chatot = chatot

    @commands.command()
    async def online(self, ctx):
        """display info about current server status."""
        ...  # your code goes here!


async def setup(chatot):
    await chatot.add_cog(Utilities(chatot))
