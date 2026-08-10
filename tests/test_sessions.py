"""
Automated Tests for NOVA Multi-Session Subsystem
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.ai.session_manager import SessionManager


class TestSessionManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sessions_dir = Path(self.temp_dir) / "sessions"
        self.session_manager = SessionManager(sessions_dir=self.sessions_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_session_creation(self):
        sid = self.session_manager.create_session("Python Project", session_id="python_proj")
        self.assertEqual(sid, "python_proj")
        self.assertEqual(self.session_manager.active_session_id, "python_proj")
        self.assertEqual(self.session_manager.active_session_name, "Python Project")

    def test_session_switching(self):
        sid1 = self.session_manager.create_session("Session One", session_id="sess_1")
        sid2 = self.session_manager.create_session("Session Two", session_id="sess_2")

        self.assertEqual(self.session_manager.active_session_id, sid2)

        switched = self.session_manager.switch_session(sid1)
        self.assertTrue(switched)
        self.assertEqual(self.session_manager.active_session_id, sid1)

    def test_session_saving_and_loading(self):
        sid = self.session_manager.create_session("Persistence Test", session_id="persist_sess")
        conv = self.session_manager.get_active_conversation()
        conv.add_user_message("Hello from user")
        conv.add_assistant_message("Hello from NOVA")

        saved = self.session_manager.save_session(sid)
        self.assertTrue(saved)
        self.assertTrue((self.sessions_dir / f"{sid}.json").exists())

        # Create new SessionManager to test disk restoration
        new_sm = SessionManager(sessions_dir=self.sessions_dir)
        loaded = new_sm.load_session(sid)
        self.assertTrue(loaded)

        loaded_conv = new_sm.get_active_conversation()
        new_sm.switch_session(sid)
        history = new_sm.get_active_conversation().get_history()

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Hello from user")
        self.assertEqual(history[1]["content"], "Hello from NOVA")

    def test_multiple_sessions_independence(self):
        sid1 = self.session_manager.create_session("Session A", session_id="sess_a")
        conv_a = self.session_manager.get_active_conversation()
        conv_a.add_user_message("Message in A")

        sid2 = self.session_manager.create_session("Session B", session_id="sess_b")
        conv_b = self.session_manager.get_active_conversation()
        conv_b.add_user_message("Message in B")

        # Verify A history
        self.session_manager.switch_session(sid1)
        hist_a = self.session_manager.get_active_conversation().get_history()
        self.assertEqual(len(hist_a), 1)
        self.assertEqual(hist_a[0]["content"], "Message in A")

        # Verify B history
        self.session_manager.switch_session(sid2)
        hist_b = self.session_manager.get_active_conversation().get_history()
        self.assertEqual(len(hist_b), 1)
        self.assertEqual(hist_b[0]["content"], "Message in B")


if __name__ == "__main__":
    unittest.main()
