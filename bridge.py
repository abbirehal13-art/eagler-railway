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
if tunnel is None:
raise ConnectionError("No tunnel agent connected")

```
    await tunnel.send(message)
```

async def tunnel_agent(ws, first_message):
global tunnel

```
if first_message != "AUTH:" + TOKEN:
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
            data_hex = parts[2]

            try:
                data = bytes.fromhex(data_hex)
            except ValueError:
                print("Invalid DATA:", cid)
                continue

            client = connections.get(cid)

            if client is not None:
                try:
                    await client.send(data)
                except Exception as e:
                    print("Client send error:", repr(e))

        elif message.startswith("CLOSE:"):
            cid = message[6:]

            client = connections.pop(cid, None)

            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass

            print("Minecraft connection closed:", cid)

except websockets.exceptions.ConnectionClosed as e:
    print("Tunnel closed:", e.code, repr(e.reason))

except Exception as e:
    print("Tunnel error:", repr(e))

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
        await send_tunnel(
            "DATA:" + cid + ":" + first_message.hex()
        )

    elif isinstance(first_message, str):
        await send_tunnel(
            "DATA:" + cid + ":" + first_message.encode().hex()
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

except Exception as e:
    print("Eagler error:", cid, repr(e))

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
        await tunnel_agent(ws, first_message)
    else:
        await eagler_client(ws, first_message)

except websockets.exceptions.ConnectionClosed:
    pass

except Exception as e:
    print("Handler error:", repr(e))
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

