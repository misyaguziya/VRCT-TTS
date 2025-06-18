import websocket
import threading
import time
import json
import logging
import sys

# Setup file logging for the client
logging.basicConfig(
    filename='/app/client_debug.log', # Changed path
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'  # Overwrite log file each time
)
# Redirect websocket trace to client log
# Note: websocket-client's enableTrace sends to logging.getLogger('websocket').addHandler(logging.StreamHandler())
# So, we need to configure that logger.
ws_logger = logging.getLogger('websocket')
ws_logger.setLevel(logging.INFO) # Or DEBUG for more verbosity
file_handler = logging.FileHandler('/app/client_ws_trace.log', mode='w') # Changed path
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
ws_logger.addHandler(file_handler)


SERVER_URL = "ws://127.0.0.1:8765"  # Make sure this matches the server

def on_message(ws, message):
    logging.info(f"Received message type: {'bytes' if isinstance(message, bytes) else 'text'}")
    current_request_id_for_binary = ws.last_sent_request_id if hasattr(ws, 'last_sent_request_id') else "unknown_binary"

    if isinstance(message, bytes):
        logging.info(f"Received binary message (audio data for {current_request_id_for_binary}), length: {len(message)}")
        print(f"Client: Received binary message (audio data for {current_request_id_for_binary}), length: {len(message)}")
        try:
            # Save with a unique name based on request_id to check all audio files
            filename = f"received_audio_{current_request_id_for_binary}.mp3"
            with open(filename, "wb") as f:
                f.write(message)
            logging.info(f"Binary data saved to {filename}")
            print(f"Client: Binary data saved to {filename}")

            # Only exit after the LAST expected audio message
            if current_request_id_for_binary == "req07_chat":
                logging.info("Final audio received, closing connection and exiting.")
                print("Client: Final audio received, closing connection and exiting.")
                ws.close()
                sys.exit(0) # Force exit after processing the final expected audio
        except Exception as e:
            logging.exception("Error saving binary data or exiting")
            print(f"Client: Error saving binary data: {e}")
            # sys.exit(1) # Don't exit on error for one audio, allow others to process
    else:
        logging.info(f"Received text message: {message}")
        print(f"Client: Received text message: {message}")
        try:
            data = json.loads(message)
            req_id = data.get("request_id", "unknown_text")
            logging.info(f"Received JSON status for request_id '{req_id}': {data.get('status')} - {data.get('message')}")
            print(f"Client: Received JSON status for request_id '{req_id}': {data.get('status')} - {data.get('message')}")
        except json.JSONDecodeError:
            logging.warning("Received non-JSON text message.")
            print("Client: Received non-JSON text message.")


