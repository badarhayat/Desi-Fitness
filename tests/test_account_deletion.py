import unittest
from pathlib import Path

import fitness_analysis
from app import app


class AccountDeletionTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.created = []

    def tearDown(self):
        for username in self.created:
            fitness_analysis.delete_user_account(username)

    def _register(self, username: str, name: str = "Delete Tester") -> None:
        self.created.append(username)
        response = self.client.post(
            "/register",
            data={
                "name": name,
                "username": username,
                "height_feet": "5",
                "height_inches": "8",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    def test_public_delete_page_does_not_require_login(self):
        response = self.client.get("/delete-account")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Delete Your Desi Fitness Account", body)
        self.assertIn("does not collect email", body)
        self.assertNotIn('name="confirm"', body)

    def test_unauthenticated_delete_is_rejected(self):
        response = self.client.post(
            "/account/delete",
            data={"confirm": "delete", "username": "anyone"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_register_login_add_data_then_delete_own_account(self):
        username = "deltest_own"
        self._register(username)
        self.assertIn(username, fitness_analysis.all_user_data)

        user_file = fitness_analysis.DATA_DIR / f"{username}.json"
        self.assertTrue(user_file.exists())

        add = self.client.post(
            "/track",
            data={"action": "save_weight", "weight": "77.8", "weight_date": "2026-09-05"},
            follow_redirects=False,
        )
        self.assertEqual(add.status_code, 302)
        self.assertEqual(len(fitness_analysis.all_user_data[username]["weight_log"]), 1)

        chart = Path(fitness_analysis.__file__).parent / "static" / f"progress_graph_{username}.png"
        chart.write_bytes(b"fake-chart")
        self.assertTrue(chart.exists())

        profile = self.client.get("/register")
        self.assertEqual(profile.status_code, 200)
        self.assertIn("Delete Account", profile.get_data(as_text=True))
        self.assertIn("Delete your account?", profile.get_data(as_text=True))

        deleted = self.client.post(
            "/account/delete",
            data={"confirm": "delete", "username": "someone_else"},
            follow_redirects=False,
        )
        self.assertEqual(deleted.status_code, 302)
        self.assertIn("/delete-account", deleted.headers.get("Location", ""))

        self.assertNotIn(username, fitness_analysis.all_user_data)
        self.assertFalse(user_file.exists())
        self.assertFalse(chart.exists())
        self.assertTrue(Path("/workspace/dishes.csv").exists())

        login = self.client.post("/login", data={"username": username}, follow_redirects=False)
        self.assertEqual(login.status_code, 200)
        self.assertIn("Username not found", login.get_data(as_text=True))

    def test_cannot_delete_another_user_while_authenticated(self):
        victim = "deltest_victim"
        attacker = "deltest_attacker"
        self._register(victim)
        self.client.get("/logout")
        self._register(attacker)

        victim_file = fitness_analysis.DATA_DIR / f"{victim}.json"
        self.assertTrue(victim_file.exists())

        self.client.post(
            "/account/delete",
            data={"confirm": "delete", "username": victim},
            follow_redirects=False,
        )

        self.assertNotIn(attacker, fitness_analysis.all_user_data)
        self.assertIn(victim, fitness_analysis.all_user_data)
        self.assertTrue(victim_file.exists())

    def test_delete_without_confirm_does_not_remove_account(self):
        username = "deltest_noconfirm"
        self._register(username)
        response = self.client.post("/account/delete", data={"confirm": "no"}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn(username, fitness_analysis.all_user_data)

    def test_web_page_login_then_delete(self):
        username = "deltest_web"
        self._register(username)
        self.client.get("/logout")

        signed_in = self.client.post(
            "/delete-account",
            data={"username": username},
            follow_redirects=False,
        )
        self.assertEqual(signed_in.status_code, 302)

        page = self.client.get("/delete-account")
        self.assertIn('name="confirm"', page.get_data(as_text=True))

        self.client.post("/account/delete", data={"confirm": "delete"})
        self.assertNotIn(username, fitness_analysis.all_user_data)

    def test_privacy_policy_describes_in_app_and_web_deletion(self):
        body = self.client.get("/privacy").get_data(as_text=True)
        self.assertIn("Profile", body)
        self.assertIn("Delete Account", body)
        self.assertIn("/delete-account", body)
        self.assertIn("does not collect email", body)


if __name__ == "__main__":
    unittest.main()
