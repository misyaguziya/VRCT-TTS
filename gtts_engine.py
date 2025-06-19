#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gtts import gTTS
from gtts import gTTSError # Import specific gTTS error
from io import BytesIO
from typing import Optional
import logging
import os # For file operations in test block

# Assuming tts_engine_interface.py is in the same directory or accessible in PYTHONPATH
try:
    from tts_engine_interface import TTSEngine
except ImportError:
    logging.warning("Could not import TTSEngine from tts_engine_interface. Defining a dummy TTSEngine for structure.")
    from abc import ABC, abstractmethod
    class TTSEngine(ABC):
        @abstractmethod
        def synthesize_speech(self, text: str, language_code: str, voice_id: Optional[str] = None, **kwargs) -> Optional[bytes]:
            pass

# Configure basic logging for the module
# Use a specific logger for this module if preferred, e.g., logger = logging.getLogger(__name__)
# For simplicity in these modules, basicConfig is okay if they are also meant to be runnable standalone for tests.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger specific to this module

class GTTS_Engine(TTSEngine):
    """
    gTTS implementation of the TTSEngine interface.
    """

    def synthesize_speech(self,
                          text: str,
                          language_code: str,
                          voice_id: Optional[str] = None,
                          **kwargs) -> Optional[bytes]:
        """
        Synthesizes speech from text using gTTS.
        Args:
            text (str): The text to synthesize.
            language_code (str): The language code for gTTS (e.g., 'en', 'ja').
            voice_id (Optional[str], optional): Not used by gTTS.
            **kwargs: Additional gTTS-specific parameters (e.g., `tld`, `slow`).
        Returns:
            Optional[bytes]: MP3 audio data, or None if synthesis failed.
        """
        # Using self.logger if defined, or module logger
        current_logger = getattr(self, 'logger', logger)
        current_logger.info(f"GTTS_Engine: Synthesizing for lang '{language_code}', text: '{text[:30]}...', kwargs: {kwargs}")

        simple_lang_code = language_code.split('-')[0]

        try:
            tts = gTTS(text=text, lang=simple_lang_code, **kwargs)
            audio_buffer = BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            audio_bytes = audio_buffer.read()
            current_logger.info(f"GTTS_Engine: Successfully synthesized speech for lang '{simple_lang_code}'. Output size: {len(audio_bytes)} bytes.")
            return audio_bytes
        except gTTSError as ge:
            current_logger.error(f"GTTS_Engine Error (gTTSError) for lang '{simple_lang_code}': {ge}", exc_info=True)
            return None
        except ValueError as ve: # Handles "Language not supported" from gTTS constructor
             current_logger.error(f"GTTS_Engine ValueError (e.g. lang not supported) for lang '{simple_lang_code}': {ve}", exc_info=True)
             return None
        except Exception as e:
            current_logger.error(f"GTTS_Engine Error (General Exception) for lang '{simple_lang_code}': {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # Ensure test-specific logging is visible
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - TEST - %(levelname)s - %(message)s')
    test_logger = logging.getLogger("GTTS_Engine_Test")
    test_logger.info("Running enhanced tests for GTTS_Engine...")

    engine = GTTS_Engine()
    # Assign the test logger to the engine instance for this test run to capture its logs better
    engine.logger = test_logger

    test_files_created = []

    def run_test_case(test_name, text, lang, should_succeed=True, **kwargs):
        test_logger.info(f"\n--- Test Case: {test_name} ---")
        test_logger.info(f"Input: text='{text}', lang='{lang}', kwargs={kwargs}")

        audio_data = engine.synthesize_speech(text, lang, **kwargs)

        if should_succeed:
            assert audio_data is not None, f"{test_name} failed: Expected audio data, got None."
            assert isinstance(audio_data, bytes), f"{test_name} failed: Expected bytes, got {type(audio_data)}."
            assert len(audio_data) > 0, f"{test_name} failed: Audio data is empty."
            test_logger.info(f"{test_name} PASSED: Received {len(audio_data)} bytes of audio data.")
            filename = f"test_output_{test_name.replace(' ', '_').lower()}.mp3"
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                test_logger.info(f"SUCCESS: Audio data for '{test_name}' saved to {filename}")
                test_files_created.append(filename)
            except IOError as e:
                test_logger.error(f"ERROR: Could not write audio for '{test_name}' to file: {e}")
        else:
            assert audio_data is None, f"{test_name} failed: Expected None, got audio data."
            test_logger.info(f"{test_name} PASSED: Correctly received None for expected failure.")

    # 1. Standard English
    run_test_case("English_Standard", "Hello world, this is a standard English test.", "en")

    # 2. Standard Japanese
    run_test_case("Japanese_Standard", "こんにちは世界、これは標準的な日本語のテストです。", "ja")

    # 3. Korean
    run_test_case("Korean_Standard", "안녕하세요, 이것은 표준 한국어 시험입니다.", "ko")

    # 4. French
    run_test_case("French_Standard", "Bonjour le monde, ceci est un test standard en français.", "fr")

    # 5. Invalid Language Code
    run_test_case("Invalid_Lang", "This should fail due to invalid language.", "xx-YY", should_succeed=False)

    # 6. Test with `tld` kwarg for regional accent (Australia)
    run_test_case("English_AU_Accent", "G'day mate, let's try for an Australian accent.", "en", tld='com.au')

    # 7. Test with `slow=True` kwarg
    run_test_case("English_Slow_Speed", "This text should be read slowly.", "en", slow=True)

    # 8. Test with `slow=False` kwarg (should be normal speed)
    run_test_case("English_Normal_Speed", "This text should be read at normal speed.", "en", slow=False)

    # 9. Test with language code containing region (e.g., en-GB)
    # GTTS_Engine simplifies this to 'en', but if a tld is also provided, it can affect accent.
    run_test_case("English_GB_Region", "A test with a GB English language code.", "en-GB", tld='co.uk')

    # 10. Test empty string
    # gTTS can handle empty string (produces very small valid mp3) or short strings.
    # Depending on desired behavior, this could be a success or failure.
    # gTTS raises an error for empty string, so engine returns None.
    run_test_case("Empty_String", "", "en", should_succeed=False)
    run_test_case("Short_String", "Ok", "en") # Short strings are fine


    test_logger.info("\n--- Test file cleanup SKIPPED for manual review subtask ---")
    # for f_name in test_files_created:
    #     if os.path.exists(f_name):
    #         try:
    #             os.remove(f_name)
    #             test_logger.info(f"Removed test file: {f_name}")
    #         except OSError as e:
    #             test_logger.error(f"Error removing test file {f_name}: {e}")
    #     else: # If file was not created due to an error in test itself
    #         test_logger.info(f"Test file '{f_name}' not found, no need to remove.")

    test_logger.info("\nAll GTTS_Engine functional tests finished (files retained for review).")


    # --- Performance Tests ---
    import time
    perf_logger = logging.getLogger("GTTS_Engine_Performance_Test")
    perf_logger.info("\n\n--- Starting GTTS_Engine Performance Tests ---")

    perf_engine = GTTS_Engine()
    perf_engine.logger = perf_logger # Assign logger to see engine's internal logs if needed

    languages_to_test = {
        "en": "Hello.",
        "ja": "こんにちは。",
        "ko": "안녕하세요.",
        "fr": "Bonjour."
    }
    long_text_en = "This is a significantly longer sentence used for the purpose of testing speech synthesis performance characteristics."
    # Simple translations for long text - actual content doesn't matter as much as length
    long_text_ja = "これは音声合成の性能特性を試験する目的で使用される、かなり長い文章です。"
    long_text_ko = "이것은 음성 합성의 성능 특성을 시험하기 위해 사용되는 상당히 긴 문장입니다."
    long_text_fr = "Ceci est une phrase significativement plus longue utilisée dans le but de tester les caractéristiques de performance de la synthèse vocale."

    long_texts_map = {
        "en": long_text_en,
        "ja": long_text_ja,
        "ko": long_text_ko,
        "fr": long_text_fr
    }

    iterations = 3 # Number of times to synthesize each text for averaging

    for lang_code, short_text in languages_to_test.items():
        perf_logger.info(f"\n--- Testing Language: {lang_code.upper()} ---")

        # Short text performance
        short_text_latencies = []
        perf_logger.info(f"Short text ('{short_text}') performance ({iterations} iterations):")
        for i in range(iterations):
            start_time = time.perf_counter()
            audio_data = perf_engine.synthesize_speech(short_text, lang_code)
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000 # milliseconds
            if audio_data:
                short_text_latencies.append(latency)
                perf_logger.info(f"  Iter {i+1}: {latency:.2f} ms (Audio size: {len(audio_data)} bytes)")
            else:
                perf_logger.warning(f"  Iter {i+1}: Synthesis failed.")

        if short_text_latencies:
            avg_latency_short = sum(short_text_latencies) / len(short_text_latencies)
            perf_logger.info(f"Average latency for SHORT text ({lang_code}): {avg_latency_short:.2f} ms")
        else:
            perf_logger.warning(f"No successful syntheses for SHORT text ({lang_code}) to calculate average.")

        # Long text performance
        long_text = long_texts_map.get(lang_code, long_text_en) # Default to English long text if specific not found
        long_text_latencies = []
        perf_logger.info(f"Long text ('{long_text[:30]}...') performance ({iterations} iterations):")
        for i in range(iterations):
            start_time = time.perf_counter()
            audio_data = perf_engine.synthesize_speech(long_text, lang_code)
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000 # milliseconds
            if audio_data:
                long_text_latencies.append(latency)
                perf_logger.info(f"  Iter {i+1}: {latency:.2f} ms (Audio size: {len(audio_data)} bytes)")
            else:
                perf_logger.warning(f"  Iter {i+1}: Synthesis failed.")

        if long_text_latencies:
            avg_latency_long = sum(long_text_latencies) / len(long_text_latencies)
            perf_logger.info(f"Average latency for LONG text ({lang_code}): {avg_latency_long:.2f} ms")
        else:
            perf_logger.warning(f"No successful syntheses for LONG text ({lang_code}) to calculate average.")

    perf_logger.info("\n--- GTTS_Engine Performance Tests Finished ---")
