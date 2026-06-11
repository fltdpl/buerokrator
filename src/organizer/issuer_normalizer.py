KNOWN_ISSUERS = {
    "DZR Deutsches Zahnärztliches Rechenzentrum GmbH": "DZR",
    "Amazon EU S.à r.l.": "Amazon",
    "EnBW Energie Baden-Württemberg AG": "EnBW",
    "KATAPULT Regional GmbH": "KATAPULT",
    "MILES Mobility GmbH": "MILES",
    "Free2move Deutschland GmbH": "Free2move",
    "Sixt Automietung KG": "Sixt",
    "Telekom Deutschland GmbH": "Telekom",
    "Telefónica Germany GmbH & Co. OHG": "Telefonica",
}


def normalize_issuer(issuer):

    return KNOWN_ISSUERS.get(issuer, issuer)
