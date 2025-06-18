# scripts/clean_ui.py

import streamlit as st
import os
import shutil
import subprocess
import pandas as pd

LOG_FILE = "logs/flagged_for_review.csv"
OUTPUT_FOLDER = "Output"
CLEANED_FOLDER = "Cleaned"
SCRIPT_TO_RUN = "scripts/clean_outputs.py"

def run_cleaning_script(selected_firms=None):
    try:
        cmd = ["python", SCRIPT_TO_RUN]
        if selected_firms:
            cmd += selected_firms
        result = subprocess.run(cmd, capture_output=True, text=True)
        st.text_area("🧼 Cleaning Output", result.stdout + "\n" + result.stderr, height=300)
    except Exception as e:
        st.error(f"❌ Failed to run cleaning script: {e}")

def render():
    st.header("🧼 Manual Review & Cleaning")

    if "selected_firms" not in st.session_state:
        st.session_state["selected_firms"] = []

    all_files = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith("_updated_contacts.xlsx") and not f.startswith("~$")]
    firm_names = sorted([f.replace("_updated_contacts.xlsx", "") for f in all_files])

    valid_defaults = [f for f in st.session_state["selected_firms"] if f in firm_names]
    selected = st.multiselect("Choose firms to clean:", firm_names, default=valid_defaults)
    st.session_state["selected_firms"] = selected

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Select All Firms to Clean", key="select_all_button"):
            st.session_state["selected_firms"] = firm_names
            st.rerun()

    with col2:
        if st.button("🧼 Run Cleaning Now", key="run_clean_button"):
            run_cleaning_script(st.session_state["selected_firms"])
            st.rerun()

    st.markdown("---")
    st.header("🚩 Manual Review: Flagged Issues")

    if not os.path.exists(LOG_FILE):
        st.info("✅ No flagged files for review.")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        flagged_lines = f.readlines()

    if not flagged_lines:
        st.success("🎉 No flagged issues remain!")
        return

    firm_names_flagged = sorted(set(line.split(":")[0].strip() for line in flagged_lines))
    selected_firm = st.selectbox("🔎 Select a flagged firm", firm_names_flagged)

    flagged_details = [line for line in flagged_lines if line.startswith(selected_firm)]
    st.write("🚩 Issues Detected:")
    for entry in flagged_details:
        st.markdown(f"- {entry.strip()}")

    st.markdown("---")

    col3, col4 = st.columns(2)

    with col3:
        if st.button("📂 Open in Excel", key=f"open_excel_{selected_firm}"):
            cleaned_path = os.path.join(CLEANED_FOLDER, f"{selected_firm}.xlsx")
            if os.path.exists(cleaned_path):
                os.startfile(cleaned_path)
            else:
                st.warning(f"Cleaned file for {selected_firm} not found.")

    with col4:
        if st.button("✅ Approve Cleaned File", key=f"approve_cleaned_{selected_firm}"):
            src = os.path.join(OUTPUT_FOLDER, f"{selected_firm}_updated_contacts.xlsx")
            dst = os.path.join(CLEANED_FOLDER, f"{selected_firm}.xlsx")
            try:
                shutil.copy(src, dst)
                new_lines = [line for line in flagged_lines if not line.startswith(selected_firm)]
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                st.success(f"✅ Approved and moved {selected_firm} to `/Cleaned/`")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to move file: {e}")
