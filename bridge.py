import os
import asyncio
import json
import urllib.request
import websockets

SANDBOX_ID = "6b755800-f95e-44bf-b5bb-7b6733a42152"
DAYTONA_PORT = 25565

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
DAYTONA_API_KEY = os.environ["DAYTONA_API_KEY"]

API_URL = (
    f"https://app.daytona.io/api/sandbox/"
    f"{SANDBOX_ID}/ports/{DAYTONA_PORT}/preview-url"
)


def get_daytona_target():
    request = urllib.request.Request(
        API_URL,
        headers={
            "Authorization": f"Bearer {DAYTONA_API_KEY}"
        },
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read())

    return data["url"], data["token"]


async def pipe(source, destination, name):
    try:
        async for message in source:
            await destination.send(message)
    except Exception as error:
        print(f"{name} pipe closed:", repr(error))


async def handle(client):
    print("Eagler client connected")

    try:
        url, token = await asyncio.to_thread(get_daytona_target)

        target_url = url.replace("https://", "wss://", 1)

        print("Daytona WebSocket:", target_url)

        async with websockets.connect(
            target_url,
            additional_headers={
                "X-Daytona-Preview-Token": token
            },
            max_size=None,
        ) as target:

            print("Connected to Daytona")

            await asyncio.gather(
                pipe(client, target, "Client → Daytona"),
                pipe(target, client, "Daytona → Client"),
            )

    except Exception as error:
        print("Bridge error:", repr(error))

    finally:
        print("Eagler client disconnected")


async def main():
    print(f"Eagler WSS bridge listening on {HOST}:{PORT}")

    async with websockets.serve(
        handle,
        HOST,
        PORT,
        max_size=None,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
