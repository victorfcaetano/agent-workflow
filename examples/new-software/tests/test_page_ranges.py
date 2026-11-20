import unittest

from page_ranges import normalize


class PageRangeTests(unittest.TestCase):
    def test_overlapping_and_adjacent_intervals_merge_in_page_order(self):
        self.assertEqual(normalize(" 8 , 1-3, 2, 5-7, 7-10, 1 "), "1-3,5-10")

    def test_single_pages_and_wide_ranges(self):
        self.assertEqual(normalize("7-7"), "7")
        self.assertEqual(normalize("4,2-1000000000,1"), "1-1000000000")

    def test_invalid_or_empty_intervals_are_rejected(self):
        for selection in ("", "0", "-4", "6-2", "1,,3", "2,", "x", "1--3", "2.5"):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                normalize(selection)
