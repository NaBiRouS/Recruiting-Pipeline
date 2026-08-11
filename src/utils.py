import re


def normalize_email(email):
    if not email:
        return ""

    return email.strip().lower()


def normalize_email_local(email):
    email = normalize_email(email)

    if "@" in email:
        return email.split("@")[0]

    return email


def normalize_phone(phone):
    if not phone:
        return ""

    return re.sub(r"\D", "", phone)


def normalize_name(name):
    if not name:
        return ""

    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)

    return name