import asyncio
import websockets
import msgpack
import uuid

async def test_client():
    room_id = "ai-test-room" # Trigger auto-agent
    username = f"user-{uuid.uuid4().hex[:4]}"
    uri = f"ws://127.0.0.1:8000/ws/{room_id}/{username}"

    async with websockets.connect(uri) as websocket:
        print(f"Connected as {username}")
        
        # Keep alive/listen loop
        async def listen():
            try:
                while True:
                    msg = await websocket.recv()
                    # output may be bytes or str
                    if isinstance(msg, bytes):
                        # try unpack
                        try:
                            data = msgpack.unpackb(msg, raw=False)
                            # If from agent, it should look like the one we sent
                            print(f"[{username}] Received MsgPack: {data}")
                        except:
                            print(f"[{username}] Received Bytes: {len(msg)} bytes")
                    else:
                         print(f"[{username}] Received Text: {msg}")
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")

        listen_task = asyncio.create_task(listen())
        
        # Send fake audio message
        print("Sending audio packet (hello!)...")
        audio_packet = {
            "type": "audio_stream",
            "payload": {
                "participant_id": username,
                "audio_data": b"fake-audio-bytes-hello-world", 
                "timestamp": 123456
            }
        }
        packed = msgpack.packb(audio_packet, use_bin_type=True)
        await websocket.send(packed)
        
        # Send another one
        await asyncio.sleep(1)
        print("Sending second audio packet...")
        await websocket.send(packed)
        
        await asyncio.sleep(2)
        listen_task.cancel()

if __name__ == "__main__":
    asyncio.run(test_client())
