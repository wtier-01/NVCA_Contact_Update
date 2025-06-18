NICKNAME_MAP = {
    "joe": "joseph",
    "joseph": "joseph",
    "bill": "william",
    "will": "william",
    "william": "william",
    "liz": "elizabeth",
    "elizabeth": "elizabeth",
    "bob": "robert",
    "rob": "robert",
    "robert": "robert",
    "alex": "alexander",
    "alexander": "alexander",
    "kate": "katherine",
    "katie": "katherine",
    "katherine": "katherine",
    # Add more mappings as needed...
}


def normalize_name(name):
    if not isinstance(name, str):
        return ""
    parts = name.strip().lower().split()
    return " ".join(NICKNAME_MAP.get(part, part) for part in parts)

