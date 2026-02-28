import discord
from discord.ext import commands
from datetime import timedelta
import json
import os
import asyncio
import time
from dotenv import load_dotenv
import subprocess
from discord.ext import tasks

OWNER_ID = 812400570680737853 

@tasks.loop(minutes=1)
async def check_battery():
    try:
        result = subprocess.check_output(["upower", "-i", "/org/freedesktop/UPower/devices/battery_display"], text=True)
        if "state:               discharging" in result:
            user = await bot.fetch_user(OWNER_ID)
            await user.send("⚠️ Hey there, looks like your computer is unplugged... I'm gonna die if you don't plug it back in soon")
    except Exception as e:
        print(f"Battery check failed: {e}")

@check_battery.before_loop
async def before_check_battery():
    await bot.wait_until_ready()

# --- 1. SETUP & STORAGE ---
load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)
bot.start_time = time.time()
DATA_FILE = "custom_commands.json"

def load_custom_commands():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_custom_commands(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

custom_commands = load_custom_commands()

# --- 2. EVENTS ---

@bot.event
async def on_ready():
    if not check_battery.is_running():
        check_battery.start()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, 
        name="Breaking Bad 🎩 wait that's a tophat"
    ))
    print(f'Logged in as {bot.user.name}')
    print('------')

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(1472996575532814571)
    if role: await member.add_roles(role)
    try:
        channel = await bot.fetch_channel(1450902662513168455)
        await channel.send(f"Welcome {member.mention} 👋 Glad to have you here! Introduce yourself here in this channel by stating your name and one this about you! You will not be able to chat in any other channels until you do. Welcome to Marketpro Lounge!")
    except: pass

@bot.event
async def on_message(message):
    if message.author.bot: return

    BAIT_CHANNEL_ID = 1475630628144808068
    JAIL_ROLE_ID = 1475967331879616532
    APPEAL_CHANNEL_ID = 1475967694971994112
    
    if message.channel.id == BAIT_CHANNEL_ID and message.author.id != OWNER_ID:
        try:
            jail_role = message.guild.get_role(JAIL_ROLE_ID)
            if jail_role:
                await message.author.add_roles(jail_role)
            await message.delete()

            try:
                await message.author.send(
                    f"⚠️ Hey there, this DM is to let you know you have been blacklisted in Marketpro Lounge. "
                    "You have been locked to the appeals channel. This is your chance to appeal before a punishment takes place."
                    "Reply to this DM or post in the #appeals channel. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
                )
            except: pass
        
            appeal_channel = bot.get_channel(APPEAL_CHANNEL_ID)
            if appeal_channel:
                await appeal_channel.send(
                    f"⚠️ {message.author.mention}, you have been blacklisted and have been locked to the appeals channel. This is your chance to appeal before a punishment takes place. "
                    "You can either appeal here or reply to the DM sent. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
                )
            return 
        except Exception as e:
            print(f"Jail failed: {e}")

    if isinstance(message.channel, discord.DMChannel):
        LOG_CHANNEL_ID = 1473490901614727343 
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="📩 New Appeal/DM", description=message.content, color=discord.Color.orange())
            embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
            await channel.send(embed=embed)
        return

    if message.content.startswith("."):
        trigger = message.content[1:].split(" ")[0].lower()
        if trigger in custom_commands:
            await message.channel.send(custom_commands[trigger])
            return
    await bot.process_commands(message)

# --- 3. COMMANDS ---

@bot.command()
@commands.has_role("MODERATOR")
async def dmasbot(ctx, member: discord.User, *, content: str):
    try:
        await member.send(f"{content}")
        await ctx.send(f"✅ Message sent to **{member}**.")
    except Exception as e:
        await ctx.send(f"❌ Failed to DM user: {e}")

@bot.command()
@commands.has_role("MODERATOR")
async def dmbymod(ctx, member: discord.User, *, content: str):
    try:
        await member.send(f"💬 **Message from Marketpro Mods:**\n{content}")
        await ctx.send(f"✅ Message sent to **{member}**.")
    except Exception as e:
        await ctx.send(f"❌ Failed to DM user: {e}")

@bot.command()
@commands.has_any_role("MODERATOR", "Jr. MODERATOR")
async def blacklist(ctx, member: discord.Member):
    j_role = ctx.guild.get_role(1475967331879616532)
    APPEAL_CHANNEL_ID = 1475967694971994112
    try:
        await member.add_roles(j_role)
        await ctx.send(f"✅ **{member.display_name}** has been locked to the appeals channel.")
        try:
            await member.send(
                f"⚠️ Hey there, this DM is to let you know you have been blacklisted in Marketpro Lounge. "
                "You have been locked to the appeals channel. This is your chance to appeal before a punishment takes place."
                "Reply to this DM or post in the #appeals channel. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
            )
        except: pass

        appeal_channel = bot.get_channel(APPEAL_CHANNEL_ID)
        if appeal_channel:
            await appeal_channel.send(
                f"⚠️ {member.mention}, you have been blacklisted and have been locked to the appeals channel. This is your chance to appeal before a punishment takes place. "
                "You can either appeal here or reply to the DM sent. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
            )
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def pull(ctx):
    if ctx.author.id != OWNER_ID: return
    try:
        subprocess.run(["git", "fetch"], check=True)
        stats = subprocess.check_output(["git", "diff", "HEAD", "origin/main", "--shortstat"], encoding="utf-8").strip()
    except: stats = "Error."
    with open("pull_signal.txt", "w") as f: f.write(stats)
    await ctx.send(f"📥 Pulling... `{stats}`")
    await asyncio.sleep(1)
    os.system("pkill -9 python3")

@bot.command()
@commands.has_any_role("MODERATOR", "Jr. Assistant", "Assistant", "Jr. MODERATOR")
async def verified(ctx, member: discord.Member):
    u_role, v_role = ctx.guild.get_role(1472996575532814571), ctx.guild.get_role(1472995242335801364)
    try:
        if u_role in member.roles: await member.remove_roles(u_role)
        await member.add_roles(v_role)
        await ctx.send(f"✅ **{member.display_name}** verified!")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason="No reason provided"):
    if not member: return
    try:
        await member.kick(reason=reason)
        await ctx.send(f"**{member.name}** has been kicked to Mars. Say hi to Elongated Muskrat for me")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason="No reason provided"):
    if not member: return
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.name}** has been `sudo rm -rf / --no-preserve-root`ed and was thrown into the void")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
async def ping(ctx): await ctx.send(f"im awake geez ({round(bot.latency * 1000)}ms)")

bot.run(os.getenv('DISCORD_TOKEN'))
