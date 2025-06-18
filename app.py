import os
import json
import pandas as pd
import streamlit as st
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from gemini_parser import parse_team_text_with_gemini
from nickname_utils import normalize_name
from output_writer import write_output
from scripts.clean_ui import render as render_clean_ui

st.set_page_config(page_title="NVCA Contact Updater", layout="centered")
tabs = st.tabs(["📇 Contact Update Tool", "🧼 Clean Outputs"])

with tabs[0]:
    st.title("📇 NVCA Contact Update Tool")

    STARRED_PATH = "starred_firms.json"
    if os.path.exists(STARRED_PATH):
        with open(STARRED_PATH, "r") as f:
            saved_starred = json.load(f)
    else:
        saved_starred = []

    try:
        contacts_df = pd.read_csv("Data/contacts.csv", encoding="ISO-8859-1")
        websites_df = pd.read_csv("Data/websites.csv", encoding="ISO-8859-1")
        st.success("✅ contacts.csv and websites.csv loaded successfully.")
    except Exception as e:
        st.error(f"❌ Failed to load files: {e}")
        st.stop()

    def is_firm_processed(firm_name):
        return os.path.exists(os.path.join("Output", f"{firm_name}_updated_contacts.xlsx"))

    all_firms = sorted(websites_df["Account Name"].dropna().tolist())
    processed_firms = [name for name in all_firms if is_firm_processed(name)]

    if "starred_firms" not in st.session_state:
        st.session_state["starred_firms"] = saved_starred

    remaining_firms = [
        name for name in all_firms
        if not is_firm_processed(name) and name not in st.session_state["starred_firms"]
    ]

    if "firm_index" not in st.session_state:
        st.session_state["firm_index"] = 0
    if "last_output" not in st.session_state:
        st.session_state["last_output"] = None
    if "just_updated" not in st.session_state:
        st.session_state["just_updated"] = False
    if "current_firm" not in st.session_state and remaining_firms:
        st.session_state["current_firm"] = remaining_firms[st.session_state["firm_index"]]

    st.sidebar.markdown("### 📁 Output File Browser")
    output_files = sorted([f for f in os.listdir("Output") if f.endswith(".xlsx")])
    display_names = [f.replace("_updated_contacts.xlsx", "") for f in output_files]

    if display_names:
        selected_file = st.sidebar.selectbox("Select Firm File", display_names)
        if st.sidebar.button("🔁 Reopen in Editor"):
            st.session_state["current_firm"] = selected_file
            if selected_file in all_firms:
                st.session_state["firm_index"] = all_firms.index(selected_file)
            st.rerun()

        path = os.path.join("Output", f"{selected_file}_updated_contacts.xlsx")
        if st.sidebar.button("📂 Open in Excel"):
            try:
                os.startfile(path)
            except Exception as e:
                st.sidebar.error(f"❌ Failed to open: {e}")

        if st.sidebar.button("➡ Next Unprocessed"):
            if remaining_firms:
                st.session_state["firm_index"] = 0
                st.session_state["current_firm"] = remaining_firms[0]
                st.rerun()
            else:
                st.sidebar.info("🎉 All firms done!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back"):
            if st.session_state["firm_index"] > 0:
                st.session_state["firm_index"] -= 1
                st.session_state["current_firm"] = remaining_firms[st.session_state["firm_index"]]
    with col2:
        if st.button("Next ➡"):
            if st.session_state["firm_index"] < len(remaining_firms) - 1:
                st.session_state["firm_index"] += 1
                st.session_state["current_firm"] = remaining_firms[st.session_state["firm_index"]]

    firm_input = st.session_state.get("current_firm")
    if firm_input:
        st.success(f"🎯 Current Firm: **{firm_input}**")
    else:
        st.info("🎉 All firms are processed!")

    st.markdown(f"**Progress**\n- ✅ {len(processed_firms)} completed\n- 🔄 {len(remaining_firms)} remaining")

    if firm_input and st.button("⭐ Star This Firm for Later"):
        if firm_input not in st.session_state["starred_firms"]:
            st.session_state["starred_firms"].append(firm_input)
            with open(STARRED_PATH, "w") as f:
                json.dump(st.session_state["starred_firms"], f)
            st.success(f"⭐ {firm_input} starred.")

    if st.session_state["starred_firms"]:
        with st.expander("⭐ View Starred Firms"):
            for starred in st.session_state["starred_firms"]:
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    st.write(f"🔹 {starred}")
                with col2:
                    if st.button("🔁 Jump", key=f"jump_{starred}"):
                        st.session_state["current_firm"] = starred
                        if starred in all_firms:
                            st.session_state["firm_index"] = all_firms.index(starred)
                        st.rerun()

    firm_lookup = {name.lower(): url for name, url in zip(websites_df["Account Name"], websites_df["Website"])}
    firm_url = firm_lookup.get(firm_input.lower()) if firm_input else None

    if firm_input:
        existing_contacts = contacts_df[contacts_df["Account Name"].str.lower() == firm_input.lower()]
        if not existing_contacts.empty:
            st.subheader("📇 Existing Contacts")
            st.dataframe(existing_contacts[["First Name", "Last Name", "Title"]])
        else:
            st.info("ℹ️ No contacts found.")

    pasted_text = st.text_area(f"📋 Paste the team section from {firm_url or 'team page'}:", height=300)

    if st.button("🚀 Run Contact Update"):
        if not pasted_text.strip():
            st.warning("⚠️ Paste something first.")
            st.stop()

        with st.spinner("🔎 Running Gemini..."):
            try:
                parsed_contacts = parse_team_text_with_gemini(pasted_text)
                if not isinstance(parsed_contacts, list):
                    raise ValueError("Gemini did not return a valid list.")
            except Exception as e:
                st.error(f"❌ Gemini failed: {e}")
                st.stop()

        def safe_full_name(row):
            first = str(row.get("First Name", "") or "").strip()
            last = str(row.get("Last Name", "") or "").strip()
            return normalize_name(f"{first} {last}")

        contacts_df["Normalized Name"] = contacts_df.apply(safe_full_name, axis=1)

        output_data, seen_new_names, matched_normalized_names = [], set(), set()

        for contact in parsed_contacts:
            raw_name = contact.get("name")
            raw_title = contact.get("title", "").strip()
            fallback_title = raw_title if isinstance(raw_title, str) else "TBU"
            notes = ""

            if not isinstance(raw_name, str) or len(raw_name.split()) < 2:
                first, last = "TBU", "TBU"
                notes = "⚠️ Malformed contact from Gemini"
            else:
                name_words = raw_name.strip().split()
                first, last = name_words[0], " ".join(name_words[1:])

            contact_name = normalize_name(f"{first} {last}")
            match = process.extractOne(contact_name, contacts_df["Normalized Name"], scorer=fuzz.token_sort_ratio)

            if match and match[1] >= 90:
                idx = contacts_df[contacts_df["Normalized Name"] == match[0]].index[0]
                current_title = contacts_df.at[idx, "Title"]
                if current_title != fallback_title and fallback_title:
                    contacts_df.at[idx, "Title"] = fallback_title
                output_data.append({
                    "First Name": contacts_df.at[idx, "First Name"],
                    "Last Name": contacts_df.at[idx, "Last Name"],
                    "Title": contacts_df.at[idx, "Title"],
                    "Account Name": contacts_df.at[idx, "Account Name"],
                    "Highlight": False,
                    "Strike": False,
                    "Notes": notes
                })
                matched_normalized_names.add(contact_name)
            elif contact_name not in seen_new_names:
                output_data.append({
                    "First Name": first,
                    "Last Name": last,
                    "Title": fallback_title,
                    "Account Name": firm_input,
                    "Highlight": True,
                    "Strike": False,
                    "Notes": notes
                })
                seen_new_names.add(contact_name)

        unmatched = contacts_df[
            (contacts_df["Account Name"].str.lower() == firm_input.lower()) &
            (~contacts_df["Normalized Name"].isin(matched_normalized_names))
        ]
        for _, row in unmatched.iterrows():
            output_data.append({
                "First Name": row["First Name"],
                "Last Name": row["Last Name"],
                "Title": row["Title"] or "",
                "Account Name": row["Account Name"],
                "Highlight": False,
                "Strike": True,
                "Notes": ""
            })

        path = os.path.join("Output", f"{firm_input}_updated_contacts.xlsx")
        try:
            # 🔍 DEBUG block: Check for bad name types before saving
            for row in output_data:
                try:
                    full_name = str(row.get("First Name", "")) + " " + str(row.get("Last Name", ""))
                    _ = full_name.strip()
                except Exception as e:
                    st.error(f"🚨 Error formatting row: {row} → {e}")
                    raise

            write_output(output_data, path)
            st.success(f"✅ Saved to `{path}`")
            st.session_state["last_output"] = path
            st.session_state["just_updated"] = True
            st.session_state["current_firm"] = firm_input
            with open(path, "rb") as f:
                st.download_button("📥 Download Excel", f, file_name=os.path.basename(path))
        except Exception as e:
            st.error(f"❌ Save failed: {e}")

    if st.session_state.get("last_output") and os.path.exists(st.session_state["last_output"]):
        try:
            st.subheader("📤 Output Preview")
            df = pd.read_excel(st.session_state["last_output"])
            st.dataframe(df)
        except:
            st.warning("⚠️ Cannot load preview.")

with tabs[1]:
    render_clean_ui()
