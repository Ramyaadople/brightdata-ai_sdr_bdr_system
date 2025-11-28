import os
import requests

def apollo_lookup_by_linkedin(linkedin_url: str, reveal_phone: bool):
    """
    Standalone Apollo Lookup Module.
    Takes LinkedIn URL and returns email + phone.
    Works without modifying ContactResearchTool.
    """
    APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

    if not APOLLO_API_KEY:
        return {
            "status": "no_api_key",
            "email": None,
            "phone": None,
            "error": "Missing APOLLO_API_KEY"
        }

    url = "https://api.apollo.io/v1/people/match"

    payload = {
        "linkedin_url": linkedin_url,
        "reveal_personal_emails": True,
        "reveal_phone_number": reveal_phone
    }

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": APOLLO_API_KEY
    }

    try:
        resp = requests.post(url, json=payload, headers=headers).json()
        person = resp.get("person")

        if not person:
            return {"status": "not_found", "email": None, "phone": None}

        email = person.get("email")
        phone = None

        if reveal_phone:
            phones = person.get("phone_numbers", [])
            phone = phones[0] if phones else None

        return {
            "status": "found",
            "email": email,
            "phone": phone
        }

    except Exception as e:
        return {
            "status": "error",
            "email": None,
            "phone": None,
            "error": str(e)
        }
