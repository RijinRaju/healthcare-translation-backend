import os
import asyncio
from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents, SpeakOptions
import anthropic
from dotenv import load_dotenv
import json
import time
from typing import Dict
import queue

load_dotenv()

app = FastAPI(title="Healthcare Translation API")

# Configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not DEEPGRAM_API_KEY or not CLAUDE_API_KEY:
    raise ValueError("Missing required API keys in environment variables")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for audio output
os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")

# Translation cache
translation_cache: Dict[str, str] = {}

async def translate_text(text: str, target_lang: str = "es") -> str:
    """Translate medical text using Claude AI with caching."""
    if not text.strip():
        return text
    
    cache_key = f"{target_lang}:{text}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system="You are a professional medical translator. Provide accurate translations of medical terminology. Translate only the text provided without adding any explanations or comments.",
            messages=[{
                "role": "user",
                "content": f"Translate this medical text to {target_lang}:\n\n{text}"
            }]
        )
        translated = message.content[0].text if message.content else text
        translation_cache[cache_key] = translated
        return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket, lang: str = Query("es")):
    """WebSocket endpoint for real-time transcription and translation."""
    await websocket.accept()
    
    # Queue for thread-safe communication
    transcript_queue = queue.Queue()
    
    # Session-level transcript accumulation
    current_transcript = ""
    last_sent_transcript = ""
    
    try:
        # Initialize Deepgram client
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.websocket.v("1")
        
        def on_message(self, result, **kwargs):
            """Handle Deepgram transcription events."""
            sentence = result.channel.alternatives[0].transcript
            if not sentence.strip():
                return
                
            nonlocal current_transcript
            
            # Update the current transcript
            if result.is_final:
                # For final results, only replace if it's longer or contains new information
                if len(sentence) > len(current_transcript) or not current_transcript.endswith(sentence.strip()):
                    current_transcript += " " + sentence if current_transcript else sentence
            else:
                # For interim results, update if it's more complete
                if len(sentence) > len(current_transcript):
                    current_transcript = sentence
            
            transcript_queue.put({
                "original": current_transcript.strip(),
                "is_final": result.is_final,
                "timestamp": time.time()
            })

        def on_error(self, error, **kwargs):
            """Handle Deepgram errors."""
            transcript_queue.put({"error": str(error)})

        # Configure Deepgram options
        options = LiveOptions(
            model="nova-2-medical",
            language="en-US",
            smart_format=True,
            punctuate=True,
            endpointing=300,
            vad_events=True,
            interim_results=True
        )
        
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        dg_connection.start(options)
        
        # Process queue and send to WebSocket
        async def process_queue():
            nonlocal last_sent_transcript
            
            while True:
                try:
                    data = transcript_queue.get(timeout=1.0)
                    
                    if "error" in data:
                        await websocket.send_text(json.dumps(data))
                    else:
                        # Only process if the transcript has changed significantly
                        transcript = data["original"]
                        is_final = data["is_final"]
                        
                        # Only send updates if:
                        # 1. It's a final result OR
                        # 2. The transcript is significantly different from the last sent
                        if (is_final or 
                            len(transcript) - len(last_sent_transcript) > 10 or
                            abs(len(transcript) - len(last_sent_transcript)) / max(1, len(last_sent_transcript)) > 0.2):
                            
                            print(f"Sending transcript: {transcript}")
                            translated = await translate_text(transcript, lang)
                            response = {
                                "original": transcript,
                                "translated": translated,
                                "is_final": is_final,
                                "timestamp": data["timestamp"]
                            }
                            await websocket.send_text(json.dumps(response))
                            last_sent_transcript = transcript
                            
                    transcript_queue.task_done()
                except queue.Empty:
                    await asyncio.sleep(0.1)  # Brief pause if queue is empty

        queue_task = asyncio.create_task(process_queue())
        
        # Main loop for receiving audio
        last_data_time = time.time()
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=5.0)
                dg_connection.send(data)
                last_data_time = time.time()
            except asyncio.TimeoutError:
                if time.time() - last_data_time > 30:  # 30s timeout
                    await websocket.send_text(json.dumps({"warning": "No audio data received for 30s"}))
                    break
                dg_connection.send(json.dumps({"type": "KeepAlive"}))

    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"WebSocket error: {str(e)}"}))
    finally:
        queue_task.cancel()
        dg_connection.finish()
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)