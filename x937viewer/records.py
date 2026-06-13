"""Field layouts for X9.37 records.

Each record type maps to an ordered list of (json_key, length, kind) tuples.
The 2-byte record type prefix is NOT included in the tables.

Kinds:
    's'  - string, whitespace-stripped
    'n'  - integer (blank -> 0)
    'd'  - date YYYYMMDD -> "YYYY-MM-DDT00:00:00Z"
    't'  - time HHMM     -> "0000-01-01THH:MM:00Z"
    'x'  - reserved / not serialized (json_key is None)

Layouts follow ANSI X9.37-2003 (DSTU) and field naming follows the JSON
output of moov-io/imagecashletter so exports are drop-in compatible.
"""

# ---------------------------------------------------------------- fixed 80-byte records

FILE_HEADER = [  # 01
    ("standardLevel", 2, "s"),
    ("testIndicator", 1, "s"),
    ("immediateDestination", 9, "s"),
    ("immediateOrigin", 9, "s"),
    ("fileCreationDate", 8, "d"),
    ("fileCreationTime", 4, "t"),
    ("ResendIndicator", 1, "s"),
    ("immediateDestinationName", 18, "s"),
    ("ImmediateOriginName", 18, "s"),
    ("fileIDModifier", 1, "s"),
    ("countryCode", 2, "s"),
    ("userField", 4, "s"),
    ("companionDocumentIndicator", 1, "s"),
]

CASH_LETTER_HEADER = [  # 10
    ("collectionTypeIndicator", 2, "s"),
    ("destinationRoutingNumber", 9, "s"),
    ("eceInstitutionRoutingNumber", 9, "s"),
    ("cashLetterBusinessDate", 8, "d"),
    ("cashLetterCreationDate", 8, "d"),
    ("cashLetterCreationTime", 4, "t"),
    ("recordTypeIndicator", 1, "s"),
    ("DocumentationTypeIndicator", 1, "s"),
    ("cashLetterID", 8, "s"),
    ("originatorContactName", 14, "s"),
    ("originatorContactPhoneNumber", 10, "s"),
    ("fedWorkType", 1, "s"),
    ("returnsIndicator", 1, "s"),
    ("userField", 1, "s"),
    (None, 1, "x"),
]

BUNDLE_HEADER = [  # 20
    ("collectionTypeIndicator", 2, "s"),
    ("destinationRoutingNumber", 9, "s"),
    ("eceInstitutionRoutingNumber", 9, "s"),
    ("bundleBusinessDate", 8, "d"),
    ("bundleCreationDate", 8, "d"),
    ("bundleID", 10, "s"),
    ("BundleSequenceNumber", 4, "s"),
    ("cycleNumber", 2, "s"),
    (None, 9, "x"),  # returnLocationRoutingNumber (not serialized by Moov)
    ("userField", 5, "s"),
    (None, 12, "x"),
]

CHECK_DETAIL = [  # 25
    ("auxiliaryOnUs", 15, "s"),
    ("externalProcessingCode", 1, "s"),
    ("payorBankRoutingNumber", 8, "s"),
    ("payorBankCheckDigit", 1, "s"),
    ("onUs", 20, "s"),
    ("itemAmount", 10, "n"),
    ("eceInstitutionItemSequenceNumber", 15, "s"),
    ("documentationTypeIndicator", 1, "s"),
    ("returnAcceptanceIndicator", 1, "s"),
    ("micrValidIndicator", 1, "n"),
    ("bofdIndicator", 1, "s"),
    ("addendumCount", 2, "n"),
    ("correctionIndicator", 1, "n"),
    ("archiveTypeIndicator", 1, "s"),
]

CHECK_DETAIL_ADDENDUM_A = [  # 26
    ("recordNumber", 1, "n"),
    ("returnLocationRoutingNumber", 9, "s"),
    ("bofdEndorsementDate", 8, "d"),
    ("bofdItemSequenceNumber", 15, "s"),
    ("bofdAccountNumber", 18, "s"),
    ("bofdBranchCode", 5, "s"),
    ("payeeName", 15, "s"),
    ("truncationIndicator", 1, "s"),
    ("bofdConversionIndicator", 1, "s"),
    ("bofdCorrectionIndicator", 1, "n"),
    ("userField", 1, "s"),
    (None, 3, "x"),
]

# 27 / 34 are variable length: head + imageReferenceKey(len) + tail
ADDENDUM_B_HEAD = [
    ("imageReferenceKeyIndicator", 1, "n"),
    ("microfilmArchiveSequenceNumber", 15, "s"),
    ("imageReferenceKeyLength", 4, "s"),
]
ADDENDUM_B_TAIL = [
    ("description", 15, "s"),
    ("userField", 4, "s"),
    (None, 5, "x"),
]

