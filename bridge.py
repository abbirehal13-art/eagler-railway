import os
import asyncio
import json
import urllib.request
import websockets

SANDBOX_ID = "6b755800-f95e-44bf-b5bb-7b6733a42152"
DAYTONA_PORT = 25565

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
TOKEN = os.environ["TUNNEL_TOKEN"]

API_URL = (
    f"https://app.daytona.io/api/sandbox/"
    f"{SANDBOX_ID}/ports/{DAYTONA_PORT}/preview-url"
)


def get_daytona_target():
    request = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {os.environ['DAYTONA_API_KEY']}"
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read())

    return data["url"], data["token"]


async def pipe(source, destination, name):
    try:
        async for message in source:
            await destination.send(message)
    except Exception as e:
        print(name, repr(e))


async def handle_eagler(client):
    print("Eagler client connected")

    try:
        url, token = await asyncio.to_thread(get_daytona_target)

        target_url = url.replace("https://", "wss://", 1)

        async with websockets.connect(
            target_url,
            additional_headers={
                "X-Daytona-Preview-Token": token
            },
            max_size=None,
            ping_interval=20,
            ping_timeout=60,
        ) as target:

            print("Connected to Daytona")

            await asyncio.gather(
                pipe(client, target, "Eagler -> Daytona"),
                pipe(target, client, "Daytona -> Eagler"),
            )

    except Exception as e:
        print("Eagler bridge error:", repr(e))

    finally:
        print("Eagler disconnected")


async def handle_tunnel(ws):
    print("Tunnel agent connected")

    try:
        auth = await ws.recv()

        if auth != "AUTH:" + TOKEN:
            print("Invalid tunnel token")
            await ws.close()
            return

        print("Tunnel authenticated")

        async for message in ws:
            print("Tunnel message:", message)

    except Exception as e:
        print("Tunnel error:", repr(e))


async def handle(ws):
    try:
        first = await ws.recv()

        if first == "AUTH:" + TOKEN:
            await handle_tunnel(ws)
        else:
            await handle_eagler(ws)

    except Exception as e:
        print("Connection error:", repr(e))


async def main():
    print("Starting bridge on port", PORT)

    async with websockets.serve(
        handle,
        HOST,
        PORT,
        max_size=None,
        ping_interval=20,
        ping_timeout=60,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
