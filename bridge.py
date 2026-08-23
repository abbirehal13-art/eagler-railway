import os
import asyncio
import uuid
import websockets

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))

TOKEN = os.environ.get("TUNNEL_TOKEN")

if not TOKEN:
    raise RuntimeError("TUNNEL_TOKEN is not set")

tunnel = None
tunnel_lock = asyncio.Lock()
connections = {}

async def send_tunnel(message):
    async with tunnel_lock:
        current_tunnel = tunnel
        
    if current_tunnel is None:
        raise ConnectionError("No tunnel agent connected")

    await current_tunnel.send(message)

async def tunnel_agent(ws, first_message):
global tunnel

```
if first_message != "AUTH:" + TOKEN:
    print("Rejected tunnel agent: invalid token")
    await ws.close(code=1008, reason="Invalid token")
    return

async with tunnel_lock:
    old_tunnel = tunnel
    tunnel = ws

if old_tunnel is not None and old_tunnel is not ws:
    try:
        await old_tunnel.close()
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
                print("Invalid DATA message")
                continue

            cid = parts[1]
            data_hex = parts[2]

            try:
                data = bytes.fromhex(data_hex)
            except ValueError:
                print("Invalid DATA hex:", cid)
                continue

            client = connections.get(cid)

            if client is not None:
                try:
                    await client.send(data)
                except Exception as error:
                    print(
                        "Client send error:",
                        cid,
                        repr(error)
                    )

        elif message.startswith("CLOSE:"):
            cid = message[6:]

            client = connections.pop(cid, None)

            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass

            print("Minecraft connection closed:", cid)

except websockets.exceptions.ConnectionClosed as error:
    print(
        "Tunnel connection closed:",
        error.code,
        repr(error.reason)
    )

except Exception as error:
    print("Tunnel error:", repr(error))

finally:
    async with tunnel_lock:
        if tunnel is ws:
            tunnel = None

    print("TUNNEL AGENT DISCONNECTED")
```

async def eagler_client(ws, first_message):
cid = str(uuid.uuid4())

```
connections[cid] = ws

print("Eagler client connected:", cid)

try:
    await send_tunnel("OPEN:" + cid)

    if isinstance(first_message, bytes):
        message = (
            "DATA:"
            + cid
            + ":"
            + first_message.hex()
        )

        await send_tunnel(message)

    elif isinstance(first_message, str):
        message = (
            "DATA:"
            + cid
            + ":"
            + first_message.encode().hex()
        )

        await send_tunnel(message)

    async for message in ws:

        if isinstance(message, bytes):
            tunnel_message = (
                "DATA:"
                + cid
                + ":"
                + message.hex()
            )

            await send_tunnel(tunnel_message)

        elif isinstance(message, str):
            tunnel_message = (
                "DATA:"
                + cid
                + ":"
                + message.encode().hex()
            )

            await send_tunnel(tunnel_message)

except websockets.exceptions.ConnectionClosed:
    pass

except Exception as error:
    print(
        "Eagler error:",
        cid,
        repr(error)
    )

finally:
    connections.pop(cid, None)

    try:
        await send_tunnel("CLOSE:" + cid)
    except Exception:
        pass

    print("Eagler client disconnected:", cid)
```

async def handle(ws):
try:
first_message = await ws.recv()

```
    if (
        isinstance(first_message, str)
        and first_message.startswith("AUTH:")
    ):
        await tunnel_agent(
            ws,
            first_message
        )

    else:
        await eagler_client(
            ws,
            first_message
        )

except websockets.exceptions.ConnectionClosed:
    pass

except Exception as error:
    print(
        "Handler error:",
        repr(error)
    )
```

async def main():
print("================================")
print("Minecraft relay starting")
print("Host:", HOST)
print("Port:", PORT)
print("WebSocket: /")
print("================================")

```
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
```

if **name** == "**main**":
asyncio.run(main())
