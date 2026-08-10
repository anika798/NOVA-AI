"""
Automated Tests for NOVA Memory Subsystem
"""
import unittest
import json
import tempfile
import shutil
from pathlib import Path

from nova.core.config import ConfigManager
from nova.services.memory_service import MemoryService


class TestMemoryService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_dir = Path(self.temp_dir) / "memory"
        self.config_path = Path(self.temp_dir) / "settings.json"
        self.config_manager = ConfigManager(self.config_path)
        self.config_manager.load()
        self.memory_service = MemoryService(self.config_manager, memory_dir=self.memory_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_memory_initialization_and_default_schemas(self):
        success = self.memory_service.initialize()
        self.assertTrue(success)
        self.assertTrue(self.memory_service.is_healthy)

        # Check default files created
        self.assertIsNotNone(self.memory_service.get_memory("long_term.json"))
        self.assertIsNotNone(self.memory_service.get_memory("short_term.json"))
        self.assertIsNotNone(self.memory_service.get_memory("user_profile.json"))
        self.assertIsNotNone(self.memory_service.get_memory("system_state.json"))

    def test_memory_create_store_retrieve(self):
        self.memory_service.initialize()

        test_data = {"test_key": "test_value", "number": 42}
        saved = self.memory_service.save_memory("test_store.json", test_data)
        self.assertTrue(saved)

        retrieved = self.memory_service.get_memory("test_store.json")
        self.assertEqual(retrieved, test_data)

    def test_memory_listing(self):
        self.memory_service.initialize()
        self.memory_service.save_memory("extra_store.json", {"data": True})

        memories = self.memory_service.list_memories()
        self.assertIn("long_term.json", memories)
        self.assertIn("short_term.json", memories)
        self.assertIn("extra_store.json", memories)

    def test_memory_deletion(self):
        self.memory_service.initialize()
        self.memory_service.save_memory("temp_store.json", {"temp": True})

        # Verify present
        self.assertIsNotNone(self.memory_service.get_memory("temp_store.json"))

        # Delete
        deleted = self.memory_service.delete_memory("temp_store.json")
        self.assertTrue(deleted)

        # Verify removed
        self.assertIsNone(self.memory_service.get_memory("temp_store.json"))

    def test_memory_persistence(self):
        self.memory_service.initialize()
        test_payload = {"persistent_fact": "NOVA is running locally."}
        self.memory_service.save_memory("persistence_test.json", test_payload)

        # Re-instantiate MemoryService pointing to same directory
        new_memory_service = MemoryService(self.config_manager, memory_dir=self.memory_dir)
        new_memory_service.initialize()

        loaded_data = new_memory_service.get_memory("persistence_test.json")
        self.assertEqual(loaded_data, test_payload)

    def test_corrupt_memory_recovery(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Write corrupted JSON content
        corrupt_file = self.memory_dir / "user_profile.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CORRUPTED DATA ...")

        # Initialize MemoryService - should handle corrupted file safely
        success = self.memory_service.initialize()
        self.assertTrue(success)

        # Should have recovered with valid schema
        profile_data = self.memory_service.get_memory("user_profile.json")
        self.assertIsNotNone(profile_data)
        self.assertIn("user_name", profile_data)


if __name__ == "__main__":
    unittest.main()
