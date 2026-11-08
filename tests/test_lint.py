import tempfile
import unittest
from pathlib import Path

from prompt_architect import frontmatter, lint

REPO_ROOT = Path(__file__).resolve().parents[1]


def rules(findings):
    return {finding.rule for finding in findings}


BROKEN_SPEC = """---
name: broken
type: blueprint
version: 1
inputs: [thing]
output_format: markdown
---

# Broken blueprint

Prose only: this blueprint forgot its architecture.
"""

GOOD_SPEC = """---
name: good
type: blueprint
version: 1.0.0
inputs: [language]
output_format: markdown-code-fence
related: [constraint-enforcement]
---

# Good blueprint

### Role
An engine that emits data.

### Context
- Language: [LANGUAGE], pinned to a version.

### Objective
Extract the configuration parameters into JSON.

### Constraints & Negative Rules
- DO NOT invent values; unstated values are null.
- DO NOT wrap the payload in fences.

### Output Specification
A single ```json fence containing the object. No prose.
Raw JSON only: first character `{`, last character `}`.

## Acceptance Checklist
- [ ] Parses on the first attempt.
"""


class RepositoryLintTests(unittest.TestCase):
    def test_repository_has_no_lint_errors(self):
        findings = lint.lint_paths([str(REPO_ROOT)])
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(errors, [], "\n".join(f.format() for f in errors))

    def test_every_spec_file_has_front_matter(self):
        missing = []
        for folder in ("blueprints", "patterns", "benchmarks"):
            for path in (REPO_ROOT / folder).glob("*.md"):
                if not frontmatter.load(path).has_front_matter:
                    missing.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(missing, [])


class DocumentLintTests(unittest.TestCase):
    def lint_text(self, text: str, name: str = "doc.md"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_text(text, encoding="utf-8")
            return lint.lint_document(frontmatter.load(path))

    def test_good_blueprint_is_clean(self):
        self.assertEqual(self.lint_text(GOOD_SPEC), [])

    def test_missing_component_sections_are_reported(self):
        found = rules(self.lint_text(BROKEN_SPEC))
        self.assertIn("PA004", found)  # missing Role/Context/Objective/...
        self.assertIn("PA005", found)  # no acceptance checklist
        self.assertIn("PA006", found)  # no negative constraint
        self.assertIn("PA007", found)  # no fallback/null protocol

    def test_bad_version_is_reported(self):
        self.assertIn("PA003", rules(self.lint_text(BROKEN_SPEC)))

    def test_guide_type_is_accepted(self):
        doc = GOOD_SPEC.replace("type: blueprint", "type: guide")
        self.assertNotIn("PA002", rules(self.lint_text(doc)))

    def test_unknown_type_is_rejected(self):
        doc = GOOD_SPEC.replace("type: blueprint", "type: whitepaper")
        self.assertIn("PA002", rules(self.lint_text(doc)))


    def test_non_spec_markdown_is_not_required_to_have_front_matter(self):
        self.assertEqual(self.lint_text("# Just notes\n\nSome prose.\n", "notes.md"), [])

    def test_spec_tree_requires_front_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blueprints" / "x.md"
            path.parent.mkdir()
            path.write_text("# No metadata\n", encoding="utf-8")
            found = rules(lint.lint_document(frontmatter.load(path)))
        self.assertIn("PA001", found)

    def test_broken_relative_link_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("See [missing](nope.md).\n", encoding="utf-8")
            found = lint.lint_links(root)
        self.assertIn("PA009", rules(found))

    def test_valid_relative_link_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# t\n", encoding="utf-8")
            (root / "a.md").write_text("See [target](target.md).\n", encoding="utf-8")
            self.assertEqual(lint.lint_links(root), [])


if __name__ == "__main__":
    unittest.main()
