#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os

# Configure basic logging to see outputs from the engines and this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Attempt to import the engine classes
try:
    from gtts_engine import GTTS_Engine
except ImportError:
    logger.critical("Failed to import GTTS_Engine from gtts_engine.py. Ensure the file exists and is accessible.")
    GTTS_Engine = None # Placeholder if import fails

try:
    from voicevox_tts_engine import Voicevox_Engine
except ImportError:
    logger.critical("Failed to import Voicevox_Engine from voicevox_tts_engine.py. Ensure the file exists and is accessible.")
    Voicevox_Engine = None # Placeholder if import fails

def main():
    logger.info("Starting TTS Engine tests...")

    # --- Test GTTS_Engine ---
    logger.info("\n" + "="*30 + "\nTesting GTTS_Engine...\n" + "="*30)
    if GTTS_Engine:
        gtts_engine = GTTS_Engine()

        # English test
        logger.info("Attempting GTTS English synthesis...")
        text_en = "Hello from gTTS engine. This is a test."
        audio_en = gtts_engine.synthesize_speech(text_en, "en")
        if audio_en:
            try:
                with open("gtts_test_output_en.mp3", "wb") as f:
                    f.write(audio_en)
                logger.info("SUCCESS: GTTS English audio saved to gtts_test_output_en.mp3")
            except IOError as e:
                logger.error(f"ERROR: Could not write GTTS English audio to file: {e}")
        else:
            logger.warning("FAIL: GTTS English synthesis returned no data.")

        # Japanese test
        logger.info("\nAttempting GTTS Japanese synthesis...")
        text_ja = "これはgTTSエンジンからのテストです。"
        audio_ja = gtts_engine.synthesize_speech(text_ja, "ja")
        if audio_ja:
            try:
                with open("gtts_test_output_ja.mp3", "wb") as f:
                    f.write(audio_ja)
                logger.info("SUCCESS: GTTS Japanese audio saved to gtts_test_output_ja.mp3")
            except IOError as e:
                logger.error(f"ERROR: Could not write GTTS Japanese audio to file: {e}")
        else:
            logger.warning("FAIL: GTTS Japanese synthesis returned no data.")
    else:
        logger.error("GTTS_Engine class not available. Skipping tests.")

    # --- Test Voicevox_Engine ---
    logger.info("\n" + "="*30 + "\nTesting Voicevox_Engine...\n" + "="*30)
    if Voicevox_Engine:
        # The Voicevox_Engine constructor will log connection attempts/failures.
        vv_engine = Voicevox_Engine()

        if not vv_engine.is_active:
            logger.warning("Voicevox_Engine is not active (failed to connect at init). Subsequent synthesis will be skipped by the engine.")

        # Japanese test
        logger.info("\nAttempting Voicevox Japanese synthesis...")
        text_vv_ja = "ボイスボックスエンジンのテストです。"
        # Using "1" as a placeholder. This might need to be a valid speaker ID
        # for your VOICEVOX engine setup if it were running.
        speaker_id_vv = "1"
        audio_vv_ja = vv_engine.synthesize_speech(text_vv_ja, "ja", speaker_id_vv)

        if audio_vv_ja:
            try:
                with open("voicevox_test_output_ja.wav", "wb") as f:
                    f.write(audio_vv_ja)
                logger.info("SUCCESS: Voicevox Japanese audio saved to voicevox_test_output_ja.wav")
            except IOError as e:
                logger.error(f"ERROR: Could not write Voicevox Japanese audio to file: {e}")
        else:
            # This is the expected outcome if the engine is not running and active.
            if not vv_engine.is_active:
                logger.info("INFO: Voicevox Japanese synthesis returned no data, as expected because engine is not active.")
            else:
                # If engine was active, this would be a failure.
                logger.warning("FAIL: Voicevox Japanese synthesis returned no data, even though engine reported as active (or test logic error).")
    else:
        logger.error("Voicevox_Engine class not available. Skipping tests.")

    logger.info("\nTTS Engine tests finished.")

    # Clean up created audio files
    files_to_remove = ["gtts_test_output_en.mp3", "gtts_test_output_ja.mp3", "voicevox_test_output_ja.wav"]
    for f_name in files_to_remove:
        if os.path.exists(f_name):
            try:
                os.remove(f_name)
                logger.info(f"Cleaned up test file: {f_name}")
            except OSError as e:
                logger.error(f"Error removing test file {f_name}: {e}")

if __name__ == '__main__':
    main()
