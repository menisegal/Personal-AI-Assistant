import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Validate that all required credentials are present
if not all([TELEGRAM_BOT_TOKEN, MY_TELEGRAM_USER_ID, GOOGLE_API_KEY]):
    raise ValueError("Missing required environment variables. Please check your .env file.")

# Initialize the LLM with Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.7
)

# Create memory saver for conversation history
memory = MemorySaver()

# System prompt for the agent
SYSTEM_PROMPT = """You are a personal smart assistant designed to help the user with a wide range of tasks. 
You are intelligent, helpful, and always aim to provide accurate and thoughtful responses. 
You have access to various tools and can help with information retrieval, planning, analysis, and more.
Be conversational, friendly, and adapt your tone to the user's needs."""

# Create the ReAct agent with memory
agent_executor = create_react_agent(
    llm,
    tools=[],  # Add tools here as needed (e.g., web search, calculator, etc.)
    checkpointer=memory,
    state_modifier=SYSTEM_PROMPT
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("Access denied.")
        return
    
    await update.message.reply_text(
        "👋 Hello! I'm your personal smart assistant. How can I help you today?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("Access denied.")
        return
    
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    try:
        # Invoke the agent with the user message
        response = agent_executor.invoke(
            {"messages": user_message},
            config={"configurable": {"thread_id": user_id}}
        )
        
        # Extract the response
        agent_response = response.get("messages", [])
        if agent_response:
            # Get the last message from the agent
            last_message = agent_response[-1].content if hasattr(agent_response[-1], 'content') else str(agent_response[-1])
            await update.message.reply_text(last_message)
        else:
            await update.message.reply_text("I couldn't generate a response. Please try again.")
    
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text(f"An error occurred: {str(e)}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command handler."""
    if update.effective_user.id != MY_TELEGRAM_USER_ID:
        await update.message.reply_text("Access denied.")
        return
    
    help_text = """
Available commands:
/start - Start the assistant
/help - Show this help message

Just send me a message and I'll respond as your personal smart assistant!
"""
    await update.message.reply_text(help_text)


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()


if __name__ == "__main__":
    main()
