"""
Unit tests for BeliefStore — covers all methods and the full spec walkthrough.
"""

import unittest

from belief_store.store import BeliefStore
from belief_store.domains.loan import setup_loan_domain


class TestAddHypothesis(unittest.TestCase):
    """Test add_hypothesis: adding, updating, and logging."""

    def test_add_new_belief(self):
        store = BeliefStore()
        store.add_hypothesis("applicant.income", 6000)

        self.assertEqual(store.beliefs["applicant.income"], 6000)
        self.assertFalse(store.is_derived["applicant.income"])
        self.assertEqual(len(store.revision_log), 1)
        self.assertEqual(store.revision_log[0]["action"], "add")

    def test_update_existing_belief(self):
        store = BeliefStore()
        store.add_hypothesis("applicant.income", 4000)
        store.add_hypothesis("applicant.income", 6000)

        self.assertEqual(store.beliefs["applicant.income"], 6000)
        self.assertEqual(len(store.revision_log), 2)
        self.assertEqual(store.revision_log[1]["action"], "update")
        self.assertEqual(store.revision_log[1]["old"], 4000)
        self.assertEqual(store.revision_log[1]["new"], 6000)


class TestDirtyPropagation(unittest.TestCase):
    """Test that changing a base belief marks downstream dependents dirty."""

    def setUp(self):
        self.store = BeliefStore()
        setup_loan_domain(self.store)
        # Set base beliefs
        self.store.add_hypothesis("applicant.income", 4000)
        self.store.add_hypothesis("applicant.credit_score", 750)
        self.store.add_hypothesis("loan.min_income", 5000)
        self.store.add_hypothesis("loan.min_credit", 600)

    def test_initial_dirty_set(self):
        """After adding base beliefs, all derived keys should be dirty."""
        self.assertIn("loan.income_eligible", self.store.dirty)
        self.assertIn("loan.credit_eligible", self.store.dirty)
        self.assertIn("loan.status", self.store.dirty)
        self.assertIn("loan.rejection_reason", self.store.dirty)

    def test_update_propagates_dirty(self):
        """Updating a base belief re-dirties its dependents."""
        # First, resolve everything
        self.store.resolve_all_dirty()
        self.assertEqual(len(self.store.dirty), 0)

        # Now update income → should dirty income_eligible, status, rejection_reason
        self.store.add_hypothesis("applicant.income", 6000)
        self.assertIn("loan.income_eligible", self.store.dirty)
        self.assertIn("loan.status", self.store.dirty)
        self.assertIn("loan.rejection_reason", self.store.dirty)
        # credit_eligible should NOT be dirty (income doesn't affect it)
        self.assertNotIn("loan.credit_eligible", self.store.dirty)


class TestRuleResolution(unittest.TestCase):
    """Test resolve_all_dirty computes correct derived values."""

    def test_loan_rejected(self):
        store = BeliefStore()
        setup_loan_domain(store)
        store.add_hypothesis("applicant.income", 4000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)

        store.resolve_all_dirty()

        self.assertFalse(store.beliefs["loan.income_eligible"])
        self.assertTrue(store.beliefs["loan.credit_eligible"])
        self.assertEqual(store.beliefs["loan.status"], "rejected")
        self.assertEqual(store.beliefs["loan.rejection_reason"], "income below minimum")
        self.assertEqual(len(store.dirty), 0)

    def test_loan_approved(self):
        store = BeliefStore()
        setup_loan_domain(store)
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)

        store.resolve_all_dirty()

        self.assertTrue(store.beliefs["loan.income_eligible"])
        self.assertTrue(store.beliefs["loan.credit_eligible"])
        self.assertEqual(store.beliefs["loan.status"], "approved")
        self.assertIsNone(store.beliefs["loan.rejection_reason"])


class TestRetraction(unittest.TestCase):
    """Test remove_hypothesis with cascading retraction."""

    def test_retract_base_cascades(self):
        store = BeliefStore()
        setup_loan_domain(store)
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)
        store.resolve_all_dirty()

        # Retract applicant.income → should cascade
        store.remove_hypothesis("applicant.income")

        self.assertNotIn("applicant.income", store.beliefs)
        # income_eligible depends on applicant.income → retracted
        self.assertNotIn("loan.income_eligible", store.beliefs)
        # status depends on income_eligible → retracted
        self.assertNotIn("loan.status", store.beliefs)
        # rejection_reason depends on income_eligible → retracted
        self.assertNotIn("loan.rejection_reason", store.beliefs)
        # credit_eligible does NOT depend on applicant.income → kept
        self.assertIn("loan.credit_eligible", store.beliefs)

    def test_retract_logs_action(self):
        store = BeliefStore()
        store.add_hypothesis("foo.bar", 42)
        log_start = len(store.revision_log)
        store.remove_hypothesis("foo.bar")

        retract_entry = store.revision_log[log_start]
        self.assertEqual(retract_entry["action"], "retract")
        self.assertEqual(retract_entry["old"], 42)
        self.assertIsNone(retract_entry["new"])


