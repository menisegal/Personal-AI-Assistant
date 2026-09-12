# Personal AI Assistant

A personal Telegram bot powered by Google's Gemini AI, built with LangGraph for maintaining conversation history and context.

## Features

- 🤖 **Intelligent Assistant**: Powered by Gemini 1.5 Flash for fast and capable responses
- 💬 **Conversation Memory**: Maintains user session history with LangGraph
- 🔐 **Secure**: Credentials managed via environment variables, not hardcoded
- 🚀 **Lightweight**: Can run on Raspberry Pi or any Python-compatible machine

## Prerequisites

- Python 3.8+
- A Telegram Bot Token (get it from [BotFather](https://t.me/botfather))
- Your Telegram User ID (get it from [userinfobot](https://t.me/userinfobot))
- A Google API Key with Generative AI access

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/menisegal/Personal-AI-Assistant.git
cd Personal-AI-Assistant
```

### 2. Create and Activate Virtual Environment

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
MY_TELEGRAM_USER_ID=your_user_id_here
GOOGLE_API_KEY=your_google_api_key_here
```

### 5. Run the Bot

```bash
python agent.py
```

The bot will start polling for messages. When running, it will only respond to messages from the user ID specified in `MY_TELEGRAM_USER_ID`.

## Deployment on Raspberry Pi

The bot is lightweight and can run on a Raspberry Pi:

1. Install Python 3.8+ on your Raspberry Pi
2. Follow the setup steps above
3. (Optional) Use `systemd` or `screen` to keep the bot running in the background

Example with `screen`:

```bash
screen -S telegram-bot
python agent.py
# Press Ctrl+A then D to detach
```

## File Structure

```
Personal-AI-Assistant/
├── agent.py              # Main bot logic
├── requirements.txt      # Python dependencies
├── .env.example         # Template for environment variables
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Usage

Once the bot is running, send messages to it on Telegram:

- `/start` - Start the assistant
- `/help` - Show available commands
- Any message - Get a response from the AI assistant

## Security Notes

- Never commit the `.env` file to version control
- Keep your `GOOGLE_API_KEY` and `TELEGRAM_BOT_TOKEN` secret
- The bot only responds to the user ID specified in `MY_TELEGRAM_USER_ID`

## Troubleshooting

### Bot doesn't respond
- Verify `MY_TELEGRAM_USER_ID` matches your actual user ID
- Check that all environment variables are correctly set in `.env`
- Ensure the bot token is valid

### "Missing required environment variables" error
- Make sure `.env` file exists and contains all three required variables
- Check for typos in variable names

### API errors from Google
- Verify your `GOOGLE_API_KEY` has access to the Generative AI API
- Check your API quota and billing status

## License

MIT License

## Contributing

Feel free to submit issues and enhancement requests!
