import discord
import asyncio
from discord.ext import commands
from utils.skypy import skypy
from utils.embed import Embed
from cogs.server_config import on_user_verified, on_user_unverified
from EZPaginator import Paginator


class Connections(commands.Cog):
    def __init__(self, bot):
        self.bot : commands.AutoShardedBot = bot
        self.connections = self.bot.users_db["connections"]
        skypy.enable_advanced_mode()

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.command(name="verify",
                      description="Verify that you own the Minecraft account and that you play on Hypixel.",
                      usage="([username])")
    async def verify_direct(self, ctx, username=None):
        await ctx.invoke(self.verify, username=username)

    @commands.command(name="usersetup",
                      description="Set up your account details and preferences",)
    async def setupdirect(self, ctx):
        await ctx.invoke(self.setup)

    @commands.group(name="account",
                    description="Set up personal settings.",
                    aliases=["acc"],
                    usage="[setup/link/unlink/profile/verify]",
                    invoke_without_command=True)
    async def account(self, ctx):
        await ctx.invoke(self.bot.get_command("help show_command"), arg="account")
    
    @account.command(name="verify", description="Verify that you own the Minecraft account and that you play on Hypixel.", usage="([username])")
    async def verify(self, ctx : commands.Context, username=None):
        user_db = await self.connections.find_one({"id" : ctx.author.id})
        if username is None and user_db is None:
            return await ctx.send(f"You have no account linked. Use `{ctx.prefix}acc verify [username]`")

        if user_db:
            player = await skypy.Player(keys=self.bot.api_keys, uuid=user_db["uuid"])
            name = str(ctx.author)
            if player.discord == name:
                if user_db["verified"] == False:
                    await self.connections.update_one(user_db, {"$set" : {"verified" : True}})
                    await ctx.send("Successfully verified!")
                    return await on_user_verified(ctx, self.bot, username)

                await ctx.send("You are already verified.")
                return await on_user_verified(ctx, self.bot, username)
            return await ctx.send(f"Your link between Hypixel and Discord is incorrect.\nHypixel: {player.discord}\nDiscord: {name}")

        if await self.link(ctx, username=username):
            await ctx.reinvoke()
                    break

        embed = Embed(title=str(user) + " <=> " + player.uname, bot=self.bot, user=ctx.author)
        await embed.set_requested_by_footer()
        scammer = bool(await self.bot.scammer_db["scammer_list"].find_one({"_id": user_db["uuid"]}))
        embed.add_field(name="General Information", value=f"Discord username: `{str(user)}`\nMc username: `{player.uname}`\nUUID: `{player.uuid}`\nLinked to Bot: `{linked}`", inline=False)
        embed.add_field(name="Advanced Information", value=f"\nScammer: `{scammer}`\nVerified: `{user_db['verified']}`", inline=False)
        return embed

    @account.command(name="info", description="Shows you all the information about your account.", usage="([username])", )
    async def info(self, ctx, user=None):
        try:
            converter = commands.UserConverter()
            user = await converter.convert(ctx, user)
        except commands.BadArgument:
            pass
        if user is None:
            user = ctx.author

        if isinstance(user, discord.abc.User):
            user_db = await self.connections.find_one({"id" : user.id})

            if user_db:
                embed = await self.get_info_embed(ctx, user, user_db)
                return await ctx.send(embed=embed)
            if user != ctx.author:
                return await ctx.send("This user is not linked to the bot.")
            return await ctx.send("You are not linked to the bot.")

        if isinstance(user, str):
            uname, uuid = await skypy.fetch_uuid_uname(user)
            dc_users = self.connections.find({"uuid" : uuid})
            dc_users = await dc_users.to_list(length=1000)

            if len(dc_users) > 0:
                embeds = []
                for dc_user in dc_users:
                    embed = await self.get_info_embed(ctx, self.bot.get_user(dc_user["id"]), dc_user)
                    embeds.append(embed)

                msg = await ctx.send(embed=embeds[0])
                if len(embeds) > 1:
                    paginator = Paginator(self.bot, msg, embeds=embeds, timeout=60, use_extend=True, only=ctx.author)
                    await paginator.start()
                return
            return await ctx.send(embed=await self.get_info_embed(ctx, None, {"uuid" : uuid, "verified" : False}, linked=False))


        raise commands.BadArgument(message="Discord User or Minecraft username")


def setup(bot):
    bot.add_cog(Connections(bot))
