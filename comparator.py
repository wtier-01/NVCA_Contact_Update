# comparator.py

def normalize(text):
    return text.strip().lower()

def compare_contacts(nvca_contacts, gemini_contacts):
    nvca_names = {normalize(c["name"]) for c in nvca_contacts}
    new_contacts = []

    for person in gemini_contacts:
        if normalize(person["name"]) not in nvca_names:
            new_contacts.append(person)

    return new_contacts
