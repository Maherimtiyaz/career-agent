import asyncio
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent as cli
import gmail_sender


class GmailCliTests(unittest.TestCase):
    def test_live_run_requires_oauth_before_initializing(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(gmail_sender, "CREDS_FILE", Path(directory) / "credentials.json"),
                patch.object(gmail_sender, "TOKEN_FILE", Path(directory) / "token.json"),
                patch.object(cli, "DRY_RUN", False),
                patch.object(cli, "init_db") as init_db,
            ):
                output = StringIO()
                cli.console = Console(file=output, force_terminal=False, no_color=True)

                with self.assertRaises(SystemExit) as error:
                    asyncio.run(cli.run())

                self.assertEqual(error.exception.code, 2)
                init_db.assert_not_called()
                self.assertIn("Gmail OAuth is not configured", output.getvalue())

    def test_dry_run_previews_without_gmail_oauth_or_sending(self):
        target = {
            "id": "test-opportunity",
            "organization": "Example Org",
            "title": "Software Intern",
            "hr_email": "recruiter@example.test",
            "email_source": "test",
            "description": "A test role",
            "url": "https://example.test/role",
        }
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(gmail_sender, "CREDS_FILE", Path(directory) / "credentials.json"),
                patch.object(gmail_sender, "TOKEN_FILE", Path(directory) / "token.json"),
                patch.object(cli, "DRY_RUN", True),
                patch.object(cli, "FOLLOWUPS_ONLY", False),
                patch.object(cli, "init_db"),
                patch.object(
                    cli,
                    "get_stats",
                    return_value={"total": 0, "replied": 0, "followups": 0, "today": 0},
                ),
                patch.object(cli, "get_todays_targets", new=AsyncMock(return_value=([target], []))),
                patch.object(cli, "already_emailed", return_value=False),
                patch.object(
                    cli,
                    "draft_cold_email",
                    new=AsyncMock(return_value={"subject": "Test", "body": "Preview"}),
                ),
                patch.object(cli, "get_pending_followups", return_value=[]),
                patch.object(cli, "send_email") as send_email,
            ):
                output = StringIO()
                cli.console = Console(file=output, force_terminal=False, no_color=True)
                asyncio.run(cli.run())

                send_email.assert_not_called()
                self.assertIn("Email previews: 1", output.getvalue())
                self.assertIn("Today: 0 emails sent", output.getvalue())


if __name__ == "__main__":
    unittest.main()
