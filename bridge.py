import os
import asyncio
import uuid
import websockets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
TOKEN = os.environ.get("TUNNEL_TOKEN")

tunnel = None
tunnel_lock = asyncio.Lock()
connections = {}

async def send_tunnel(message):
    async with tunnel_lock:
        current = tunnel

    if current is None:
       raise ConnectionError("No tunnel agent connected")

    await current.send(message)

async def tunnel_agent(ws, first):
    global tunnel

if first != "AUTH:" + TOKEN:
    print("Rejected tunnel agent")
    await ws.close(code=1008, reason="Invalid token")
    return

async with tunnel_lock:
    old = tunnel
    tunnel = ws

if old is not None and old is not ws:
    try:
        await old.close()
    except Exception:
        pass

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
            encoded = parts[2]

            try:
                data = bytes.fromhex(encoded)
            except ValueError:
                print("Invalid DATA:", cid)
                continue

            client = connections.get(cid)

            if client is not None:
                try:
                    await client.send(data)
                except Exception as error:
                    print("Client send error:", repr(error))

        elif message.startswith("CLOSE:"):
            cid = message[6:]
            client = connections.pop(cid, None)

            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass

except websockets.exceptions.ConnectionClosed as error:
    print("Tunnel closed:", error.code, repr(error.reason))

except Exception as error:
    print("Tunnel error:", repr(error))

finally:
    async with tunnel_lock:
        if tunnel is ws:
            tunnel = None

    print("TUNNEL AGENT DISCONNECTED")

async def eagler_client(ws, first):
    cid = str(uuid.uuid4())
    connections[cid] = ws

print("Eagler client connected:", cid)

try:
    await send_tunnel("OPEN:" + cid)

    if isinstance(first, bytes):
        await send_tunnel(
            "DATA:" + cid + ":" + first.hex()
        )

    elif isinstance(first, str):
        await send_tunnel(
            "DATA:" + cid + ":" + first.encode().hex()
        )

    async for message in ws:
        if isinstance(message, bytes):
            await send_tunnel(
                "DATA:" + cid + ":" + message.hex()
            )

        elif isinstance(message, str):
            await send_tunnel(
                "DATA:" + cid + ":" + message.encode().hex()
            )

except websockets.exceptions.ConnectionClosed:
    pass

except Exception as error:
    print("Eagler error:", cid, repr(error))

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

    if (
        isinstance(first, str)
        and first.startswith("AUTH:")
    ):
        await tunnel_agent(ws, first)
    else:
        await eagler_client(ws, first)

except websockets.exceptions.ConnectionClosed:
    pass

except Exception as error:
    print("Handler error:", repr(error))

async def main():
print("================================")
print("Minecraft relay starting")
print("Host:", HOST)
print("Port:", PORT)
print("WebSocket: /")
print("================================")

async with websockets.serve(
    handle,
    HOST,
    PORT,
    max_size=None,
    ping_interval=20,
    ping_timeout=60,
    close_timeout=10,
):
    print("Minecraft relay READY")
    await asyncio.Future()

if **name** == "**main**":
asyncio.run(main())
