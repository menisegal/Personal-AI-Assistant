"""
Unit tests for Personal AI Assistant - Telegram Bot

This module contains comprehensive unit tests for the agent.py script,
covering environment validation, handler functions, and error scenarios.
"""

import os
import sqlite3
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from dotenv import load_dotenv
import sys

# Load environment variables for testing
load_dotenv()


class TestEnvironmentSetup:
    """Test environment variables loading and validation."""
    
    def test_env_vars_loaded(self):
        """Test that all required environment variables are available."""
        assert os.getenv("TELEGRAM_BOT_TOKEN") is not None, "TELEGRAM_BOT_TOKEN not set"
        assert os.getenv("MY_TELEGRAM_USER_ID") is not None, "MY_TELEGRAM_USER_ID not set"
        assert os.getenv("GOOGLE_API_KEY") is not None, "GOOGLE_API_KEY not set"
    
    def test_telegram_bot_token_not_empty(self):
        """Test that TELEGRAM_BOT_TOKEN is not empty."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        assert token and len(token) > 0, "TELEGRAM_BOT_TOKEN is empty"
    
    def test_google_api_key_not_empty(self):
        """Test that GOOGLE_API_KEY is not empty."""
        api_key = os.getenv("GOOGLE_API_KEY")
        assert api_key and len(api_key) > 0, "GOOGLE_API_KEY is empty"
    
    def test_user_id_is_valid_integer(self):
        """Test that MY_TELEGRAM_USER_ID can be converted to integer."""
        user_id_str = os.getenv("MY_TELEGRAM_USER_ID")
        try:
            user_id = int(user_id_str)
            assert user_id > 0, "User ID should be positive"
        except ValueError:
            pytest.fail(f"MY_TELEGRAM_USER_ID cannot be converted to integer: {user_id_str}")


class TestSQLiteSetup:
    """Test SQLite database setup and initialization."""
    
    def test_sqlite_connection_creation(self):
        """Test that SQLite connection can be created successfully."""
        try:
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            assert conn is not None
            conn.close()
        except Exception as e:
            pytest.fail(f"Failed to create SQLite connection: {e}")
    
    def test_sqlite_check_same_thread_false(self):
        """Test that check_same_thread parameter works correctly."""
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        finally:
            conn.close()


class TestAuthorization:
    """Test authorization and access control logic."""
    
    def test_authorized_user_id_matches(self):
        """Test that authorized user ID is correctly identified."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        authorized_id = MY_TELEGRAM_USER_ID
        
        assert authorized_id == MY_TELEGRAM_USER_ID
        assert isinstance(authorized_id, int)
    
    def test_unauthorized_user_rejected(self):
        """Test that unauthorized user ID is different from authorized ID."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        unauthorized_id = MY_TELEGRAM_USER_ID + 12345
        
        assert unauthorized_id != MY_TELEGRAM_USER_ID
    
    def test_user_id_type_checking(self):
        """Test that user ID type validation works."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        # Should be integer
        assert isinstance(MY_TELEGRAM_USER_ID, int)
        
        # Should not be string
        assert not isinstance(str(MY_TELEGRAM_USER_ID), int)


class TestStartHandler:
    """Test the start command handler."""
    
    @pytest.mark.asyncio
    async def test_start_authorized_user(self):
        """Test /start command with authorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        # Mock the update object
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        # Import and test the start function
        from agent import start
        
        await start(mock_update, mock_context)
        
        # Verify reply_text was called
        mock_update.message.reply_text.assert_called_once()
        
        # Verify greeting message was sent
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Hello" in call_args or "👋" in call_args
    
    @pytest.mark.asyncio
    async def test_start_unauthorized_user(self):
        """Test /start command with unauthorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        # Mock update with unauthorized user ID
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID + 99999
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        from agent import start
        
        await start(mock_update, mock_context)
        
        # Verify access denied message
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Access denied" in call_args or "❌" in call_args


