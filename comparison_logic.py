import pandas as pd
from difflib import SequenceMatcher

NICKNAME_MAP = {
    "joe": "joseph", "jim": "james", "bob": "robert", "bill": "william", "liz": "elizabeth", "kate": "katherine",
    "tom": "thomas", "dave": "david", "dan": "daniel", "mike": "michael", "steve": "steven"
}

def normalize_name(name):
    parts = name.lower().strip().split()
    return " ".join([NICKNAME_MAP.get(p, p) for p in parts])

def compare_contacts(nvca_contacts, new_contacts):
    existing_names = nvca_contacts["Full Name"].dropna().apply(normalize_name).tolist()
    matched, new, updated = [], [], []

    for new_contact in new_contacts:
        new_name_normalized = normalize_name(new_contact["name"])
        match_found = False

        for i, existing_name in enumerate(existing_names):
            if SequenceMatcher(None, new_name_normalized, existing_name).ratio() > 0.9:
                match_found = True
                current_title = nvca_contacts.loc[i, "Title"]
                if current_title.strip().lower() != new_contact["title"].strip().lower():
                    nvca_contacts.at[i, "Title"] = new_contact["title"]  # Update title
                matched.append(i)
                break

        if not match_found:
            new.append(new_contact)

    missing = nvca_contacts.drop(index=matched)
    return nvca_contacts, new, missing
