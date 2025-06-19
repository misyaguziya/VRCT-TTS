#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import os
import shutil
import html
from typing import List, Dict, Any, Optional

# Configure logging for this test script
# Set to DEBUG to capture all new logs, including raw messages and TTSManager debug logs
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - TEST_INTEGRATION - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get logger for this module

# Attempt to import necessary classes
try:
    from tts_manager import TTSManager
    from config import Config # Used for setting specific config file for tests
    # Import engine classes only to ensure they are available if TTSManager needs them,
    # not for direct use in this test script.
    from gtts_engine import GTTS_Engine
    from voicevox_tts_engine import Voicevox_Engine

except ImportError as e:
    logger.critical(f"Failed to import necessary modules: {e}. Ensure all engine and config files are accessible.")
    TTSManager = None # Prevent tests from running if imports fail
    Config = None


# Define default test configuration settings
# This mirrors the structure expected by Config.load() and TTSManager
DEFAULT_TEST_CONFIG_SETTINGS = {
    "language_engine_mapping": {
        "default_engine": "gtts",
        "language_specific": [
            {"lang_code": "ja", "engine": "voicevox", "voice_id": "1"}, # Japanese uses Voicevox speaker 1
            {"lang_code": "ja-JP", "engine": "voicevox", "voice_id": "1"},
            {"lang_code": "en", "engine": "gtts", "voice_id": None},
            {"lang_code": "en-US", "engine": "gtts", "voice_id": None},
            # Example of engine-specific param in config for tld
            {"lang_code": "en-GB", "engine": "gtts", "voice_id": None, "tld_config_key_for_gtts": "co.uk"},
            {"lang_code": "ko", "engine": "gtts", "voice_id": None},
            {"lang_code": "ko-KR", "engine": "gtts", "voice_id": None}
        ],
        "fallback_engine": "gtts"
    },
    "user_preferred_voices": {
        "gtts": {"default_voice_id": None},
        "voicevox": {"default_voice_id": "1"}
    },
    # Include default general settings that Config.py would normally provide
    "speaker_id": 1, "device_index": None, "device_index_2": None, "speaker_2_enabled": False,
    "host_name": "すべて", "host_name_2": "すべて", "volume": 0.8, "ws_url": "ws://127.0.0.1:2231"
}

TEMP_CONFIG_FILENAME = "/app/temp_config_integration.json"
ORIGINAL_CONFIG_BACKUP_FILENAME = "/app/config.json.integration_backup"
TEST_AUDIO_OUTPUT_DIR = "/app/test_audio_outputs"


