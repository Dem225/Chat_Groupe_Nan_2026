# import os
# import asyncio
# import httpx
# from dotenv import load_dotenv

# load_dotenv()


# async def main():
#     headers = {
#         "api-key": os.getenv("BREVO_API_KEY"),
#         "accept": "application/json",
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.get(
#             "https://api.brevo.com/v3/account",
#             headers=headers,
#         )

#         print("Statut :", response.status_code)

#         if response.status_code == 200:
#             print("Authentification Brevo réussie.")
#         else:
#             print("Réponse Brevo :", response.text)


# asyncio.run(main())