# scripts/deduper.py

import os
import sys
import pandas as pd
from fuzzywuzzy import fuzz

# ✅ Fix path issue so nickname_utils works even if run from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from nickname_utils import normalize_name

def dedupe_contacts(df, firm_name, log_path="logs/flagged_for_review.csv"):
    df = df.copy()

    # Combine first + last to form full names
    df["Full Name"] = df["First Name"].fillna('') + " " + df["Last Name"].fillna('')
    df["Normalized Name"] = df["Full Name"].apply(normalize_name)

    # Initialize tracking
    seen = {}
    to_keep = []
    flagged = []

    for i, row in df.iterrows():
        name = row["Normalized Name"]
        title = str(row.get("Title", "")).strip()

        matched = False
        for seen_name, seen_title in seen.items():
            score = fuzz.token_sort_ratio(name, seen_name)
            if score >= 95:
                if title == seen_title:
                    matched = True  # Drop exact duplicate
                    break
                else:
                    # Keep both if titles differ
                    matched = False
                    break

        if not matched:
            seen[name] = title
            to_keep.append(row)
        else:
            continue  # Drop exact duplicates

    cleaned_df = pd.DataFrame(to_keep)

    # Flag near-matches
    all_names = list(cleaned_df["Normalized Name"])
    for i, name1 in enumerate(all_names):
        for name2 in all_names[i + 1:]:
            score = fuzz.token_sort_ratio(name1, name2)
            if 90 <= score < 95:
                flagged.append(f"{firm_name}: {name1} ~ {name2} (Score: {score})")

    # Save flagged issues
    if flagged:
        os.makedirs("logs", exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            for entry in flagged:
                f.write(entry + "\n")

    return cleaned_df
