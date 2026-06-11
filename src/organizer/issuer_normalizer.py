KNOWN_ISSUERS = {
    "DZR Deutsches Zahnärztliches Rechenzentrum GmbH": "DZR",
}


def normalize_issuer(issuer):

    return KNOWN_ISSUERS.get(issuer, issuer)