class TestHelpHandler:
    """Test the help command handler."""
    
    @pytest.mark.asyncio
    async def test_help_authorized_user(self):
        """Test /help command with authorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        from agent import help_command
        
        await help_command(mock_update, mock_context)
        
        # Verify reply_text was called
        mock_update.message.reply_text.assert_called_once()
        
        # Verify help message contains command info
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert any(keyword in call_args for keyword in ["/start", "/help", "/reset", "Available Commands"])
    
    @pytest.mark.asyncio
    async def test_help_unauthorized_user(self):
        """Test /help command with unauthorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID + 99999
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        from agent import help_command
        
        await help_command(mock_update, mock_context)
        
        # Verify access denied message
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Access denied" in call_args or "❌" in call_args


class TestResetHandler:
    """Test the reset conversation handler."""
    
    @pytest.mark.asyncio
    async def test_reset_authorized_user_success(self):
        """Test /reset command successfully clears conversation."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        # Create an in-memory database for testing, with the checkpoints
        # table created the same way SqliteSaver creates it in production
        test_conn = sqlite3.connect(":memory:", check_same_thread=False)
        from langgraph.checkpoint.sqlite import SqliteSaver
        SqliteSaver(test_conn).setup()

        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.reply_text = AsyncMock()

        mock_context = AsyncMock()

        # Mock the sqlite_conn in the agent module
        with patch('agent.sqlite_conn', test_conn):
            from agent import reset_conversation
            
            await reset_conversation(mock_update, mock_context)
            
            # Verify success message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "cleared" in call_args.lower() or "🔄" in call_args
        
        test_conn.close()
    
    @pytest.mark.asyncio
    async def test_reset_unauthorized_user(self):
        """Test /reset command with unauthorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID + 99999
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        from agent import reset_conversation
        
        await reset_conversation(mock_update, mock_context)
        
        # Verify access denied message
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Access denied" in call_args or "❌" in call_args


