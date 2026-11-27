import unittest
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class ThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        cls.css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        cls.js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    def test_toggle_button_present(self):
        self.assertIn('id="theme-toggle"', self.html)
        self.assertIn("Modo escuro", self.html)

    def test_css_defines_light_and_dark_variables(self):
        self.assertIn("--bg:", self.css)
        self.assertIn("--fg:", self.css)
        self.assertIn(':root[data-theme="dark"]', self.css)
        self.assertIn("@media (prefers-color-scheme: dark)", self.css)
        self.assertIn(':root:not([data-theme="light"])', self.css)
        self.assertIn("background: var(--bg)", self.css)
        self.assertIn("color: var(--fg)", self.css)

    def test_js_persists_theme_choice(self):
        self.assertIn("localStorage.setItem(THEME_KEY, theme)", self.js)
        self.assertIn("document.documentElement.dataset.theme", self.js)
        self.assertIn("prefers-color-scheme: dark", self.js)
        self.assertIn("themeToggle.addEventListener('click'", self.js)

    def test_js_handles_storage_failures(self):
        self.assertIn("function readStoredTheme()", self.js)
        self.assertIn("function storeTheme(theme)", self.js)
        self.assertIn("let currentTheme = null", self.js)
        self.assertIn("storeTheme(next)", self.js)
        self.assertIn("applyTheme(next)", self.js)
        self.assertEqual(self.js.count("  } catch {"), 2)


if __name__ == "__main__":
    unittest.main()