CHECK_DETAIL_ADDENDUM_C = [  # 28 (and 35 for returns)
    ("recordNumber", 2, "n"),
    ("endorsingBankRoutingNumber", 9, "s"),
    ("bofdEndorsementBusinessDate", 8, "d"),
    ("endorsingBankItemSequenceNumber", 15, "s"),
    ("truncationIndicator", 1, "s"),
    ("endorsingBankConversionIndicator", 1, "s"),
    ("endorsingBankCorrectionIndicator", 1, "n"),
    ("returnReason", 1, "s"),
    ("userField", 15, "s"),
    ("endorsingBankIdentifier", 1, "n"),
    (None, 24, "x"),
]

RETURN_DETAIL = [  # 31
    ("payorBankRoutingNumber", 8, "s"),
    ("payorBankCheckDigit", 1, "s"),
    ("onUs", 20, "s"),
    ("itemAmount", 10, "n"),
    ("returnReason", 1, "s"),
    ("addendumCount", 2, "n"),
    ("documentationTypeIndicator", 1, "s"),
    ("forwardBundleDate", 8, "d"),
    ("eceInstitutionItemSequenceNumber", 15, "s"),
    ("externalProcessingCode", 1, "s"),
    ("returnNotificationIndicator", 1, "n"),
    ("archiveTypeIndicator", 1, "s"),
    ("timesReturned", 1, "n"),
    (None, 8, "x"),
]

RETURN_DETAIL_ADDENDUM_A = CHECK_DETAIL_ADDENDUM_A  # 32, same layout as 26

RETURN_DETAIL_ADDENDUM_B = [  # 33
    ("payorBankName", 18, "s"),
    ("auxiliaryOnUs", 15, "s"),
    ("payorBankSequenceNumber", 15, "s"),
    ("payorBankBusinessDate", 8, "d"),
    ("payorAccountName", 22, "s"),
]

RETURN_DETAIL_ADDENDUM_D = CHECK_DETAIL_ADDENDUM_C  # 35, same layout as 28

IMAGE_VIEW_DETAIL = [  # 50
    ("imageIndicator", 1, "n"),
    ("imageCreatorRoutingNumber", 9, "s"),
    ("imageCreatorDate", 8, "d"),
    ("imageViewFormatIndicator", 2, "s"),
    ("imageViewCompressionAlgorithm", 2, "s"),
    ("imageViewDataSize", 7, "s"),
    ("viewSideIndicator", 1, "n"),
    ("viewDescriptor", 2, "s"),
    ("digitalSignatureIndicator", 1, "n"),
    ("digitalSignatureMethod", 2, "s"),
    ("securityKeySize", 5, "n"),
    ("protectedDataStart", 7, "n"),
    ("protectedDataLength", 7, "n"),
    ("imageRecreateIndicator", 1, "n"),
    ("userField", 8, "s"),
    (None, 1, "x"),
    ("overrideIndicator", 1, "s"),
    (None, 13, "x"),
]

# 52 is variable length: head + refKey(len) + lenSig(5) + sig(len) + lenImage(7) + image(len)
IMAGE_VIEW_DATA_HEAD = [
    ("eceInstitutionRoutingNumber", 9, "s"),
    ("bundleBusinessDate", 8, "d"),
    ("cycleNumber", 2, "s"),
    ("eceInstitutionItemSequenceNumber", 15, "s"),
    ("securityOriginatorName", 16, "s"),
    ("securityAuthenticatorName", 16, "s"),
    ("securityKeyName", 16, "s"),
    ("clippingOrigin", 1, "n"),
    ("clippingCoordinateH1", 4, "s"),
    ("clippingCoordinateH2", 4, "s"),
    ("clippingCoordinateV1", 4, "s"),
    ("clippingCoordinateV2", 4, "s"),
    ("lengthImageReferenceKey", 4, "s"),
]

