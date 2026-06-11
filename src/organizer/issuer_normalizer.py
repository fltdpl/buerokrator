KNOWN_ISSUERS = {
    "Musterabrechnung Rechenzentrum GmbH": "Musterabrechnung",
}


def normalize_issuer(issuer):

    return KNOWN_ISSUERS.get(issuer, issuer)
