# Venice AI Discord Bot

A modular Discord bot that provides AI-powered answers using Venice.ai's API with configurable FAQ integration and response moderation.

## Features
- Venice AI API integration with configurable LLM models
- Dynamic server-specific configurations
- FAQ scraping & contextual responses
- Embedded/plain text response styles
- Built-in moderation interface
- Asynchronous web scraping

## 🚀 Setup Guide

### Prerequisites
- Python 3.9+
- Discord bot token
- Venice.ai API key
- Server ID for configuration

### Installation
```bash
# Clone repository
git clone https://github.com/presstab/venice_discobot.git
cd venice_discobot

# Install dependencies
pip3 install -r requirements.txt
```

### Configuration
1. Create `.env` file in `venice_discobot` directory:
```ini
DISCORD_TOKEN=your_discord_token
VENICE_API_KEY=your_venice_api_key
```

2. Default `config/server_config.json` structure:
```json
{
    "SERVER_ID": {
        "command_prefix": "!",
        "answer_style": "embedded",
        "model": "llama-3.3-70b",
        "bot_name": "VeniceAI",
        "discord_topic": "Venice AI",
        "context_file": "src/assets/faq_venice.json",
        "faq_url": "https://venice.ai/faqs",
        "faq_start_phrase": "How do I prevent my chat",
        "faq_end_phrase": "AI companies can’t and won’t."
    }
}
```
`SERVER_ID` is the Discord server ID

`context_file` is optional

`faq_url` is the url that will be searched before each user request

`faq_start_phrase` is a unique phrase that is the start of the faq section. Anything before this phrase will not be sent to the LLM.

`faq_end_phrase` is a unique phrase that is at the end of the faq section. Anything after this phrase will not be sent to the LLM.

`discord_topic` is what the LLM is told that it is an expert at

`bot_name` is the name that the bot should label itself in messages

### To setup for multiple servers: ###
```
{
  "ID_1": {
          "command_prefix": "!",
          "answer_style": "embedded",
          "model": "llama-3.3-70b",
          "bot_name": "VeniceAI",
          "discord_topic": "Venice AI",
          "context_file": "src/assets/faq_venice.json",
          "faq_url": "https://venice.ai/faqs",
          "faq_start_phrase": "How do I prevent my chat",
          "faq_end_phrase": "AI companies can’t and won’t."
      },
  "ID_2": {
          "command_prefix": "!",
          "answer_style": "embedded",
          "model": "llama-3.3-70b",
          "bot_name": "CoolCompanyBot",
          "discord_topic": "Cool Company",
          "context_file": "",
          "faq_url": "https://cool.co/faqs",
          "faq_start_phrase": "This is the first text in our faq",
          "faq_end_phrase": "this is the last sentence in our faq!"
      },
```
## 🏃 Running the Bot

From the `venice_discobot` directory:
```bash
# Start the bot
python3 src/bot.py
```

### Basic Commands
```bash
!ask <question>      # Get AI-powered response
!config view         # View server settings (moderator only)
!config set <key> <value>  # Modify configuration (moderator only)
```

### Testing
```bash
pytest tests/ -v
```

## 📝 Notes
- Store sensitive data in `.env` only
- Server configs auto-create on first run
- Embedded mode requires Discord bot permissions:
  - Send Messages
  - Embed Links
  - Manage Messages (for moderation)
```
