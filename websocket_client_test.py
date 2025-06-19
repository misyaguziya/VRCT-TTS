#!/usr/bin/env python3
import websocket
import json
import html
import time
import threading
import logging
import os
from gtts import gTTS

# Client log file
CLIENT_LOG_FILE = "/app/client.log" # Absolute path

# Configure logging to also go to a file
# Clear previous log file if it exists
if os.path.exists(CLIENT_LOG_FILE):
    os.remove(CLIENT_LOG_FILE)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - CLIENT - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CLIENT_LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)

# Attempt to import VOICEVOX components
VOICEVOX_AVAILABLE = False
try:
    from voicevox import VOICEVOXClient
    from voicevox_speaker import VoicevoxSpeaker
    VOICEVOX_AVAILABLE = True
    logging.info("VOICEVOXClient and VoicevoxSpeaker imported successfully.")
except ImportError as e:
    logging.warning(f"Could not import VOICEVOX components: {e}. VOICEVOX path will be skipped.")
except Exception as e:
    logging.error(f"An unexpected error occurred during VOICEVOX component import: {e}")


WS_URL = "ws://127.0.0.1:2231"
stop_client_event = threading.Event()
AUDIO_FILE_NAME = "/app/temp_gtts_audio.mp3" # Absolute path

def play_audio_mock(filename):
    logging.info(f"MOCK PLAYBACK: Would play {filename} here if enabled.")
    # Actual playback is removed to prevent blocking and environment issues.
    # try:
    #     player_command = ""
    #     if os.name == 'posix':
    #         if os.system(f"which afplay > /dev/null 2>&1") == 0:
    #             player_command = f"afplay {filename} > /dev/null 2>&1"
    #         elif os.system(f"which mpg123 > /dev/null 2>&1") == 0:
    #             player_command = f"mpg123 -q {filename} > /dev/null 2>&1"
    #         else:
    #             logging.warning("No suitable audio player (mpg123 or afplay) found. Cannot play audio.")
    #             logging.info(f"Audio saved to {filename}")
    #             return

    #         # os.system(player_command) # EXECUTION REMOVED

    #     elif os.name == 'nt':
    #         # os.system(f"start {filename}") # EXECUTION REMOVED
    #         pass
    #     else:
    #         logging.warning(f"Unsupported OS ({os.name}) for audio playback.")
    #         logging.info(f"Audio saved to {filename}")
    #         return
    #     logging.info(f"Attempted to play {filename} (command: {player_command if player_command else 'start ...'}).")
    # except Exception as e:
    #     logging.error(f"Error playing audio file {filename}: {e}")
    #     logging.info(f"Audio saved to {filename}")