def setup_test_config_for_integration(config_dict: Dict[str, Any], config_filename: str = TEMP_CONFIG_FILENAME) -> Optional[str]:
    logger.info(f"Setting up test config at: {config_filename}")

    original_config_file_path = Config.CONFIG_FILE # This is the actual path used by Config class (e.g. /app/config.json)

    if os.path.exists(original_config_file_path):
        try:
            shutil.copyfile(original_config_file_path, ORIGINAL_CONFIG_BACKUP_FILENAME)
            logger.info(f"Backed up existing original config '{original_config_file_path}' to '{ORIGINAL_CONFIG_BACKUP_FILENAME}'")
        except Exception as e:
            logger.error(f"Failed to back up original config '{original_config_file_path}': {e}")
            pass
    elif os.path.exists(ORIGINAL_CONFIG_BACKUP_FILENAME):
        # If original doesn't exist but backup does, means previous cleanup might have failed to restore
        os.remove(ORIGINAL_CONFIG_BACKUP_FILENAME)
        logger.info(f"Removed stale backup file: {ORIGINAL_CONFIG_BACKUP_FILENAME}")


    try:
        with open(config_filename, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
        logger.info(f"Test config content written to {config_filename}")
        return original_config_file_path
    except Exception as e:
        logger.error(f"Failed to write test config to {config_filename}: {e}")
        return None

def cleanup_test_config_for_integration(original_config_file_path_to_restore_to: Optional[str], test_config_filename_used: str = TEMP_CONFIG_FILENAME):
    logger.info(f"Cleaning up test config: {test_config_filename_used}")
    if os.path.exists(test_config_filename_used):
        try:
            os.remove(test_config_filename_used)
            logger.info(f"Removed test config file: {test_config_filename_used}")
        except Exception as e:
            logger.error(f"Failed to remove test config file {test_config_filename_used}: {e}")

    if os.path.exists(ORIGINAL_CONFIG_BACKUP_FILENAME):
        if original_config_file_path_to_restore_to: # This is the path where Config.CONFIG_FILE points
            try:
                shutil.move(ORIGINAL_CONFIG_BACKUP_FILENAME, original_config_file_path_to_restore_to)
                logger.info(f"Restored original config to '{original_config_file_path_to_restore_to}' from backup.")
            except Exception as e:
                logger.error(f"Failed to restore original config from backup: {e}")
        else:
            os.remove(ORIGINAL_CONFIG_BACKUP_FILENAME)
            logger.warning(f"Removed backup config file '{ORIGINAL_CONFIG_BACKUP_FILENAME}' as original path was not specified for restore.")
    elif original_config_file_path_to_restore_to and os.path.exists(original_config_file_path_to_restore_to) and original_config_file_path_to_restore_to != test_config_filename_used :
        # If no backup existed, but the original config file path is known and IS NOT the temp test file path
        # then it means the original config file might have been created by Config.load() with defaults.
        # We should clean it up to leave a truly clean state if it wasn't there before test.
        # This logic is tricky; for now, simpler cleanup is above.
        # The main goal is that Config.CONFIG_FILE points to the right place after tests.
        pass


def save_test_audio(audio_data: Optional[bytes], base_filename: str, index: int, audio_format_hint: str = "audio"):
    if not audio_data:
        logger.warning(f"Test {index} ({base_filename}): No audio data to save.")
        return

    if not os.path.exists(TEST_AUDIO_OUTPUT_DIR):
        try:
            os.makedirs(TEST_AUDIO_OUTPUT_DIR)
            logger.info(f"Created test audio output directory: {TEST_AUDIO_OUTPUT_DIR}")
        except OSError as e:
            logger.error(f"Failed to create test audio output directory {TEST_AUDIO_OUTPUT_DIR}: {e}")
            return


    extension = ".wav" if audio_format_hint == "wav" else ".mp3"
    if audio_format_hint == "audio":
         if audio_data.startswith(b'RIFF'): extension = ".wav"
         elif audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb'): extension = ".mp3"


    filepath = os.path.join(TEST_AUDIO_OUTPUT_DIR, f"{base_filename}_{index}{extension}")
    try:
        with open(filepath, "wb") as f:
            f.write(audio_data)
        logger.info(f"Test {index} ({base_filename}): Audio data saved to {filepath} (Size: {len(audio_data)} bytes)")
    except IOError as e:
        logger.error(f"Test {index} ({base_filename}): ERROR - Could not write audio to file {filepath}: {e}")


def run_simulated_on_message_logic(test_messages_list: List[Dict[str, Any]], config_to_use: Dict[str, Any], test_run_label: str):
    logger.info(f"\n--- Starting Test Run: {test_run_label} ---")

    # Initialize counters for simulating main.py's logic
    ws_message_count = 0
    sent_type_count = 0
    received_type_count = 0
    chat_type_count = 0
    successful_synthesis_count = 0
    failed_synthesis_count = 0

    original_config_class_var_val = Config.CONFIG_FILE

    # This setup function writes to TEMP_CONFIG_FILENAME and returns the original Config.CONFIG_FILE value
    path_of_config_to_restore_later = setup_test_config_for_integration(config_to_use, TEMP_CONFIG_FILENAME)
    if not path_of_config_to_restore_later: # If setup failed to write the temp config
        logger.error("Aborting test run due to setup_test_config failure.")
        return

    Config.CONFIG_FILE = TEMP_CONFIG_FILENAME # Crucial: Point Config class to use the temporary file

    tts_manager = None
    try:
        tts_manager = TTSManager() # Instantiates with the temp config

        for i, msg_data in enumerate(test_messages_list):
            ws_message_count += 1
            # Simulate main.py's raw message logging (already set to DEBUG for the script's root logger)
            logger.debug(f"Simulated Raw WebSocket message received: {msg_data}")

            logger.info(f"\nProcessing message {i+1}/{len(test_messages_list)} ({ws_message_count} overall) for {test_run_label}: {msg_data.get('type')} - {msg_data.get('message')[:30]}...")

            message_type = msg_data.get("type")
            if message_type == "SENT":
                sent_type_count += 1
            elif message_type == "RECEIVED":
                received_type_count += 1
            elif message_type == "CHAT":
                chat_type_count += 1

            original_message = html.unescape(msg_data.get("message", ""))
            translation = html.unescape(msg_data.get("translation", ""))
            src_languages = msg_data.get("src_languages", ["en"])
            dst_languages = msg_data.get("dst_languages", ["en"])

            text_to_synthesize = None
            lang_to_synthesize_in = None
            tts_kwargs = {}

            if message_type == "SENT":
                text_to_synthesize = original_message
                lang_to_synthesize_in = src_languages[0] if src_languages else "en"
                if lang_to_synthesize_in.lower() == "en-gb":
                     # Check if config has specific tld for en-GB for gTTS
                     for rule in config_to_use.get("language_engine_mapping",{}).get("language_specific",[]):
                         if rule.get("lang_code","").lower() == "en-gb" and rule.get("engine","").lower() == "gtts":
                             if "tld_config_key_for_gtts" in rule: # Use specific key from config
                                 tts_kwargs['tld'] = rule["tld_config_key_for_gtts"]
                                 break
            elif message_type == "RECEIVED":
                text_to_synthesize = translation if translation else original_message
                lang_to_synthesize_in = dst_languages[0] if dst_languages else "en"
            elif message_type == "CHAT":
                text_to_synthesize = original_message
                lang_to_synthesize_in = src_languages[0] if src_languages else "en"

            logger.info(f"Determined for synthesis: text='{text_to_synthesize[:30]}...', lang='{lang_to_synthesize_in}', kwargs={tts_kwargs}")

            if text_to_synthesize and lang_to_synthesize_in:
                # Ensure TTSManager uses the re-pointed Config.CONFIG_FILE by re-loading if necessary
                # or ensure its initial load got the right one. TTSManager loads on init.
                # If TTSManager's self.config is not updated, this test won't reflect config changes.
                # The current TTSManager reloads config via reload_config() or on new instantiation.
                # We created a new TTSManager instance after setting Config.CONFIG_FILE, so it's fine.

                audio_data = tts_manager.synthesize(
                    text_to_synthesize,
                    lang_to_synthesize_in,
                    target_message_type=message_type,
                    **tts_kwargs
                )

                if audio_data:
                    logger.info(f"Audio generated: True, Length: {len(audio_data)} bytes")
                    params_for_saving = tts_manager.determine_synthesis_parameters(lang_to_synthesize_in)
                    engine_used_for_saving = params_for_saving.get("engine_name", "unknown")
                    audio_format_hint = "wav" if engine_used_for_saving == "voicevox" else "mp3"

                    # If voicevox was chosen but is inactive, fallback (likely gTTS) will be used
                    if tts_manager.voicevox_engine and not tts_manager.voicevox_engine.is_active and engine_used_for_saving == "voicevox":
                        fallback_engine_name = tts_manager.config.get("language_engine_mapping", {}).get("fallback_engine", "gtts")
                        audio_format_hint = "wav" if fallback_engine_name == "voicevox" else "mp3"

                    save_test_audio(audio_data, f"{test_run_label}_msg_{message_type.lower()}", i + 1, audio_format_hint)
                    successful_synthesis_count +=1
                else:
                    logger.warning("Audio generated: False (TTSManager.synthesize returned None)")
                    failed_synthesis_count +=1
            else:
                logger.info(f"No text/lang determined for synthesis for message: {msg_data}")

            # Simulate main.py's periodic logging
            if ws_message_count % 2 == 0: # Log more frequently for this test (e.g., every 2 messages)
                logger.info(f"Simulated WebSocket Message Stats for {test_run_label}: Total Received: {ws_message_count}, "
                            f"SENT: {sent_type_count}, RECEIVED: {received_type_count}, CHAT: {chat_type_count}, "
                            f"Successful TTS: {successful_synthesis_count}, Failed TTS: {failed_synthesis_count}")
    finally:
        # Log final stats for the run
        logger.info(f"Final Simulated WebSocket Message Stats for {test_run_label}: Total Received: {ws_message_count}, "
                    f"SENT: {sent_type_count}, RECEIVED: {received_type_count}, CHAT: {chat_type_count}, "
                    f"Successful TTS: {successful_synthesis_count}, Failed TTS: {failed_synthesis_count}")

        # Crucial: Restore Config.CONFIG_FILE to its original value for subsequent tests or app use
        Config.CONFIG_FILE = original_config_class_var_val
        # And cleanup the temp config file and restore backup if any
        cleanup_test_config_for_integration(path_of_config_to_restore_later, TEMP_CONFIG_FILENAME)
        logger.info(f"--- Finished Test Run: {test_run_label} ---")


SAMPLE_TEST_MESSAGES = [
    {"type": "SENT", "message": "Hello world, this is a test from the simulated VRCT.", "src_languages": ["en"], "dst_languages": ["ja"]},
    {"type": "RECEIVED", "message": "こんにちは世界、これはVRCTからのテストです。", "translation": "Hello world, this is a test from VRCT.", "src_languages": ["ja"], "dst_languages": ["en"]},
    {"type": "SENT", "message": "これは日本語のテストです。", "src_languages": ["ja"], "dst_languages": ["en"]},
    {"type": "RECEIVED", "message": "This is an English message.", "translation": "これは英語のメッセージです。", "src_languages": ["en"], "dst_languages": ["ja"]},
    {"type": "CHAT", "message": "Chat message in English.", "src_languages": ["en"], "dst_languages": ["ja"]},
    {"type": "SENT", "message": "안녕하세요, 한국어 테스트입니다.", "src_languages": ["ko"], "dst_languages": ["en"]},
    {"type": "SENT", "message": "This is a message for en-GB.", "src_languages": ["en-GB"], "dst_languages": ["ja"]}, # Will use tld from DEFAULT_TEST_CONFIG_SETTINGS
]

if __name__ == '__main__':
    if not TTSManager or not Config:
        logger.critical("TTSManager or Config not imported correctly. Aborting tests.")
    else:
        # Ensure the main /app/config.json is deleted before tests if it exists from other runs,
        # so that backup/restore logic is clean.
        if os.path.exists(Config.CONFIG_FILE) and Config.CONFIG_FILE == "/app/config.json":
            logger.info(f"Removing existing main config file '{Config.CONFIG_FILE}' before starting integration tests.")
            os.remove(Config.CONFIG_FILE)
        if os.path.exists(ORIGINAL_CONFIG_BACKUP_FILENAME): # Remove any leftover backup
             os.remove(ORIGINAL_CONFIG_BACKUP_FILENAME)


        logger.info("=== Running Test Pass 1: Default Test Configuration ===")
        run_simulated_on_message_logic(SAMPLE_TEST_MESSAGES, DEFAULT_TEST_CONFIG_SETTINGS, "DefaultConfig")

        logger.info("\n\n=== Running Test Pass 2: Voicevox as Default, Specific rule for Japanese to gTTS ===")
        # Start with a copy of default and modify
        custom_config_2 = json.loads(json.dumps(DEFAULT_TEST_CONFIG_SETTINGS)) # Deep copy

        custom_config_2["language_engine_mapping"]["default_engine"] = "voicevox"
        # Update Japanese rule to use gTTS, overriding the default test config's ja->voicevox
        updated_lang_specific = []
        for rule in custom_config_2["language_engine_mapping"]["language_specific"]:
            if rule["lang_code"] == "ja" or rule["lang_code"] == "ja-JP":
                updated_lang_specific.append({"lang_code": rule["lang_code"], "engine": "gtts", "voice_id": None})
            else:
                updated_lang_specific.append(rule)
        custom_config_2["language_engine_mapping"]["language_specific"] = updated_lang_specific

        run_simulated_on_message_logic(SAMPLE_TEST_MESSAGES, custom_config_2, "VoicevoxDefault_JaToGTTS")

        # Clean up any audio files created in the test directory
        if os.path.exists(TEST_AUDIO_OUTPUT_DIR):
            logger.info(f"\nTest audio directory cleanup SKIPPED for manual review subtask: {TEST_AUDIO_OUTPUT_DIR}")
            # try:
            #     shutil.rmtree(TEST_AUDIO_OUTPUT_DIR)
            #     logger.info("Successfully removed test audio directory and its contents.")
            # except Exception as e:
            #     logger.error(f"Error removing test audio directory {TEST_AUDIO_OUTPUT_DIR}: {e}")

        logger.info("\nAll integration tests finished (files retained for review).")
