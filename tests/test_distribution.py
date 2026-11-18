"""Distribution: make install, uninstall and dist (skipped without make), install.sh from an unpacked tarball, the Homebrew
formula script and formula, the VS Code tasks file, the release workflow's tarball steps, and shellcheck of the new
scripts. Run: python3 -m unittest discover -s tests. Names and data are made up.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from helpers import BASH, REPO, pkm_env, run_pkm

VERSION = (REPO / "VERSION").read_text().strip()
PACKED = ["bin", "lib", "share", "install.sh", "LICENSE", "README.md", "CHANGELOG.md", "VERSION"]


def tarball_of(folder, dest):
    """A tarball laid out like make dist's: a pkm-<version>/ top folder with the packed files."""
    with tarfile.open(dest, "w:gz") as archive:
        for name in PACKED:
            archive.add(REPO / name, arcname=f"pkm-{VERSION}/{name}")
    return dest


class Makefile(unittest.TestCase):
    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_install_links_pkm_and_the_link_runs_from_another_folder(self):
        with tempfile.TemporaryDirectory() as prefix, tempfile.TemporaryDirectory() as elsewhere:
            subprocess.run(["make", "-C", str(REPO), "install", f"PREFIX={prefix}"], check=True, capture_output=True)
            link = pathlib.Path(prefix, "bin/pkm")
            self.assertTrue(link.is_symlink())
            self.assertEqual(os.readlink(link), f"{prefix}/lib/pkm-{VERSION}/bin/pkm")
            result = subprocess.run([str(link), "version"], cwd=elsewhere, capture_output=True, text=True)
            self.assertEqual(result.stdout.strip(), VERSION, result.stderr)
            doctor = subprocess.run([str(link), "doctor"], cwd=elsewhere, capture_output=True, text=True,
                                    env=pkm_env())
            self.assertIn("rg", doctor.stdout)

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_uninstall_removes_what_install_made_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as prefix:
            subprocess.run(["make", "-C", str(REPO), "install", f"PREFIX={prefix}"], check=True, capture_output=True)
            other = pathlib.Path(prefix, "bin/other")
            other.write_text("keep me\n")
            subprocess.run(["make", "-C", str(REPO), "uninstall", f"PREFIX={prefix}"], check=True, capture_output=True)
            self.assertFalse(pathlib.Path(prefix, "lib", f"pkm-{VERSION}").exists())
            self.assertFalse(pathlib.Path(prefix, "bin/pkm").is_symlink())
            self.assertEqual(other.read_text(), "keep me\n")

    @unittest.skipUnless(shutil.which("make"), "make is not installed")
    def test_dist_writes_the_tarball_with_its_checksum_and_the_packed_files(self):
        with tempfile.TemporaryDirectory() as dist:
            subprocess.run(["make", "-C", str(REPO), "dist", f"DIST={dist}"], check=True, capture_output=True)
            tarball = pathlib.Path(dist, f"pkm-{VERSION}.tar.gz")
            checksum = pathlib.Path(dist, f"pkm-{VERSION}.tar.gz.sha256").read_text()
            self.assertEqual(checksum.split()[0], hashlib.sha256(tarball.read_bytes()).hexdigest())
            with tarfile.open(tarball) as archive:
                names = archive.getnames()
            for name in PACKED:
                self.assertIn(f"pkm-{VERSION}/{name}", names)
            self.assertIn(f"pkm-{VERSION}/bin/pkm", names)
            self.assertFalse([n for n in names if "/tests/" in n or "/packaging/" in n], names)

    def test_make_check_runs_the_checks_and_the_tests(self):
        text = (REPO / "Makefile").read_text()
        self.assertRegex(text, r"(?m)^check:\n\tpython3 scripts/check\.py\n\tpython3 -m unittest discover -s tests")


class InstallScript(unittest.TestCase):
    def test_install_sh_downloads_nothing(self):
        self.assertNotRegex((REPO / "install.sh").read_text(), r"\b(curl|wget|git clone)\b")

    def test_install_from_an_unpacked_tarball_then_version_and_doctor(self):
        with tempfile.TemporaryDirectory() as work:
            work = pathlib.Path(work)
            tarball = tarball_of(REPO, work / f"pkm-{VERSION}.tar.gz")
            with tarfile.open(tarball) as archive:
                archive.extractall(work, filter="data") if hasattr(tarfile, "data_filter") else archive.extractall(work)
            prefix = work / "prefix"
            install = subprocess.run(["sh", str(work / f"pkm-{VERSION}/install.sh"), "--prefix", str(prefix)],
                                     capture_output=True, text=True, env=pkm_env())
            self.assertIn(str(prefix), install.stdout)
            self.assertIn("PATH", install.stdout)
            pkm = str(prefix / "bin/pkm")
            version = subprocess.run([pkm, "version"], capture_output=True, text=True, cwd=work)
            self.assertEqual(version.stdout.strip(), VERSION, version.stderr)
            doctor = subprocess.run([pkm, "doctor"], capture_output=True, text=True, cwd=work, env=pkm_env())
            self.assertIn("rg", doctor.stdout)


