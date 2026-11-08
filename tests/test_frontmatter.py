import tempfile
import unittest
from pathlib import Path

from prompt_architect import frontmatter


SAMPLE = """---
name: demo
type: blueprint
version: 1.0.0
inputs: [language, platform]
output_format: markdown-code-fence
related:
  - chain-of-thought
  - constraint-enforcement
---

# Body
"""


class FrontMatterTests(unittest.TestCase):
    def test_parses_scalars_and_inline_lists(self):
        meta, body = frontmatter.split_front_matter(SAMPLE)
        self.assertEqual(meta["name"], "demo")
        self.assertEqual(meta["version"], "1.0.0")
        self.assertEqual(meta["inputs"], ["language", "platform"])
        self.assertTrue(body.startswith("\n# Body"))

    def test_parses_block_lists(self):
        meta, _ = frontmatter.split_front_matter(SAMPLE)
        self.assertEqual(meta["related"], ["chain-of-thought", "constraint-enforcement"])

    def test_no_front_matter_returns_original_text(self):
        meta, body = frontmatter.split_front_matter("# Title\n\ntext")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Title\n\ntext")

    def test_unterminated_front_matter_is_not_metadata(self):
        meta, body = frontmatter.split_front_matter("---\nname: x\n# no close")
        self.assertEqual(meta, {})
        self.assertIn("name: x", body)

    def test_strips_trailing_comments_from_unquoted_scalars(self):
        meta, _ = frontmatter.split_front_matter("---\nname: demo  # inline note\n---\n")
        self.assertEqual(meta["name"], "demo")

    def test_crlf_is_normalised(self):
        meta, body = frontmatter.split_front_matter(SAMPLE.replace("\n", "\r\n"))
        self.assertEqual(meta["name"], "demo")
        self.assertTrue(body.startswith("\n# Body"))

    def test_load_sets_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(SAMPLE, encoding="utf-8")
            doc = frontmatter.load(path)
            self.assertTrue(doc.has_front_matter)
            self.assertEqual(doc.path, path)


if __name__ == "__main__":
    unittest.main()
