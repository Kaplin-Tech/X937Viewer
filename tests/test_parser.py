"""Acceptance tests: parser output must match moov-io/imagecashletter.

Run from the repository root:  python -m unittest discover tests -v
"""

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from x937viewer import parse_file, to_json, to_json_obj  # noqa: E402
from x937viewer.parser import parse_bytes, X937Error  # noqa: E402

EXAMPLE = os.path.join(ROOT, "Example")
MOOV = os.path.join(EXAMPLE, "moov")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class ParserAcceptance(unittest.TestCase):
    """Deep-compare against JSON produced by Moov's imagecashletter."""

    def assert_matches(self, x937_path, json_path):
        f = parse_file(x937_path)
        self.assertEqual(f.warnings, [], "parse warnings")
        self.assertEqual(to_json_obj(f), load_json(json_path))

    def test_ebcdic_example_matches_moov_demo_output(self):
        self.assert_matches(os.path.join(EXAMPLE, "iclFile.x937"),
                            os.path.join(EXAMPLE, "validation.json"))

    def test_ebcdic_example_matches_upstream_reference(self):
        self.assert_matches(os.path.join(EXAMPLE, "iclFile.x937"),
                            os.path.join(MOOV, "valid-x937.json"))

    def test_ascii_variant(self):
        self.assert_matches(os.path.join(MOOV, "valid-ascii.x937"),
                            os.path.join(MOOV, "valid-x937.json"))

    def test_byte_identical_serialization(self):
        """Our JSON text should match Moov's reference byte for byte."""
        f = parse_file(os.path.join(MOOV, "valid-ascii.x937"))
        with open(os.path.join(MOOV, "valid-x937.json"), encoding="utf-8") as fh:
            ref = fh.read()
        self.assertEqual(to_json(f), ref.rstrip("\n"))


class ReturnsAndLeniency(unittest.TestCase):
    def test_returns_file(self):
        f = parse_file(os.path.join(MOOV, "BNK20180905121042882-A.icl"))
        self.assertEqual(f.warnings, [])
        self.assertEqual(len(f.cash_letters()), 2)
        kinds = [k for _, _, _, k in f.all_items()]
        self.assertEqual(kinds.count("check"), 4)
        self.assertEqual(kinds.count("return"), 4)
        ret = f.data["cashLetters"][0]["bundles"][1]["returns"][0]
        self.assertEqual(ret["returnReason"], "A")
        self.assertEqual(ret["itemAmount"], 100000)
        self.assertEqual(len(ret["returnDetailAddendumA"]), 1)
        self.assertEqual(len(ret["returnDetailAddendumD"]), 1)
        self.assertEqual(ret["returnDetailAddendumB"][0]["payorBankName"], "Payor Bank Name")

    def test_without_micr_valid_indicator(self):
        f = parse_file(os.path.join(MOOV, "without-micrValidIndicator.icl"))
        check = f.data["cashLetters"][0]["bundles"][0]["checks"][0]
        self.assertEqual(check["micrValidIndicator"], 0)

    def test_images_extracted(self):
        f = parse_file(os.path.join(EXAMPLE, "iclFile.x937"))
        check = f.data["cashLetters"][0]["bundles"][0]["checks"][0]
        front, back = check["imageViewData"]
        self.assertEqual(len(front["imageData"]), 7408)
        self.assertEqual(len(back["imageData"]), 8646)
        self.assertTrue(front["imageData"].startswith(b"II*\x00"))  # little-endian TIFF

    def test_garbage_rejected(self):
        with self.assertRaises(X937Error):
            parse_bytes(b"this is not an icl file at all..........")

    def test_truncated_file_warns_not_crashes(self):
        with open(os.path.join(EXAMPLE, "iclFile.x937"), "rb") as fh:
            data = fh.read()
        f = parse_bytes(data[: len(data) // 2])
        self.assertTrue(f.warnings)


class RoundTrip(unittest.TestCase):
    def test_json_reload_is_stable(self):
        f = parse_file(os.path.join(EXAMPLE, "iclFile.x937"))
        once = to_json(f)
        again = json.dumps(json.loads(once), indent=4)
        self.assertEqual(once, again)


if __name__ == "__main__":
    unittest.main()
