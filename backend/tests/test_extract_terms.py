"""Run with: python -m unittest discover tests  (stdlib only, no extra dependency)"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.claude_agent import extract_terms


class TestExtractTerms(unittest.TestCase):
    def test_drops_conversational_filler(self):
        # the whole sentence used to be sent to the database, matching nothing
        self.assertEqual(extract_terms("suggest a mecha anime"), ["mecha"])
        self.assertEqual(extract_terms("what's a good romance series"), ["romance"])
        self.assertEqual(extract_terms("hi, got any good drama?"), ["drama"])

    def test_keeps_genre_words(self):
        for genre in ("action", "drama", "romance", "mecha", "psychological"):
            self.assertIn(genre, extract_terms(f"recommend a {genre} anime"), genre)

    def test_adds_singular_for_plurals(self):
        self.assertEqual(extract_terms("anime about ninjas"), ["ninjas", "ninja"])
        # -ss words are not plurals
        self.assertEqual(extract_terms("a show about chess"), ["chess"])

    def test_falls_back_to_the_raw_phrase(self):
        # all filler: searching every word would match the whole catalogue
        self.assertEqual(extract_terms("hello there"), ["hello there"])
        self.assertEqual(extract_terms(""), [])

    def test_keeps_titles_intact(self):
        self.assertEqual(extract_terms("Naruto"), ["naruto"])
        self.assertEqual(extract_terms("Cowboy Bebop"), ["cowboy", "bebop"])


if __name__ == "__main__":
    unittest.main()
