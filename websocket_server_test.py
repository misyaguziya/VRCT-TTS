#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SERVER - %(levelname)s - %(message)s')

PORT = 2231

async def actual_server_handler(websocket):
    client_addr = websocket.remote_address if websocket and hasattr(websocket, 'remote_address') else "Unknown client"
    logging.info(f"Client connected from {client_addr}")

    messages_to_send = [
        {"type": "SENT", "message": "Hello world, this is a test from the simulated VRCT.", "src_languages": ["en"], "dst_languages": ["ja"]},
        {"type": "RECEIVED", "message": "こんにちは世界、これはVRCTからのテストです。", "translation": "Hello world, this is a test from VRCT.", "src_languages": ["ja"], "dst_languages": ["en"]},
        {"type": "SENT", "message": "これは日本語のテストです。", "src_languages": ["ja"], "dst_languages": ["en"]},
        {"type": "RECEIVED", "message": "This is an English message.", "translation": "これは英語のメッセージです。", "src_languages": ["en"], "dst_languages": ["ja"]},
        {"type": "CHAT", "message": "Chat message in English, how are you doing today?", "src_languages": ["en"], "dst_languages": ["ja"]},
        {"type": "SENT", "message": "안녕하세요, 한국어 테스트입니다.", "src_languages": ["ko"], "dst_languages": ["en"]}, # Korean test
        {"type": "SENT", "message": "Hola mundo, esto es una prueba en español.", "src_languages": ["es"], "dst_languages": ["en"]}, # Spanish test
        {"type": "SENT", "message": "This is a message for en-GB.", "src_languages": ["en-GB"], "dst_languages": ["ja"]}, # Test for en-GB specific handling
    ]

    try:
        for i, message_data in enumerate(messages_to_send):
            try:
                await websocket.send(json.dumps(message_data))
                logging.info(f"Sent message ({i+1}/{len(messages_to_send)}): {message_data}")
                await asyncio.sleep(4) # Delay between messages to allow client processing time
            except websockets.exceptions.ConnectionClosed as e:
                logging.warning(f"Sender: Connection closed while trying to send: {e.reason} (code: {e.code}). Stopping sender.")
                break
            except Exception as e:
                logging.error(f"Sender: Error sending message: {e}", exc_info=True)
                break

        logging.info("Sender: Task finished sending all messages.")

        # Keep connection open for a bit longer to ensure client processes last message
        await asyncio.sleep(10)

        if not websocket.closed: # Check if not already closed by client
            logging.info("Sender: Attempting to close connection gracefully.")
            await websocket.close(code=1000, reason="Server finished sending messages")
            logging.info("Sender: Connection closed gracefully.")

    except Exception as e:
        logging.error(f"An error occurred in actual_server_handler: {e}", exc_info=True)
    finally:
        logging.info(f"Client {client_addr} processing finished in actual_server_handler.")


async def main():
    logging.info(f"Starting WebSocket server on ws://127.0.0.1:{PORT}")
    # Server will run for a longer duration to allow main.py to connect and interact fully.
    # It will stop sending messages after the list is exhausted but will keep listening.
    # The server itself will need to be manually stopped or run with a timeout if used in automated tests.
    # For this subtask, we run it in background and kill it.
    async with websockets.serve(actual_server_handler, "127.0.0.1", PORT):
        logging.info("Server started. Waiting for connections...")
        # This await asyncio.Future() will keep the server running indefinitely
        # until it's externally stopped or an unhandled exception occurs in main().
        # For the test script, we'll run it in the background and kill it.
        # If this script were run directly and meant to self-terminate:
        # await asyncio.sleep(60) # Example: run for 60 seconds
        # logging.info("Server shutting down after designated run time.")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server shutting down due to KeyboardInterrupt.")
    except Exception as e:
        logging.error(f"Server failed to start or run: {e}", exc_info=True)
