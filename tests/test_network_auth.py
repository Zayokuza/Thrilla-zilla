"""Stage 5 RED tests for scoped network authorization."""

import tempfile
import unittest
from pathlib import Path

_IMPORT_ERROR = None

try:
    from thrilla.network_auth import (
        AuthorizationStore,
        NetworkOperation,
        NetworkPermissionError,
        NetworkPolicy,
    )
except ModuleNotFoundError as error:
    if getattr(error, "name", "") != "thrilla.network_auth":
        raise
    _IMPORT_ERROR = error
    AuthorizationStore = None
    NetworkOperation = None
    NetworkPermissionError = None
    NetworkPolicy = None


class Stage5NetworkAuthModuleRedTest(unittest.TestCase):
    def test_network_auth_module_exists(self):
        self.assertIsNone(
            _IMPORT_ERROR,
            "Stage 5 network authorization module not implemented yet",
        )


@unittest.skipIf(
    _IMPORT_ERROR is not None,
    "Stage 5 network authorization module not implemented yet",
)
class NetworkAuthorizationBehaviorTests(unittest.TestCase):
    def make_policy(
        self,
        root,
        *,
        public_read=True,
        write=False,
    ):
        store = AuthorizationStore(Path(root))
        policy = NetworkPolicy(
            public_read_enabled=public_read,
            write_enabled=write,
            authorization_store=store,
        )
        return store, policy

    def test_public_read_is_allowed_when_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            _, policy = self.make_policy(root)

            policy.require(
                NetworkOperation.PUBLIC_READ,
                "https://example.com/docs",
            )

    def test_public_read_is_blocked_when_disabled(self):
        with tempfile.TemporaryDirectory() as root:
            _, policy = self.make_policy(
                root,
                public_read=False,
            )

            with self.assertRaises(NetworkPermissionError):
                policy.require(
                    NetworkOperation.PUBLIC_READ,
                    "https://example.com/docs",
                )

    def test_authenticated_read_requires_prior_scope_authorization(self):
        with tempfile.TemporaryDirectory() as root:
            store, policy = self.make_policy(root)

            with self.assertRaises(NetworkPermissionError):
                policy.require(
                    NetworkOperation.AUTH_READ,
                    "https://private.example.com/account",
                    account="me",
                )

            authorization = store.authorize_read(
                "private.example.com",
                "me",
            )

            self.assertEqual(
                authorization.site,
                "private.example.com",
            )
            self.assertEqual(
                authorization.account,
                "me",
            )
            self.assertEqual(
                authorization.scope,
                "read",
            )

            policy.require(
                NetworkOperation.AUTH_READ,
                "https://private.example.com/account",
                account="me",
            )

    def test_authenticated_read_authorization_persists_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            first = AuthorizationStore(Path(root))
            first.authorize_read(
                "https://Private.Example.com/some/path",
                "owner@example.com",
            )

            restarted = AuthorizationStore(Path(root))

            self.assertTrue(
                restarted.can_read(
                    "private.example.com",
                    "owner@example.com",
                )
            )

    def test_revoke_removes_only_requested_site_account_scope(self):
        with tempfile.TemporaryDirectory() as root:
            store = AuthorizationStore(Path(root))
            store.authorize_read(
                "example.com",
                "one",
            )
            store.authorize_read(
                "example.com",
                "two",
            )

            self.assertTrue(
                store.revoke_read(
                    "example.com",
                    "one",
                )
            )
            self.assertFalse(
                store.can_read(
                    "example.com",
                    "one",
                )
            )
            self.assertTrue(
                store.can_read(
                    "example.com",
                    "two",
                )
            )

    def test_read_authorization_never_grants_network_write(self):
        with tempfile.TemporaryDirectory() as root:
            store, policy = self.make_policy(
                root,
                write=False,
            )
            store.authorize_read(
                "example.com",
                "me",
            )

            policy.require(
                NetworkOperation.AUTH_READ,
                "https://example.com/private",
                account="me",
            )

            with self.assertRaises(NetworkPermissionError):
                policy.require(
                    NetworkOperation.WRITE,
                    "https://example.com/post",
                    account="me",
                )

    def test_write_requires_explicit_write_policy_even_for_public_site(self):
        with tempfile.TemporaryDirectory() as root:
            _, policy = self.make_policy(
                root,
                public_read=True,
                write=False,
            )

            with self.assertRaises(NetworkPermissionError):
                policy.require(
                    NetworkOperation.WRITE,
                    "https://example.com/post",
                )

            _, writable_policy = self.make_policy(
                root,
                public_read=True,
                write=True,
            )

            writable_policy.require(
                NetworkOperation.WRITE,
                "https://example.com/post",
            )

    def test_authorization_store_metadata_contains_no_credentials(self):
        with tempfile.TemporaryDirectory() as root:
            store = AuthorizationStore(Path(root))
            store.authorize_read(
                "example.com",
                "owner",
            )

            text = (
                Path(root)
                / "network-authorizations.json"
            ).read_text(encoding="utf-8")

            lowered = text.lower()
            for forbidden in (
                "password",
                "token",
                "cookie",
                "api_key",
                "apikey",
                "private_key",
                "bearer",
            ):
                self.assertNotIn(forbidden, lowered)

    def test_site_normalization_uses_hostname_not_path(self):
        with tempfile.TemporaryDirectory() as root:
            store = AuthorizationStore(Path(root))
            store.authorize_read(
                "https://EXAMPLE.com:443/a/b?x=1",
                "me",
            )

            self.assertTrue(
                store.can_read(
                    "example.com",
                    "me",
                )
            )
            self.assertTrue(
                store.can_read(
                    "https://example.com/other",
                    "me",
                )
            )


if __name__ == "__main__":
    unittest.main()

