import os
import discord
import time
import sys
from pathlib import Path
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import aiohttp
# Add parent directory to path to allow importing from config
sys.path.append(str(Path(__file__).parent.parent))
from src.venice_api import VeniceAPI
from src.respond import post_response
from config.config import get_server_config, update_server_config, DISCORD_TOKEN, VENICE_API_KEY


async def scrape_venice_faq(url, cutoff_before_phrase="", cutoff_after_phrase=""):
    """
    Asynchronously scrape the Venice.ai FAQ page and return parsed HTML.
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"Error: Unable to fetch page (Status Code: {response.status})")
                return None

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text(separator="\n", strip=True)

            #cut out anything before the phrase match
            if cutoff_before_phrase != "":
                index = text.find(cutoff_before_phrase)
                if index != -1:
                    text = text[index:]

            #cut out anything after the phrase match
            if cutoff_after_phrase != "":
                index = text.find(cutoff_after_phrase)
                if index != -1:
                    text = text[:index + len(cutoff_after_phrase)]

            return text

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with a dynamic command prefix
def get_prefix(bot, message):
    if message.guild:
        # Get server-specific prefix
        config = get_server_config(message.guild.id)
        return config["command_prefix"]
    return "!"  # Default prefix for DMs


bot = commands.Bot(command_prefix=get_prefix, intents=intents)
venice_api = VeniceAPI(api_key=VENICE_API_KEY)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.command(name='ask')
async def ask(ctx, *, question):
    """Ask a question to Venice AI"""
    # Get server configuration
    server_config = get_server_config(ctx.guild.id)
    
    # Start timing the response
    start_time = time.time()
    
    # Get bot name and model from config
    bot_name = server_config["bot_name"]
    model = server_config["model"]
    
    await ctx.send(f"{bot_name}-{model} is thinking...")
    
    try:
        # Set the model from server config
        venice_api.model = model
        
        # Get context file if configured
        context_file = server_config["context_file"]
        if context_file:
            try:
                with open(context_file, 'r') as f:
                    context = f.read()
            except Exception as e:
                print(f"Error reading context file: {e}")

        faq_url = server_config["faq_url"]
        cutoff_before_phrase = server_config["faq_start_phrase"]
        cutoff_after_phrase = server_config["faq_end_phrase"]
        topic = server_config["discord_topic"]

        # Get live website faq
        additional_context = await scrape_venice_faq(faq_url, cutoff_before_phrase, cutoff_after_phrase)
        
        # Get answer from Venice AI
        answer = await venice_api.get_answer(question, topic, context_file=None, raw_context=additional_context)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Send the response based on answer style configuration
        if server_config["answer_style"] == "embedded":
            await post_response(ctx, question, answer, bot, server_config, response_time)
        else:  # plain text response
            await ctx.send(f"**Question:** {question}\n\n{answer['answer']}\n\n*Response time: {response_time:.2f}s*")
    except Exception as e:
        await ctx.send(f"Request failed.")
        print(e)


@bot.command(name='config')
async def config_command(ctx, setting=None, *, value=None):
    """View or modify server configuration"""
    # Check if user has permission to change settings
    if setting is not None and value is not None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You need administrator permissions to change config settings.")
            return
    
    # Get current server configuration
    server_config = get_server_config(ctx.guild.id)
    
    # If no arguments, show current config
    if setting is None:
        config_message = "**Server Configuration:**\n"
        for key, val in server_config.items():
            config_message += f"• **{key}**: `{val}`\n"
        await ctx.send(config_message)
        return
    
    # Check if setting exists
    if setting not in server_config:
        await ctx.send(f"Unknown setting: {setting}. Available settings: {', '.join(server_config.keys())}")
        return
    
    # If no value provided, show current setting
    if value is None:
        await ctx.send(f"**{setting}** is currently set to: `{server_config[setting]}`")
        return
    
    # Update the setting
    # Convert boolean strings to actual booleans
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.lower() == "none":
        value = None
        
    # Update the configuration
    update_server_config(ctx.guild.id, {setting: value})
    await ctx.send(f"Updated **{setting}** to: `{value}`")


def run():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
