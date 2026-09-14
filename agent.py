"""
Personal AI Assistant - Telegram Bot with Persistent Memory

This script implements a Telegram bot powered by Google's Gemini AI with LangGraph.
It uses SQLite for persistent conversation memory, maintaining context across restarts.

Features:
- Secure credential management via environment variables
- Persistent conversation history with SqliteSaver
- LangGraph ReAct agent with memory persistence
- Strict access control (only responds to authorized user)
- Async message handling with typing indicators
"""

import logging
import os
import sqlite3
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
import langchain.agents

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# ENVIRONMENT & CREDENTIALS SETUP
# ============================================================================

# Load environment variables from .env file
load_dotenv()

# Retrieve credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_TELEGRAM_USER_ID_STR = os.getenv("MY_TELEGRAM_USER_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validate that all required environment variables are present
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env file")
if not MY_TELEGRAM_USER_ID_STR:
    raise ValueError("Missing MY_TELEGRAM_USER_ID in .env file")
if not GOOGLE_API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

# Convert user ID to integer for comparison
try:
    MY_TELEGRAM_USER_ID = int(MY_TELEGRAM_USER_ID_STR)
except ValueError:
    raise ValueError(f"MY_TELEGRAM_USER_ID must be an integer, got: {MY_TELEGRAM_USER_ID_STR}")

logger.info("✅ All environment variables loaded successfully")

# ============================================================================
# PERSISTENT MEMORY SETUP
# ============================================================================

# Initialize SQLite connection for persistent memory storage
# check_same_thread=False allows the connection to be used across different threads
# This is necessary for async Telegram bot operations
try:
    sqlite_conn = sqlite3.connect("memory.db", check_same_thread=False)
    memory_saver = SqliteSaver(sqlite_conn)
    logger.info("✅ SQLite database connected: memory.db")
except Exception as e:
    raise RuntimeError(f"Failed to initialize SQLite database: {e}")

# ============================================================================
# LLM & AGENT SETUP
# ============================================================================

# Initialize the LLM with Google's Gemini Flash model
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", api_key=GOOGLE_API_KEY)

logger.info("✅ ChatGoogleGenerativeAI initialized with gemini-3.6-flash")

# System prompt that defines the agent's behavior and personality
SYSTEM_PROMPT = """You are a personal smart assistant designed to help the user with a wide range of tasks.
You are intelligent, helpful, and always aim to provide accurate and thoughtful responses.
You have access to various tools and can help with information retrieval, planning, analysis, and more.
Be conversational, friendly, and adapt your tone to the user's needs.

Important: Always maintain context from previous messages and build upon the conversation history."""

# Create the ReAct agent with persistent SqliteSaver checkpointer
# This ensures conversation history is saved to SQLite and restored on restart
agent_executor = langchain.agents.create_agent(
    model=llm,
    tools=[],  # Add tools here as needed (e.g., web search, calculator, etc.)
    checkpointer=memory_saver,  # Use SqliteSaver for persistent memory
    system_prompt=SYSTEM_PROMPT
)

logger.info("✅ LangGraph ReAct agent created with persistent memory")

# ============================================================================
# TELEGRAM BOT COMMAND HANDLERS
# ============================================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start command handler.
    
    Responds to /start command with a greeting message.
    Only responds if the sender is the authorized user.
    """
    # Security check: only respond to authorized user
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        logger.warning("Unauthorized access attempt from user: %s", update.effective_user.id)
        return

    greeting_text = "👋 Hello! I'm your personal smart assistant. How can I help you today?"
    await update.message.reply_text(greeting_text)
    logger.info("/start command received from authorized user: %s", update.effective_user.id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Help command handler.
    
    Displays available commands and usage instructions.
    Only responds if the sender is the authorized user.
    """
    # Security check: only respond to authorized user
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        logger.warning("Unauthorized access attempt from user: %s", update.effective_user.id)
        return

    help_text = """
📖 **Available Commands:**
/start - Start the assistant and see a greeting
/help - Show this help message
/reset - Clear conversation history

**How to use:**
Simply send any message and I'll respond as your personal smart assistant!
Your conversation history is automatically saved and persists across restarts.
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")
    logger.info("/help command received from authorized user: %s", update.effective_user.id)


async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reset command handler.
    
    Clears the conversation history for the current user.
    This deletes all stored messages from the SQLite database for this thread.
    Only responds if the sender is the authorized user.
    """
    # Security check: only respond to authorized user
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        logger.warning("Unauthorized access attempt from user: %s", update.effective_user.id)
        return

    user_id = str(update.effective_user.id)
    thread_id = f"chat_{user_id}"

    try:
        # Delete the conversation history from the database
        cursor = sqlite_conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        sqlite_conn.commit()

        await update.message.reply_text("🔄 Conversation history cleared. Starting fresh!")
        logger.info("Conversation reset for user: %s", user_id)
    except Exception as e:
        error_msg = f"Failed to reset conversation: {str(e)}"
        await update.message.reply_text(f"❌ {error_msg}")
        logger.error(error_msg)


TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def extract_text_content(content) -> str:
    """
    Extract plain text from a LangChain message content field.

    Newer Gemini models return content as a list of blocks
    (e.g. [{'type': 'text', 'text': '...', 'extras': {'signature': '...'}}])
    instead of a plain string. Only the 'text' fields are kept; the
    'extras' signature blobs are discarded since they can be huge and
    are not meant to be shown to the user.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


async def send_long_message(message, text: str) -> None:
    """Send text to Telegram, splitting it into multiple messages if it exceeds Telegram's length limit."""
    for i in range(0, len(text), TELEGRAM_MAX_MESSAGE_LENGTH):
        await message.reply_text(text[i:i + TELEGRAM_MAX_MESSAGE_LENGTH])


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message handler for user input.
    
    Processes incoming text messages and generates responses using the LangGraph agent.
    Maintains conversation context using persistent SQLite memory with unique thread IDs.
    
    Only responds if the sender is the authorized user.
    """
    # Security check: only respond to authorized user
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("❌ Access denied.")
        logger.warning("Unauthorized access attempt from user: %s", update.effective_user.id)
        return

    user_message = update.message.text
    user_id = str(update.effective_user.id)
    thread_id = f"chat_{user_id}"  # Persistent thread ID for conversation history

    logger.info("Message received from user %s: %s...", user_id, user_message[:50])
    
    # Show typing indicator to indicate the bot is processing
    await update.message.chat.send_action("typing")
    
    try:
        # Invoke the agent with the user message
        # The thread_id ensures conversation history is loaded from SQLite
        response = agent_executor.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        # Extract the final response from the agent
        # The response contains the entire conversation state
        if "messages" in response and response["messages"]:
            # Get the last message from the response
            last_message = response["messages"][-1]
            
            # Handle both content strings and message objects
            if isinstance(last_message, str):
                agent_response = last_message
            elif hasattr(last_message, "content"):
                agent_response = extract_text_content(last_message.content)
            else:
                agent_response = str(last_message)

            if not agent_response.strip():
                agent_response = "I couldn't generate a response. Please try again."

            # Send the response back to the user (split if it exceeds Telegram's limit)
            await send_long_message(update.message, agent_response)
            logger.info("Response sent to user %s: %s...", user_id, agent_response[:50])
        else:
            error_msg = "I couldn't generate a response. Please try again."
            await update.message.reply_text(error_msg)
            logger.warning("No response generated for user %s", user_id)

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(f"❌ {error_msg}")

# ============================================================================
# BOT INITIALIZATION & MAIN LOOP
# ============================================================================


def main() -> None:
    """
    Initialize and start the Telegram bot.
    
    Sets up all command and message handlers, then starts polling for updates.
    The bot will run continuously until interrupted.
    """
    logger.info("Initializing Telegram bot application...")
    
    # Create the Application with the bot token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reset", reset_conversation))
    
    # Register message handler for all text messages (excluding commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ All handlers registered")
    logger.info("🚀 Starting bot polling... (Press Ctrl+C to stop)")
    logger.info("Bot will only respond to user ID: %s", MY_TELEGRAM_USER_ID)
    
    # Start polling for updates
    # This is a blocking call that keeps the bot running
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        raise
    finally:
        # Clean up: close SQLite connection
        if sqlite_conn:
            sqlite_conn.close()
            logger.info("SQLite connection closed")
