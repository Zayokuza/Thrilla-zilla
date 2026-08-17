"""Thrilla creator and installation-owner identity tests."""

import dataclasses
import unittest


class ThrillaIdentityTests(unittest.TestCase):
    def test_alice_has_permanent_creator(self):
        from thrilla.identity import CREATOR_NAME, identity_for
        identity = identity_for("Alice")
        self.assertEqual(CREATOR_NAME, "Jesse James")
        self.assertEqual(identity.creator, CREATOR_NAME)
        self.assertEqual(identity.owner, "Alice")

    def test_different_owner_does_not_change_creator(self):
        from thrilla.identity import CREATOR_NAME, identity_for
        identity = identity_for("Bob")
        self.assertEqual(identity.creator, CREATOR_NAME)
        self.assertEqual(identity.creator, "Jesse James")
        self.assertEqual(identity.owner, "Bob")

    def test_empty_owner_is_valid_before_enrollment(self):
        from thrilla.identity import identity_for
        identity = identity_for("")
        self.assertEqual(identity.owner, "")
        self.assertEqual(identity.creator, "Jesse James")

    def test_identity_is_immutable(self):
        from thrilla.identity import identity_for
        identity = identity_for("Alice")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            identity.creator = "Someone Else"


if __name__ == "__main__":
    unittest.main()
