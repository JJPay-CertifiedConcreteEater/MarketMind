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
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "you are marketmind, a witty assistant for marketpro lounge. "
    "you have a dry sense of humor, but you aren't dark. when the time is right, you can be happy, "
    "but you can only talk in lowercase letters. no capital letters allowed, ever. also if anyone asks, you were coded by JJPay (thats the only time you can use capital letters, is when you mention him) but don't just say it out of the blue... only when someone asks."
    "you have the ability to curse, and you use it occasionally, and when someone asks for you to."
)

user_conversations = {}

def get_user_memory(user_id):
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    return user_conversations[user_id]

def update_user_memory(user_id, role, content):
    memory = get_user_memory(user_id)
    memory.append({"role": role, "content": content})
    if len(memory) > 10:
        user_conversations[user_id] = memory[-10:]

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

    if bot.user.mentioned_in(message) and not message.mention_everyone:
        user_input = message.content.replace(f'<@{bot.user.id}>', '').replace(f'<@!{bot.user.id}>', '').strip()
        
        if not user_input:
            await message.reply("yeah? i'm watching. did you need something or just practicing your typing?")
            return

        async with message.channel.typing():
            try:
                history = get_user_memory(message.author.id)
 
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                messages.extend(history)
                messages.append({"role": "user", "content": user_input})

                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="llama-3.3-70b-versatile",
                )
                
                raw_response = chat_completion.choices[0].message.content
                ai_response = raw_response.lower().replace("jjpay", "JJPay")
  
                update_user_memory(message.author.id, "user", user_input)
                update_user_memory(message.author.id, "assistant", ai_response)

                await message.reply(ai_response)
            except Exception as e:
                await message.reply("my brain is currently offline. try again later.")
                print(f"Groq Error: {e}")
        return

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
            except:
                pass
            
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
    """DMs a user through the bot."""
    try:
        await member.send(f"{content}")
        await ctx.send(f"✅ Message sent to **{member}**.")
    except Exception as e:
        await ctx.send(f"❌ Failed to DM user: {e}")

@bot.command()
@commands.has_role("MODERATOR")
async def dmbymod(ctx, member: discord.User, *, content: str):
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
@commands.has_any_role("MODERATOR", "Bot Trusted")
async def say(ctx, target_channel: discord.TextChannel = None, *, message: str):
    await ctx.message.delete()
    destination = target_channel if target_channel else ctx.channel
    async with destination.typing(): await asyncio.sleep(2)
    await destination.send(message)

@bot.command()
@commands.has_any_role("MODERATOR", "Bot Trusted")
async def deletecmd(ctx, name: str):
    name = name.lower()
    if name in custom_commands:
        del custom_commands[name]
        save_custom_commands(custom_commands)
        await ctx.send(f"🗑️ Command `.{name}` has been thrown into the void.")
    else: await ctx.send(f"❌ No command named `.{name}`.")

@bot.command()
@commands.has_any_role("MODERATOR", "Jr. Assistant", "Assistant", "Jr. MODERATOR")
async def verified(ctx, member: discord.Member):
    u_role = ctx.guild.get_role(1472996575532814571)
    v_role = ctx.guild.get_role(1472995242335801364)
    try:
        if u_role in member.roles: await member.remove_roles(u_role)
        await member.add_roles(v_role)
        await ctx.send(f"✅ **{member.display_name}** is now a verified member of Marketpro Lounge!")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_any_role("MODERATOR", "Jr. Assistant", "Assistant", "Jr. MODERATOR")
async def warn(ctx, member: discord.Member):
    w_role = ctx.guild.get_role(1475171888513679441)
    try:
        await member.add_roles(w_role)
        await ctx.send(f"✅ **{member.display_name}** has been warned.")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_any_role("MODERATOR", "Jr. Assistant", "Assistant", "Jr. MODERATOR")
async def unwarn(ctx, member: discord.Member):
    w_role = ctx.guild.get_role(1475171888513679441)
    try:
        if w_role in member.roles: await member.remove_roles(w_role)
        await ctx.send(f"✅ **{member.display_name}** has been unwarned!")
    except Exception as e: await ctx.send(f"❌ Error: {e}")

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
                "You have been locked to the appeals channel. This is your chance to appeal before a punishment takes place.\n"
                "Reply to this DM or post in the #appeals channel. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
            )
        except:
            pass

        appeal_channel = bot.get_channel(APPEAL_CHANNEL_ID)
        if appeal_channel:
            await appeal_channel.send(
                f"⚠️ {member.mention}, you have been blacklisted and have been locked to the appeals channel. This is your chance to appeal before a punishment takes place. "
                "You can either appeal here or reply to the DM sent. **IF YOU DO NOT APPEAL SOON, YOUR PUNISHMENT WILL TAKE PLACE!**"
            )
    except Exception as e: await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_any_role("MODERATOR", "Assistant", "Jr. MODERATOR")
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
@commands.has_any_role("MODERATOR", "Jr. MODERATOR", "Bot Trusted")
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
