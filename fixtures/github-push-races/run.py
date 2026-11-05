import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest


source = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location(
    "publisher_regressions", source / "tests/test_dependabot_rebuild_dist.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
token = os.environ.pop("RACE_TOKEN", "")
repository = os.environ["GITHUB_REPOSITORY"]
run_id = os.environ["GITHUB_RUN_ID"]
attempt = os.environ["GITHUB_RUN_ATTEMPT"]
if not token:
    sys.exit("The scratch-branch publishing token is unavailable.")
if repository != "v-chiranjib-swain/setup-node-test":
    sys.exit("Harness restricted to the disposable setup-node-test repository.")
if not re.fullmatch(r"\d+", run_id) or not re.fullmatch(r"\d+", attempt):
    sys.exit("Invalid GitHub run identity.")


class GitHubRaces(module.WorkflowTests):
    def setUp(self):
        super().setUp()
        self.branch = f"test/dist-races-{run_id}-{attempt}-{self._testMethodName}"
        self.url = f"https://github.com/{repository}.git"
        self.askpass = self.root / "race-askpass"
        self.askpass.write_text(
            '#!/bin/sh\ncase "$1" in\n'
            ' *Username*) printf "%s\\n" x-access-token ;;\n'
            ' *Password*) printf "%s\\n" "$RACE_GIT_TOKEN" ;;\n'
            ' *) exit 1 ;;\nesac\n'
        )
        self.askpass.chmod(0o700)
        self.auth = os.environ | {
            "RACE_GIT_TOKEN": token,
            "GIT_ASKPASS": str(self.askpass),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "",
        }
        self.assertEqual(
            self.transport("ls-remote", self.url, f"refs/heads/{self.branch}"),
            "",
            "Scratch branch already exists; refusing to modify it.",
        )
        self.git("remote", "set-url", "origin", self.url)
        self.addCleanup(self.delete_scratch_branch)
        self.transport("push", "origin", f"{self.sha}:refs/heads/{self.branch}")
        self.env.update({
            "PUBLISH_TOKEN": token,
            "HEAD_REF": self.branch,
            "REPOSITORY": repository,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "",
        })
        self.pr["head"]["ref"] = self.branch
        self.pr["head"]["repo"]["full_name"] = repository
        self.changed_archive()

    def transport(self, *arguments):
        result = module.REAL_RUN(
            ["git", *arguments],
            cwd=self.repo,
            env=self.auth,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotIn(token, result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f"Scratch Git operation failed: {result.stderr}")
        return result.stdout.strip()

    def remote_sha(self):
        result = self.transport("ls-remote", self.url, f"refs/heads/{self.branch}")
        self.assertTrue(result, "Scratch branch unexpectedly missing.")
        return result.split()[0]

    def delete_scratch_branch(self):
        existing = self.transport("ls-remote", self.url, f"refs/heads/{self.branch}")
        if existing:
            sha = existing.split()[0]
            self.transport(
                "push",
                f"--force-with-lease=refs/heads/{self.branch}:{sha}",
                "origin",
                f":refs/heads/{self.branch}",
            )
        self.assertEqual(
            self.transport("ls-remote", self.url, f"refs/heads/{self.branch}"), ""
        )
        print(f"Deleted scratch branch {self.branch}", flush=True)

    def reject_after_mutation(self, mutate, expected):
        fired = False

        def intercept(arguments, kwargs):
            nonlocal fired
            if arguments[0] == "git" and "push" in arguments and not fired:
                fired = True
                mutate()

        status, output = self.run_script(module.PUBLISH, intercept=intercept)
        self.assertTrue(fired)
        self.assertNotEqual(status, 0, output)
        self.assertIn(expected, output)
        self.assertNotIn(token, output)
        pushes = [call for call in self.calls if call[0] == "git" and "push" in call]
        self.assertEqual(len(pushes), 1, "Rejected publisher must not retry.")

    def test_ancestor_reset(self):
        def reset():
            self.transport(
                "push",
                f"--force-with-lease=refs/heads/{self.branch}:{self.sha}",
                "origin",
                f"{self.ancestor}:refs/heads/{self.branch}",
            )

        self.reject_after_mutation(reset, "Remote branch no longer matches the built SHA")
        self.assertEqual(self.remote_sha(), self.ancestor)
        print("PASS ancestor reset: stale push rejected; ancestor preserved.", flush=True)

    def test_forward_update(self):
        newer = self.git(
            "commit-tree", f"{self.sha}^{{tree}}", "-p", self.sha, "-m", "Race forward update"
        ).strip()
        self.reject_after_mutation(
            lambda: self.transport("push", "origin", f"{newer}:refs/heads/{self.branch}"),
            "branch changed during publication",
        )
        self.assertEqual(self.remote_sha(), newer)
        print("PASS forward update: stale push rejected; newer commit preserved.", flush=True)

    def test_competing_publishers(self):
        second = self.root / "second"
        self.git("clone", str(self.repo), str(second))
        self.git("switch", "--detach", self.sha, cwd=second)
        self.git("remote", "set-url", "origin", self.url, cwd=second)
        winner = None

        def publish_second():
            nonlocal winner
            original_repo = self.repo
            original_calls = self.calls
            self.repo = second
            self.calls = []
            try:
                status, output = self.run_script(
                    module.PUBLISH,
                    overrides={"GIT_COMMITTER_DATE": "2001-01-01T00:00:00+00:00"},
                )
                self.assertEqual(status, 0, output)
                self.assertNotIn(token, output)
                winner = self.remote_sha()
            finally:
                self.repo = original_repo
                self.calls = original_calls

        self.reject_after_mutation(publish_second, "branch changed during publication")
        self.assertIsNotNone(winner)
        self.assertNotEqual(winner, self.sha)
        self.assertEqual(self.remote_sha(), winner)
        print("PASS competing publishers: second wins; first rejected without retry.", flush=True)


suite = unittest.TestSuite(
    GitHubRaces(name)
    for name in ("test_ancestor_reset", "test_forward_update", "test_competing_publishers")
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
