"""Tests for check --urls: one GET per address, at most 8 at once, each place reported, 404 and 410 and no answer
reported, other statuses answered, curl needed (exit 2 without it), and a plain check never runs curl. Uses a local
HTTP server and a closed port, never the internet. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import http.server
import os
import pathlib
import shutil
import socket
import stat
import tempfile
import threading
import unittest

from helpers import VaultCase, pkm_env, run_pkm

PATHS = {"/ok": 200, "/gone": 410, "/missing": 404, "/fail": 500, "/login": 200}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/moved":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        self.send_response(PATHS.get(self.path, 404))
        self.end_headers()

    def log_message(self, *args):
        pass


def closed_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class CheckUrls(VaultCase):
    def setUp(self):
        super().setUp()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.dead = closed_port()
        base = f"http://127.0.0.1:{self.port}"
        self.write("notes/links.md", "# Links\n\n"
                   f"- ok [x]({base}/ok)\n"
                   f"- gone {base}/gone\n"
                   f"- gone again {base}/gone\n"
                   f"- missing {base}/missing\n"
                   f"- closed http://127.0.0.1:{self.dead}/nothing\n"
                   f"- failing {base}/fail\n"
                   f"- moved {base}/moved\n")
        self.gone = f"{base}/gone"
        self.missing = f"{base}/missing"
        self.closed = f"http://127.0.0.1:{self.dead}/nothing"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    @unittest.skipUnless(shutil.which("curl"), "curl is not on PATH")
    def test_each_place_gets_its_404_410_or_no_answer(self):
        result = self.pkm("check", "--urls")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for line in [f"- notes/links.md:4: 410: {self.gone}",
                     f"- notes/links.md:5: 410: {self.gone}",
                     f"- notes/links.md:6: 404: {self.missing}",
                     f"- notes/links.md:7: no answer: {self.closed}"]:
            self.assertIn(line, result.stdout)

    @unittest.skipUnless(shutil.which("curl"), "curl is not on PATH")
    def test_other_statuses_count_as_answered(self):
        result = self.pkm("check", "--urls").stdout
        self.assertNotIn("notes/links.md:8:", result)
        self.assertNotIn("notes/links.md:3:", result)
        self.assertNotIn("notes/links.md:9:", result)

    def test_a_plain_check_makes_no_requests_and_is_clean(self):
        self.assertEqual(self.pkm("check").returncode, 0)


class CurlStub(VaultCase):
    """A curl on PATH that logs each call and answers 200, so the calls can be counted."""

    def setUp(self):
        super().setUp()
        self.stub_dir = pathlib.Path(tempfile.mkdtemp())
        self.log = self.stub_dir / "calls.log"
        script = self.stub_dir / "curl"
        script.write_text('#!/bin/sh\nfor a; do u=$a; done\necho "start $u" >> "$PKM_TEST_CURL_LOG"\n'
                          'sleep 0.3\necho "end $u" >> "$PKM_TEST_CURL_LOG"\necho 200\n')
        script.chmod(script.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        shutil.rmtree(self.stub_dir, ignore_errors=True)
        super().tearDown()

    def env(self):
        return {"PATH": f"{self.stub_dir}{os.pathsep}{os.environ['PATH']}", "PKM_TEST_CURL_LOG": str(self.log)}

    def test_a_plain_check_never_runs_curl(self):
        self.write("notes/links.md", "- http://example.test/a\n")
        result = self.pkm("check", env=self.env())
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_one_get_per_distinct_address(self):
        self.write("notes/links.md", "- http://example.test/a\n- http://example.test/a\n- http://example.test/b\n")
        self.assertEqual(self.pkm("check", "--urls", env=self.env()).returncode, 0)
        calls = [line for line in self.log.read_text().splitlines() if line.startswith("start ")]
        self.assertEqual(sorted(calls), ["start http://example.test/a", "start http://example.test/b"])

    def test_at_most_eight_requests_at_once(self):
        self.write("notes/links.md", "".join(f"- http://example.test/{i}\n" for i in range(12)))
        self.assertEqual(self.pkm("check", "--urls", env=self.env()).returncode, 0)
        running, most = 0, 0
        for line in self.log.read_text().splitlines():
            running += 1 if line.startswith("start ") else -1
            most = max(most, running)
        self.assertLessEqual(most, 8)
        self.assertGreater(most, 1)

    def test_without_curl_it_is_a_usage_error(self):
        self.write("notes/links.md", "- http://example.test/a\n")
        tools = pathlib.Path(tempfile.mkdtemp())
        try:
            for name in ["rg", "jq", "awk", "sed", "sort", "uniq", "cut", "grep", "tr", "wc", "head", "tail", "find",
                         "xargs", "mktemp", "cat", "mv", "cp", "rm", "mkdir", "date", "printf", "dirname", "basename",
                         "stat", "cmp", "tee", "sh", "bash", "git", "touch", "diff"]:
                found = shutil.which(name)
                if found:
                    (tools / name).symlink_to(found)
            environment = pkm_env(PKM_NOW="20261025143012", XDG_CONFIG_HOME=self.config_home, PATH=str(tools))
            result = run_pkm(["check", "--urls"], cwd=self.root, env=environment, vault=self.root)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("curl", result.stderr)
        finally:
            shutil.rmtree(tools, ignore_errors=True)

    def test_doctor_lists_curl_as_optional(self):
        self.assertIn("curl", self.pkm("doctor").stdout)


if __name__ == "__main__":
    unittest.main()