class TestPromptConstruction(unittest.TestCase):
    """Test to_prompt serialization and dirty assertion."""

    def test_clean_prompt(self):
        store = BeliefStore()
        setup_loan_domain(store)
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)
        store.resolve_all_dirty()

        prompt, keys = store.to_prompt(["applicant", "loan"])

        # All relevant beliefs should be included
        self.assertIn("[base] applicant.income = 6000", prompt)
        self.assertIn("[derived] loan.status = approved", prompt)
        self.assertEqual(len(keys), 8)  # 4 base + 4 derived

    def test_dirty_assertion_raises(self):
        store = BeliefStore()
        setup_loan_domain(store)
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)
        # Resolve first so derived beliefs exist in the store
        store.resolve_all_dirty()
        # Now update a base belief to re-dirty derived beliefs
        store.add_hypothesis("applicant.income", 3000)

        with self.assertRaises(AssertionError):
            store.to_prompt(["loan"])

    def test_entity_filtering(self):
        store = BeliefStore()
        store.add_hypothesis("applicant.income", 6000)
        store.add_hypothesis("unrelated.data", "hello")

        prompt, keys = store.to_prompt(["applicant"])

        self.assertIn("applicant.income", prompt)
        self.assertNotIn("unrelated", prompt)
        self.assertEqual(len(keys), 1)


class TestRevisionLog(unittest.TestCase):
    """Test format_revision_log output."""

    def test_log_format(self):
        store = BeliefStore()
        store.add_hypothesis("x.a", 1)
        store.add_hypothesis("x.a", 2)

        log = store.format_revision_log()

        self.assertIn("[add]", log)
        self.assertIn("[update]", log)
        self.assertIn("1 → 2", log)

    def test_since_index(self):
        store = BeliefStore()
        store.add_hypothesis("x.a", 1)
        store.add_hypothesis("x.b", 2)

        log = store.format_revision_log(since_index=1)

        self.assertNotIn("x.a", log)
        self.assertIn("x.b", log)


class TestFullWalkthrough(unittest.TestCase):
    """Full walkthrough from the spec: Turn 1 (rejected) → Turn 2 (approved)."""

    def test_spec_walkthrough(self):
        store = BeliefStore()
        setup_loan_domain(store)

        # === Turn 1: Initial beliefs (income too low → rejected) ===
        store.add_hypothesis("applicant.income", 4000)
        store.add_hypothesis("applicant.credit_score", 750)
        store.add_hypothesis("loan.min_income", 5000)
        store.add_hypothesis("loan.min_credit", 600)

        store.resolve_all_dirty()

        self.assertFalse(store.beliefs["loan.income_eligible"])
        self.assertTrue(store.beliefs["loan.credit_eligible"])
        self.assertEqual(store.beliefs["loan.status"], "rejected")
        self.assertEqual(
            store.beliefs["loan.rejection_reason"], "income below minimum"
        )

        # Build prompt — should be all clean
        prompt_t1, _ = store.to_prompt(["applicant", "loan"])
        self.assertIn("[derived] loan.status = rejected", prompt_t1)

        # === Turn 2: Income updated (now qualifies → approved) ===
        log_before_t2 = len(store.revision_log)

        store.add_hypothesis("applicant.income", 6000)

        # Verify dirty propagation
        self.assertIn("loan.income_eligible", store.dirty)
        self.assertIn("loan.status", store.dirty)
        self.assertIn("loan.rejection_reason", store.dirty)
        self.assertNotIn("loan.credit_eligible", store.dirty)

        store.resolve_all_dirty()

        self.assertTrue(store.beliefs["loan.income_eligible"])
        self.assertEqual(store.beliefs["loan.status"], "approved")
        self.assertIsNone(store.beliefs["loan.rejection_reason"])

        # Build prompt — should show approved
        prompt_t2, _ = store.to_prompt(["applicant", "loan"])
        self.assertIn("[derived] loan.status = approved", prompt_t2)

        # Check revision log for turn 2
        log_t2 = store.format_revision_log(since_index=log_before_t2)
        self.assertIn("[update]", log_t2)
        self.assertIn("[derived]", log_t2)
        self.assertIn("income_check", log_t2)


if __name__ == "__main__":
    unittest.main()
