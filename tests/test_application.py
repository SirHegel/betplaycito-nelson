from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from betplaycito import __version__  # noqa: E402
from betplaycito.server import (  # noqa: E402
    BetPlaycitoApp,
    VARIABLES,
    VARIABLE_GROUPS,
)


NEW_GROUPS = {
    "total_shots_range": ("total_shots_over255", "total_shots_under265"),
    "shots_on_target_range": (
        "shots_on_target_over75",
        "shots_on_target_under85",
    ),
    "corners_range": ("corners_plus95", "corners_minus105"),
    "cards_range": ("cards_plus4", "cards_minus5"),
    "half_goals": (
        "first_half_more_goals",
        "second_half_more_goals",
        "halves_equal_goals",
    ),
}


class BetPlaycitoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="betplaycito-test-")
        root = Path(self.temporary.name)
        self.app = BetPlaycitoApp(
            data_dir=root / "datos",
            config_path=root / "config.local.json",
        )
        connection = self.app.database.connect()
        try:
            user_id = int(connection.execute("SELECT id FROM users").fetchone()[0])
        finally:
            connection.close()
        self.user = {"id": user_id, "username": "Administrador"}

    def tearDown(self) -> None:
        self.temporary.cleanup()


class CatalogTests(unittest.TestCase):
    def test_catalog_has_unique_groups_and_categories(self) -> None:
        group_keys = [group["key"] for group in VARIABLE_GROUPS]
        category_keys = [
            category
            for group in VARIABLE_GROUPS
            for category in group["categories"]
        ]
        self.assertEqual(11, len(group_keys))
        self.assertEqual(len(group_keys), len(set(group_keys)))
        self.assertEqual(24, len(category_keys))
        self.assertEqual(len(category_keys), len(set(category_keys)))
        self.assertEqual(set(category_keys), set(VARIABLES))

    def test_requested_groups_keep_their_stable_keys(self) -> None:
        groups = {group["key"]: tuple(group["categories"]) for group in VARIABLE_GROUPS}
        for group_key, categories in NEW_GROUPS.items():
            self.assertEqual(categories, groups[group_key])

    def test_version_is_synchronized(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        installer = (
            PROJECT_ROOT / "packaging" / "windows" / "BetPlaycito-Nelson.iss"
        ).read_text(encoding="utf-8")
        self.assertIn(f'version = "{__version__}"', pyproject)
        self.assertIn(f'#define AppVersion "{__version__}"', installer)


class FreshDatabaseTests(BetPlaycitoTestCase):
    def test_new_installation_has_no_business_data(self) -> None:
        self.assertEqual([], self.app.list_teams())
        dashboard = self.app.dashboard([])
        self.assertEqual(0, dashboard["totals"]["observations"])
        self.assertEqual(0, dashboard["totals"]["adjustments"])
        self.assertEqual(0, dashboard["totals"]["matches"])
        self.assertTrue(all(group["total"] == 0 for group in dashboard["groups"]))

        history = self.app.history(page=1, page_size=25, item_type="all", team_ids=[])
        self.assertEqual([], history["items"])
        self.assertEqual(0, history["total"])
        self.assertEqual(1, history["total_pages"])

        exported = self.app.export_payload()
        self.assertEqual([], exported["teams"])
        self.assertEqual([], exported["adjustments"])
        self.assertEqual([], exported["matches"])

    def test_requested_manual_counters_are_persistent_and_calculated(self) -> None:
        for categories in NEW_GROUPS.values():
            for category in categories:
                self.app.create_adjustment(
                    {"variable": category, "delta": 1, "team_id": None},
                    self.user,
                )
        self.app.create_adjustment(
            {"variable": "first_half_more_goals", "delta": 1, "team_id": None},
            self.user,
        )

        dashboard = self.app.dashboard([])
        groups = {group["key"]: group for group in dashboard["groups"]}
        for group_key, categories in NEW_GROUPS.items():
            expected_total = len(categories) + (1 if group_key == "half_goals" else 0)
            self.assertEqual(expected_total, groups[group_key]["total"])

        halves = {
            category["key"]: category
            for category in groups["half_goals"]["categories"]
        }
        self.assertEqual(2, halves["first_half_more_goals"]["count"])
        self.assertEqual(50.0, halves["first_half_more_goals"]["percentage"])
        self.assertEqual(25.0, halves["second_half_more_goals"]["percentage"])
        self.assertEqual(25.0, halves["halves_equal_goals"]["percentage"])

        validated = self.app._validate_restore_payload(self.app.export_payload())
        self.assertEqual(12, len(validated["adjustments"]))


class EmptyPreviewTests(unittest.TestCase):
    def test_direct_file_preview_contains_no_seeded_business_records(self) -> None:
        script = (SOURCE_ROOT / "betplaycito" / "web" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("const PREVIEW_TEAMS = [];", script)
        self.assertIn("const PREVIEW_HISTORY = [];", script)
        self.assertNotIn("PREVIEW_TEAM_COUNTS", script)


if __name__ == "__main__":
    unittest.main()
