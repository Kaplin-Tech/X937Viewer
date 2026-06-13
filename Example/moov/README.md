# Moov imagecashletter test data

Test files from [moov-io/imagecashletter](https://github.com/moov-io/imagecashletter)
(`test/testdata/`, Apache-2.0). Every file below is byte-identical to upstream —
verified against the upstream git blob SHA-1.

| File | Size | Git blob SHA | Notes |
|---|---|---|---|
| `valid-ascii.x937` | 17136 | `5e33ecd1…` | ASCII + variable-length records; same logical file as `../iclFile.x937` |
| `without-micrValidIndicator.icl` | 17136 | `707da2c4…` | `valid-ascii` with blank micrValidIndicator (record 25) |
| `BNK20180905121042882-A.icl` | 6520 | `c7a65d50…` | 2 cash letters; forward items, returns (31–35), no images |
| `icl-valid.json` | 71539 | `80520b67…` | Moov JSON file format (2 cash letters, 60 items) |
| `valid-x937.json` | 31764 | `0e325950…` | Expected JSON output for `valid-ascii.x937` / `iclFile.x937` |
| `cash-letter.json` | 29461 | `c001631d…` | Single cash letter JSON fragment |

Note: `../iclFile.x937` equals upstream `valid-ebcdic.x937` (`438222f2…`), and
`../validation.json` is the Moov demo's JSON output for it.

Not yet mirrored (upstream rate limit at fetch time): `BNK20181010121042882-A.icl`,
`creditRecord61.icl` (record 61 credit coverage), `base64-encoded-images.json`,
`file-header.json`, `issue138.json`, `issue228.json`, `missing-bundle-control.json`.
