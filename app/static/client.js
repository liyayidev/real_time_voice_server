const SAMPLE_RATE = 16000;
const FRAME_SIZE = 320; // 20ms

let websocket = null;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let isConnected = false;
let startTime = 0;

// Update UI
const logDiv = document.getElementById("log");
const statusDiv = document.getElementById("status");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const micToggle = document.getElementById("micToggle");
const audioStats = document.getElementById("audioStats");

let bytesSent = 0;
let bytesRecv = 0;

function log(msg) {
    const time = new Date().toLocaleTimeString();
    logDiv.innerHTML += `<div>[${time}] ${msg}</div>`;
    logDiv.scrollTop = logDiv.scrollHeight;
}

function updateStatus(msg, color = "#eee") {
    statusDiv.textContent = `Status: ${msg}`;
    statusDiv.style.color = color;
}

connectBtn.onclick = async () => {
    const username = document.getElementById("username").value;
    const roomId = document.getElementById("roomId").value;
    if (!username || !roomId) return alert("Please enter username and room ID");

    // Init Audio Context first (permissions)
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
        await audioContext.resume();
    } catch (e) {
        log("Error initializing AudioContext: " + e);
        return;
    }

    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const port = window.location.port ? `:${window.location.port}` : "";
    const url = `${proto}://${window.location.hostname}${port}/ws/${roomId}/${username}`;

    websocket = new WebSocket(url);
    websocket.binaryType = "arraybuffer";

    websocket.onopen = () => {
        isConnected = true;
        updateStatus("Connected", "lightgreen");
        connectBtn.disabled = true;
        disconnectBtn.disabled = false;
        micToggle.disabled = false;
        log("WebSocket connected");
    };

    websocket.onclose = () => {
        isConnected = false;
        updateStatus("Disconnected", "red");
        connectBtn.disabled = false;
        disconnectBtn.disabled = true;
        micToggle.disabled = true;
        micToggle.checked = false;
        stopAudio();
        log("WebSocket disconnected");
    };

    websocket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
            try {
                const data = new Uint8Array(event.data);
                const msg = msgpack.decode(data);

                if (msg.type === "audio_stream") {
                    const payload = msg.payload;
                    const audioData = payload.audio_data; // This is Uint8Array (bytes)

                    bytesRecv += audioData.length;
                    updateStats();

                    // Decode (Simple Int16 -> Float32)
                    playPcmAudio(audioData);
                } else if (msg.type === "system") {
                    log(`System: ${msg.payload.message}`);
                }
            } catch (e) {
                console.error("Decode error", e);
            }
        }
    };
};

disconnectBtn.onclick = () => {
    if (websocket) websocket.close();
};

micToggle.onchange = async () => {
    if (micToggle.checked) {
        await startAudio();
    } else {
        stopAudio();
    }
};

async function startAudio() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = audioContext.createMediaStreamSource(mediaStream);

        // Use ScriptProcessor for raw access (Old API but simple for this demo)
        // audioWorklet is better for prod but requires extra file loading logic
        scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);

        scriptProcessor.onaudioprocess = (e) => {
            if (!isConnected) return;

            const inputData = e.inputBuffer.getChannelData(0);

            // Downsample / Convert to Int16
            // Note: Simplistic conversion. 
            // Web Audio is float32 [-1, 1]. We need Int16.
            // We also assume sample rate match roughly or server handles it.
            // If ctx is 48k and we want 16k, we skip samples.

            const ratio = audioContext.sampleRate / SAMPLE_RATE;
            const outputLength = Math.floor(inputData.length / ratio);
            const pcmData = new Int16Array(outputLength);

            for (let i = 0; i < outputLength; i++) {
                const offset = Math.floor(i * ratio);
                let s = Math.max(-1, Math.min(1, inputData[offset]));
                pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            // Send
            const msg = {
                type: "audio_stream",
                payload: {
                    participant_id: "web", // server ignores this usually and uses socket user
                    audio_data: new Uint8Array(pcmData.buffer),
                    timestamp: Date.now()
                }
            };

            const packed = msgpack.encode(msg);
            websocket.send(packed);

            bytesSent += packed.length;
            updateStats();
        };

        source.connect(scriptProcessor);
        scriptProcessor.connect(audioContext.destination); // destination is mute usually for mic, need to be careful of feedback loop
        // We actually shouldn't connect to destination if we don't want to hear ourselves. 
        // But Chrome requires connection to destination for ScriptProcessor to fire.
        // Solution: Create a Gain node with 0 gain.
        const muteNode = audioContext.createGain();
        muteNode.gain.value = 0;
        scriptProcessor.connect(muteNode);
        muteNode.connect(audioContext.destination);

        log("Microphone started");

    } catch (e) {
        log("Mic Error: " + e);
        micToggle.checked = false;
    }
}

function stopAudio() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }
    if (scriptProcessor) {
        scriptProcessor.disconnect();
        scriptProcessor = null;
    }
    log("Microphone stopped");
}

let nextPlayTime = 0;

function playPcmAudio(uint8Bytes) {
    // Convert Uint8Array -> Int16Array -> Float32
    const int16 = new Int16Array(uint8Bytes.buffer, uint8Bytes.byteOffset, uint8Bytes.byteLength / 2);
    const float32 = new Float32Array(int16.length);

    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768.0;
    }

    // Create buffer
    const buffer = audioContext.createBuffer(1, float32.length, SAMPLE_RATE);
    buffer.getChannelData(0).set(float32);

    // Schedule play
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    const now = audioContext.currentTime;
    if (nextPlayTime < now) nextPlayTime = now;

    source.start(nextPlayTime);
    nextPlayTime += buffer.duration;
}

function updateStats() {
    audioStats.innerText = `Audio: ${formatBytes(bytesSent)} sent / ${formatBytes(bytesRecv)} recv`;
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    const k = 1024;
    const sizes = ['KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
