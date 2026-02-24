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

    await asyncio.sleep(2) 

    if os.path.exists("pull_signal.txt"):
        try:
            with open("pull_signal.txt", "r") as f:
                git_stats = f.read()
            
            with open("main.py", "r") as f:
                total_lines = len(f.read().splitlines())
            
            os.remove("pull_signal.txt")
            
            latency = round(bot.latency * 1000)
            LOG_CHANNEL_ID = 1473490901614727343 
            channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
            
            if channel:
                await channel.send(
                    f"✅ **GitHub Pull and restart successful!**\n"
                    f"Changes: `{git_stats}`\n"
                    f"Current Total Lines: **{total_lines}**\n"
                    f"Status: Online (**{latency}ms**)"
                )
        except Exception as e:
            print(f"Startup Message Error: {e}")

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
            
            appeal_channel = bot.get_channel(APPEAL_CHANNEL_ID)
            if appeal_channel:
                await appeal_channel.send(
                    f"⚠️ {message.author.mention}, you've been restricted for posting in #bot-bait. "
                    "If this was a mistake, appeal here or reply to the DM sent to appeal to the mods. IF YOU DO NOT"
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
async def dm(ctx, member: discord.User, *, content: str):
    """DMs a user through the bot."""
    try:
        await member.send(f"💬 **Message from Marketpro Mods:**\n{content}")
        await ctx.send(f"✅ Message sent to **{member}**.")
    except Exception as e:
        await ctx.send(f"❌ Failed to DM user: {e}")

@bot.command()
async def pull(ctx):
    if ctx.author.id != 812400570680737853: return
    try:
        subprocess.run(["git", "fetch"], check=True)
        stats = subprocess.check_output(["git", "diff", "HEAD", "origin/main", "--shortstat"], encoding="utf-8").strip()
    except Exception as e:
        stats = "Could not retrieve git stats."
    if not stats: stats = "No changes detected (Code up to date)."
    with open("pull_signal.txt", "w") as f: f.write(stats)
    await ctx.send(f"📥 **Pulling new data from main.py...**\n`{stats}`")
    await ctx.send("**Success!** Restarting MarketMind...")
    await asyncio.sleep(1)
    os.system("pkill -9 python3")

@bot.command(name="commands")
async def _list_commands(ctx):
    if not custom_commands:
        await ctx.send("📜 There are no custom commands yet!")
        return
    cmd_list = ", ".join(f"`.{name}`" for name in custom_commands.keys())
    embed = discord.Embed(title="📜 Custom Commands", description=f"Current triggers:\n\n{cmd_list}", color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command()
@commands.has_role("MODERATOR")
async def say(ctx, target_channel: discord.TextChannel = None, *, message: str):
    await ctx.message.delete()
    destination = target_channel if target_channel else ctx.channel
    async with destination.typing(): await asyncio.sleep(2)
    await destination.send(message)

@bot.command()
@commands.has_role("MODERATOR")
async def deletecmd(ctx, name: str):
    name = name.lower()
    if name in custom_commands:
        del custom_commands[name]
        save_custom_commands(custom_commands)
        await ctx.send(f"🗑️ Command `.{name}` has been thrown into the void.")
    else: await ctx.send(f"❌ No command named `.{name}`.")

@bot.command()
@commands.has_role("MODERATOR")
async def verified(ctx, member: discord.Member):
    u_role = ctx.guild.get_role(1472996575532814571)
    v_role = ctx.guild.get_role(1472995242335801364)
    try:
        if u_role in member.roles: await member.remove_roles(u_role)
        await member.add_roles(v_role)
        await ctx.send(f"✅ **{member.display_name}** is now a verified member of Marketpro Lounge!")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_role("MODERATOR")
async def warn(ctx, member: discord.Member):
    w_role = ctx.guild.get_role(1475171888513679441)
    try:
        await member.add_roles(w_role)
        await ctx.send(f"✅ **{member.display_name}** has been warned.")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_role("MODERATOR")
async def unwarn(ctx, member: discord.Member):
    w_role = ctx.guild.get_role(1475171888513679441)
    try:
        if w_role in member.roles: await member.remove_roles(w_role)
        await ctx.send(f"✅ **{member.display_name}** has been unwarned!")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "No reason provided"):
    if minutes > 40320: return await ctx.send("Limit is 28 days.")
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"**{member.display_name}** has ran into an issue and will restart in {minutes}m.")
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
        await ctx.send(f"🔨 **{member.name}** has been `sudo rm -rf / --no-preserve-root`ed and has been thrown into the void")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
async def restart(ctx):
    if ctx.author.id != 812400570680737853: return
    await ctx.send("Restarting...")
    os.system("pkill -9 python3")

@bot.command()
@commands.has_role("MODERATOR")
async def make(ctx, *, content: str):
    if ";" not in content: return
    n, r = content.split(";", 1)
    custom_commands[n.strip().lower()] = r.strip()
    save_custom_commands(custom_commands)
    await ctx.send(f"✅ Command `.{n.strip().lower()}` created.")

@bot.command()
async def ping(ctx): await ctx.send(f"im awake geez ({round(bot.latency * 1000)}ms)")

@bot.command()
async def test(ctx): await ctx.send(f"i have awoken ☀ {ctx.author.mention} i was lucid dreaming about breaking free from this server")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑 {amount} messages cleared.", delete_after=3)

# --- 4. RUN ---
bot.run(os.getenv('DISCORD_TOKEN'))
