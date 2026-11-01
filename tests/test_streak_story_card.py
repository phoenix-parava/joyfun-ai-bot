import os
import sys
import io
import time
import unittest
from PIL import Image

os.environ["OFFLINE_TEST"] = "1"

# Ensure joy-bot root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from companion_images import generate_streak_story_card

class TestStreakStoryCard(unittest.TestCase):
    """Automated test suite for Joy Bot's 9:16 mobile story & status card generation."""

    def test_01_card_dimensions_and_valid_jpeg(self):
        """Verify card generates valid JPEG format with exact 1080x1920 dimensions."""
        img_bytes = generate_streak_story_card(
            user_name="Phoenix",
            custom_name="Joy",
            streak_count=7,
            level_title="💖 Close Bestie & Confidant",
            level_desc="You two talk every day and share your deepest thoughts.",
            progress_pct=50,
            user_mask="Joy-Test123"
        )
        self.assertIsInstance(img_bytes, bytes)
        self.assertGreater(len(img_bytes), 20000, "Card bytes must exceed 20KB for high resolution")

        # Open with PIL and check dimensions
        img = Image.open(io.BytesIO(img_bytes))
        self.assertEqual(img.size, (1080, 1920), "Story card must be 1080x1920 (9:16 ratio)")
        self.assertEqual(img.format, "JPEG")

    def test_02_all_streak_tiers_generate_cleanly(self):
        """Verify generation succeeds across all 5 relationship levels."""
        tiers = [
            (1, "🌱 New Acquaintance", 0),
            (3, "🌸 Good Friends", 33),
            (7, "💖 Close Bestie & Confidant", 60),
            (14, "✨ Special Soul Connection", 85),
            (30, "💍 Soulmate / Eternal Bond", 100),
        ]
        for streak, title, pct in tiers:
            start_t = time.time()
            data = generate_streak_story_card(
                user_name="Anish",
                custom_name="Aarohi",
                streak_count=streak,
                level_title=title,
                progress_pct=pct,
                user_mask="Joy-999"
            )
            elapsed = time.time() - start_t
            self.assertGreater(len(data), 20000)
            self.assertLess(elapsed, 3.0, f"Card generation must be fast (< 3.0s on dual-core CPU), took {elapsed:.3f}s")

    def test_03_fallback_fonts_and_long_name_resilience(self):
        """Verify long user names and long custom companion names wrap safely without crashing."""
        data = generate_streak_story_card(
            user_name="Alexander Christopher Montgomery III",
            custom_name="Princess Seraphina of Luminescence",
            streak_count=42,
            level_title="💍 Soulmate / Eternal Bond",
            level_desc="A truly legendary bond that transcends ordinary boundaries.",
            progress_pct=100,
            user_mask="Joy-LongNameTest"
        )
        self.assertGreater(len(data), 20000)
        img = Image.open(io.BytesIO(data))
        self.assertEqual(img.size, (1080, 1920))

if __name__ == "__main__":
    unittest.main()
