"""Exercise the commit validator through its command-line interface."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_commits.py"


class CommitChecks(unittest.TestCase):
    """Check CLI results against literal message and repository fixtures."""

    def check_message(self, message: str) -> subprocess.CompletedProcess[str]:
        """Validate one message through standard input."""
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--message-file", "-"],
            input=message,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_messages(self) -> None:
        """Accept optional scopes, breaking markers, and free-form bodies."""
        for message in (
            "fix: correct quiet mode state",
            "feat(climate)!: change mode mapping",
            "chore(main): release 1.1.0",
            "custom: document a project-specific change",
            "FIX: correct quiet mode state",
            "fix: correct mapping\n\nA free-form body.\nAnother line.\n\nRefs: #42",
            "feat: change defaults\n\nBREAKING CHANGE: previous defaults are removed",
            "feat: change defaults\n\nBREAKING-CHANGE: previous defaults are removed",
        ):
            with self.subTest(message=message):
                result = self.check_message(message)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    result.stdout, "Validated 1 Conventional Commit message(s).\n"
                )

    def test_invalid_messages(self) -> None:
        """Reject malformed headers, bodies, and breaking-change footers."""
        for message in (
            "",
            "Fix quiet mode",
            "fix:no separating space",
            "feat: ",
            "feat(): empty scope",
            "feat( ): blank scope",
            "fix: mapping\nNo blank line",
            "feat: defaults\n\nbreaking change: removed defaults",
            "feat: defaults\n\nBREAKING CHANGE: ",
        ):
            with self.subTest(message=message):
                result = self.check_message(message)
                self.assertEqual(result.returncode, 1)
                self.assertIn("message:", result.stderr)

    def test_message_file(self) -> None:
        """Read a proposed commit message from a file."""
        with tempfile.TemporaryDirectory() as directory:
            message_file = Path(directory) / "message.txt"
            message_file.write_text("ci: check commit messages\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--message-file", str(message_file)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout, "Validated 1 Conventional Commit message(s).\n"
            )

    def test_git_range_checks_new_commits_and_skips_merge_commits(self) -> None:
        """Ignore legacy history and merges but reject invalid new commits."""
        with tempfile.TemporaryDirectory() as directory:
            env = {
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }

            def git(*args: str) -> str:
                return subprocess.check_output(
                    ["git", *args],
                    cwd=directory,
                    env=env,
                    text=True,
                    stderr=subprocess.PIPE,
                ).strip()

            def check_range(revisions: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(SCRIPT), "--range", revisions],
                    cwd=directory,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )

            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.com")
            git("commit", "--allow-empty", "-m", "Legacy baseline")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "feature")
            git("commit", "--allow-empty", "-m", "feat: add a register")
            git("checkout", "main")
            git("merge", "--no-ff", "feature", "-m", "Merge branch feature")
            result = check_range(f"{base}..HEAD")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout, "Validated 1 Conventional Commit message(s).\n"
            )
            git("commit", "--allow-empty", "-m", "Invalid new commit")
            bad_sha = git("rev-parse", "HEAD")
            result = check_range(f"{base}..HEAD")
            self.assertEqual(result.returncode, 1)
            self.assertIn(f"{bad_sha}: Use <type>", result.stderr)
            self.assertEqual(check_range("missing-ref..HEAD").returncode, 1)


if __name__ == "__main__":
    unittest.main()
