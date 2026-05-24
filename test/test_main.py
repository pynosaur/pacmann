"""Tests for pacmann."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import __version__


class TestVersion(unittest.TestCase):
    def test_version_format(self):
        parts = __version__.split('.')
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertTrue(p.isdigit())

    def test_version_matches_program(self):
        program = ROOT / '.program'
        text = program.read_text()
        for line in text.splitlines():
            if line.startswith('version:'):
                v = line.split(':', 1)[1].strip()
                self.assertEqual(v, __version__)
                break
        else:
            self.fail('.program has no version field')

    def test_version_matches_doc(self):
        doc = ROOT / 'doc' / 'pacmann.yaml'
        text = doc.read_text()
        for line in text.splitlines():
            if line.startswith('VERSION:'):
                v = line.split(':', 1)[1].strip()
                self.assertEqual(v, __version__)
                break
        else:
            self.fail('doc/pacmann.yaml has no VERSION field')


class TestCLI(unittest.TestCase):
    def test_help(self):
        r = subprocess.run(
            [sys.executable, '-m', 'app.main', '--help'],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn('pacmann', r.stdout)
        self.assertIn('Toru Iwatani', r.stdout)

    def test_version(self):
        r = subprocess.run(
            [sys.executable, '-m', 'app.main', '--version'],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn(__version__, r.stdout.strip())


class TestMaze(unittest.TestCase):
    def test_parse_counts(self):
        from app.main import _parse, ORIGINAL_MAZE, MW, MH
        walls, dots, energizers, doors, pac_start = _parse()
        self.assertEqual(len(energizers), 4)
        self.assertGreater(len(dots), 200)
        self.assertGreater(len(walls), 400)
        self.assertEqual(pac_start, (13, 23))
        self.assertEqual(len(ORIGINAL_MAZE), MH)
        for row in ORIGINAL_MAZE:
            self.assertEqual(len(row), MW)


if __name__ == '__main__':
    unittest.main()
