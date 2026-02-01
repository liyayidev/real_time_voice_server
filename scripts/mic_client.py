import asyncio
import websockets
import msgpack
import uuid
import sys
import time

try:
    import pyaudio
except ImportError:
    print("PyAudio not installed. Please install it to use the mic client.")
    sys.exit(1)

# Config
CHUNK = 320 # 20ms @ 16kHz
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

async def mic_client():
    room_id = "ai-mic-test"
    username = f"user-mic-{uuid.uuid4().hex[:4]}"
    uri = f"ws://127.0.0.1:8000/ws/{room_id}/{username}"

    p = pyaudio.PyAudio()
    
    # Open Stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* Recording and streaming to server...")

    async with websockets.connect(uri) as websocket:
        print(f"Connected as {username}")
        
        async def send_audio():
            while True:
                # Read from mic (non-blocking way is better, but this is simple client)
                data = stream.read(CHUNK, exception_on_overflow=False)
                
                msg = {
                    "type": "audio_stream",
                    "payload": {
                        "participant_id": username,
                        "audio_data": data,
                        "timestamp": int(time.time() * 1000)
                    }
                }
                packed = msgpack.packb(msg, use_bin_type=True)
                await websocket.send(packed)
                await asyncio.sleep(0.001)

        async def listen():
            try:
                while True:
                    msg = await websocket.recv()
                    if isinstance(msg, bytes):
                        try:
                            # If we get audio back, maybe play it?
                            # For now, just print stats
                            data = msgpack.unpackb(msg, raw=False)
                            if data.get("type") == "audio_stream":
                                size = len(data["payload"]["audio_data"])
                                print(f"Received Audio: {size} bytes", end='\r')
                        except:
                            pass
            except Exception as e:
                print(f"Listen error: {e}")

        # Run send and listen
        task_send = asyncio.create_task(send_audio())
        task_listen = asyncio.create_task(listen())
        
        await asyncio.gather(task_send, task_listen)
        
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(mic_client())
    except KeyboardInterrupt:
        print("\nStopping...")
