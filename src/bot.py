import os
import discord
import time
import sys
from pathlib import Path
from discord.ext import commands
from discord.ext import tasks
from dotenv import load_dotenv


# Add parent directory to path to allow importing from config
sys.path.append(str(Path(__file__).parent.parent))
from src.venice_api import VeniceAPI
from src.respond import post_response
from src.price import get_price_data
from src.data_feeds import DataAugmenter
from config.config import get_server_config, update_server_config, DISCORD_TOKEN, VENICE_API_KEY


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
data_augmenter = None  # Will be initialized when needed with server-specific settings


@tasks.loop(minutes=30)
async def refresh_data_timer():
    """Background task to refresh the data augmenter every 30 minutes"""
    global data_augmenter
    if data_augmenter is not None:
        try:
            print(f"[AUTO] Refreshing DataAugmenter cache (30-minute interval)...")
            await data_augmenter.refresh()
            print(f"[AUTO] DataAugmenter cache refresh completed")
        except Exception as e:
            print(f"[AUTO] Error in scheduled refresh: {e}")


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Initialize data_augmenter if not already initialized
    global data_augmenter
    if data_augmenter is None:
        # Get server config from the first guild the bot is in (fallback)
        if bot.guilds:
            server_config = get_server_config(bot.guilds[0].id)
            scrape_list = server_config.get("scrape_list", [])
            data_augmenter = DataAugmenter(scrape_list)
    
    # Start the automatic refresh timer
    refresh_data_timer.start()
    print(f"Started automatic data refresh timer (every 30 minutes)")

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
        topic = server_config.get("discord_topic", "VeniceFAQ")
        
        # Type validation for topic parameter
        if not isinstance(topic, str):
            await ctx.send(f"Configuration error: discord_topic must be a string, got {type(topic).__name__}")
            return

        # Initialize DataAugmenter with server-specific settings if needed
        global data_augmenter
        if data_augmenter is None:
            scrape_list = server_config.get("scrape_list", [])
            data_augmenter = DataAugmenter(scrape_list)
        
        # Get live website faq and docs using the DataAugmenter
        additional_context = await data_augmenter.get_data()
        
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
    
    # Reset data_augmenter to None to force reload with new settings on next use
    global data_augmenter
    if setting == "scrape_list":
        data_augmenter = None
    
    await ctx.send(f"Updated **{setting}** to: `{value}`")


@bot.command(name='refresh_data')
async def refresh_data(ctx):
    """Refresh the cached data from all sources"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator permissions to refresh data.")
        return
    
    server_config = get_server_config(ctx.guild.id)
    scrape_list = server_config.get("scrape_list", [])
    
    # Initialize or get the data augmenter
    global data_augmenter
    if data_augmenter is None:
        data_augmenter = DataAugmenter(scrape_list)
    
    await ctx.send("Refreshing data cache... This might take a moment.")
    
    try:
        start_time = time.time()
        await data_augmenter.refresh()
        elapsed_time = time.time() - start_time
        
        await ctx.send(f"Data cache refreshed successfully! (Took {elapsed_time:.2f}s)")
    except Exception as e:
        await ctx.send(f"Error refreshing data: {str(e)}")
        print(f"Error refreshing data: {e}")


def run():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
