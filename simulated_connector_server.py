import asyncio
import websockets
import json
import time
from gtts import gTTS
import io
import logging

# Setup file logging for the server
logging.basicConfig(
    filename='/app/server_debug.log', # Changed path
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # Overwrite log file each time
)

CONNECTOR_PORT = 8765

async def handler(websocket): # Removed 'path'
    logging.info(f"Client connected from {websocket.remote_address}")
    print(f"Server: Client connected from {websocket.remote_address}") # Keep console for immediate feedback if possible
    try:
        async for message in websocket:
            logging.info(f"Received message: {message[:200]}") # Log first 200 chars
            print(f"Server: Received message: {message[:50]}") # Keep console for immediate feedback
            try:
                data = json.loads(message)
                request_id = data.get("request_id", "unknown_request")
                logging.info(f"Parsed JSON for request_id: {request_id}")

                if data.get("type") == "TTS_SYNTHESIZE":
                    text_to_synthesize = data.get("message")
                    lang_code = data.get("src_languages", "en")

                    if not text_to_synthesize:
                        error_msg = {"status": "error", "message": "No text provided for synthesis", "request_id": request_id}
                        logging.error(f"No text provided for synthesis for request_id: {request_id}")
                        await websocket.send(json.dumps(error_msg))
                        logging.info(f"Sent error response: {error_msg}")
                        continue

                    logging.info(f"Synthesizing '{text_to_synthesize[:30]}...' in {lang_code} for request_id: {request_id}")

                    status_msg = {"status": "synthesizing", "message": "Audio synthesis started", "request_id": request_id}
                    await websocket.send(json.dumps(status_msg))
                    logging.info(f"Sent status update: {status_msg}")
                    try:
                        start_time = time.time()
                        tts = gTTS(text=text_to_synthesize, lang=lang_code)
                        mp3_fp = io.BytesIO()
                        tts.write_to_fp(mp3_fp)
                        audio_bytes = mp3_fp.getvalue()
                        end_time = time.time()
                        synthesis_duration = end_time - start_time
                        logging.info(f"gTTS synthesis successful for request_id {request_id}. Duration: {synthesis_duration:.4f}s. Size: {len(audio_bytes)} bytes.")

                        success_status_msg = {
                            "status": "success",
                            "message": "Audio synthesized successfully",
                            "request_id": request_id,
                            "synthesis_duration_sec": round(synthesis_duration, 4)
                        }
                        await websocket.send(json.dumps(success_status_msg))
                        logging.info(f"Sent success status: {success_status_msg}")

                        await websocket.send(audio_bytes)
                        logging.info(f"Sent binary audio data (MP3) for request_id {request_id}.")

                    except Exception as e:
                        logging.exception(f"gTTS synthesis failed for request_id: {request_id}")
                        gtts_error_msg = {"status": "error", "message": f"gTTS synthesis failed: {str(e)}", "request_id": request_id}
                        await websocket.send(json.dumps(gtts_error_msg))
                        logging.info(f"Sent gTTS error: {gtts_error_msg}")

                else:
                    logging.warning(f"Unknown message type received: {data.get('type')}")
                    unknown_type_msg = {"status": "error", "message": f"Unknown message type: {data.get('type')}", "request_id": request_id}
                    await websocket.send(json.dumps(unknown_type_msg))
                    logging.info(f"Sent unknown type error: {unknown_type_msg}")

            except json.JSONDecodeError:
                logging.error("Invalid JSON message received.")
                error_msg = {"status": "error", "message": "Invalid JSON message received"}
                await websocket.send(json.dumps(error_msg)) # No request_id if root JSON fails
                logging.info(f"Sent JSON decode error: {error_msg}")
            except Exception as e:
                logging.exception("Error processing message") # This will log the stack trace
                try:
                    # Attempt to get request_id if data was partially parsed or available
                    req_id_for_err = data.get("request_id", "unknown") if 'data' in locals() else "unknown"
                    generic_error_msg = {"status": "error", "message": f"Internal server error: {str(e)}", "request_id": req_id_for_err}
                    await websocket.send(json.dumps(generic_error_msg))
                except: # If websocket is already closed or other issues
                    logging.error("Failed to send generic error to client after exception.")
    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"Client {websocket.remote_address} disconnected normally.")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.warning(f"Client {websocket.remote_address} connection closed with error: {e}")
    except Exception as e:
        logging.exception(f"An unexpected error occurred with client {websocket.remote_address}")


async def main():
    logging.info(f"Starting simulated connector WebSocket server on ws://0.0.0.0:{CONNECTOR_PORT}")
    print(f"Starting simulated connector WebSocket server on ws://0.0.0.0:{CONNECTOR_PORT}") # Keep for console
    async with websockets.serve(handler, "0.0.0.0", CONNECTOR_PORT):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server shutting down via KeyboardInterrupt...")
        print("Server shutting down...") # Keep for console
    except Exception as e:
        logging.exception("Server failed to start or run")
        print(f"Server failed to start or run: {e}") # Keep for console
