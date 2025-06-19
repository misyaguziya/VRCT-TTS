#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Dict
import logging
import requests # For requests.exceptions.RequestException
import os # For file cleanup

# Assuming voicevox.py and tts_engine_interface.py are in the same directory or accessible in PYTHONPATH
try:
    from voicevox import VOICEVOXClient
except ImportError:
    logging.critical("Failed to import VOICEVOXClient. Ensure voicevox.py is accessible.")
    # Define a dummy if not found, so the rest of the file can be parsed.
    class VOICEVOXClient:
        def __init__(self, host: str, port: int): pass
        def speakers(self): return None
        def audio_query(self, text: str, speaker_id: int) -> Dict: return {} # Ensure it returns a Dict
        def synthesis(self, query_response: Dict, speaker_id: int) -> Optional[bytes]: return None # Ensure it returns Optional[bytes]

try:
    from tts_engine_interface import TTSEngine
except ImportError:
    logging.critical("Failed to import TTSEngine. Ensure tts_engine_interface.py is accessible.")
    from abc import ABC, abstractmethod
    class TTSEngine(ABC):
        @abstractmethod
        def synthesize_speech(self, text: str, language_code: str, voice_id: Optional[str] = None, **kwargs) -> Optional[bytes]:
            pass

# Configure basic logging for the module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger specific to this module


class Voicevox_Engine(TTSEngine):
    """
    VOICEVOX Engine implementation of the TTSEngine interface.
    """

    def __init__(self, host: str = "localhost", port: int = 50021):
        """
        Initializes the Voicevox_Engine.
        Args:
            host (str, optional): Hostname of the VOICEVOX engine. Defaults to "localhost".
            port (int, optional): Port of the VOICEVOX engine. Defaults to 50021.
        """
        # Use self.logger for instance-specific logging if preferred, or module-level logger
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # self.logger.propagate = False # if you want to stop propagation to root logger
        # self.logger.addHandler(logging.StreamHandler()) # Example: ensure output if no root config

        self.logger.info(f"Initializing Voicevox_Engine with host={host}, port={port}")
        self.client = VOICEVOXClient(host=host, port=port)
        self._active = False
        self._check_engine_connection()

    def _check_engine_connection(self):
        """Checks if the VOICEVOX engine is accessible. Sets self._active flag."""
        try:
            speakers = self.client.speakers()
            if speakers is not None:
                self.logger.info("Successfully connected to VOICEVOX engine and fetched speakers.")
                self._active = True
            else:
                self.logger.warning("Connected to VOICEVOX engine, but no speakers found or engine returned None for speakers.")
                self._active = False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to connect to VOICEVOX engine during initialization: {e}")
            self._active = False
        except Exception as e: # Catch any other unexpected error during speaker check
            self.logger.error(f"An unexpected error occurred while checking VOICEVOX engine connection: {e}", exc_info=True)
            self._active = False

    @property
    def is_active(self) -> bool:
        """Returns true if the engine is connected and active, false otherwise."""
        return self._active

    def synthesize_speech(self,
                          text: str,
                          language_code: str,
                          voice_id: Optional[str] = None,
                          **kwargs) -> Optional[bytes]:
        """
        Synthesizes speech from text using the VOICEVOX engine.
        Args:
            text (str): The text to synthesize.
            language_code (str): Language code. VOICEVOX primarily supports Japanese ('ja' or 'ja-jp').
            voice_id (Optional[str], optional): Speaker ID (style ID). Must be string convertible to int.
            **kwargs: Additional parameters (currently unused by this engine).
        Returns:
            Optional[bytes]: WAV audio data, or None if synthesis failed.
        """
        self.logger.debug(f"Synthesize request: lang='{language_code}', voice_id='{voice_id}', text='{text[:30]}...'")

        if not self.is_active:
            self.logger.warning("Engine is not active (failed to connect at init or connection lost). Skipping synthesis.")
            return None

        if language_code.lower() not in ['ja', 'ja-jp']:
            self.logger.warning(f"Voicevox_Engine primarily supports Japanese. Received lang: '{language_code}'. Skipping.")
            return None

        if voice_id is None:
            self.logger.error("Voice_id (speaker ID) is required for Voicevox synthesis.")
            return None

        try:
            int_speaker_id = int(voice_id)
        except ValueError:
            self.logger.error(f"Voice_id must be a string convertible to an integer. Received: '{voice_id}'.")
            return None

        try:
            self.logger.info(f"Attempting audio query with speaker ID: {int_speaker_id} for text: '{text[:30]}...'")
            audio_query_response: Dict = self.client.audio_query(text, int_speaker_id)

            if audio_query_response is None:
                self.logger.error("Audio_query returned None (unexpected). This might indicate an issue with the client or engine response.")
                return None

            self.logger.info("Audio query successful. Attempting synthesis.")
            audio_data: Optional[bytes] = self.client.synthesis(audio_query_response, int_speaker_id)

            if audio_data:
                self.logger.info(f"Successfully synthesized speech for speaker ID {int_speaker_id}. Output size: {len(audio_data)} bytes.")
                return audio_data
            else: # Should ideally not happen if synthesis raises error on failure
                self.logger.warning(f"Synthesis returned no data for speaker ID {int_speaker_id} (unexpected).")
                return None

        except requests.exceptions.RequestException as re:
            self.logger.error(f"Connection Error during VOICEVOX API call: {re}", exc_info=True)
            return None
        except Exception as e: # Catch other errors from client methods or unexpected issues
            self.logger.error(f"General Error during VOICEVOX synthesis: {e}", exc_info=True)
            # Potentially re-set _active if this indicates a persistent issue
            # if isinstance(e, (BrokenPipeError, ConnectionAbortedError)): self._active = False
            return None

