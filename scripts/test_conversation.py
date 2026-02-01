import asyncio
import websockets
import msgpack
import uuid

async def test_client():
    # Use 'ai-mock-test' to trigger the MockConversationalAgent
    room_id = "ai-mock-test" 
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
                            # Logic to print prettier
                            payload = data.get("payload", {})
                            ptype = data.get("type", "")
                            
                            if ptype == "audio_stream":
                                audio_len = len(payload.get("audio_data", b""))
                                print(f"[{username}] Received Audio: {audio_len} bytes")
                            else:
                                print(f"[{username}] Received Msg: {data}")
                        except:
                            print(f"[{username}] Received Bytes: {len(msg)} bytes")
                    else:
                         print(f"[{username}] Received Text: {msg}")
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")

        listen_task = asyncio.create_task(listen())
        
        # Send fake audio message continually to trigger the Mock STT (threshold > 16000 bytes)
        print("Sending audio stream...")
        audio_packet = {
            "type": "audio_stream",
            "payload": {
                "participant_id": username,
                "audio_data": b'\x01' * 1000, # 1KB per packet
                "timestamp": 123456
            }
        }
        packed = msgpack.packb(audio_packet, use_bin_type=True)
        
        # Send enough to trigger STT (~16 packets)
        for i in range(30):
            await websocket.send(packed)
            await asyncio.sleep(0.05)
        
        print("Finished sending audio. Waiting for response...")
        await asyncio.sleep(5)
        listen_task.cancel()

if __name__ == "__main__":
    asyncio.run(test_client())
