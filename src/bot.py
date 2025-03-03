import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from venice_api import VeniceAPI
from moderation import post_response

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
venice_api = VeniceAPI(api_key=os.getenv('VENICE_API_KEY'))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='ask')
async def ask(ctx, *, question):
    """Ask a question to Venice AI"""
    await ctx.send(f"VeniceAI-{venice_api.model} is thinking...")
    
    try:
        # Get answer from Venice AI
        answer = await venice_api.get_answer(question)
        
        # Send the response for moderation
        await post_response(ctx, question, answer, bot, venice_api.model)
    except Exception as e:
        await ctx.send(f"Sorry, I encountered an error: {str(e)}")

def run():
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    run()