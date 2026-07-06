"""Maps Korus protocol catalog IDs to myclinic instrument package slugs."""

PROTOCOL_TO_INSTRUMENT_SLUG: dict[str, str] = {
    "abfw": "abfw",
    "proc": "proc",
    "tvip": "tvip",
    "ppvt": "ppvt",
    "ados2": "ados-2",
    "cars": "cars",
    "vbmapp": "vb-mapp",
    "abllsr": "ablls-r",
    "afls": "afls",
    "tli": "tli",
    "denver2": "denver-ii",
    "bayley3": "bayley-iii",
    "pard": "pard",
    "fois": "fois",
    "adl": "adl",
    "adl-linguagem": "adl-linguagem",
    "eat10": "eat-10",
    "doss": "doss",
    "masa": "masa",
    "mbgr": "mbgr",
    "amiofe": "amiofe",
    "omes": "omes",
}

MANIFEST_INSTRUMENT_SLUGS: frozenset[str] = frozenset(PROTOCOL_TO_INSTRUMENT_SLUG.values())

# Protocols scored on the client (afeto-clinic-manager configs)
CLIENT_SCORED_PROTOCOLS: frozenset[str] = frozenset(
    {
        "mchat",
        "snap-iv",
        "rastreio-tdah",
        "rastreio-tea",
        "asrs",
        "discalculia",
        "dislexia",
        "sdq",
        "vanderbilt",
        "ata",
        "desenvolvimento-infantil",
        "habilidades-sociais",
        "desempenho-escolar",
        "entrevista-aprendizagem",
        "portage",
    }
)

SPM_PROTOCOL = "spm"


def resolve_instrument_slug(protocol_id: str) -> str | None:
    return PROTOCOL_TO_INSTRUMENT_SLUG.get(protocol_id.lower())


def has_manifest_package(protocol_id: str) -> bool:
    slug = resolve_instrument_slug(protocol_id)
    return slug is not None and slug in MANIFEST_INSTRUMENT_SLUGS
