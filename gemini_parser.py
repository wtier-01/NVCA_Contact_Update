import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

# Load environment variable
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Gemini model
model = genai.GenerativeModel("models/gemini-1.5-flash")


def fallback_parse(response_text):
    """
    Fallback: extract every 2 lines as name and title.
    """
    lines = [line.strip() for line in response_text.strip().splitlines() if line.strip()]
    contacts = []
    for i in range(0, len(lines) - 1, 2):
        name = lines[i]
        title = lines[i + 1]
        contacts.append({
            "name": name,
            "title": title if is_valid_title(title) else ""
        })
    return contacts


def clean_gemini_output(raw_text):
    """
    Strips ```json\n...\n``` wrappers from Gemini output.
    """
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
    return raw_text


def is_valid_title(text):
    """
    Rejects bios masquerading as titles.
    """
    if not text:
        return False
    blacklist = [
        "background", "experience", "expert", "entrepreneur", "operator", "decades",
        "building", "growth", "investor", "consulting", "track record", "C-Suite", "subject-matter"
    ]
    return (
        len(text.split()) <= 6
        and not any(term in text.lower() for term in blacklist)
    )


def parse_team_text_with_gemini(team_text):
    """
    Uses Gemini to extract structured {name, title} pairs.
    Filters or blanks out invalid title content.
    """
    prompt = f"""Extract a list of team members from the following text. For each person, return:
- Full name
- Job title (actual role like Partner, Analyst, Principal — not a bio or summary)

If the title isn't clear or it's just a background description, leave the title blank.

Return the output as a JSON list of dictionaries:
[
  {{"name": "Jane Doe", "title": "Partner"}},
  {{"name": "John Smith", "title": ""}}
]

Here is the text:
{team_text}
"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        print("\n🔎 RAW GEMINI RESPONSE:\n", repr(raw_text))

        cleaned = clean_gemini_output(raw_text)
        parsed = json.loads(cleaned)

        # Handle stringified JSON
        if isinstance(parsed, str):
            parsed = json.loads(parsed)

        if isinstance(parsed, list):
            return [
                {"name": entry.get("name", "").strip(), "title": entry.get("title", "").strip() if is_valid_title(entry.get("title", "")) else ""}
                for entry in parsed
                if isinstance(entry, dict) and "name" in entry
            ]

    except Exception as e:
        print("❌ Gemini parsing error:", e)
        print("⚠️ Falling back to line-by-line parsing.")

    return fallback_parse(cleaned if 'cleaned' in locals() else team_text)
