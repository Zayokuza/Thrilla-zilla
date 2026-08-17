import unittest


class EquipmentDomainTests(unittest.TestCase):
    def api(self):
        from thrilla.equipment import (
            EQUIPMENT_NAMES,
            normalized_equipment_state,
            verify_creator_code,
        )
        return (
            EQUIPMENT_NAMES,
            normalized_equipment_state,
            verify_creator_code,
        )

    def test_creator_code_1989_succeeds(self):
        _, _, verify_creator_code = self.api()
        self.assertTrue(verify_creator_code("1989"))

    def test_incorrect_creator_codes_fail(self):
        _, _, verify_creator_code = self.api()
        for value in ("", "1988", "1990", " 1989 ", "Jesse"):
            with self.subTest(value=value):
                self.assertFalse(verify_creator_code(value))

    def test_empty_state_contains_exactly_five_off_modules(self):
        names, normalize, _ = self.api()

        self.assertEqual(
            names,
            ("sword", "shield", "helmet", "armor", "boots"),
        )

        self.assertEqual(
            normalize({}),
            {
                "sword": False,
                "shield": False,
                "helmet": False,
                "armor": False,
                "boots": False,
            },
        )

    def test_mixed_boolean_state_is_preserved(self):
        _, normalize, _ = self.api()

        self.assertEqual(
            normalize({
                "sword": True,
                "shield": False,
                "helmet": True,
                "armor": False,
                "boots": True,
            }),
            {
                "sword": True,
                "shield": False,
                "helmet": True,
                "armor": False,
                "boots": True,
            },
        )

    def test_unknown_equipment_is_discarded(self):
        _, normalize, _ = self.api()

        state = normalize({
            "sword": True,
            "laser": True,
        })

        self.assertNotIn("laser", state)
        self.assertEqual(len(state), 5)
        self.assertTrue(state["sword"])


if __name__ == "__main__":
    unittest.main()
