KNOWN_ISSUERS = {
    "Musterabrechnung Rechenzentrum GmbH": "Musterabrechnung",
    "Musterversand EU S.à r.l.": "Musterversand",
    "Musterstrom Energie AG": "Musterstrom",
    "Musterverlag Regional GmbH": "Musterverlag",
    "Mustermobil Mobility GmbH": "Mustermobil",
    "Musterfahrt Deutschland GmbH": "Musterfahrt",
    "Mustermiete Automietung KG": "Mustermiete",
    "Musterfunk Deutschland GmbH": "Musterfunk",
    "Zweitfunk Germany GmbH & Co. OHG": "Zweitfunk",
    "Musterbau Versichern und Bausparen Allgemeine Versicherung AG": "Musterbau",
    "Versichern und Bausparen Allgemeine Versicherung AG": "Musterbau",
    "Allgemeine Versicherung AG": "Musterbau",
    "Musterbau Lebensversicherungsverein a. G.": "Musterbau",
    "Musterbau Versichern und Bausparen Lebensversicherungsverein a. G.": "Musterbau",
    "Musterbau Krankenversicherungsverein a G.": "Musterbau",
    "Lebensversicherungsverein a. G.": "Musterbau",
}


def normalize_issuer(issuer):

    return KNOWN_ISSUERS.get(issuer, issuer)
