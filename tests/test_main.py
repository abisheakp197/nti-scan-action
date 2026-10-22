import os
import unittest
from unittest.mock import patch, MagicMock
from src.main import (
    generate_badge_markdown,
    update_readme,
    run_scanner,
    commit_and_push_badge,
    main
)

class TestNTIScanAction(unittest.TestCase):
    def test_generate_badge_markdown(self):
        badge = generate_badge_markdown(85)
        expected = "[![NTI Verified](https://img.shields.io/badge/NTI_Score-85%2F100-brightgreen)](https://nti-registry.vercel.app)"
        self.assertEqual(badge, expected)

    def test_update_readme_new_file(self):
        tmp_readme = "test_README_new.md"
        if os.path.exists(tmp_readme):
            os.remove(tmp_readme)
        try:
            badge = generate_badge_markdown(90)
            update_readme(badge, readme_path=tmp_readme)
            with open(tmp_readme, "r") as f:
                content = f.read()
            self.assertEqual(content, badge + "\n")
        finally:
            if os.path.exists(tmp_readme):
                os.remove(tmp_readme)

    def test_update_readme_prepend(self):
        tmp_readme = "test_README_prepend.md"
        with open(tmp_readme, "w") as f:
            f.write("# My Repo\nThis is a test.")
        try:
            badge = generate_badge_markdown(95)
            update_readme(badge, readme_path=tmp_readme)
            with open(tmp_readme, "r") as f:
                content = f.read()
            self.assertTrue(content.startswith(badge + "\n\n# My Repo"))
        finally:
            if os.path.exists(tmp_readme):
                os.remove(tmp_readme)

    def test_update_readme_replace_existing(self):
        tmp_readme = "test_README_replace.md"
        old_badge = generate_badge_markdown(70)
        with open(tmp_readme, "w") as f:
            f.write(old_badge + "\n\n# My Repo")
        try:
            new_badge = generate_badge_markdown(100)
            update_readme(new_badge, readme_path=tmp_readme)
            with open(tmp_readme, "r") as f:
                content = f.read()
            self.assertIn("100%2F100", content)
            self.assertNotIn("70%2F100", content)
        finally:
            if os.path.exists(tmp_readme):
                os.remove(tmp_readme)

    @patch("src.main.run_cmd")
    def test_run_scanner_success(self, mock_run_cmd):
        mock_res = MagicMock()
        mock_res.stdout = "NTI-1 Score: 88/100 (Grade A)"
        mock_res.stderr = ""
        mock_run_cmd.return_value = mock_res

        score = run_scanner()
        self.assertEqual(score, 88)

    @patch("src.main.run_cmd")
    def test_run_scanner_failure_fallback(self, mock_run_cmd):
        mock_run_cmd.side_effect = Exception("Scanner failed")
        score = run_scanner()
        self.assertEqual(score, 0)

    @patch("src.main.run_cmd")
    def test_commit_and_push_badge(self, mock_run_cmd):
        mock_diff = MagicMock()
        mock_diff.returncode = 1
        mock_run_cmd.side_effect = [
            MagicMock(), # git config user.name
            MagicMock(), # git config user.email
            MagicMock(), # git add
            mock_diff,   # git diff --staged
            MagicMock(), # git commit
            MagicMock()  # git push
        ]
        commit_and_push_badge("fake-token", readme_path="README.md")
        self.assertEqual(mock_run_cmd.call_count, 6)

    @patch("src.main.commit_and_push_badge")
    @patch("src.main.update_readme")
    @patch("src.main.run_scanner")
    @patch("src.main.install_scanner")
    def test_main_fail_on_vulnerability(self, mock_install, mock_scan, mock_update, mock_commit):
        mock_scan.return_value = 50
        with patch.dict(os.environ, {"INPUT_FAIL_ON_VULNERABILITY": "true"}):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
