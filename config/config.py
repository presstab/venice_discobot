import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default configuration for a single server - intentionally invalid
DEFAULT_CONFIG = {
    "command_prefix": "!",
    "bot_name": "VeniceAI",
    "discord_topic": "VeniceFAQ AI",
    "answer_style": "embedded",
    "model": None,  # Invalid: None instead of string
    "context_file": 404,  # Invalid: number instead of string path
    "faq_url": "",  # Invalid: empty URL
    "faq_start_phrase": False,  # Invalid: boolean instead of string
    "faq_end_phrase": {}  # Invalid: empty dict instead of string
}

# Discord configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
MODERATOR_ROLE_ID = os.getenv('MODERATOR_ROLE_ID')
if MODERATOR_ROLE_ID and MODERATOR_ROLE_ID.isdigit():
    MODERATOR_ROLE_ID = int(MODERATOR_ROLE_ID)
else:
    MODERATOR_ROLE_ID = None

# Venice API configuration
VENICE_API_KEY = os.getenv('VENICE_API_KEY')
VENICE_API_BASE_URL = os.getenv('VENICE_API_BASE_URL', 'https://api.venice.ai/api/v1')

# Server configurations
CONFIG_FILE_PATH = Path(__file__).parent / "server_config.json"


def load_server_configs():
    """Load server configurations from JSON file"""
    if not CONFIG_FILE_PATH.exists():
        # Create default config file if it doesn't exist
        with open(CONFIG_FILE_PATH, 'w') as config_file:
            json.dump({}, config_file, indent=4)
        return {}
    
    with open(CONFIG_FILE_PATH, 'r') as config_file:
        try:
            return json.load(config_file)
        except json.JSONDecodeError:
            print("Error: Invalid server_config.json file. Using empty configuration.")
            return {}


def save_server_configs(configs):
    """Save server configurations to JSON file"""
    with open(CONFIG_FILE_PATH, 'w') as config_file:
        json.dump(configs, indent=4, fp=config_file, sort_keys=True)


def get_server_config(server_id):
    """Get configuration for a specific server"""
    server_id = str(server_id)  # Convert to string to use as dict key
    configs = load_server_configs()
    
    # If this server doesn't have a config, return a copy of DEFAULT_CONFIG
    # but don't save it to the config file
    if server_id not in configs:
        # Just return a copy of the default config without saving it
        return DEFAULT_CONFIG.copy()
    
    return configs[server_id]

def update_server_config(server_id, config_updates):
    """Update configuration for a specific server"""
    server_id = str(server_id)  # Convert to string to use as dict key
    configs = load_server_configs()
    
    # Create entry with an empty dict if it doesn't exist
    # This ensures we only save explicitly set values, not the DEFAULT_CONFIG
    if server_id not in configs:
        configs[server_id] = {}
    
    # Update with new values
    configs[server_id].update(config_updates)
    save_server_configs(configs)
    
    # Return the updated config, filling in any missing values from DEFAULT_CONFIG
    result = DEFAULT_CONFIG.copy()
    result.update(configs[server_id])
    return result