class Formula(unittest.TestCase):
    def test_formula_script_fills_the_url_and_checksum_from_a_tarball(self):
        with tempfile.TemporaryDirectory() as work:
            work = pathlib.Path(work)
            tarball = tarball_of(REPO, work / f"pkm-{VERSION}.tar.gz")
            out = work / "pkm.rb"
            subprocess.run(["sh", str(REPO / "scripts/formula.sh"), str(tarball), str(out)], check=True,
                           capture_output=True)
            text = out.read_text()
            self.assertIn(f'url "https://github.com/Zejnilovic/scripts-pkms/releases/download/v{VERSION}/pkm-{VERSION}.tar.gz"', text)
            self.assertIn(f'sha256 "{hashlib.sha256(tarball.read_bytes()).hexdigest()}"', text)
            self.assertNotIn("PLACEHOLDER", text)

    def test_the_formula_has_the_dependencies_and_a_test(self):
        text = (REPO / "packaging/pkm.rb").read_text()
        for line in ['depends_on "ripgrep"', 'depends_on "jq"', "test do", 'pkm version', 'sha256 "PLACEHOLDER']:
            self.assertIn(line, text)

    @unittest.skipUnless(shutil.which("ruby"), "ruby is not installed")
    def test_the_formula_is_valid_ruby(self):
        result = subprocess.run(["ruby", "-c", str(REPO / "packaging/pkm.rb")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class EditorTasks(unittest.TestCase):
    PATH = REPO / "share/pkm/editors/vscode/tasks.json"

    def test_tasks_json_is_valid_and_has_the_pkm_tasks(self):
        data = json.loads(self.PATH.read_text())
        commands = {task["label"]: task.get("args") for task in data["tasks"]}
        self.assertEqual(commands["pkm: day"], ["day"])
        self.assertEqual(commands["pkm: tasks"], ["tasks"])
        self.assertEqual(commands["pkm: check"], ["check"])
        self.assertEqual(commands["pkm: add"], ["add", "${input:entry}"])
        self.assertTrue({i["id"] for i in data["inputs"]} >= {"entry", "words"})

    def test_the_problem_matcher_reads_path_line_text(self):
        data = json.loads(self.PATH.read_text())
        pattern = data["problemMatchers"][0]["pattern"]
        regex = re.compile(pattern["regexp"])
        for sample in ["notes/apollo.md:31: Risk: budget", "- notes/apollo.md:31: no answer: http://x"]:
            match = regex.match(sample)
            self.assertIsNotNone(match, sample)
            self.assertEqual(match.group(pattern["file"]), "notes/apollo.md")
            self.assertEqual(match.group(pattern["line"]), "31")


class ReleaseWorkflow(unittest.TestCase):
    def steps(self):
        text = (REPO / ".github/workflows/release.yml").read_text()
        return text.split("\n      - name: ")[1:]

    def step_named(self, name):
        return [step for step in self.steps() if step.startswith(name)]

    def test_the_tarball_is_built_after_the_release_in_every_run(self):
        names = [step.split("\n")[0] for step in self.steps()]
        self.assertLess(names.index("Create the GitHub release"), names.index("Build the tarball"))
        build = self.step_named("Build the tarball")[0]
        self.assertIn("run: make dist", build)
        self.assertNotIn("if:", build)

    def test_the_formula_is_written_from_the_tarball_and_pushed_to_the_tap_only_on_a_real_release(self):
        names = [step.split("\n")[0] for step in self.steps()]
        self.assertLess(names.index("Build the tarball"), names.index("Write the formula"))
        write = self.step_named("Write the formula")[0]
        self.assertNotIn("if:", write)
        self.assertIn("Zejnilovic/homebrew-tap", write)
        self.assertIn('sh scripts/formula.sh "dist/pkm-$VERSION.tar.gz"', write)
        push = self.step_named("Update the formula in the tap")[0]
        self.assertIn("if: ${{ !inputs.dry_run }}", push)
        self.assertIn("secrets.HOMEBREW_TAP_TOKEN", push)
        self.assertLess(names.index("Attach the tarball to the release"), names.index("Update the formula in the tap"))

    def test_a_job_installs_the_release_from_the_tap_and_tests_it(self):
        text = (REPO / ".github/workflows/release.yml").read_text()
        verify = text.split("\n  verify:\n")[1]
        self.assertIn("needs: release", verify)
        self.assertIn("if: ${{ !inputs.dry_run }}", verify)
        for line in ["brew install zejnilovic/tap/pkm", "brew test zejnilovic/tap/pkm", "brew audit --strict --online zejnilovic/tap/pkm"]:
            self.assertIn(line, verify)

    def test_the_tarball_and_its_checksum_are_attached_only_on_a_real_release(self):
        upload = self.step_named("Attach the tarball")[0]
        self.assertIn("if: ${{ !inputs.dry_run }}", upload)
        self.assertIn("gh release upload", upload)
        self.assertIn(".sha256", upload)


class Lint(unittest.TestCase):
    @unittest.skipUnless(shutil.which("shellcheck"), "shellcheck is not installed")
    def test_install_and_formula_scripts_are_shellcheck_clean(self):
        result = subprocess.run(["shellcheck", "install.sh", "scripts/formula.sh"], cwd=REPO, capture_output=True,
                                text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
