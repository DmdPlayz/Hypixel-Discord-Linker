import discord
import aiohttp
from utils.util import is_staff
from discord.ext import commands, tasks
from utils.embed import Embed
from utils.skypy import skypy
from bson.objectid import ObjectId
from EZPaginator import Paginator
from time import time
from datetime import datetime, timedelta

class Misc(commands.Cog, name="Misc"):
    """Miscellaneous commands"""
    def __init__(self, bot):
        self.bot = bot 
        self.trelloEnabled = False
        if hasattr(self.bot, "trello_board"):
            self.my_board = self.bot.trello_board
            self.my_lists = self.my_board.list_lists()
            self.trelloEnabled = True
        self.stats.start()

    @commands.command(name="status", description="Checks the status of the bot.")
    async def status(self, ctx):
        statuses = {"stats_api" : [False, ""], "slothpixel" : [False, ""], "hypixel_api" : [False, ""], "database" : [False, ""]}

        db_status = await self.bot.db_client["admin"].command({"ping" : 1})
        if db_status["ok"] == 1:
            statuses["database"][0] = True

        try:
            await skypy.Player(keys=self.bot.api_keys, uuid="930aa39d62e0457fa0117c0d70e6ed43")
            statuses["hypixel_api"][0] = True
        except Exception as e:
            statuses["hypixel_api"][1] = e

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), raise_for_status=True) as s:
                async with s.get("https://api.slothpixel.me/api/health") as resp:
                    if resp.status == 200:
                        statuses["slothpixel"][0] = True
                    else:
                        statuses["slothpixel"][1] = resp.status
        except Exception as e:
            statuses["slothpixel"][1] = e

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), raise_for_status=True) as s:
                async with s.get(self.bot.stats_api + "/930aa39d62e0457fa0117c0d70e6ed43?key=" + self.bot.api_keys[0]) as resp:
                    if resp.status == 200 and (await resp.json())["success"]:
                        statuses["stats_api"][0] = True
                    else:
                        statuses["stats_api"][1] = f"{resp.status} + {await resp.json()}"
        except Exception as e:
            statuses["stats_api"][1] = e

        embed = Embed(title="Status", bot=self.bot, user=ctx.author)
        await embed.set_made_with_love_footer()
        embed.add_field(name="Uptime", value=f"{timedelta(seconds=round(time() - self.bot.start_time))}")
        embed.add_field(name="Bot Websocket Latency", value="\n".join([f"Shard ID: {shard[0]} Latency: {round(shard[1] * 1000)}ms" for shard in self.bot.latencies] + [(f"Average Latency: {round(self.bot.latency * 1000)}ms")]), inline=False)
        for name, status in statuses.items():
            if status[0] == True:
                embed.add_field(name=name.replace("_", " ").capitalize(), value="Working", inline=False)
                continue
            print(status[1])
            embed.add_field(name=name.replace("_", " ").capitalize(), value="Not working\nError: " + str(status[1]), inline=False)
        await ctx.send(embed=embed)    
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        config = self.bot.config
        logguild = self.bot.get_guild(config["support_guild"]["ID"])
        logchannel = logguild.get_channel(config["support_guild"]["log_channel"])
        #msg = await logchannel.fetch_message(config["support_guild"]["stats"]["message"])
        embed = discord.Embed(title="Guild add", description=f"NAME: {guild.name} \nID: {guild.id} \nMembers: {guild.member_count}", color=0x00FF00)
        await logchannel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        config = self.bot.config
        logguild = self.bot.get_guild(config["support_guild"]["ID"])
        logchannel = logguild.get_channel(config["support_guild"]["log_channel"])
        embed = discord.Embed(title="Guild remove", description=f"NAME: {guild.name} \nID: {guild.id} \nMembers: {guild.member_count}", color=0xff0000)
        await logchannel.send(embed=embed)
    
    
    @tasks.loop(minutes=5)
    async def stats(self):
        config = self.bot.config["support_guild"]
        guild = self.bot.get_guild(config["ID"])
        config = config["stats"]
        channel = guild.get_channel(config["channel"])
        message = await channel.fetch_message(config["message"])
        
        guilds = self.bot.guilds
        
        members = 0
        for guild in guilds:
            members += guild.member_count
                
        guild_members = []
        for guild in guilds:
            guild : discord.Guild
            guild_members.append(guild.member_count)
        guilds_sorted = sorted(guild_members, reverse=True)[:10]
        guilds_sorted_str = [str(place + 1) + ". " + str(guild) for place, guild in enumerate(guilds_sorted)]
        final_list = "\n".join(guilds_sorted_str)
        embed = Embed(title="Statistics", bot=self.bot, user=None)
        embed.add_field(name="Servers:", value=len(guilds), inline=False)
        embed.add_field(name="Members:", value=members, inline=False)
        embed.add_field(name="Top 10 Member count:", value=final_list, inline=False)
        await embed.set_made_with_love_footer()
        await message.edit(embed=embed)
    
    @stats.before_loop
    async def before_stats(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Misc(bot))
