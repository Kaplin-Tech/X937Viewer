# X937 Viewer — Implementation Plan

A self-contained, local Python desktop app for browsing X9.37 (Image Cash Letter) check files.
Parsing model and JSON output mimic [moov-io/imagecashletter](https://github.com/moov-io/imagecashletter).
No web server, no network — everything runs locally.

## Confirmed from `Example/`

- `iclFile.x937` is **EBCDIC** (cp037) with **4-byte big-endian record length prefixes** (variable line length mode — same as Moov's `ReadVariableLineLengthOption` + `ReadEbcdicEncodingOption`). It is byte-identical to Moov's `valid-ebcdic.x937`.
- `Example/moov/` holds additional upstream Moov test data (ASCII variant, returns file, reference JSON outputs), each SHA-verified against the upstream repo — see `Example/moov/README.md`.
- `validation.json` is Moov's exact output: camelCase keys, amounts in cents (int), dates as `2020-10-16T00:00:00Z`, absent addenda as `null`, image bytes base64 in `imageData` (TIFF, little-endian `II*\0`).
- Structure: `{id, fileHeader, cashLetters[ {id, cashLetterHeader, bundles[ {id, bundleHeader, checks[...], bundleControl} ], cashLetterControl} ], fileControl}`.

## Tech stack

| Piece | Choice | Why |
|---|---|---|
| GUI | **PySide6** (Qt 6) | Modern native look on Win 11, real table widget, splitters, image viewer |
| Images | **Pillow** | Decodes CCITT G4 TIFF check images → QPixmap |
| Parser | Pure stdlib | No deps needed for byte parsing / EBCDIC (`codecs` cp037) |
| Python | 3.10+ | dataclasses, match statements |

`requirements.txt`: `PySide6`, `Pillow`.

## Project layout

```
X937Viewer/
├── x937viewer/
│   ├── __init__.py
│   ├── __main__.py        # python -m x937viewer
│   ├── records.py         # field specs per record type (name, pos, len, type)
│   ├── parser.py          # framing, encoding detection, record → dict
│   ├── model.py           # File/CashLetter/Bundle/Check dataclasses
│   ├── json_export.py     # Moov-compatible JSON serialization
│   └── gui/
│       ├── main_window.py # window, menus, toolbar
│       ├── check_list.py  # table + search/filter
│       ├── detail_pane.py # metadata side pane
│       └── image_view.py  # front/back toggle, zoom, TIFF decode
├── tests/
│   └── test_parser.py     # parse Example file, compare to validation.json
├── Example/               # existing sample + Moov reference output
├── main.py                # convenience launcher
├── requirements.txt
├── README.md              # credits Moov's imagecashletter
└── LICENSE
```

## Parser design

**Framing / encoding auto-detection** (first 4–6 bytes):

- `00 00 00 50` prefix → variable-length records; record type byte `F0 F1` → EBCDIC, `30 31` → ASCII.
- No prefix, starts `30 31` ("01") → fixed 80-byte ASCII lines (Moov's default mode).
- Records 52 (Image View Data) carry binary TIFF — only the fixed header portion is character-decoded; image bytes stay raw.

**Record types supported** (same set as Moov):

| Type | Record | Type | Record |
|---|---|---|---|
| 01 | File Header | 50 | Image View Detail |
| 10 | Cash Letter Header | 52 | Image View Data |
| 20 | Bundle Header | 54 | Image View Analysis |
| 25 | Check Detail | 61/62 | Credit / Credit Item |
| 26/27/28 | Check Detail Addendum A/B/C | 70 | Bundle Control |
| 31 | Return Detail | 85 | Routing Number Summary |
| 32–35 | Return Addendum A–D | 90 | Cash Letter Control |
| 40 | Image View (returns path) | 99 | File Control |
| 68 | User General/Payee Endorsement | | |

Each record type is declared as a field table in `records.py` (offset, length, name, kind: alpha/numeric/amount/date/time/binary), so parsing is data-driven, not hand-coded per field. Unknown record types are kept raw and reported, never crash.

**Hierarchy assembly:** stream of records → state machine attaches 26/27/28 and 50/52/54 to the current check (record 25), checks to current bundle (20), bundles to current cash letter (10).

**Lenient mode:** bad field values are kept as-is with a warnings list shown in the GUI; a viewer should open imperfect files.

## JSON export — Moov compatibility rules

- Key names exactly match Moov's Go json tags (taken from `validation.json`).
- Amounts → int cents; counts → int; everything else → string, trailing/leading spaces trimmed per Moov behavior.
- Dates `YYYYMMDD` → `YYYY-MM-DDT00:00:00Z`; times merged where Moov does (e.g. businessDate + creationTime).
- Empty repeated groups → `null` (not `[]`); `id` fields → `""`.
- `imageData`/`digitalSignature` → base64.
- Export = File ▸ Export to JSON…, writes the whole file; pretty-printed.

**Acceptance tests:** `tests/test_parser.py` parses `Example/iclFile.x937` and deep-compares to `Example/validation.json` (key-order independent) — the definition of done for the parser. Additional cases: `Example/moov/valid-ascii.x937` → `valid-x937.json`, `without-micrValidIndicator.icl` (lenient parsing), and `BNK20180905121042882-A.icl` (returns records 31–35, multiple cash letters, no images).

## GUI design (PySide6)

```
┌──────────────────────────────────────────────────────────┐
│  Toolbar: [Open]  [Export JSON]   Search: [______] 🔍    │
├──────────────┬───────────────────────────┬───────────────┤
│ Check list   │   Check image             │ Metadata pane │
│ (table)      │   [Front | Back] toggle   │ (tree view)   │
│ seq | amount │   zoom / fit-width        │ check detail, │
│ routing      │   ◀ prev   next ▶         │ addenda,      │
│ account/onUs │                           │ image info    │
│ date         │                           │ bundle/letter │
├──────────────┴───────────────────────────┴───────────────┤
│ Status bar: file name · N checks · warnings              │
└──────────────────────────────────────────────────────────┘
```

- **Check list:** QTableView over all checks across all bundles/cash letters; columns: #, item amount ($x,xxx.xx), payor routing, onUs/account, sequence number, date. Sortable.
- **Search:** live filter on amount (accepts `1,234.56` or cents) and account/routing/onUs/sequence substrings.
- **Image view:** record 52 TIFF → Pillow → QPixmap; Front/Back segmented toggle (image views matched by `viewSideIndicator` on record 50); zoom in/out/fit; prev/next check buttons + arrow keys.
- **Metadata pane:** QTreeWidget grouped: Check Detail, Addendum A/B/C, Image View Detail/Data/Analysis, parent Bundle Header, Cash Letter Header, File Header.
- **Style:** Qt Fusion style + dark/light follows OS; spacing and a few stylesheet touches for a modern feel.
- Large files: parse on a worker thread with progress; images decoded lazily on selection.

## Milestones

1. **Parser core** — framing, EBCDIC/ASCII, all record tables, hierarchy. *Gate: acceptance test passes vs `validation.json`.*
2. **JSON export** — CLI-callable too (`python -m x937viewer --to-json file.x937`).
3. **GUI shell** — window, open file, check table, metadata pane.
4. **Image rendering** — front/back toggle, zoom, navigation.
5. **Search + polish** — filtering, warnings display, keyboard shortcuts, icon.
6. **Docs** — README (features, screenshots, install, usage, credit to Moov's imagecashletter as the basis/reference implementation), Apache-2.0 alignment note, .gitignore.

## Verification

- Acceptance test above on every change to parser.
- Round-trip sanity: export JSON, reload JSON, compare object trees.
- Manual GUI pass: open example, toggle front/back, search "1104" and an amount, export and diff against `validation.json`.
