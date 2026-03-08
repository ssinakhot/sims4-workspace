import os
from ctypes import Structure, c_uint
from multiprocessing.sharedctypes import Value

import pytest


@pytest.fixture(autouse=True)
def _mock_settings(mock_settings):
    mock_settings.num_threads = 2
    mock_settings.decompiler_timeout = 10.0


class TestStats:
    def test_stats_structure(self):
        from util.decompile import Stats
        s = Value(Stats, 0, 0, 0, 0)
        assert s.suc_count == 0
        assert s.fail_count == 0
        assert s.count == 0
        assert s.col_count == 0

    def test_total_stats_structure(self):
        from util.decompile import TotalStats
        t = Value(TotalStats, 0, 0, 0, 0)
        assert t.suc_count == 0
        assert t.minutes == 0


class TestPrintProgress:
    def test_success_increments(self):
        from util.decompile import Stats, TotalStats, print_progress
        stats = Value(Stats, 0, 0, 0, 0)
        total = Value(TotalStats, 0, 0, 0, 0)

        print_progress(stats, total, True)
        assert stats.suc_count == 1
        assert stats.fail_count == 0
        assert stats.count == 1
        assert total.suc_count == 1

    def test_failure_increments(self):
        from util.decompile import Stats, TotalStats, print_progress
        stats = Value(Stats, 0, 0, 0, 0)
        total = Value(TotalStats, 0, 0, 0, 0)

        print_progress(stats, total, False)
        assert stats.fail_count == 1
        assert stats.suc_count == 0
        assert stats.count == 1
        assert total.fail_count == 1

    def test_col_count_wraps_at_80(self):
        from util.decompile import Stats, TotalStats, print_progress
        stats = Value(Stats, 0, 0, 0, 0)
        total = Value(TotalStats, 0, 0, 0, 0)

        for _ in range(80):
            print_progress(stats, total, True)
        assert stats.col_count == 0  # reset after 80


class TestPrintSummary:
    def test_outputs_stats(self, capsys):
        from util.decompile import Stats, print_summary
        stats = Value(Stats, 7, 3, 10, 0)

        print_summary(stats)
        output = capsys.readouterr().out
        assert "S: 7" in output
        assert "F: 3" in output
        assert "T: 10" in output
        assert "70.0%" in output
        assert "30.0%" in output


class TestInitProcess:
    def test_sets_process_module_globals(self):
        from util.decompile import init_process, Stats, TotalStats
        from util import process_module

        stats = Value(Stats, 0, 0, 0, 0)
        total = Value(TotalStats, 0, 0, 0, 0)

        init_process(stats, total)
        assert process_module.stats is stats
        assert process_module.total_stats is total


class TestStdoutDecompile:
    def test_writes_stdout_to_file(self, tmp_path):
        from util.decompile import stdout_decompile

        dest = str(tmp_path / "output.py")
        # Use python3 to echo some text to stdout
        success, result = stdout_decompile(
            "python3", ["-c", "print('decompiled code')"], dest
        )

        assert success
        assert os.path.isfile(dest)
        with open(dest) as f:
            assert "decompiled code" in f.read()

    def test_returns_false_on_failure(self, tmp_path):
        from util.decompile import stdout_decompile

        dest = str(tmp_path / "output.py")
        success, result = stdout_decompile(
            "python3", ["-c", "import sys; sys.exit(1)"], dest
        )
        assert not success


class TestDecompilePrintTotals:
    def test_with_results(self, capsys):
        from util.decompile import TotalStats, decompile_print_totals, totals
        totals.suc_count = 8
        totals.fail_count = 2
        totals.count = 10
        totals.minutes = 5

        decompile_print_totals()
        output = capsys.readouterr().out
        assert "S: 8" in output
        assert "F: 2" in output
        assert "T: 10" in output

        # Reset globals
        totals.suc_count = 0
        totals.fail_count = 0
        totals.count = 0
        totals.minutes = 0

    def test_with_zero_count(self, capsys):
        from util.decompile import decompile_print_totals, totals
        totals.count = 0

        decompile_print_totals()
        output = capsys.readouterr().out
        assert "No files were processed" in output
