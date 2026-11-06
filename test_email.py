import asyncio

from service.email_service import send_verification_email


async def main():
    email = input("Entre ton adresse email de réception : ")

    code = "123456"

    try:
        await send_verification_email(email, code)
        print("Email envoyé avec succès !")

    except Exception as e:
        print("Erreur lors de l'envoi :", e)


asyncio.run(main())