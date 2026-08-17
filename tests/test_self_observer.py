import importlib
import importlib.util
import unittest


class SelfProviderTests(unittest.TestCase):
    REPO = "/tmp/thrilla-test-repo"

    RESPONSES = {
        (
            "rev-parse",
            "--show-toplevel",
        ): "/tmp/thrilla-test-repo",
        (
            "branch",
            "--show-current",
        ): "thrilla/test-branch",
        (
            "rev-parse",
            "HEAD",
        ): (
            "0123456789abcdef"
            "0123456789abcdef"
            "01234567"
        ),
        (
            "log",
            "-1",
            "--pretty=%s",
        ): "feat: test repository observer",
        (
            "status",
            "--porcelain",
        ): "",
    }

    def provider_type(self):
        spec = importlib.util.find_spec(
            "thrilla.observers"
        )

        self.assertIsNotNone(spec)

        module = importlib.import_module(
            "thrilla.observers"
        )

        self.assertTrue(
            hasattr(module, "SelfProvider"),
            "SelfProvider is not implemented",
        )

        return module.SelfProvider

    def provider(
        self,
        responses=None,
        calls=None,
    ):
        if responses is None:
            responses = dict(
                self.RESPONSES
            )

        if calls is None:
            calls = []

        def run_fn(
            args,
            cwd,
        ):
            calls.append(
                (
                    tuple(args),
                    cwd,
                )
            )

            return responses[
                tuple(args)
            ]

        return self.provider_type()(
            repo_root=self.REPO,
            version="9.9.9-test",
            run_fn=run_fn,
        )

    def test_recognizes_version_question(self):
        self.assertTrue(
            self.provider().supports(
                "What version are you?"
            )
        )

    def test_recognizes_branch_question(self):
        self.assertTrue(
            self.provider().supports(
                "What branch are you on?"
            )
        )

    def test_recognizes_commit_question(self):
        self.assertTrue(
            self.provider().supports(
                "What commit are you running?"
            )
        )

    def test_recognizes_repository_clean_question(self):
        self.assertTrue(
            self.provider().supports(
                "Is your repository clean?"
            )
        )

    def test_recognizes_repository_location_question(self):
        self.assertTrue(
            self.provider().supports(
                "Where is your repository?"
            )
        )

    def test_recognizes_project_identity_question(self):
        self.assertTrue(
            self.provider().supports(
                "What project are you?"
            )
        )

    def test_recognizes_code_state_question(self):
        self.assertTrue(
            self.provider().supports(
                "What is your current code state?"
            )
        )

    def test_unrelated_prompt_is_unsupported(self):
        self.assertFalse(
            self.provider().supports(
                "Explain recursion."
            )
        )

    def test_collects_repository_state(self):
        context = self.provider().collect(
            "What is your current code state?"
        )

        expected_sha = (
            "0123456789abcdef"
            "0123456789abcdef"
            "01234567"
        )

        self.assertEqual(
            context.direct_answer,
            (
                "Project: THRILLA-ZILLA\n"
                "Version: 9.9.9-test\n"
                "Repository root: "
                "/tmp/thrilla-test-repo\n"
                "Branch: thrilla/test-branch\n"
                "HEAD: "
                + expected_sha
                + " feat: test repository observer\n"
                "Worktree clean: yes\n"
                "Changed paths: 0"
            ),
        )

        self.assertIsNone(
            context.gap
        )

    def test_git_queries_are_read_only_and_deterministic(self):
        calls = []

        self.provider(
            calls=calls
        ).collect(
            "What branch are you on?"
        )

        self.assertEqual(
            calls,
            [
                (
                    (
                        "rev-parse",
                        "--show-toplevel",
                    ),
                    self.REPO,
                ),
                (
                    (
                        "branch",
                        "--show-current",
                    ),
                    self.REPO,
                ),
                (
                    (
                        "rev-parse",
                        "HEAD",
                    ),
                    self.REPO,
                ),
                (
                    (
                        "log",
                        "-1",
                        "--pretty=%s",
                    ),
                    self.REPO,
                ),
                (
                    (
                        "status",
                        "--porcelain",
                    ),
                    self.REPO,
                ),
            ],
        )

    def test_dirty_worktree_is_reported(self):
        responses = dict(
            self.RESPONSES
        )

        responses[
            (
                "status",
                "--porcelain",
            )
        ] = (
            " M thrilla/app.py\n"
            "?? scratch.txt"
        )

        context = self.provider(
            responses=responses
        ).collect(
            "Is your repository clean?"
        )

        self.assertIn(
            "Worktree clean: no",
            context.direct_answer,
        )

        self.assertIn(
            "Changed paths: 2",
            context.direct_answer,
        )

    def test_detached_head_is_reported(self):
        responses = dict(
            self.RESPONSES
        )

        responses[
            (
                "branch",
                "--show-current",
            )
        ] = ""

        context = self.provider(
            responses=responses
        ).collect(
            "What branch are you on?"
        )

        self.assertIn(
            "Branch: (detached HEAD)",
            context.direct_answer,
        )

    def test_repository_evidence_is_structured(self):
        context = self.provider().collect(
            "What commit are you running?"
        )

        self.assertEqual(
            len(context.evidence),
            1,
        )

        evidence = context.evidence[0]

        self.assertEqual(
            evidence.source,
            "repository_state",
        )

        self.assertIn(
            "local git repository",
            evidence.detail.lower(),
        )

        self.assertIn(
            "THRILLA-ZILLA",
            evidence.content,
        )

        self.assertIn(
            "thrilla/test-branch",
            evidence.content,
        )

    def test_direct_answer_allows_model_bypass(self):
        context = self.provider().collect(
            "What version are you?"
        )

        self.assertIsNotNone(
            context.direct_answer
        )


if __name__ == "__main__":
    unittest.main()
