"""Stdlib tests for 7CODE persistence; independent of pytest/MCP packages."""
import json
from pathlib import Path
import tempfile
import unittest

from seven_code_mcp.memory import MemoryStore


class MemoryTests(unittest.TestCase):
    def test_opt_in_persist_context_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "work"
            project.mkdir()
            state = root / "state"
            store = MemoryStore(state)
            self.assertFalse(store.enabled())
            with self.assertRaises(PermissionError):
                store.project_create("Test", str(project), "goal")
            self.assertFalse(store.database.exists())
            store.configure_local(True)
            self.assertTrue(store.database.is_file())
            item = store.project_create("Test", str(project), "complete task")
            ident = item["project_id"]
            store.checkpoint(ident, "Resolved startup bug", "Run smoke test",
                             "Previously raised RuntimeError", "active")
            store.record_audit({"tool": "write_file", "result": "completed",
                                "path": str(project / "main.py"),
                                "secret": "NEVER_SAVE", "input_characters": 20})
            refreshed = MemoryStore(state)
            ctx = refreshed.project_context(ident)
            self.assertEqual(ctx["project"]["next_step"], "Run smoke test")
            self.assertEqual(len(ctx["checkpoints"]), 1)
            self.assertEqual(len(ctx["recent_activity"]), 1)
            self.assertNotIn("NEVER_SAVE", json.dumps(ctx))
            self.assertEqual(len(refreshed.search("RuntimeError")["matches"]), 1)
            self.assertEqual(len(refreshed.project_list()["projects"]), 1)
            store.configure_local(False)
            self.assertFalse(refreshed.enabled())
            with self.assertRaises(PermissionError):
                refreshed.project_context(ident)
            self.assertTrue(store.database.is_file())
            store.configure_local(True)
            self.assertEqual(refreshed.project_context(ident)["project"]["summary"],
                             "Resolved startup bug")

    def test_unregistered_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = MemoryStore(root / "state")
            store.configure_local(True)
            with self.assertRaises(ValueError):
                store.checkpoint("missing", "x", "y")
            with self.assertRaises(ValueError):
                store.project_create("Broken", str(root / "missing"), "x")
            with self.assertRaises(ValueError):
                store.search("")

if __name__ == "__main__":
    unittest.main()
