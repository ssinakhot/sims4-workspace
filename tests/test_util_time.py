import datetime
from util.time import get_minutes, get_hours, get_minutes_remain, get_time_str


class TestGetMinutes:
    def test_one_hour(self):
        start = datetime.datetime(2024, 1, 1, 12, 0, 0)
        end = datetime.datetime(2024, 1, 1, 13, 0, 0)
        assert get_minutes(end, start) == 60

    def test_zero(self):
        t = datetime.datetime(2024, 1, 1, 12, 0, 0)
        assert get_minutes(t, t) == 0

    def test_partial_minutes(self):
        start = datetime.datetime(2024, 1, 1, 12, 0, 0)
        end = datetime.datetime(2024, 1, 1, 12, 30, 45)
        assert get_minutes(end, start) == 30  # int truncation


class TestGetHours:
    def test_even_hours(self):
        assert get_hours(120) == 2

    def test_partial_hours(self):
        assert get_hours(90) == 1

    def test_zero(self):
        assert get_hours(0) == 0


class TestGetMinutesRemain:
    def test_even_hour(self):
        assert get_minutes_remain(120) == 0

    def test_with_remainder(self):
        assert get_minutes_remain(90) == 30

    def test_less_than_hour(self):
        assert get_minutes_remain(45) == 45


class TestGetTimeStr:
    def test_zero(self):
        assert get_time_str(0) == "0:00"

    def test_one_hour(self):
        assert get_time_str(60) == "1:00"

    def test_one_hour_five(self):
        assert get_time_str(65) == "1:05"

    def test_two_hours_thirty(self):
        assert get_time_str(150) == "2:30"

    def test_single_digit_minutes(self):
        assert get_time_str(3) == "0:03"