IMAGE_VIEW_ANALYSIS = [  # 54
    ("globalImageQuality", 1, "n"),
    ("globalImageUsability", 1, "n"),
    ("imagingBankSpecificTest", 1, "n"),
    ("partialImage", 1, "n"),
    ("excessiveImageSkew", 1, "n"),
    ("piggybackImage", 1, "n"),
    ("tooLightOrTooDark", 1, "n"),
    ("streaksAndOrBands", 1, "n"),
    ("belowMinimumImageSize", 1, "n"),
    ("exceedsMaximumImageSize", 1, "n"),
    (None, 12, "x"),
    ("imageEnabledPOD", 1, "n"),
    ("sourceDocumentBad", 1, "n"),
    ("dateUsability", 1, "n"),
    ("payeeUsability", 1, "n"),
    ("convenienceAmountUsability", 1, "n"),
    ("amountInWordsUsability", 1, "n"),
    ("signatureUsability", 1, "n"),
    ("payorNameAddressUsability", 1, "n"),
    ("micrLineUsability", 1, "n"),
    ("memoLineUsability", 1, "n"),
    ("payorBankNameAddressUsability", 1, "n"),
    ("payeeEndorsementUsability", 1, "n"),
    ("bofdEndorsementUsability", 1, "n"),
    ("transitEndorsementUsability", 1, "n"),
    (None, 7, "x"),
    ("userField", 20, "s"),
    (None, 15, "x"),
]

CREDIT = [  # 61
    ("auxiliaryOnUs", 15, "s"),
    ("externalProcessingCode", 1, "s"),
    ("payorBankRoutingNumber", 9, "s"),
    ("creditAccountNumberOnUs", 20, "s"),
    ("itemAmount", 10, "n"),
    ("eceInstitutionItemSequenceNumber", 15, "s"),
    ("documentationTypeIndicator", 1, "s"),
    ("accountTypeCode", 1, "s"),
    ("sourceWorkCode", 2, "s"),
    ("workType", 1, "s"),
    ("debitCreditIndicator", 1, "s"),
    (None, 2, "x"),
]

CREDIT_ITEM = [  # 62
    ("auxiliaryOnUs", 15, "s"),
    ("externalProcessingCode", 1, "s"),
    ("postingBankRoutingNumber", 9, "s"),
    ("onUs", 20, "s"),
    ("itemAmount", 14, "n"),
    ("creditItemSequenceNumber", 15, "s"),
    ("documentationTypeIndicator", 1, "s"),
    ("accountTypeCode", 1, "s"),
    ("sourceWorkCode", 2, "s"),
    (None, 1, "x"),
]

ROUTING_NUMBER_SUMMARY = [  # 85
    ("cashLetterRoutingNumber", 9, "s"),
    ("routingNumberTotalAmount", 14, "n"),
    ("routingNumberItemCount", 6, "n"),
    ("userField", 24, "s"),
    (None, 25, "x"),
]

BUNDLE_CONTROL = [  # 70
    ("bundleitemsCount", 4, "n"),
    ("bundleTotalAmount", 12, "n"),
    ("micrValidTotalAmount", 12, "n"),
    ("bundleImagesCount", 5, "n"),
    ("userField", 20, "s"),
    ("creditTotalIndicator", 1, "n"),
    (None, 24, "x"),
]

CASH_LETTER_CONTROL = [  # 90
    ("cashLetterBundleCount", 6, "n"),
    ("cashLetterItemsCount", 8, "n"),
    ("cashLetterTotalAmount", 14, "n"),
    ("cashLetterImagesCount", 9, "n"),
    ("eceInstitutionName", 18, "s"),
    ("settlementDate", 8, "d"),
    ("creditTotalIndicator", 1, "n"),
    (None, 14, "x"),
]

FILE_CONTROL = [  # 99
    ("cashLetterCount", 6, "n"),
    ("totalRecordCount", 8, "n"),
    ("totalItemCount", 8, "n"),
    ("fileTotalAmount", 16, "n"),
    ("immediateOriginContactName", 14, "s"),
    ("immediateOriginContactPhoneNumber", 10, "s"),
    ("creditTotalIndicator", 1, "n"),
    (None, 15, "x"),
]

#: record type -> human readable name
RECORD_NAMES = {
    "01": "File Header",
    "10": "Cash Letter Header",
    "20": "Bundle Header",
    "25": "Check Detail",
    "26": "Check Detail Addendum A",
    "27": "Check Detail Addendum B",
    "28": "Check Detail Addendum C",
    "31": "Return Detail",
    "32": "Return Detail Addendum A",
    "33": "Return Detail Addendum B",
    "34": "Return Detail Addendum C",
    "35": "Return Detail Addendum D",
    "50": "Image View Detail",
    "52": "Image View Data",
    "54": "Image View Analysis",
    "61": "Credit",
    "62": "Credit Item",
    "68": "User Record",
    "70": "Bundle Control",
    "85": "Routing Number Summary",
    "90": "Cash Letter Control",
    "99": "File Control",
}
