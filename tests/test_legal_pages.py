import unittest

from app import app


class LegalPagesTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_privacy_page_is_public(self):
        response = self.client.get("/privacy")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Privacy Policy", body)
        self.assertIn("Muhammad Badar Hayat", body)
        self.assertIn("yasmeenaziz016@gmail.com", body)

    def test_terms_page_is_public(self):
        response = self.client.get("/terms")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Terms of Use", response.get_data(as_text=True))

    def test_support_page_is_public(self):
        response = self.client.get("/support")
        self.assertEqual(response.status_code, 200)
        self.assertIn("yasmeenaziz016@gmail.com", response.get_data(as_text=True))

    def test_login_still_required_for_home(self):
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_pwa_manifest_and_icons_exist(self):
        manifest = self.client.get("/static/manifest.json")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("Desi Fitness", manifest.get_data(as_text=True))
        self.assertEqual(self.client.get("/static/icon-192.png").status_code, 200)
        self.assertEqual(self.client.get("/static/icon-512.png").status_code, 200)


if __name__ == "__main__":
    unittest.main()
