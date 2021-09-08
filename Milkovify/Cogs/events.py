import json
import re
from datetime import datetime, timedelta
import time

import discord
from discord.ext import commands

from Core.Utils.predicates import ReactionPredicate
from Core.Utils.menus import start_adding_reactions

log = logging.getLogger(__name__)

JOIN_THRESHOLD = 7

def is_hex(st):
    if st.lower() in 'abcdef' or st.isdigit():
        return st

def setup(client):
    client.add_cog(MessageParser(client))

def check_new_account(threshold: int, member: discord.Member):
    """
    I wrote this like 2 years ago, improvement probably required.
    """
    now = datetime.utcnow()
    time_string = None
    account_age = now - member.created_at
    if account_age < threshold:
        # 0 = Hours, 1 = Minutes, 2 = Seconds
        # Super duper hacky.
        #I hate this
        time_array = []
        hms = str(account_age).split(":")
        if hms[0]:
            time_array.append(hms[0] + " hours")
        if hms[1]:
            time_array.append(hms[1] + " minutes")
        time_string = ", ".join(time_array)

        emb = discord.Embed(title="**Account made:** {} Ago".format(time_string))
        emb.set_footer(text="ID: {}".format(member.id), icon_url='https://media.giphy.com/media/qjPD3Me0OCvFC/giphy.gif')
        return emb, True
    return None, False


class MessageParser(commands.Cog):
    """
    Unused as of now, will contain
    - Crosslink implementation for server
    - Belt acceptance detection.
    """

    def __init__(self, client):
        self.client = client
        self.belts = [
            787696270675542066,  # Red
            787696266401939497,  # Brown
            787696274514247700,  # Black
        ]
        self.custom_roles = json.load(
            open("roles.json")
        )  # dict of `member.id` : `role.id`
        self.bye = True
        self.greet = True
        self.log_channel = None 

    @commands.command(name="rolename", aliases=["rname"])
    async def rolename(self, ctx, *, name: str):
        if str(ctx.author.id) not in self.custom_roles:
            return
        custom_role = discord.utils.find(
            lambda r: r.id == int(self.custom_roles[str(ctx.author.id)]),
            ctx.message.guild.roles,
        )
        oldname = custom_role.name
        await custom_role.edit(name=name)
        await ctx.send(
            "Changed your role name from `{0}` to `{1}`".format(oldname, name)
        )
    @commands.command(name="rolecolor",aliases=['rolecolour','rcolor','rcolour'])
    async def rolecolor(self,ctx,*,color :str):
        # Should be black belt only
        if str(ctx.author.id) not in self.custom_roles:
            return
        blackbelt = discord.utils.find(
            lambda r: r.id == self.belts[2],
            ctx.message.guild.roles,
        )
        if blackbelt not in ctx.author.roles:
             await ctx.send('Get Your Black Belt first, nerd')
             return
        custom_role = discord.utils.find(
            lambda r: r.id == int(self.custom_roles[str(ctx.author.id)]),
            ctx.message.guild.roles,
        )
        color=color.replace('#','').strip()
        color=''.join(filter(lambda x: is_hex(x), color))
        print(color)
        try:
            d_color = discord.Colour(int(f"0x{color}", 16))
        except:
            return await ctx.send('Not even close to hex.')
        if d_color == custom_role.color:
            await ctx.send('Wait that\'s the same color')
            return
        try:
            old_color = custom_role.color
            await custom_role.edit(color=d_color)
            await ctx.send('Changed your colour from {0} to {1}'.format(old_color,d_color))
        except Exception as e:
            await ctx.send('Out of range: #000000 to #FFFFFF')

    @commands.command(name="roleinit", aliases=["rinit"])
    @commands.has_permissions(manage_roles=True, ban_members=True)
    async def roleinit(self, ctx, member: discord.Member):
        msg = await ctx.send(
            "Are you sure you want to initialise a custom role for {0}".format(
                member.name
            )
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            new_role = await ctx.guild.create_role(name="{0} Role".format(member.name))
            await member.add_roles(new_role)
            self.custom_roles[str(member.id)] = str(new_role.id)
            with open("roles.json", "w") as f:
                json.dump(self.custom_roles, f, ensure_ascii=False, indent=4)
            await ctx.send(
                "Done! {0} your custom role is ready! Use !rolename (!rname) to edit!".format(
                    member.mention
                )
            )
        else:
            await ctx.send("Eejit.")

    @commands.command(name="roledelete", aliases=["rdelete"])
    @commands.has_permissions(manage_roles=True, ban_members=True)
    async def roledelete(self, ctx, member: discord.Member):
        msg = await ctx.send(
            "Are you sure you want to delete {0}'s custom role?'".format(member.name)
        )
        start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)

        pred = ReactionPredicate.yes_or_no(msg, ctx.author)
        await ctx.bot.wait_for("reaction_add", check=pred)
        if pred.result is True:
            try:
                custom_role = discord.utils.find(
                    lambda r: r.id == int(self.custom_roles[str(member.id)]),
                    ctx.message.guild.roles,
                )
                del self.custom_roles[str(member.id)]
                with open("roles.json", "w") as f:
                    json.dump(self.custom_roles, f, ensure_ascii=False, indent=4)
                await custom_role.delete()
                await ctx.send("BANG! and the dirt is gone!")
            except Exception as e:
                await ctx.send(e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        return

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.greet:
            if self.log_channel is None:
                self.log_channel = discord.utils.find(
                    lambda c: c.id == 403340004786569217, # Yeah this is hardcoded.
                    self.client.get_all_channels())
            # Let's find if they're NEW
            # Now let's find their invite.
            emb, new_acc = check_new_account(
                timedelta(days=int(JOIN_THRESHOLD)), member)
        if new_acc:
            await self.log_channel.send("**<@!{}> has joined!**".format(member.id), embed=emb)
        elif self.greet:
            await self.log_channel.send("**<@!{}> has joined!** | `{}`".format(member.id,member.id))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        ### Could do with more detail?
        if self.bye:
            if self.log_channel is None:
                self.log_channel = discord.utils.find(
                    lambda c: c.id == 403340004786569217,
                    self.client.get_all_channels())
            await self.log_channel.send("**{} has left!**".format(member))
     
        
