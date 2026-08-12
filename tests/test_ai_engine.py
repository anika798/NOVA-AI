"""
Automated Tests for NOVA AI Engine Subsystem
"""
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import shutil

from nova.core.config import ConfigManager
from nova.ai.engine import AIEngineService
from nova.utils.constants import OllamaClientError


class TestAIEngineService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "settings.json"
        self.config_manager = ConfigManager(self.config_path)
        self.config_manager.load()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("nova.ai.engine.OllamaClient.check_connection")
    @patch("nova.ai.engine.OllamaClient.is_model_available")
    def test_ai_engine_initialization_success(self, mock_is_model, mock_check_conn):
        mock_check_conn.return_value = (True, "0.1.30")
        mock_is_model.return_value = True

        engine = AIEngineService(self.config_manager)
        success = engine.initialize()

        self.assertTrue(success)
        self.assertTrue(engine.is_healthy)
        self.assertEqual(engine.target_model, "qwen2.5:7b")

    @patch("nova.ai.engine.OllamaClient.check_connection")
    def test_ai_engine_initialization_failure(self, mock_check_conn):
        mock_check_conn.return_value = (False, None)

        engine = AIEngineService(self.config_manager)
        success = engine.initialize()

        self.assertFalse(success)
        self.assertFalse(engine.is_healthy)

    @patch("nova.ai.engine.OllamaClient.chat")
    @patch("nova.ai.engine.OllamaClient.check_connection")
    @patch("nova.ai.engine.OllamaClient.is_model_available")
    def test_chat_functionality(self, mock_is_model, mock_check_conn, mock_chat):
        mock_check_conn.return_value = (True, "0.1.30")
        mock_is_model.return_value = True
        mock_chat.return_value = {
            "message": {"role": "assistant", "content": "Hello! I am NOVA."},
            "done": True,
        }

        engine = AIEngineService(self.config_manager)
        engine.initialize()

        response = engine.chat("Hello NOVA")
        self.assertIsNotNone(response)
        self.assertIn("Hello! I am NOVA.", response.cleaned_content)
        mock_chat.assert_called_once()

    @patch("nova.ai.engine.OllamaClient.generate")
    @patch("nova.ai.engine.OllamaClient.check_connection")
    @patch("nova.ai.engine.OllamaClient.is_model_available")
    def test_generate_functionality(self, mock_is_model, mock_check_conn, mock_generate):
        mock_check_conn.return_value = (True, "0.1.30")
        mock_is_model.return_value = True
        mock_generate.return_value = {
            "response": "Generated test code snippet",
            "done": True,
        }

        engine = AIEngineService(self.config_manager)
        engine.initialize()

        response = engine.generate("Write a test function")
        self.assertIsNotNone(response)
        self.assertIn("Generated test code snippet", response.cleaned_content)
        mock_generate.assert_called_once()

    def test_empty_input_handling(self):
        engine = AIEngineService(self.config_manager)

        res_chat = engine.chat("")
        self.assertIn("Prompt cannot be empty", res_chat.cleaned_content)

        res_chat_spaces = engine.chat("   ")
        self.assertIn("Prompt cannot be empty", res_chat_spaces.cleaned_content)

        res_gen = engine.generate("")
        self.assertIn("Prompt cannot be empty", res_gen.cleaned_content)

    @patch("nova.ai.engine.OllamaClient.chat")
    def test_ollama_failure_graceful_handling(self, mock_chat):
        mock_chat.side_effect = OllamaClientError("Connection refused by Ollama daemon")

        engine = AIEngineService(self.config_manager)
        response = engine.chat("Test prompt during outage")

        self.assertIsNotNone(response)
        self.assertIn("Could not communicate with local Ollama server", response.cleaned_content)

    @patch("nova.ai.engine.OllamaClient.generate")
    @patch("nova.ai.engine.OllamaClient.check_connection")
    @patch("nova.ai.engine.OllamaClient.is_model_available")
    def test_warmup_functionality(self, mock_is_model, mock_check_conn, mock_generate):
        mock_check_conn.return_value = (True, "0.1.30")
        mock_is_model.return_value = True

        engine = AIEngineService(self.config_manager)
        engine.initialize()
        result = engine.warmup()

        self.assertTrue(result)
        mock_generate.assert_called_once()

    def test_set_model(self):
        engine = AIEngineService(self.config_manager)
        self.assertTrue(engine.set_model("qwen2.5:3b"))
        self.assertEqual(engine.target_model, "qwen2.5:3b")


if __name__ == "__main__":
    unittest.main()

