import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("stable", Path(__file__).with_name("justin-stable.py"))
stable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stable)


class StableTests(unittest.TestCase):
    def test_only_published_stable_releases_ordered_numerically(self):
        releases = [
            {"tag_name": tag, "draft": draft, "prerelease": prerelease}
            for tag, draft, prerelease in [
                ("v1.9.0", False, False),
                ("v1.10.0", False, False),
                ("v2.0.0", True, False),
                ("v3.0.0", False, True),
                ("v4.0.0-rc1", False, False),
                ("justin-abcdef", False, False),
            ]
        ]
        self.assertEqual(stable.select_release(releases), "v1.10.0")
        with self.assertRaises(ValueError):
            stable.select_release(releases[2:])

    def test_pagination_does_not_hide_a_newer_stable_release(self):
        def release(tag):
            return {"tag_name": tag, "draft": False, "prerelease": False}

        from io import BytesIO
        with patch.object(stable, "urlopen", side_effect=[
            BytesIO(json.dumps([release("v1.0.0")] * 100).encode()),
            BytesIO(json.dumps([release("v2.0.0")]).encode()),
        ]):
            self.assertEqual(stable.latest_stable(), "v2.0.0")

    def test_rollback_and_moved_tags_stop_before_merge(self):
        record = {"tag": "v2.0.0", "commit": "a" * 40}
        with patch.object(stable, "git") as git:
            for tag, commit in [("v1.0.0", "b" * 40), ("v2.0.0", "b" * 40)]:
                with self.assertRaises(ValueError):
                    stable.integrate(record, tag, commit)
            git.assert_not_called()

    def test_merge_conflict_leaves_the_record_unchanged(self):
        record = {"tag": "v1.0.0", "commit": "a" * 40}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stable.json"
            original = json.dumps(record)
            path.write_text(original)
            with patch.object(stable, "RECORD", path), patch.object(stable, "git", side_effect=[
                "", subprocess.CalledProcessError(1, ["git", "merge"]), "core/conflict.go",
            ]):
                with self.assertRaises(subprocess.CalledProcessError):
                    stable.integrate(record, "v2.0.0", "b" * 40)
            self.assertEqual(path.read_text(), original)

    def test_workflow_only_conflicts_keep_fork_ci_and_update_stable_record(self):
        record = {"tag": "v1.0.0", "commit": "a" * 40}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stable.json"
            path.write_text(json.dumps(record))
            with patch.object(stable, "RECORD", path), patch.object(stable, "git", side_effect=[
                "", subprocess.CalledProcessError(1, ["git", "merge"]),
                ".github/workflows/release.yml", "", "", "",
            ]) as git:
                stable.integrate(record, "v2.0.0", "b" * 40)
                git.assert_any_call("restore", "--source=HEAD", "--staged", "--worktree", "--", ".github")
            self.assertEqual(json.loads(path.read_text()), {"tag": "v2.0.0", "commit": "b" * 40})


if __name__ == "__main__":
    unittest.main()
