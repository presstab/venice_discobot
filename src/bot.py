import os
import discord
import time
import sys
import json
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
data_augmenters = {}  # Dictionary to store guild-specific DataAugmenter instances


@tasks.loop(minutes=30)
async def refresh_data_timer():
    """Background task to refresh all guild-specific data augmenters every 30 minutes"""
    global data_augmenters
    if data_augmenters:
        print(f"[AUTO] Refreshing {len(data_augmenters)} DataAugmenter caches (30-minute interval)...")
        for guild_id, augmenter in list(data_augmenters.items()):  # Create a copy of items to avoid modification during iteration
            try:
                await augmenter.refresh()
                print(f"[AUTO] DataAugmenter cache refresh completed for guild {guild_id}")
            except Exception as e:
                print(f"[AUTO] Error in scheduled refresh for guild {guild_id}: {e}")


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # No need to initialize data_augmenters here
    # Each guild will get its own DataAugmenter instance when needed
    
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

        # Initialize or get guild-specific DataAugmenter
        global data_augmenters
        guild_id = ctx.guild.id
        
        # Create a new DataAugmenter for this guild if it doesn't exist
        if guild_id not in data_augmenters:
            scrape_list = server_config.get("scrape_list", [])
            data_augmenters[guild_id] = DataAugmenter(scrape_list, guild_id)
            print(f"Created new DataAugmenter for guild {guild_id}")
        
        # Get live website faq and docs using the guild-specific DataAugmenter
        additional_context = await data_augmenters[guild_id].get_data()
        
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
        
        await ctx.send(f"{bot_name}-{model} is browsing for the latest price data...")
        
        # Set the model from server config
        venice_api.model = model

        price_data = await get_price_data()
        if price_data is None:
            await ctx.send(f"{bot_name}-{model} API call failed...")
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

        # Initialize or get guild-specific DataAugmenter to incorporate custom context
        global data_augmenters
        guild_id = ctx.guild.id
        
        # Create a new DataAugmenter for this guild if it doesn't exist
        if guild_id not in data_augmenters:
            scrape_list = server_config.get("scrape_list", [])
            data_augmenters[guild_id] = DataAugmenter(scrape_list, guild_id)
            print(f"Created new DataAugmenter for guild {guild_id} in price command")
        
        # Get custom context for this guild
        try:
            custom_data = await data_augmenters[guild_id].get_data()
            # Combine price data with any custom context
            combined_context = f"{price_data}\n\n{custom_data}"
        except Exception as e:
            print(f"Error getting custom context for price command: {e}")
            combined_context = price_data

        topic = server_config.get("discord_topic", "VeniceFAQ")
        answer = await venice_api.get_answer(question, topic, context_file=None, raw_context=combined_context, additional_dev_prompt=dev_additional_prompt)

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
    # Check if user has permission for ALL config operations (viewing and changing)
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members):
        await ctx.send("You need moderator or administrator permissions to view or change config settings.")
        return
    
    # Additional check for making changes (require administrator)
    if setting is not None and value is not None and not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator permissions to change config settings. Moderators can only view settings.")
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
    
    # Reset guild's DataAugmenter if scrape_list is changed
    global data_augmenters
    guild_id = ctx.guild.id
    if setting == "scrape_list" and guild_id in data_augmenters:
        # Remove the guild's DataAugmenter to force recreation with new settings
        del data_augmenters[guild_id]
        print(f"Removed DataAugmenter for guild {guild_id} due to scrape_list change")
    
    await ctx.send(f"Updated **{setting}** to: `{value}`")


def get_custom_context(guild_id=None):
    """
    Helper function to load custom context data
    If guild_id is provided, returns context specific to that guild
    Otherwise returns all context data
    """
    custom_context_path = "config/custom_context.json"
    try:
        with open(custom_context_path, "r") as f:
            data = json.load(f)
        # Ensure the expected structure exists for guild-specific contexts
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, json.JSONDecodeError):
        # Create a new file with default structure if it doesn't exist or is invalid
        data = {}
    
    # Return specific guild data if requested
    if guild_id:
        guild_id_str = str(guild_id)  # Convert to string for JSON key
        if guild_id_str not in data:
            data[guild_id_str] = {"context_list": []}
        # Ensure context_list exists in guild data
        if "context_list" not in data[guild_id_str] or not isinstance(data[guild_id_str]["context_list"], list):
            data[guild_id_str]["context_list"] = []
        return data[guild_id_str]
    
    # Return all data if no guild specified
    return data


def save_custom_context(data, guild_id=None):
    """
    Helper function to save custom context data
    If guild_id is provided, saves only that guild's context
    Otherwise saves all context data
    """
    custom_context_path = "config/custom_context.json"
    
    # If saving for a specific guild
    if guild_id:
        # Load existing data first
        try:
            with open(custom_context_path, "r") as f:
                all_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_data = {}
        
        # Update only the specified guild's data
        guild_id_str = str(guild_id)
        all_data[guild_id_str] = data
        
        # Save back the complete data
        with open(custom_context_path, "w") as f:
            json.dump(all_data, f, indent=4)
    else:
        # Save all data
        with open(custom_context_path, "w") as f:
            json.dump(data, f, indent=4)