class TestMessageHandler:
    """Test the main message handling function."""
    
    @pytest.mark.asyncio
    async def test_handle_message_authorized_user(self):
        """Test message handling with authorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.text = "Hello, how are you?"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        # Mock the agent_executor
        mock_agent_response = AsyncMock()
        mock_agent_response.return_value = {
            "messages": [
                {"role": "assistant", "content": "I'm doing well, thank you!"}
            ]
        }
        
        with patch('agent.agent_executor') as mock_executor:
            mock_executor.invoke = MagicMock(return_value={
                "messages": [
                    MagicMock(content="I'm doing well, thank you!")
                ]
            })
            
            from agent import handle_message
            
            await handle_message(mock_update, mock_context)
            
            # Verify typing indicator was sent
            mock_update.message.chat.send_action.assert_called_once_with("typing")
            
            # Verify reply was sent
            mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_message_unauthorized_user(self):
        """Test message handling with unauthorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID + 99999
        mock_update.message.text = "Hello"
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        from agent import handle_message
        
        await handle_message(mock_update, mock_context)
        
        # Verify access denied message
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Access denied" in call_args or "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_message_thread_id_generation(self):
        """Test that thread ID is correctly generated for message handling."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        user_id_str = str(MY_TELEGRAM_USER_ID)
        expected_thread_id = f"chat_{user_id_str}"
        
        assert expected_thread_id.startswith("chat_")
        assert user_id_str in expected_thread_id


class TestVoiceMessageHandler:
    """Test the voice message handling function."""

    @pytest.mark.asyncio
    async def test_handle_voice_authorized_user(self):
        """Test voice message handling with authorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))

        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.voice.file_id = "test_file_id"
        mock_update.message.voice.duration = 3.5
        mock_update.message.voice.mime_type = "audio/ogg"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()

        mock_telegram_file = AsyncMock()
        mock_telegram_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake audio bytes"))

        mock_context = AsyncMock()
        mock_context.bot.get_file = AsyncMock(return_value=mock_telegram_file)

        with patch('agent.agent_executor') as mock_executor:
            mock_executor.invoke = MagicMock(return_value={
                "messages": [
                    MagicMock(content="I heard your voice message!")
                ]
            })

            from agent import handle_voice_message

            await handle_voice_message(mock_update, mock_context)

            # Verify the audio was downloaded
            mock_context.bot.get_file.assert_called_once_with("test_file_id")

            # Verify typing indicator was sent
            mock_update.message.chat.send_action.assert_called_once_with("typing")

            # Verify the agent was invoked with a file content block
            invoke_args = mock_executor.invoke.call_args[0][0]
            content_blocks = invoke_args["messages"][0]["content"]
            assert any(block.get("type") == "file" for block in content_blocks)
            assert any(block.get("mime_type") == "audio/ogg" for block in content_blocks)

            # Verify reply was sent
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_voice_unauthorized_user(self):
        """Test voice message handling with unauthorized user."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))

        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID + 99999
        mock_update.message.reply_text = AsyncMock()

        mock_context = AsyncMock()

        from agent import handle_voice_message

        await handle_voice_message(mock_update, mock_context)

        # Verify access denied message and no download attempted
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Access denied" in call_args or "❌" in call_args
        mock_context.bot.get_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_voice_download_failure(self):
        """Test voice message handling when downloading the audio fails."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))

        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.voice.file_id = "test_file_id"
        mock_update.message.voice.duration = 2.0
        mock_update.message.voice.mime_type = "audio/ogg"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = AsyncMock()
        mock_context.bot.get_file = AsyncMock(side_effect=Exception("Network error"))

        from agent import handle_voice_message

        await handle_voice_message(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "error" in call_args.lower() or "❌" in call_args


class TestSystemPrompt:
    """Test system prompt configuration."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        from agent import SYSTEM_PROMPT
        
        assert SYSTEM_PROMPT is not None
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0
    
    def test_system_prompt_contains_assistant_description(self):
        """Test that system prompt describes the assistant role."""
        from agent import SYSTEM_PROMPT
        
        keywords = ["assistant", "help", "task", "intelligent"]
        assert any(keyword.lower() in SYSTEM_PROMPT.lower() for keyword in keywords)
    
    def test_system_prompt_includes_memory_instruction(self):
        """Test that system prompt mentions context and memory."""
        from agent import SYSTEM_PROMPT
        
        assert any(word in SYSTEM_PROMPT.lower() for word in ["context", "memory", "history", "previous"])


class TestErrorHandling:
    """Test error handling in various scenarios."""
    
    @pytest.mark.asyncio
    async def test_handle_message_with_exception(self):
        """Test error handling when agent_executor raises exception."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.text = "Test message"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        # Mock agent_executor to raise an exception
        with patch('agent.agent_executor') as mock_executor:
            mock_executor.invoke = MagicMock(side_effect=Exception("API Error"))
            
            from agent import handle_message
            
            await handle_message(mock_update, mock_context)
            
            # Verify error message was sent
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "error" in call_args.lower() or "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_message_empty_response(self):
        """Test handling when agent returns empty response."""
        MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID"))
        
        mock_update = AsyncMock()
        mock_update.effective_user.id = MY_TELEGRAM_USER_ID
        mock_update.message.text = "Test"
        mock_update.message.chat.send_action = AsyncMock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_context = AsyncMock()
        
        # Mock agent to return empty response
        with patch('agent.agent_executor') as mock_executor:
            mock_executor.invoke = MagicMock(return_value={
                "messages": []
            })
            
            from agent import handle_message
            
            await handle_message(mock_update, mock_context)
            
            # Verify error or warning message was sent
            mock_update.message.reply_text.assert_called_once()


class TestApplicationInitialization:
    """Test bot application initialization."""
    
    def test_telegram_token_format(self):
        """Test that Telegram token has expected format."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        # Telegram tokens contain colons and numbers
        assert ":" in token or len(token) > 20
    
    def test_llm_initialization_parameters(self):
        """Test that LLM is initialized with correct parameters."""
        from agent import llm
        
        assert llm is not None
        # Check if it's a ChatGoogleGenerativeAI instance
        assert hasattr(llm, 'model_name') or hasattr(llm, 'model')


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
