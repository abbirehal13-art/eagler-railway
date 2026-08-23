import os
import asyncio
import uuid
import websockets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
TOKEN = os.environ["TUNNEL_TOKEN"]

tunnel = None
tunnel_lock = asyncio.Lock()
connections = {}


async def send_tunnel(message):
    async with tunnel_lock:
        if tunnel is None:
            raise ConnectionError("No tunnel agent connected")
        await tunnel.send(message)


async def tunnel_agent(ws):
    global tunnel

    auth = await ws.recv()

    if auth != "AUTH:" + TOKEN:
        print("Rejected tunnel agent")
        await ws.close()
        return

    async with tunnel_lock:
        tunnel = ws

    print("TUNNEL AGENT CONNECTED")

    try:
        async for message in ws:
            if not isinstance(message, str):
                continue

            if message.startswith("DATA:"):
                parts = message.split(":", 2)

                if len(parts) != 3:
                    continue

                cid = parts[1]
                data = parts[2]

                client = connections.get(cid)

                if client:
                    try:
                        await client.send(bytes.fromhex(data))
                    except Exception as e:
                        print("Client send error:", repr(e))

            elif message.startswith("CLOSE:"):
                cid = message[6:]
                client = connections.pop(cid, None)

                if client:
                    try:
                        await client.close()
                    except Exception:
                        pass

    except Exception as e:
        print("Tunnel error:", repr(e))

    finally:
        async with tunnel_lock:
            if tunnel is ws:
                tunnel = None

        print("TUNNEL AGENT DISCONNECTED")


async def eagler_client(ws):
    cid = str(uuid.uuid4())
    connections[cid] = ws

    print("Eagler client connected:", cid)

    try:
        await send_tunnel("OPEN:" + cid)

        async for message in ws:
            if isinstance(message, bytes):
                await send_tunnel(
                    f"DATA:{cid}:{message.hex()}"
                )

            elif isinstance(message, str):
                await send_tunnel(
                    f"DATA:{cid}:{message.encode().hex()}"
                )

    except Exception as e:
        print("Eagler error:", repr(e))

    finally:
        connections.pop(cid, None)

        try:
            await send_tunnel("CLOSE:" + cid)
        except Exception:
            pass

        print("Eagler client disconnected:", cid)


async def handle(ws):
    try:
        first = await ws.recv()

        # Tunnel agents identify themselves with AUTH:
        if isinstance(first, str) and first.startswith("AUTH:"):
            await tunnel_agent_with_first(ws, first)
            return

        # Otherwise this is an Eagler client.
        await eagler_client_with_first(ws, first)

    except Exception as e:
        print("Connection handler error:", repr(e))


async def tunnel_agent_with_first(ws, first):
    global tunnel

    if first != "AUTH:" + TOKEN:
        print("Rejected tunnel agent")
        await ws.close()
        return

    async with tunnel_lock:
        tunnel = ws

    print("TUNNEL AGENT CONNECTED")

    try:
        async for message in ws:
            if not isinstance(message, str):
                continue

            if message.startswith("DATA:"):
                parts = message.split(":", 2)

                if len(parts) != 3:
                    continue

                cid = parts[1]
                data = parts[2]

                client = connections.get(cid)

                if client:
                    await client.send(bytes.fromhex(data))

            elif message.startswith("CLOSE:"):
                cid = message[6:]
                client = connections.pop(cid, None)

                if client:
                    await client.close()

    except Exception as e:
        print("Tunnel error:", repr(e))

    finally:
        async with tunnel_lock:
            if tunnel is ws:
                tunnel = None

        print("TUNNEL AGENT DISCONNECTED")


async def eagler_client_with_first(ws, first):
    cid = str(uuid.uuid4())
    connections[cid] = ws

    print("Eagler client connected:", cid)

    try:
        await send_tunnel("OPEN:" + cid)

        if isinstance(first, bytes):
            await send_tunnel(
                f"DATA:{cid}:{first.hex()}"
            )

        elif isinstance(first, str):
            await send_tunnel(
                f"DATA:{cid}:{first.encode().hex()}"
            )

        async for message in ws:
            if isinstance(message, bytes):
                await send_tunnel(
                    f"DATA:{cid}:{message.hex()}"
                )
            elif isinstance(message, str):
                await send_tunnel(
                    f"DATA:{cid}:{message.encode().hex()}"
                )

    except Exception as e:
        print("Eagler error:", repr(e))

    finally:
        connections.pop(cid, None)

        try:
            await send_tunnel("CLOSE:" + cid)
        except Exception:
            pass

        print("Eagler client disconnected:", cid)


async def main():
    print("Starting Minecraft relay")
    print("WebSocket:", PORT)

    async with websockets.serve(
        handle,
        HOST,
        PORT,
        max_size=None,
        ping_interval=20,
        ping_timeout=60,
        close_timeout=10,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