@bot.command(name='add')
async def add_context(ctx, *, message):
    """Add a custom context message to the bot's knowledge base for this guild"""
    # Check for moderator or administrator permissions
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members):
        await ctx.send("You need moderator or administrator permissions to add context messages.")
        return
    
    # Validate the message
    if not message or len(message) < 2:
        await ctx.send("Message is too short. Please provide a meaningful context message.")
        return
    
    # Limit message size to prevent abuse (2000 is Discord's own message limit)
    max_msg_length = 500  # Reasonable size for a context item
    if len(message) > max_msg_length:
        await ctx.send(f"Message is too long. Please keep it under {max_msg_length} characters.")
        return
    
    # Sanitize input - we won't strip all HTML, but we'll prevent the most common issues
    # This is a basic sanitization - more complex validation could be added
    message = message.replace("<", "&lt;").replace(">", "&gt;")
    
    try:
        # Read the current custom context file for this guild
        guild_data = get_custom_context(ctx.guild.id)
        
        # Check for duplicate entries
        if message in guild_data["context_list"]:
            await ctx.send("This message already exists in the context database.")
            return
        
        # Add the new message to context_list
        guild_data["context_list"].append(message)
        
        # Limit total number of items to prevent file size abuse
        max_items = 100
        if len(guild_data["context_list"]) > max_items:
            guild_data["context_list"] = guild_data["context_list"][-max_items:]  # Keep only the most recent items
        
        # Write back to the file with pretty formatting
        save_custom_context(guild_data, ctx.guild.id)
        
        # Refresh the guild's data augmenter to include the new context
        global data_augmenters
        guild_id = ctx.guild.id
        if guild_id in data_augmenters:
            await data_augmenters[guild_id].refresh()
        
        await ctx.send(f"Context message added successfully! Current context has {len(guild_data['context_list'])} items.")
    except Exception as e:
        await ctx.send(f"Error adding context message: {str(e)}")
        print(f"Error adding context message: {e}")


@bot.command(name='context')
async def list_context(ctx, delete_index: int = None):
    """List all custom context items or delete an item by index for this guild"""
    # Check for moderator or administrator permissions for ALL context operations
    if not (ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.moderate_members):
        await ctx.send("You need moderator or administrator permissions to view or manage context items.")
        return
    
    try:
        # Get guild-specific context data
        guild_data = get_custom_context(ctx.guild.id)
        context_list = guild_data["context_list"]
        
        # Handle delete operation if index is provided
        if delete_index is not None:
            # Convert to zero-based index
            delete_index = int(delete_index) - 1
            
            if delete_index < 0 or delete_index >= len(context_list):
                await ctx.send(f"Invalid index. Please use a number between 1 and {len(context_list)}.")
                return
            
            removed_item = context_list.pop(delete_index)
            save_custom_context(guild_data, ctx.guild.id)
            
            # Refresh the guild's data augmenter to exclude the deleted context
            global data_augmenters
            guild_id = ctx.guild.id
            if guild_id in data_augmenters:
                await data_augmenters[guild_id].refresh()
                
            await ctx.send(f"Removed context item: \"{removed_item}\"")
            return
        
        # List all items
        if not context_list:
            await ctx.send("No custom context items found for this server.")
            return
        
        # Format output with numbered list
        response = f"**Custom Context Items for {ctx.guild.name}:**\n"
        for i, item in enumerate(context_list, 1):
            # Truncate long items in the listing
            display_item = item
            if len(display_item) > 100:
                display_item = display_item[:97] + "..."
            response += f"{i}. {display_item}\n"
            
            # Send in multiple messages if too long for Discord's limit
            if len(response) > 1900:
                await ctx.send(response)
                response = ""
        
        if response:
            await ctx.send(response)
            
    except Exception as e:
        await ctx.send(f"Error processing context: {str(e)}")
        print(f"Error with context command: {e}")


@bot.command(name='refresh_data')
async def refresh_data(ctx):
    """Refresh the cached data from all sources"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("You need administrator permissions to refresh data.")
        return
    
    server_config = get_server_config(ctx.guild.id)
    scrape_list = server_config.get("scrape_list", [])
    
    # Initialize or get the guild-specific data augmenter
    global data_augmenters
    guild_id = ctx.guild.id
    
    # Create a new DataAugmenter for this guild if it doesn't exist
    if guild_id not in data_augmenters:
        data_augmenters[guild_id] = DataAugmenter(scrape_list, guild_id)
        print(f"Created new DataAugmenter for guild {guild_id}")
    
    await ctx.send("Refreshing data cache for this server... This might take a moment.")
    
    try:
        start_time = time.time()
        await data_augmenters[guild_id].refresh()
        elapsed_time = time.time() - start_time
        
        await ctx.send(f"Data cache for this server refreshed successfully! (Took {elapsed_time:.2f}s)")
    except Exception as e:
        await ctx.send(f"Error refreshing data: {str(e)}")
        print(f"Error refreshing data for guild {guild_id}: {e}")


def run():
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run()