def on_error(ws, error):
    logging.error(f"Error: {error}")
    print(f"Client: Error: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info(f"### Connection closed ### code: {close_status_code}, msg: {close_msg}")
    print(f"Client: ### Connection closed ### code: {close_status_code}, msg: {close_msg}")

def on_open(ws):
    logging.info("### Connection opened ###")
    print("Client: ### Connection opened ###")
    def run(*args):
        try:
            time.sleep(1)
            # 1. TTS_GET_VOICES
            get_voices_req = {"command": "TTS_GET_VOICES", "request_id": "req01"}
            ws.send(json.dumps(get_voices_req))
            logging.info(f"Sent: {json.dumps(get_voices_req)}")
            print(f"Client: Sent: {json.dumps(get_voices_req)}")
            time.sleep(0.5)

            # 2. TTS_SET_DEFAULT_VOICE (example)
            set_default_voice_req = {"command": "TTS_SET_DEFAULT_VOICE", "request_id": "req02", "voice_id": "co.uk"}
            ws.send(json.dumps(set_default_voice_req))
            logging.info(f"Sent: {json.dumps(set_default_voice_req)}")
            print(f"Client: Sent: {json.dumps(set_default_voice_req)}")
            time.sleep(0.5)

            # 3. TTS_SET_GLOBAL_SETTINGS (example)
            set_global_settings_req = {"command": "TTS_SET_GLOBAL_SETTINGS", "request_id": "req03", "settings": {"language": "ja"}}
            ws.send(json.dumps(set_global_settings_req))
            logging.info(f"Sent: {json.dumps(set_global_settings_req)}")
            print(f"Client: Sent: {json.dumps(set_global_settings_req)}")
            time.sleep(0.5)

            # 4. TTS_SYNTHESIZE (SENT type) - First time (cache miss expected)
            tts_synthesize_sent_1 = {
                "command": "TTS_SYNTHESIZE", "request_id": "req04_sent_1",
                "type": "SENT",
                "message": "Hello, this is a test message from VRCT.",
                "src_languages": "en",
                "voice_id": "com" # Example TLD
            }
            ws.send(json.dumps(tts_synthesize_sent_1))
            logging.info(f"Sent: {json.dumps(tts_synthesize_sent_1)}")
            print(f"Client: Sent: {json.dumps(tts_synthesize_sent_1)}")
            time.sleep(2) # Allow time for synthesis

            # 5. TTS_SYNTHESIZE (SENT type) - Second time (cache hit expected)
            tts_synthesize_sent_2 = {
                "command": "TTS_SYNTHESIZE", "request_id": "req05_sent_2",
                "type": "SENT",
                "message": "Hello, this is a test message from VRCT.", # Same text, lang, voice
                "src_languages": "en",
                "voice_id": "com"
            }
            ws.send(json.dumps(tts_synthesize_sent_2))
            logging.info(f"Sent: {json.dumps(tts_synthesize_sent_2)}")
            print(f"Client: Sent: {json.dumps(tts_synthesize_sent_2)}")
            time.sleep(2) # Allow time for cache retrieval / synthesis

            # 6. TTS_SYNTHESIZE (RECEIVED type)
            tts_synthesize_received = {
                "command": "TTS_SYNTHESIZE", "request_id": "req06_received",
                "type": "RECEIVED",
                "translation": "こんにちは、これはVRCTからの翻訳テストメッセージです。", # Japanese text
                "dst_languages": "ja", # Japanese lang code
                "voice_id": "co.jp" # Japanese TLD
            }
            ws.send(json.dumps(tts_synthesize_received))
            logging.info(f"Sent: {json.dumps(tts_synthesize_received)}")
            print(f"Client: Sent: {json.dumps(tts_synthesize_received)}")
            time.sleep(2)

            # 7. TTS_SYNTHESIZE (CHAT type)
            tts_synthesize_chat = {
                "command": "TTS_SYNTHESIZE", "request_id": "req07_chat",
                "type": "CHAT",
                "message": "This is a chat message.",
                "src_languages": "en",
                "voice_id": "com.au" # Australian TLD
            }
            ws.send(json.dumps(tts_synthesize_chat))
            logging.info(f"Sent: {json.dumps(tts_synthesize_chat)}")
            print(f"Client: Sent: {json.dumps(tts_synthesize_chat)}")
            time.sleep(2)

            # 8. TTS_STOP (Conceptual)
            tts_stop_req = {"command": "TTS_STOP", "request_id": "req08_stop"}
            ws.send(json.dumps(tts_stop_req))
            logging.info(f"Sent: {json.dumps(tts_stop_req)}")
            print(f"Client: Sent: {json.dumps(tts_stop_req)}")

            # Client will exit when it receives the binary message for the last TTS_SYNTHESIZE
            # or one of the earlier ones if sys.exit() is hit.
            # The current logic in on_message is to exit on *any* binary message.
            # For this test sequence, we want to receive multiple binary messages.
            # So, the sys.exit(0) in on_message needs to be conditional or removed for full test.
            # For now, it will exit after the first successful TTS_SYNTHESIZE.
            # This needs refinement if we want to test sequence of multiple TTS_SYNTHESIZE.
            # Let's assume for this test run, we are okay with it exiting after first audio.
            # The server logs will show processing of subsequent messages if client hangs around.

        except Exception as e:
            logging.exception("Error in on_open run thread")
            print(f"Client: Error in on_open run thread: {e}")
            # Optionally try to close ws here if error occurs before normal flow
            # ws.close()
            # sys.exit(1) # Consider if thread errors should terminate main client

    # Store last sent request_id on ws object to correlate binary audio
    original_send = ws.send
    def send_with_req_id_tracking(payload, opcode=websocket.ABNF.OPCODE_TEXT):
        if opcode == websocket.ABNF.OPCODE_TEXT:
            try:
                data = json.loads(payload)
                ws.last_sent_request_id = data.get("request_id", "unknown_send")
            except:
                ws.last_sent_request_id = "unknown_non_json_send"
        return original_send(payload, opcode)
    ws.send = send_with_req_id_tracking

    threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    logging.info("Client script started.")
    print("Client script started. Logging to /tmp/client_debug.log and /tmp/client_ws_trace.log")

    websocket.enableTrace(True) # This will now log to the file handler configured for 'websocket' logger

    ws_client = websocket.WebSocketApp(SERVER_URL,
                                       on_open=on_open,
                                       on_message=on_message,
                                       on_error=on_error,
                                       on_close=on_close)

    logging.info(f"Attempting to connect to {SERVER_URL}...")
    print(f"Client: Attempting to connect to {SERVER_URL}...")
    try:
        ws_client.run_forever()
    except Exception as e:
        logging.exception("ws_client.run_forever() raised an exception.")
        print(f"Client: ws_client.run_forever() failed: {e}")
    finally:
        logging.info("Client script finished or run_forever exited.")
        print("Client: Exited.")