if __name__ == '__main__':
    # Ensure test-specific logging is visible
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - TEST - %(name)s - %(levelname)s - %(message)s')
    test_logger = logging.getLogger("Voicevox_Engine_Test")
    # test_logger.propagate = False # To avoid duplicate messages if root logger also has handlers
    # test_logger.addHandler(logging.StreamHandler())


    test_logger.info("Running enhanced tests for Voicevox_Engine...")

    engine = Voicevox_Engine() # Default host/port
    engine.logger = test_logger # Assign test logger to instance for its logs

    test_files_created = []

    def run_test_case(test_name, text, lang, voice_id, expected_to_synthesize_if_engine_active=False, temp_active_flag=None):
        test_logger.info(f"\n--- Test Case: {test_name} ---")
        test_logger.info(f"Input: text='{text}', lang='{lang}', voice_id='{voice_id}'")

        original_active_state = engine._active
        if temp_active_flag is not None:
            engine._active = temp_active_flag # Temporarily override for testing logic paths
            test_logger.info(f"Temporarily set engine._active to {temp_active_flag} for this test.")

        audio_data = engine.synthesize_speech(text, lang, voice_id)

        # Restore original active state
        if temp_active_flag is not None:
            engine._active = original_active_state

        if engine.is_active and expected_to_synthesize_if_engine_active:
            # This block assumes engine IS active and SHOULD produce audio
            assert audio_data is not None, f"{test_name} failed: Expected audio data (if engine active), got None."
            assert isinstance(audio_data, bytes), f"{test_name} failed: Expected bytes, got {type(audio_data)}."
            test_logger.info(f"{test_name} PASSED (simulated active): Received {len(audio_data)} bytes.")
            filename = f"test_output_{test_name.replace(' ', '_').lower()}.wav"
            try:
                with open(filename, "wb") as f: f.write(audio_data)
                test_logger.info(f"SUCCESS (simulated active): Audio for '{test_name}' saved to {filename}")
                test_files_created.append(filename)
            except IOError as e:
                test_logger.error(f"ERROR (simulated active): Could not write audio for '{test_name}': {e}")
        elif not engine.is_active and not expected_to_synthesize_if_engine_active:
            # This block assumes engine is NOT active, so audio_data should be None
            assert audio_data is None, f"{test_name} failed: Expected None (engine inactive), got audio data."
            test_logger.info(f"{test_name} PASSED: Correctly received None (engine inactive).")
        elif expected_to_synthesize_if_engine_active == False and audio_data is None:
            # This handles cases like invalid lang or voice_id, where None is expected even if engine was active
             test_logger.info(f"{test_name} PASSED: Correctly received None (input validation or other error).")
        else:
            # Unexpected outcome
            test_logger.warning(f"{test_name} UNEXPECTED: engine.is_active={engine.is_active}, expected_to_synthesize_if_engine_active={expected_to_synthesize_if_engine_active}, got_audio_data={audio_data is not None}")


    # Initial state: Engine is likely inactive as no real VOICEVOX instance is running
    test_logger.info(f"Initial engine active state: {engine.is_active}")
    if not engine.is_active:
        test_logger.warning("Engine is not active. Most synthesis tests will confirm error handling.")

    # 1. Standard Japanese (engine inactive)
    run_test_case("Japanese_Standard_Inactive", "こんにちは、テストです。", "ja", "1", expected_to_synthesize_if_engine_active=False)

    # 2. Non-Japanese language (engine inactive, but test logic for non-ja path)
    run_test_case("English_Lang_Inactive", "Hello", "en", "1", expected_to_synthesize_if_engine_active=False, temp_active_flag=True) # Force active to test lang check

    # 3. Missing voice_id (engine inactive, but test logic for missing voice_id)
    run_test_case("Missing_VoiceID_Inactive", "こんにちは", "ja", None, expected_to_synthesize_if_engine_active=False, temp_active_flag=True) # Force active

    # 4. Invalid voice_id format (e.g., not an int string)
    run_test_case("Invalid_VoiceID_Format_Inactive", "こんにちは", "ja", "not-an-integer", expected_to_synthesize_if_engine_active=False, temp_active_flag=True) # Force active

    # 5. Syntactically valid but likely non-existent high number voice_id
    # (If engine were active, it might error. Here, it's more about passing validation)
    run_test_case("NonExistent_VoiceID_Inactive", "テスト", "ja", "9999", expected_to_synthesize_if_engine_active=False)

    # 6. Test general exception handling during synthesis (simulated)
    test_logger.info("\n--- Test Case: Simulate General Engine Error ---")
    # Create a new engine instance for this specific test to monkey-patch
    error_sim_engine = Voicevox_Engine()
    error_sim_engine.logger = test_logger

    if not error_sim_engine.is_active: # If connection failed as usual
        error_sim_engine._active = True # Manually set active to bypass initial check for this test
        test_logger.info("Simulated General Error Test: Manually set engine to active to proceed past initial check.")

    original_audio_query = error_sim_engine.client.audio_query
    def mock_audio_query_raises_error(text, speaker_id):
        test_logger.info("Simulated General Error Test: audio_query is called, will raise RuntimeError.")
        raise RuntimeError("Simulated unexpected error in audio_query!")

    error_sim_engine.client.audio_query = mock_audio_query_raises_error

    audio_data_err_sim = error_sim_engine.synthesize_speech("シミュレートエラー", "ja", "1")
    assert audio_data_err_sim is None, "Simulated General Error Test failed: Expected None from synthesize_speech."
    test_logger.info("Simulated General Error Test PASSED: Correctly received None after simulated runtime error.")
    error_sim_engine.client.audio_query = original_audio_query # Restore original method
    error_sim_engine._active = False # Reset active state if it was manually set


    test_logger.info("\n--- Cleaning up test files ---")
    for f_name in test_files_created: # Should be empty if engine never successfully synthesized
        if os.path.exists(f_name): # This check might be redundant if list is empty
            try:
                os.remove(f_name)
                test_logger.info(f"Removed test file: {f_name}")
            except OSError as e:
                test_logger.error(f"Error removing test file {f_name}: {e}")
        # else: # No need for else, if f_name is not in list or doesn't exist, it's skipped.
            # test_logger.info(f"Test file not found (expected if synthesis failed): {f_name}")

    test_logger.info("\nAll Voicevox_Engine functional tests finished.")

    # --- Performance Tests ---
    import time
    perf_logger = logging.getLogger("Voicevox_Engine_Performance_Test")
    # Ensure performance logs are also visible clearly
    perf_logger.parent = test_logger # Inherit handlers from test_logger if any specific were set
    perf_logger.setLevel(logging.INFO) # Ensure INFO level for perf logs

    perf_logger.info("\n\n--- Starting Voicevox_Engine Performance Tests ---")

    # Re-instantiate engine for performance testing, use its own logger for clarity
    # Or can use the same 'engine' instance if its state is clean
    perf_engine = Voicevox_Engine()
    perf_engine.logger = perf_logger # Direct engine logs to perf_logger

    iterations = 3
    speaker_id_for_perf_test = "1" # Assuming '1' is a valid/common ID

    if not perf_engine.is_active:
        perf_logger.warning("Engine is not active. Full performance testing cannot be done.")

        # Measure time for a single synthesize call to confirm quick return
        perf_logger.info("Measuring quick return time for inactive engine (1 iteration):")
        start_time = time.perf_counter()
        perf_engine.synthesize_speech("テスト", "ja", speaker_id_for_perf_test)
        end_time = time.perf_counter()
        latency = (end_time - start_time) * 1000 # milliseconds
        perf_logger.info(f"  Inactive engine call latency: {latency:.2f} ms")
    else:
        perf_logger.info(f"Engine is ACTIVE. Proceeding with performance tests using speaker ID: {speaker_id_for_perf_test}")

        short_text_ja = "こんにちは。"
        long_text_ja = "これはボイスボックス音声合成エンジンの性能特性を試験するための、かなり長い日本語の文章です。"

        # Short text performance
        short_text_latencies = []
        perf_logger.info(f"Short text ('{short_text_ja}') performance ({iterations} iterations):")
        for i in range(iterations):
            start_time = time.perf_counter()
            audio_data = perf_engine.synthesize_speech(short_text_ja, "ja", speaker_id_for_perf_test)
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000 # milliseconds
            if audio_data:
                short_text_latencies.append(latency)
                perf_logger.info(f"  Iter {i+1}: {latency:.2f} ms (Audio size: {len(audio_data)} bytes)")
            else:
                perf_logger.warning(f"  Iter {i+1}: Synthesis failed.")

        if short_text_latencies:
            avg_latency_short = sum(short_text_latencies) / len(short_text_latencies)
            perf_logger.info(f"Average latency for SHORT text (ja): {avg_latency_short:.2f} ms")
        else:
            perf_logger.warning(f"No successful syntheses for SHORT text (ja) to calculate average.")

        # Long text performance
        long_text_latencies = []
        perf_logger.info(f"Long text ('{long_text_ja[:30]}...') performance ({iterations} iterations):")
        for i in range(iterations):
            start_time = time.perf_counter()
            audio_data = perf_engine.synthesize_speech(long_text_ja, "ja", speaker_id_for_perf_test)
            end_time = time.perf_counter()
            latency = (end_time - start_time) * 1000 # milliseconds
            if audio_data:
                long_text_latencies.append(latency)
                perf_logger.info(f"  Iter {i+1}: {latency:.2f} ms (Audio size: {len(audio_data)} bytes)")
            else:
                perf_logger.warning(f"  Iter {i+1}: Synthesis failed.")

        if long_text_latencies:
            avg_latency_long = sum(long_text_latencies) / len(long_text_latencies)
            perf_logger.info(f"Average latency for LONG text (ja): {avg_latency_long:.2f} ms")
        else:
            perf_logger.warning(f"No successful syntheses for LONG text (ja) to calculate average.")

    perf_logger.info("\n--- Voicevox_Engine Performance Tests Finished ---")
