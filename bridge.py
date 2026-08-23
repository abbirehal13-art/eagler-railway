```python
import os
import asyncio
import uuid
import websockets
from websockets.http11 import Response
from websockets.datastructures import Headers


# ============================================================
# CONFIG
# ============================================================

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))

TOKEN = os.environ.get("TUNNEL_TOKEN")
if not TOKEN:
    raise RuntimeError("TUNNEL_TOKEN environment variable is missing")


# ============================================================
# GLOBAL STATE
# ============================================================

tunnel = None
tunnel_lock = asyncio.Lock()

# cid -> Eagler WebSocket
connections = {}


# ============================================================
# TUNNEL → EAGLER
# ============================================================

async def send_tunnel(message):
    async with tunnel_lock:
        current_tunnel = tunnel

        if current_tunnel is None:
            raise ConnectionError("No tunnel agent connected")

        await current_tunnel.send(message)


# ============================================================
# TUNNEL AGENT
# ============================================================

async def tunnel_agent(ws, first_message):
    global tunnel

    expected = "AUTH:" + TOKEN

    if first_message != expected:
        print("Rejected tunnel agent: invalid token")
        await ws.close()
        return

    async with tunnel_lock:
        # Replace an old/dead tunnel with this connection.
        old_tunnel = tunnel
        tunnel = ws

    if old_tunnel is not None and old_tunnel is not ws:
        try:
            await old_tunnel.close()
        except Exception:
            pass

    print("========================================")
    print("TUNNEL AGENT CONNECTED")
    print("========================================")

    try:
        async for message in ws:

            if not isinstance(message, str):
                continue

            # ------------------------------------------------
            # Railway → Daytona: send data to Minecraft
            # ------------------------------------------------

            if message.startswith("DATA:"):

                parts = message.split(":", 2)

                if len(parts) != 3:
                    print("Invalid DATA message")
                    continue

                cid = parts[1]
                hex_data = parts[2]

                try:
                    data = bytes.fromhex(hex_data)
                except ValueError:
                    print("Invalid hexadecimal DATA:", cid)
                    continue

                client = connections.get(cid)

                if client is not None:
                    try:
                        await client.send(data)
                    except Exception as e:
                        print("Client send error:", repr(e))

            # ------------------------------------------------
            # Minecraft connection closed
            # ------------------------------------------------

            elif message.startswith("CLOSE:"):

                cid = message[6:]
                client = connections.pop(cid, None)

                if client is not None:
                    try:
                        await client.close()
                    except Exception:
                        pass

                print("Closed Eagler connection:", cid)

    except websockets.exceptions.ConnectionClosed as e:
        print("Tunnel WebSocket closed:", repr(e))

    except Exception as e:
        print("Tunnel error:", repr(e))

    finally:

        async with tunnel_lock:
            if tunnel is ws:
                tunnel = None

        print("========================================")
        print("TUNNEL AGENT DISCONNECTED")
        print("========================================")


# ============================================================
# EAGLER CLIENT
# ============================================================

async def eagler_client(ws, first_message):

    cid = str(uuid.uuid4())

    connections[cid] = ws

    print("Eagler client connected:", cid)

    try:

        # Tell Daytona to open a Minecraft TCP connection.
        await send_tunnel(
            "OPEN:" + cid
        )

        # Forward the first WebSocket message.
        if isinstance(first_message, bytes):

            await send_tunnel(
                f"DATA:{cid}:{first_message.hex()}"
            )

        elif isinstance(first_message, str):

            await send_tunnel(
                f"DATA:{cid}:{first_message.encode().hex()}"
            )

        # Forward subsequent messages.
        async for message in ws:

            if isinstance(message, bytes):

                await send_tunnel(
                    f"DATA:{cid}:{message.hex()}"
                )

            elif isinstance(message, str):

                await send_tunnel(
                    f"DATA:{cid}:{message.encode().hex()}"
                )

    except ConnectionError as e:

        print(
            "Eagler connection failed:",
            cid,
            repr(e)
        )

    except websockets.exceptions.ConnectionClosed as e:

        print(
            "Eagler WebSocket closed:",
            cid,
            repr(e)
        )

    except Exception as e:

        print(
            "Eagler error:",
            cid,
            repr(e)
        )

    finally:

        connections.pop(cid, None)

        try:
            await send_tunnel(
                "CLOSE:" + cid
            )
        except Exception:
            pass

        print(
            "Eagler client disconnected:",
            cid
        )


# ============================================================
# WEBSOCKET CONNECTION HANDLER
# ============================================================

async def handle(ws):

    try:

        first_message = await ws.recv()

        # Tunnel agent authentication.
        if (
            isinstance(first_message, str)
            and first_message.startswith("AUTH:")
        ):

            await tunnel_agent(
                ws,
                first_message
            )

            return

        # Otherwise this is an Eagler client.
        await eagler_client(
            ws,
            first_message
        )

    except websockets.exceptions.ConnectionClosed as e:

        print(
            "Connection closed during handshake:",
            repr(e)
        )

    except Exception as e:

        print(
            "Connection handler error:",
            repr(e)
        )


# ============================================================
# HTTP HEALTH CHECK
# ============================================================

async def process_request(connection, request):

    if request.path == "/health":

        headers = Headers()

        headers["Content-Type"] = "text/plain"
        headers["Content-Length"] = "2"

        return Response(
            200,
            "OK",
            headers,
            b"OK",
        )

    return None


# ============================================================
# SERVER
# ============================================================

async def main():

    print("========================================")
    print("Starting Minecraft relay")
    print("========================================")
    print("Host:", HOST)
    print("Port:", PORT)
    print("Health: /health")
    print("WebSocket endpoint: /")
    print("========================================")

    async with websockets.serve(
        handle,
        HOST,
        PORT,
        max_size=None,
        ping_interval=20,
        ping_timeout=60,
        close_timeout=10,
        process_request=process_request,
    ):

        print("Minecraft relay is READY")

        await asyncio.Future()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    asyncio.run(main())
```