def on_message(ws, message_str):
    try:
        logging.info(f"Raw message received: {message_str}")
        data = json.loads(message_str)
        message_type = data.get("type")

        if message_type == "SENT" or message_type == "CHAT":
            received_message = data.get("message", "")
            decoded_message = html.unescape(received_message)

            logging.info(f"Processed message - Type: {message_type}, Original: '{received_message}', Decoded: '{decoded_message}'")

            # gTTS Path
            text_to_speak = decoded_message
            lang = ''
            if "hello world" in text_to_speak.lower():
                lang = 'en'
            elif "こんにちは世界" in text_to_speak:
                lang = 'ja'

            if lang:
                try:
                    logging.info(f"Attempting gTTS synthesis for lang='{lang}', text='{text_to_speak}'")
                    tts = gTTS(text=text_to_speak, lang=lang)
                    tts.save(AUDIO_FILE_NAME)
                    logging.info(f"gTTS audio saved to {AUDIO_FILE_NAME}")
                    play_audio_mock(AUDIO_FILE_NAME) # Using mocked playback
                except Exception as e:
                    logging.error(f"gTTS processing failed: {e}", exc_info=True)
            else:
                logging.info("No specific language detected for gTTS for this message.")

            # Simulate VOICEVOX Path
            if VOICEVOX_AVAILABLE:
                if "world" in text_to_speak.lower() or "世界" in text_to_speak:
                    logging.info("Attempting VOICEVOX synthesis path...")
                    try:
                        vv_client = VOICEVOXClient()
                        try:
                            speakers_info = vv_client.speakers()
                            if not speakers_info:
                                logging.warning("VOICEVOX engine returned no speakers.")
                                raise ConnectionRefusedError("No speakers from VOICEVOX engine")

                            speaker_id_to_use = None
                            # Simplified speaker selection for testing
                            if speakers_info and speakers_info[0].get("styles"):
                                speaker_id_to_use = speakers_info[0]["styles"][0]["id"]
                                logging.info(f"Using first available speaker ID for VOICEVOX: {speaker_id_to_use}")
                            else:
                                logging.error("Could not determine a speaker ID for VOICEVOX (no speakers or styles found).")
                                raise ValueError("No suitable VOICEVOX speaker ID found.")

                            logging.info(f"VOICEVOX: Attempting query and synthesis with speaker ID: {speaker_id_to_use} for text: '{text_to_speak}'")
                            query = vv_client.audio_query(text_to_speak, speaker_id_to_use)
                            audio_data = vv_client.synthesis(query, speaker_id_to_use)

                            if audio_data:
                                logging.info(f"VOICEVOX synthesis successful (audio data length: {len(audio_data)}).")
                                logging.info("VOICEVOX audio would be played here if enabled.")
                            else:
                                logging.warning("VOICEVOX synthesis returned no audio data.")

                        except ConnectionRefusedError:
                            logging.warning("VOICEVOX path: Failed to connect to engine at default localhost:50021 (Connection Refused). This is expected if engine is not running.")
                        except Exception as e_vv_inner:
                            logging.error(f"VOICEVOX path: Error during synthesis process: {e_vv_inner}", exc_info=True)

                    except Exception as e_vv_outer:
                        logging.error(f"VOICEVOX path: Outer error: {e_vv_outer}", exc_info=True)
                else:
                    logging.info("Message not designated for VOICEVOX path test this time.") # Should not happen with current server msgs
            else:
                logging.info("VOICEVOX components not available, skipping VOICEVOX path.")
        else:
            logging.info(f"Received other message type or format: {data}")

    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON: {message_str}")
    except Exception as e:
        logging.error(f"Error processing message: {e}", exc_info=True)

def on_error(ws, error):
    logging.error(f"WebSocket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    logging.info(f"WebSocket Closed: Status {close_status_code}, Message: {close_msg}")
    stop_client_event.set()

def on_open(ws):
    logging.info("WebSocket Connection Opened. Listening for messages...")

def start_websocket_client():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    logging.info(f"Attempting to connect to {WS_URL}...")
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    # Let client run until server closes connection or timeout
    if not stop_client_event.wait(timeout=25): # Slightly increased timeout
        logging.info("Client timeout reached, attempting to close WebSocket.")
        if wst.is_alive(): # Check if WebSocket thread is running
             ws.close()
    logging.info("Exiting client main thread function.")


if __name__ == "__main__":
    if os.name == 'posix' and os.system("which mpg123 > /dev/null 2>&1") != 0 and os.system("which afplay > /dev/null 2>&1") != 0:
        logging.warning("mpg123 or afplay is not installed. Audio playback will be skipped for gTTS. Please install a player if audio is desired (e.g., 'sudo apt-get install mpg123').")

    try:
        start_websocket_client()
        logging.info("WebSocket client processing finished.")
    except KeyboardInterrupt:
        logging.info("\nWebSocket client shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"Client failed: {e}", exc_info=True)
    finally:
        if os.path.exists(AUDIO_FILE_NAME):
            try:
                os.remove(AUDIO_FILE_NAME)
                logging.info(f"Temporary audio file {AUDIO_FILE_NAME} removed.")
            except Exception as e_rm:
                logging.error(f"Error removing temporary audio file {AUDIO_FILE_NAME}: {e_rm}")
        logging.info("Client program fully finished.")
