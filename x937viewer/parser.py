"""X9.37 / Image Cash Letter parser.

Supports the same on-disk variants as moov-io/imagecashletter:

* variable line length (4-byte big-endian record length prefixes), EBCDIC or ASCII
* fixed 80-byte records, EBCDIC or ASCII, with or without CR/LF separators

The parser is deliberately lenient: malformed field values are kept verbatim
and reported through ``X937File.warnings`` instead of raising, because a
viewer should be able to open imperfect files.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

from . import records as R

EBCDIC = "cp037"
ASCII = "latin-1"  # tolerant superset of ASCII


class X937Error(Exception):
    """Raised when a file cannot be recognised as X9.37 at all."""


# --------------------------------------------------------------------------- model


@dataclass
class X937File:
    """Parsed file. ``data`` mirrors the Moov JSON structure (dicts/lists),
    except that image/signature payloads are raw ``bytes`` until exported."""

    data: dict = field(default_factory=dict)
    encoding: str = ASCII          # source character encoding
    variable_length: bool = False  # had 4-byte length prefixes
    warnings: List[str] = field(default_factory=list)
    source_path: Optional[str] = None

    # -- convenience accessors -------------------------------------------------
    def cash_letters(self) -> list:
        return self.data.get("cashLetters") or []

    def all_items(self) -> list:
        """Flat list of (cash_letter, bundle, item, kind) for checks and returns."""
        out = []
        for cl in self.cash_letters():
            for b in cl.get("bundles") or []:
                for c in b.get("checks") or []:
                    out.append((cl, b, c, "check"))
                for r in b.get("returns") or []:
                    out.append((cl, b, r, "return"))
        return out

    def item_count(self) -> int:
        return len(self.all_items())


# --------------------------------------------------------------------------- helpers


def _to_int(text: str, warnings: List[str], what: str) -> int:
    text = text.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        warnings.append(f"{what}: non-numeric value {text!r}, using 0")
        return 0


def _to_date(text: str) -> str:
    text = text.strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}T00:00:00Z"
    return "0001-01-01T00:00:00Z"  # Go zero time


def _to_time(text: str) -> str:
    text = text.strip()
    if len(text) == 4 and text.isdigit():
        return f"0000-01-01T{text[0:2]}:{text[2:4]}:00Z"
    return "0000-01-01T00:00:00Z"


def parse_fields(layout, text: str, warnings: List[str], rname: str) -> dict:
    """Slice ``text`` according to ``layout`` and convert kinds."""
    out = {"id": ""}
    pos = 0
    for key, length, kind in layout:
        raw = text[pos:pos + length]
        pos += length
        if kind == "x" or key is None:
            continue
        if kind == "s":
            out[key] = raw.strip()
        elif kind == "n":
            out[key] = _to_int(raw, warnings, f"{rname}.{key}")
        elif kind == "d":
            out[key] = _to_date(raw)
        elif kind == "t":
            out[key] = _to_time(raw)
    return out


# --------------------------------------------------------------------------- framing


def _sniff(data: bytes):
    """Return (variable_length, encoding)."""
    if len(data) < 6:
        raise X937Error("file too short to be an X9.37 file")
    (prefix,) = struct.unpack(">I", data[:4])
    if 0 < prefix <= len(data) - 4:
        if data[4:6] == b"01":
            return True, ASCII
        if data[4:6] == b"\xf0\xf1":
            return True, EBCDIC
    if data[0:2] == b"01":
        return False, ASCII
    if data[0:2] == b"\xf0\xf1":
        return False, EBCDIC
    raise X937Error(
        "unrecognized X9.37 framing: file does not start with a File Header "
        "record in ASCII or EBCDIC, with or without length prefixes"
    )


def _iter_records_variable(data: bytes, warnings: List[str]):
    """Yield raw record bytes from a length-prefixed file."""
    i, n = 0, len(data)
    while i < n:
        if n - i < 4:
            warnings.append(f"trailing {n - i} byte(s) ignored at end of file")
            return
        (length,) = struct.unpack(">I", data[i:i + 4])
        i += 4
        if length == 0:
            warnings.append(f"zero-length record at offset {i - 4}; stopping")
            return
        if i + length > n:
            warnings.append(
                f"record at offset {i - 4} claims {length} bytes but only "
                f"{n - i} remain; keeping the partial record")
            length = n - i
        yield data[i:i + length]
        i += length


def _iter_records_fixed(data: bytes, encoding: str, warnings: List[str]):
    """Yield raw record bytes from a fixed-80 file (optionally newline separated).

    Record 52 carries binary image data whose size is declared in-band, so it
    is reassembled from the declared lengths rather than assumed to be 80 bytes.
    """
    rec52 = "52".encode(EBCDIC) if encoding == EBCDIC else b"52"
    i, n = 0, len(data)
    while i < n:
        # skip record separators
        while i < n and data[i:i + 1] in (b"\r", b"\n"):
            i += 1
        if i >= n:
            return
        if data[i:i + 2] == rec52:
            # head through lengthImageReferenceKey = 2 + 103 = 105 chars
            head = data[i:i + 105]
            if len(head) < 105:
                warnings.append("truncated Image View Data record at end of file")
                yield data[i:]
                return
            try:
                l_key = int(head[101:105].decode(encoding).strip() or 0)
                p = i + 105 + l_key
                l_sig = int(data[p:p + 5].decode(encoding).strip() or 0)
                p += 5 + l_sig
                l_img = int(data[p:p + 7].decode(encoding).strip() or 0)
                p += 7 + l_img
            except (ValueError, UnicodeDecodeError):
                warnings.append(
                    f"could not read image lengths in record 52 at offset {i}; "
                    "assuming 80-byte record")
                p = i + 80
            yield data[i:min(p, n)]
            i = p
        else:
            yield data[i:i + 80]
            i += 80


# --------------------------------------------------------------------------- record decoding


def _decode_record(raw: bytes, encoding: str, warnings: List[str]):
    """Return (record_type, text_or_none, raw). For record 52 text is the head only."""
    try:
        rtype = raw[:2].decode(encoding)
    except UnicodeDecodeError:
        return None, None, raw
    return rtype, raw, raw


def _parse_record_52(raw: bytes, encoding: str, warnings: List[str]) -> dict:
    """Variable-structure Image View Data record."""
    out = {"id": ""}
    head = raw[2:105].decode(encoding, errors="replace")
    out.update(parse_fields(R.IMAGE_VIEW_DATA_HEAD, head, warnings, "imageViewData"))
    out.pop("id", None)
    out = {"id": "", **out}

    def _length(text: str, what: str) -> int:
        return _to_int(text, warnings, what)

    p = 105
    l_key = _length(out.get("lengthImageReferenceKey", "0"), "imageViewData.lengthImageReferenceKey")
    out["imageReferenceKey"] = raw[p:p + l_key].decode(encoding, errors="replace").strip()
    p += l_key

    len_sig_text = raw[p:p + 5].decode(encoding, errors="replace")
    out["lengthDigitalSignature"] = len_sig_text.strip()
    l_sig = _length(len_sig_text, "imageViewData.lengthDigitalSignature")
    p += 5
    out["digitalSignature"] = bytes(raw[p:p + l_sig])  # bytes -> base64 at export
    p += l_sig

    len_img_text = raw[p:p + 7].decode(encoding, errors="replace")
    out["lengthImageData"] = len_img_text.strip()
    l_img = _length(len_img_text, "imageViewData.lengthImageData")
    p += 7
    img = bytes(raw[p:p + l_img])
    if len(img) != l_img:
        warnings.append(
            f"imageViewData: declared image length {l_img} but record holds {len(img)} bytes")
    out["imageData"] = img
    return out


def _parse_addendum_b(raw_text: str, warnings: List[str], rname: str) -> dict:
    """Records 27 / 34: variable imageReferenceKey in the middle."""
    out = {"id": ""}
    out.update(parse_fields(R.ADDENDUM_B_HEAD, raw_text, warnings, rname))
    head_len = sum(l for _, l, _ in R.ADDENDUM_B_HEAD)
    l_key = _to_int(out.get("imageReferenceKeyLength", "0"), warnings, f"{rname}.imageReferenceKeyLength")
    out["imageReferenceKey"] = raw_text[head_len:head_len + l_key].strip()
    tail = parse_fields(R.ADDENDUM_B_TAIL, raw_text[head_len + l_key:], warnings, rname)
    tail.pop("id", None)
    out.update(tail)
    return out


def _new_item(detail: dict, kind: str) -> dict:
    """Attach the repeated-group keys Moov always serializes on items."""
    if kind == "check":
        detail["checkDetailAddendumA"] = []
        detail["checkDetailAddendumB"] = []
        detail["checkDetailAddendumC"] = []
    else:
        detail["returnDetailAddendumA"] = []
        detail["returnDetailAddendumB"] = []
        detail["returnDetailAddendumC"] = []
        detail["returnDetailAddendumD"] = []
    detail["imageViewDetail"] = []
    detail["imageViewData"] = []
    detail["imageViewAnalysis"] = []
    return detail


# --------------------------------------------------------------------------- main parse


def parse_bytes(data: bytes, source_path: Optional[str] = None) -> X937File:
    variable, encoding = _sniff(data)
    f = X937File(encoding=encoding, variable_length=variable, source_path=source_path)
    w = f.warnings

    file_dict = {"id": "", "fileHeader": None, "cashLetters": [], "fileControl": None}
    f.data = file_dict

    cl = None        # current cash letter
    bundle = None    # current bundle
    item = None      # current check or return dict
    item_kind = None

    if variable:
        record_iter = _iter_records_variable(data, w)
    else:
        record_iter = _iter_records_fixed(data, encoding, w)

    for raw in record_iter:
        try:
            rtype = raw[:2].decode(encoding)
        except UnicodeDecodeError:
            w.append("record with undecodable type skipped")
            continue

        if rtype == "52":
            if item is None:
                w.append("Image View Data (52) found outside a check/return; skipped")
                continue
            item["imageViewData"].append(_parse_record_52(raw, encoding, w))
            continue

        text = raw[2:].decode(encoding, errors="replace")
        rname = R.RECORD_NAMES.get(rtype, rtype)

        if rtype == "01":
            file_dict["fileHeader"] = parse_fields(R.FILE_HEADER, text, w, rname)
        elif rtype == "10":
            cl = {"id": "", "cashLetterHeader": parse_fields(R.CASH_LETTER_HEADER, text, w, rname),
                  "bundles": [], "credits": [], "creditItems": [], "routingNumberSummary": [],
                  "cashLetterControl": None}
            file_dict["cashLetters"].append(cl)
            bundle = item = None
        elif rtype == "20":
            if cl is None:
                w.append("Bundle Header (20) before any Cash Letter Header; creating implicit cash letter")
                cl = {"id": "", "cashLetterHeader": {"id": ""}, "bundles": [], "credits": [],
                      "creditItems": [], "routingNumberSummary": [], "cashLetterControl": None}
                file_dict["cashLetters"].append(cl)
            bundle = {"id": "", "bundleHeader": parse_fields(R.BUNDLE_HEADER, text, w, rname),
                      "checks": [], "returns": [], "bundleControl": None}
            cl["bundles"].append(bundle)
            item = None
        elif rtype == "25":
            if bundle is None:
                w.append("Check Detail (25) outside a bundle; skipped")
                continue
            item = _new_item(parse_fields(R.CHECK_DETAIL, text, w, rname), "check")
            item_kind = "check"
            bundle["checks"].append(item)
        elif rtype == "31":
            if bundle is None:
                w.append("Return Detail (31) outside a bundle; skipped")
                continue
            item = _new_item(parse_fields(R.RETURN_DETAIL, text, w, rname), "return")
            item_kind = "return"
            bundle["returns"].append(item)
        elif rtype in ("26", "32"):
            key = "checkDetailAddendumA" if item_kind == "check" else "returnDetailAddendumA"
            if item is None:
                w.append(f"{rname} outside an item; skipped")
                continue
            item[key].append(parse_fields(R.CHECK_DETAIL_ADDENDUM_A, text, w, rname))
        elif rtype in ("27", "34"):
            if item is None:
                w.append(f"{rname} outside an item; skipped")
                continue
            key = "checkDetailAddendumB" if rtype == "27" else "returnDetailAddendumC"
            item[key].append(_parse_addendum_b(text, w, rname))
        elif rtype == "33":
            if item is None or item_kind != "return":
                w.append("Return Detail Addendum B (33) outside a return; skipped")
                continue
            item["returnDetailAddendumB"].append(
                parse_fields(R.RETURN_DETAIL_ADDENDUM_B, text, w, rname))
        elif rtype in ("28", "35"):
            key = "checkDetailAddendumC" if rtype == "28" else "returnDetailAddendumD"
            if item is None:
                w.append(f"{rname} outside an item; skipped")
                continue
            item[key].append(parse_fields(R.CHECK_DETAIL_ADDENDUM_C, text, w, rname))
        elif rtype == "50":
            if item is None:
                w.append("Image View Detail (50) outside an item; skipped")
                continue
            item["imageViewDetail"].append(parse_fields(R.IMAGE_VIEW_DETAIL, text, w, rname))
        elif rtype == "54":
            if item is None:
                w.append("Image View Analysis (54) outside an item; skipped")
                continue
            item["imageViewAnalysis"].append(parse_fields(R.IMAGE_VIEW_ANALYSIS, text, w, rname))
        elif rtype == "61":
            if cl is None:
                w.append("Credit (61) outside a cash letter; skipped")
                continue
            cl["credits"].append(parse_fields(R.CREDIT, text, w, rname))
        elif rtype == "62":
            if cl is None:
                w.append("Credit Item (62) outside a cash letter; skipped")
                continue
            cl["creditItems"].append(parse_fields(R.CREDIT_ITEM, text, w, rname))
        elif rtype == "85":
            if cl is None:
                w.append("Routing Number Summary (85) outside a cash letter; skipped")
                continue
            cl["routingNumberSummary"].append(
                parse_fields(R.ROUTING_NUMBER_SUMMARY, text, w, rname))
        elif rtype == "70":
            if bundle is None:
                w.append("Bundle Control (70) outside a bundle; skipped")
                continue
            bundle["bundleControl"] = parse_fields(R.BUNDLE_CONTROL, text, w, rname)
            bundle = None
            item = None
        elif rtype == "90":
            if cl is None:
                w.append("Cash Letter Control (90) outside a cash letter; skipped")
                continue
            cl["cashLetterControl"] = parse_fields(R.CASH_LETTER_CONTROL, text, w, rname)
            cl = None
            bundle = item = None
        elif rtype == "99":
            file_dict["fileControl"] = parse_fields(R.FILE_CONTROL, text, w, rname)
        elif rtype == "68":
            w.append("User record (68) kept raw (not interpreted)")
        else:
            w.append(f"unknown record type {rtype!r} skipped")

    if file_dict["fileHeader"] is None:
        raise X937Error("no File Header (01) record found")
    return f


def parse_file(path: str) -> X937File:
    with open(path, "rb") as fh:
        return parse_bytes(fh.read(), source_path=path)
