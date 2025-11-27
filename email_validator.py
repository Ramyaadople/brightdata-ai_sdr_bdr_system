import os
import requests

# ---------------------------------------------------
#  CONFIG → replace with your AbstractAPI key
# ---------------------------------------------------
ABSTRACT_API_KEY = os.getenv("ABSTRACT_API_KEY")  # Or hardcode here
# ABSTRACT_API_KEY = "YOUR_KEY_HERE"

def check_email(email):
    if not ABSTRACT_API_KEY:
        raise Exception("❌ ABSTRACT_API_KEY not set in environment")

    url = "https://emailvalidation.abstractapi.com/v1/"
    params = {
        "api_key": ABSTRACT_API_KEY,
        "email": email
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {
            "status": "error",
            "message": f"API request failed: {e}"
        }

    # Fields from Abstract API
    is_valid_format = data.get("is_valid_format", {}).get("value", False)
    is_mx_found = data.get("is_mx_found", {}).get("value", False)
    is_smtp_valid = data.get("is_smtp_valid", {}).get("value", False)
    is_disposable = data.get("is_disposable_email", {}).get("value", False)
    deliverability = data.get("deliverability", "")
    quality_score = data.get("quality_score", 0)
    autocorrect = data.get("autocorrect")

    # Decision Logic
    if is_disposable:
        result = "invalid (disposable email)"
    elif not is_valid_format:
        result = "invalid (bad format)"
    elif is_smtp_valid or deliverability.upper() == "DELIVERABLE":
        result = "valid"
    elif quality_score and float(quality_score) >= 0.7:
        result = "likely valid"
    else:
        result = "unknown - low confidence"

    return {
        "email": email,
        "result": result,
        "deliverability": deliverability,
        "is_valid_format": is_valid_format,
        "is_mx_found": is_mx_found,
        "is_smtp_valid": is_smtp_valid,
        "is_disposable": is_disposable,
        "quality_score": quality_score,
        "autocorrect": autocorrect,
        "raw_response": data
    }


# ---------------------------------------------------
#   RUN DIRECTLY FROM TERMINAL
# ---------------------------------------------------
if __name__ == "__main__":
    email_to_test = input("Enter an email to validate: ")

    result = check_email(email_to_test)

    print("\n========= Email Validation Result =========")
    for key, value in result.items():
        print(f"{key}: {value}")
