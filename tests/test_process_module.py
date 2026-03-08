from util import process_module


class TestProcessModule:
    def test_initial_state(self):
        """process_module globals should default to None."""
        assert hasattr(process_module, "stats")
        assert hasattr(process_module, "total_stats")

    def test_assignable(self):
        """Globals should be assignable (used by multiprocessing init)."""
        original_stats = process_module.stats
        original_total = process_module.total_stats
        try:
            process_module.stats = "test_value"
            process_module.total_stats = "test_total"
            assert process_module.stats == "test_value"
            assert process_module.total_stats == "test_total"
        finally:
            process_module.stats = original_stats
            process_module.total_stats = original_total
