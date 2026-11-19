"""Regression tests for raw-capture vs structured-depth evidence diagnostics."""
from __future__ import annotations

import unittest

import build


HOUSTON = {
    "id": "club-depth-hou",
    "name": "Houston Texans depth chart",
    "url": "https://www.houstontexans.com/team/depth-chart",
    "publisher": "Houston Texans (club site)",
    "tier": "official-club",
    "marker": "depth",
    "kind": "club-depth-chart",
    "club": "HOU",
}


def capture(*, run_id: str, table_tags: int | None, row_tags: int | None,
            result: str = "ok", delta: str = "first") -> dict:
    return {
        "run_id": run_id,
        "run_trigger": "schedule",
        "source_id": HOUSTON["id"],
        "url": HOUSTON["url"],
        "final_url": HOUSTON["url"],
        "publisher": HOUSTON["publisher"],
        "tier": HOUSTON["tier"],
        "fetch_start_utc": "2026-11-19T08:55:31Z",
        "fetch_end_utc": "2026-11-19T08:55:31Z",
        "http_status": 200 if result == "ok" else None,
        "content_type": "text/html",
        "bytes": 481598 if result == "ok" else 0,
        "sha256": "a" * 64 if result == "ok" else "",
        "marker": "depth",
        "marker_found": result == "ok",
        "table_tags": table_tags,
        "row_tags": row_tags,
        "previous_sha256": None,
        "delta": delta,
        "result": result,
        "reason": "" if result == "ok" else "network error",
    }


class CaptureStructureDiagnosticsTests(unittest.TestCase):
    def test_zero_tag_success_is_flagged_and_linked_to_the_official_page(self) -> None:
        rows = [capture(run_id="20261119T085422Z", table_tags=0, row_tags=0)]
        alerts = build.structural_alerts([HOUSTON], rows)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["id"], "C-08-HOU")
        self.assertEqual((alerts[0]["missing_count"], alerts[0]["successful_count"]), (1, 1))

        dashboard = build.build_index([HOUSTON], rows)
        flagged = build.build_flagged([HOUSTON], rows)
        self.assertIn("0 table tags", dashboard)
        self.assertIn("0 row tags", dashboard)
        self.assertIn('href="flagged.html#C-08-HOU"', dashboard)
        self.assertIn('id="C-08-HOU"', flagged)
        self.assertIn(f'href="{HOUSTON["url"]}"', flagged)
        self.assertIn("20261119T085422Z", flagged)
        self.assertIn("blocked for structured use", flagged)
        self.assertIn("do not transcribe an image or infer depth", flagged)

    def test_positive_tag_counts_are_still_labelled_unparsed(self) -> None:
        rows = [capture(run_id="20261119T085422Z", table_tags=3, row_tags=18)]
        self.assertEqual(build.structural_alerts([HOUSTON], rows), [])
        dashboard = build.build_index([HOUSTON], rows)
        flagged = build.build_flagged([HOUSTON], rows)
        self.assertIn("3 table tags", dashboard)
        self.assertIn("18 row tags", dashboard)
        self.assertIn("HTML tag counts only; values not parsed", dashboard)
        self.assertNotIn('id="C-08-HOU"', flagged)

    def test_historical_unstructured_capture_remains_flagged_after_a_later_tagged_capture(self) -> None:
        rows = [
            capture(run_id="20261117T001518Z", table_tags=0, row_tags=0, delta="first"),
            capture(run_id="20261119T085422Z", table_tags=3, row_tags=18, delta="changed"),
        ]
        alert = build.structural_alerts([HOUSTON], rows)[0]
        self.assertEqual((alert["missing_count"], alert["successful_count"]), (1, 2))
        dashboard = build.build_index([HOUSTON], rows)
        flagged = build.build_flagged([HOUSTON], rows)
        self.assertIn('href="flagged.html#C-08-HOU"', dashboard)
        self.assertIn("A positive table-tag AND row-tag count was not observed in 1 of 2", flagged)
        self.assertIn("Latest successful capture 20261119T085422Z", flagged)

    def test_failed_latest_attempt_is_not_reported_as_a_zero_tag_success(self) -> None:
        rows = [
            capture(run_id="20261117T001518Z", table_tags=0, row_tags=0, delta="first"),
            capture(run_id="20261119T085422Z", table_tags=None, row_tags=None,
                    result="fail", delta="failed"),
        ]
        dashboard = build.build_index([HOUSTON], rows)
        flagged = build.build_flagged([HOUSTON], rows)
        self.assertIn("not observed (capture failed)", dashboard)
        self.assertIn("its structure is not assessed", flagged)
        self.assertIn("1 of 1 successful raw capture", flagged)


if __name__ == "__main__":
    unittest.main()
