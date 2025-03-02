import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = '!'
MODERATOR_ROLE_ID = os.getenv('MODERATOR_ROLE_ID')
if MODERATOR_ROLE_ID and MODERATOR_ROLE_ID.isdigit():
    MODERATOR_ROLE_ID = int(MODERATOR_ROLE_ID)
else:
    MODERATOR_ROLE_ID = None

# Venice API configuration
VENICE_API_KEY = os.getenv('VENICE_API_KEY')
VENICE_API_BASE_URL = os.getenv('VENICE_API_BASE_URL', 'https://api.venice.ai')