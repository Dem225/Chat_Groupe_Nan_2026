import asyncio
import websockets

async def chat():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as websocket:
        while True:
            message = input("Moi : ")
            await websocket.send(message)

            reponse = await websocket.recv()
            print("Serveur :", reponse)

asyncio.run(chat())