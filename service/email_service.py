import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


async def send_verification_email(
    recipient_email: str,
    code: str
):
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("BREVO_SENDER_EMAIL")

    if not api_key or not sender_email:
        raise ValueError(
            "Configuration Brevo manquante dans le fichier .env"
        )

    headers = {
        "api-key": api_key,
        "accept": "application/json",
        "content-type": "application/json"
    }

    data = {
        "sender": {
            "name": "Chat Group NAN",
            "email": sender_email
        },
        "to": [
            {
                "email": recipient_email
            }
        ],
        "subject": "Confirmation de votre adresse email",
        "textContent": (
            f"Votre code de confirmation est : {code}\n"
            "Ce code expire dans 10 minutes."
        ),
        "htmlContent": f"""
            <h2>Confirmation de votre adresse email</h2>
            <p>Voici votre code de confirmation :</p>
            <h1>{code}</h1>
            <p>Ce code expire dans 10 minutes.</p>
        """
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            BREVO_API_URL,
            headers=headers,
            json=data
        )

        response.raise_for_status()

    return True