import os
import discord
import time
import sys
from pathlib import Path
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import aiohttp
import re
import json

# Add parent directory to path to allow importing from config
sys.path.append(str(Path(__file__).parent.parent))
from src.venice_api import VeniceAPI
from src.respond import post_response
from src.price import get_price_data
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

            # Find and store the desired script content before removing scripts
            desired_script = soup.find("script", text=lambda t: t and "Frequently Asked Questions" in t)
            if desired_script:
                faq_content = desired_script.get_text()
                # Assume faq_content is the string you extracted
                # This regex finds the first JSON-like block (from the first '{' to the last '}')
                json_match = re.search(r'({.*})', faq_content, re.DOTALL)

                if json_match:
                    json_str = json_match.group(1)
                    cleaned_json_str = json_str.replace('\\"', '"')
                    return cleaned_json_str

            return None

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

@bot.command(name="nick")
async def set_nickname(ctx, new_name: str):
    """Manually change the bot's nickname"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator to change config nick.")
        return
    try:
        await ctx.guild.me.edit(nick=new_name)
        await ctx.send(f"Nickname changed to {new_name} ✅")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change my nickname ❌")
    except discord.HTTPException:
        await ctx.send("Failed to change nickname due to an API error ❌")


@bot.command(name='ask')
async def ask(ctx, *, question):
    """Ask a question to Venice AI"""
    # Get server configuration
    server_config = get_server_config(ctx.guild.id)
    
    # Start timing the response
    start_time = time.time()
    
    try:
        # Get bot name and model from config - validate types
        bot_name = server_config.get("bot_name", "VeniceAI")
        model = server_config.get("model")
        
        # Validate critical config values
        if not isinstance(bot_name, str):
            await ctx.send(f"Configuration error: bot_name must be a string, got {type(bot_name).__name__}")
            return
            
        if not isinstance(model, str):
            await ctx.send(f"Configuration error: model must be a string, got {type(model).__name__}")
            return
        
        await ctx.send(f"{bot_name}-{model} is thinking...")
        
        # Set the model from server config
        venice_api.model = model
        
        # Get context file if configured - validate type
        context_file = server_config.get("context_file")
        context = None
        if context_file:
            if not isinstance(context_file, str):
                await ctx.send(f"Configuration error: context_file must be a string path, got {type(context_file).__name__}")
                return
                
            try:
                with open(context_file, 'r') as f:
                    context = f.read()
            except Exception as e:
                await ctx.send(f"Error reading context file: {context_file}")
                print(f"Error reading context file: {e}")
                return

        # Get and validate other config values
        faq_url = server_config.get("faq_url", "")
        cutoff_before_phrase = server_config.get("faq_start_phrase", "")
        cutoff_after_phrase = server_config.get("faq_end_phrase", "")
        topic = server_config.get("discord_topic", "VeniceFAQ")
        
        # Type validation for string parameters
        for name, value in [
            ("faq_url", faq_url),
            ("faq_start_phrase", cutoff_before_phrase),
            ("faq_end_phrase", cutoff_after_phrase),
            ("discord_topic", topic)
        ]:
            if not isinstance(value, str):
                await ctx.send(f"Configuration error: {name} must be a string, got {type(value).__name__}")
                return

        # Get live website faq
        additional_context = await scrape_venice_faq(faq_url, cutoff_before_phrase, cutoff_after_phrase)
        
        # Get answer from Venice AI
        answer = await venice_api.get_answer(question, topic, context_file=None, raw_context=additional_context)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Send the response based on answer style configuration
        answer_style = server_config.get("answer_style", "embedded")
        if not isinstance(answer_style, str):
            answer_style = "embedded"  # Default if invalid
            
        if answer_style == "embedded":
            await post_response(ctx, question, answer, bot, server_config, response_time)
        else:  # plain text response
            await ctx.send(f"**Question:** {question}\n\n{answer['answer']}\n\n*Response time: {response_time:.2f}s*")
    except Exception as e:
        await ctx.send(f"Request failed. Check your server configuration.")
        print(f"Error processing request: {e}")


@bot.command(name='price')
async def price_command(ctx, *, question=None):
    """Get the current price and information about Venice token"""
    # Get server configuration
    server_config = get_server_config(ctx.guild.id)
    
    # Start timing the response
    start_time = time.time()
    
    try:
        # Get bot name and model from config
        bot_name = server_config.get("bot_name", "VeniceAI")
        model = server_config.get("model")
        
        # Validate critical config values
        if not isinstance(bot_name, str):
            await ctx.send(f"Configuration error: bot_name must be a string, got {type(bot_name).__name__}")
            return
            
        if not isinstance(model, str):
            await ctx.send(f"Configuration error: model must be a string, got {type(model).__name__}")
            return
        
        await ctx.send(f"{bot_name}-{model} is checking CoinGecko for data...")
        
        # Set the model from server config
        venice_api.model = model

        price_data = await get_price_data()
        if price_data is None:
            await ctx.send(f"{bot_name}-{model} CoinGecko call failed...")
            return

        dev_additional_prompt = """
            Give the user helpful information about the price, market data, or other VVV price related information 
            they are looking for. Keep the answer brief, but also pack some interesting details in that a cryptocurrency 
            'hodler' would find relevant. Answer the question correctly, but also try to highlight positives about VVV 
            (if possible, and don't make it too obvious, sounding like a 'shill'). 
            So far your instructions give you a 'conversational' response of about 3 out of 10 (all info, no conversing), 
            alter your response so that the score would be 4 out of 10, provide fact-rich concise answers (emoji's encouraged). 
            The provided data is live market data, don't add any disclaimer for data timing. 
            Don't highlight all time high price unless it is close to that price now.
        """

        # Use the provided question or default to a basic price question
        if question is None:
            question = "What is the current price of VVV?"

        topic = server_config.get("discord_topic", "VeniceFAQ")
        answer = await venice_api.get_answer(question, topic, context_file=None, raw_context=price_data, additional_dev_prompt=dev_additional_prompt)

        # Calculate response time
        response_time = time.time() - start_time

        # Send the response based on answer style configuration
        answer_style = server_config.get("answer_style", "embedded")
        if not isinstance(answer_style, str):
            answer_style = "embedded"  # Default if invalid

        if answer_style == "embedded":
            await post_response(ctx, question, answer, bot, server_config, response_time)
        else:  # plain text response
            await ctx.send(f"**Venice Token Price Info:**\n\n{answer['answer']}\n\n*Response time: {response_time:.2f}s*")
    except Exception as e:
        await ctx.send(f"Failed to fetch price information. Please try again later.")
        print(f"Error processing price request: {e}")

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
            # Handle empty string values specially to make them visible
            if val == "":
                display_val = "none"
            else:
                display_val = val
            config_message += f"• **{key}**: `{display_val}`\n"
        await ctx.send(config_message)
        return
    
    # Check if setting exists
    if setting not in server_config:
        await ctx.send(f"Unknown setting: {setting}. Available settings: {', '.join(server_config.keys())}")
        return
    
    # If no value provided, show current setting
    if value is None:
        display_val = server_config[setting]
        if display_val == "":
            display_val = "none"
        await ctx.send(f"**{setting}** is currently set to: `{display_val}`")
        return
    
    # Update the setting
    # Convert string values to appropriate types based on setting
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.lower() == "none":
        value = None
    
    # Handle numeric values (important for our intentionally invalid config)
    try:
        if value and value.isdigit():
            value = int(value)
    except (AttributeError, ValueError):
        pass
        
    # Update the configuration
    update_server_config(ctx.guild.id, {setting: value})
    await ctx.send(f"Updated **{setting}** to: `{value}`")


def run():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
