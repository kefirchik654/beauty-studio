import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.slots import free_starts, subtract_breaks  # noqa: E402

TZ = ZoneInfo("Asia/Krasnoyarsk")
DAY = date(2026, 11, 9)  # понедельник
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=TZ)


def at(h, m=0):
    return datetime(2026, 11, 9, h, m, tzinfo=TZ)


class SlotsTest(unittest.TestCase):
    def test_subtract_breaks(self):
        res = subtract_breaks([(time(10), time(19))], [(time(13), time(14))])
        self.assertEqual(res, [(time(10), time(13)), (time(14), time(19))])

    def test_example_from_spec(self):
        """Анна 10–19, обед 13–14, запись 11–12, услуга 90 мин, шаг 30."""
        slots = free_starts(
            DAY, TZ, [(time(10), time(19))], [(time(13), time(14))],
            [(at(11), at(12))], 90, 0, 30, NOW,
        )
        self.assertEqual(
            [s.strftime("%H:%M") for s in slots],
            ["14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
        )

    def test_buffer_blocks_neighbour(self):
        """Запись 10:00–11:00 с буфером 15 мин: 11:00 слот не нужен, если буфер входит в busy_until."""
        busy = [(at(10), at(11, 15))]  # busy_until уже включает буфер
        slots = free_starts(DAY, TZ, [(time(10), time(13))], [], busy, 60, 0, 30, NOW)
        self.assertEqual([s.strftime("%H:%M") for s in slots], ["11:30", "12:00"])

    def test_service_buffer_must_fit_before_next_booking(self):
        """Окрашивание 90 + буфер 15: запись в 12:00 блокирует начало в 10:30 (заканчивается 12:00 + буфер)."""
        busy = [(at(12), at(13))]
        slots = free_starts(DAY, TZ, [(time(10), time(14))], [], busy, 90, 15, 30, NOW)
        self.assertEqual([s.strftime("%H:%M") for s in slots], ["10:00"])

    def test_min_lead_time(self):
        now = datetime(2026, 11, 9, 10, 20, tzinfo=TZ)
        slots = free_starts(DAY, TZ, [(time(10), time(13))], [], [], 60, 0, 30, now, 60)
        self.assertEqual([s.strftime("%H:%M") for s in slots], ["11:30", "12:00"])

    def test_no_work_no_slots(self):
        self.assertEqual(free_starts(DAY, TZ, [], [], [], 60, 0, 30, NOW), [])


if __name__ == "__main__":
    unittest.main()
