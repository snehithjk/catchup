import os
import tempfile
import unittest
from datetime import datetime, timezone

from catchup.brief import render_stub_brief, truncate_diff
from catchup.changes import ingest
from catchup.exposure import build_knowledge_map
from catchup.git import changed_paths, log
from catchup.pipeline import parse_window_start, run_pipeline
from catchup.ranking import rank_changes
from catchup.storage import append_feedback, load_feedback
from catchup.verify import verify_brief
from fixtures.synthetic.generate import ALICE, CUTOFF, WINDOW_END, create_repo


class CatchupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="catchup-test-")
        self.truth = create_repo(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_git_history_and_paths_are_readable(self):
        records = log(self.temp.name)
        self.assertEqual(len(records), 5)
        paths = changed_paths(self.temp.name, records[-1])
        self.assertTrue(paths)

    def test_exposure_decay_and_basis(self):
        records = log(self.temp.name, before=CUTOFF)
        path_map = {record.commit: [path for _, path in changed_paths(self.temp.name, record)]
                    for record in records}
        as_of = datetime.fromisoformat(CUTOFF)
        knowledge = build_knowledge_map(records, path_map, [ALICE], as_of, half_life_days=90)
        self.assertIn("app/service.py", knowledge)
        self.assertIn("authored", knowledge["app/service.py"].basis)
        older = knowledge["app/service.py"].score
        newer = build_knowledge_map(records, path_map, [ALICE],
                                    datetime(2025, 1, 11, tzinfo=timezone.utc), half_life_days=90)
        self.assertGreater(newer["app/service.py"].score, older)

    def test_ingestion_detects_signature_change(self):
        records = log(self.temp.name, since=CUTOFF, before=WINDOW_END)
        changes = ingest(self.temp.name, records)
        service = next(change for change in changes if "app/service.py" in change.paths)
        self.assertIn("app/service.py", service.signature_paths)
        self.assertGreater(service.additions, 0)

    def test_pipeline_personalizes_and_is_grounded(self):
        result, brief = run_pipeline(
            self.temp.name, [ALICE], datetime.fromisoformat(CUTOFF),
            datetime.fromisoformat(WINDOW_END), persist=False,
        )
        self.assertTrue(result.ranked)
        self.assertEqual(result.ranked[0].change.paths, ("app/service.py",))
        grounded, errors = verify_brief(self.temp.name, brief)
        self.assertTrue(grounded, errors)

    def test_empty_personalized_brief_is_valid_markdown(self):
        result, brief = run_pipeline(
            self.temp.name, ["nobody@example.com"], datetime.fromisoformat(CUTOFF),
            datetime.fromisoformat(WINDOW_END), persist=False,
        )
        self.assertFalse(result.ranked)
        self.assertIn("other window changes", brief)
        grounded, errors = verify_brief(self.temp.name, brief)
        self.assertTrue(grounded, errors)

    def test_verifier_rejects_uncited_and_ungrounded_claims(self):
        records = log(self.temp.name)
        commit = records[0].short_commit
        ok, errors = verify_brief(self.temp.name, "This sentence has no citation.")
        self.assertFalse(ok)
        self.assertTrue(errors)
        bad = "The `does/not-exist.py` file changed ({}).".format(commit)
        ok, errors = verify_brief(self.temp.name, bad)
        self.assertFalse(ok)
        self.assertTrue(any("absent from diff" in error for error in errors))

    def test_feedback_is_append_only_and_latest_value_wins(self):
        append_feedback(self.temp.name, "abc1234", "irrelevant")
        append_feedback(self.temp.name, "abc1234", "new")
        feedback = load_feedback(self.temp.name)
        self.assertEqual(feedback["abc1234"].label, "new")

    def test_feedback_changes_rank_score(self):
        result, _ = run_pipeline(
            self.temp.name, [ALICE], datetime.fromisoformat(CUTOFF),
            datetime.fromisoformat(WINDOW_END), persist=False,
        )
        changes = ingest(self.temp.name, log(self.temp.name, since=CUTOFF, before=WINDOW_END))
        exposure = result.knowledge_map
        from catchup.graph import build_import_graph
        fan_in = build_import_graph([], {})
        base, _ = rank_changes(changes, exposure, fan_in, top_n=10)
        from catchup.models import Feedback
        nudged, _ = rank_changes(changes, exposure, fan_in,
                                  {base[0].change.item_id: Feedback(base[0].change.item_id, "irrelevant", "")},
                                  top_n=10)
        self.assertLess(nudged[0].score, base[0].score)

    def test_duration_parser(self):
        as_of = datetime(2025, 1, 31, tzinfo=timezone.utc)
        self.assertEqual(parse_window_start("2d", as_of).day, 29)
        self.assertEqual(parse_window_start("2025-01-01", as_of).tzinfo, timezone.utc)

    def test_diff_truncation_prioritizes_exposed_file(self):
        patch = (
            "diff --git a/unrelated.py b/unrelated.py\n" + "x" * 80 + "\n"
            + "diff --git a/app/service.py b/app/service.py\n" + "y" * 80 + "\n"
        )
        excerpt = truncate_diff(patch, ["app/service.py"], limit=140)
        self.assertIn("app/service.py", excerpt)


if __name__ == "__main__":
    unittest.main()
