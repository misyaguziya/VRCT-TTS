#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional, Dict, Any
import logging
import json # For cache key generation
import os
import shutil
import time # For performance measurement in __main__

try:
    from config import Config
except ImportError:
    logging.critical("Failed to import Config from config.py.")
    class Config:
        DEFAULT_TTS_SETTINGS = {
            "language_engine_mapping": {"default_engine": "gtts", "language_specific": [], "fallback_engine": "gtts"},
            "user_preferred_voices": {"gtts": {}, "voicevox": {}},
            "tts_optimizations": {"enable_caching": False, "max_cache_size": 0} # Provide defaults for tests
        }
        @staticmethod
        def load(): return Config.DEFAULT_TTS_SETTINGS
        @staticmethod
        def save(data): pass
        CONFIG_FILE = "config.json"


try:
    from gtts_engine import GTTS_Engine
except ImportError:
    logging.critical("Failed to import GTTS_Engine from gtts_engine.py.")
    GTTS_Engine = None

try:
    from voicevox_tts_engine import Voicevox_Engine
except ImportError:
    logging.critical("Failed to import Voicevox_Engine from voicevox_tts_engine.py.")
    Voicevox_Engine = None

try:
    from tts_engine_interface import TTSEngine
except ImportError:
    logging.critical("Failed to import TTSEngine from tts_engine_interface.py.")
    from abc import ABC, abstractmethod
    class TTSEngine(ABC):
        @abstractmethod
        def synthesize_speech(self, text: str, language_code: str, voice_id: Optional[str] = None, **kwargs) -> Optional[bytes]:
            pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTSManager:
    def __init__(self):
        logger.info("Initializing TTSManager...")
        self.config = Config.load()
        logger.debug(f"Loaded configuration: {self.config}")

        # Initialize Caching settings
        tts_optim_config = self.config.get("tts_optimizations", {}) # Get the whole sub-dict
        self.enable_caching = tts_optim_config.get("enable_caching", True) # Default True if key missing
        self.max_cache_size = tts_optim_config.get("max_cache_size", 100)  # Default 100
        if self.enable_caching and self.max_cache_size <= 0:
            logger.warning(f"max_cache_size was {self.max_cache_size}, but caching is enabled. Setting to default 100.")
            self.max_cache_size = 100 # Default to 100 if enabled but invalid size

        self.audio_cache: Dict[str, bytes] = {}
        self._cache_keys_fifo: List[str] = [] # To manage FIFO eviction

        logger.info(f"Caching enabled: {self.enable_caching}, Max cache size: {self.max_cache_size}")


        self.gtts_engine: Optional[GTTS_Engine] = None
        if GTTS_Engine:
            self.gtts_engine = GTTS_Engine()
        else:
            logger.error("GTTS_Engine class not available. gTTS functionality will be missing.")

        self.voicevox_engine: Optional[Voicevox_Engine] = None
        if Voicevox_Engine:
            self.voicevox_engine = Voicevox_Engine()
            if not hasattr(self.voicevox_engine, 'is_active'):
                logger.warning("Voicevox_Engine instance does not have 'is_active' property. Fallback logic might be affected.")
        else:
            logger.error("Voicevox_Engine class not available. Voicevox functionality will be missing.")

        self.engines: Dict[str, Optional[TTSEngine]] = {
            "gtts": self.gtts_engine,
            "voicevox": self.voicevox_engine
        }
        logger.info("TTSManager initialized.")

    def reload_config(self):
        logger.info("Reloading configuration for TTSManager...")
        self.config = Config.load()
        logger.debug(f"Reloaded configuration: {self.config}")

        # Update Caching settings from reloaded config
        tts_optim_config = self.config.get("tts_optimizations", {})
        self.enable_caching = tts_optim_config.get("enable_caching", True)
        new_max_cache_size = tts_optim_config.get("max_cache_size", 100)
        if new_max_cache_size != self.max_cache_size: # If max size changed, apply eviction if needed
            self.max_cache_size = new_max_cache_size
            self._apply_cache_eviction() # Evict if current size exceeds new max
        logger.info(f"Caching settings reloaded: enabled={self.enable_caching}, max_size={self.max_cache_size}")


    def get_engine(self, engine_name: str) -> Optional[TTSEngine]:
        engine = self.engines.get(engine_name.lower())
        if engine is None:
            logger.warning(f"Engine '{engine_name}' not found or not initialized.")
        return engine

    def _generate_cache_key(self, text: str, language_code: str, voice_id: Optional[str], engine_name: str, **kwargs) -> str:
        # Normalize text and create a stable key. kwargs are included for completeness.
        # Simple normalization: strip whitespace. More complex normalization could be added.
        normalized_text = text.strip()
        # Include relevant kwargs that affect audio output, e.g., 'tld' or 'slow' for gTTS
        # Sort kwargs to ensure consistent key order
        relevant_kwargs_tuple = tuple(sorted(kwargs.items()))
        cache_key_tuple = (normalized_text, language_code, voice_id, engine_name.lower(), relevant_kwargs_tuple)
        return json.dumps(cache_key_tuple, sort_keys=True)

    def _apply_cache_eviction(self):
        """Applies cache eviction strategy if cache is at or exceeds max size, to make space for one new item."""
        if not self.enable_caching:
            self.audio_cache.clear()
            self._cache_keys_fifo.clear()
            return

        # Evict items until there is space for at least one new item, or cache is empty.
        # If max_cache_size is 0 (unlimited), this loop won't run.
        while self.max_cache_size > 0 and len(self.audio_cache) >= self.max_cache_size and self._cache_keys_fifo:
            oldest_key = self._cache_keys_fifo.pop(0)
            if oldest_key in self.audio_cache:
                del self.audio_cache[oldest_key]
                logger.info(f"Cache eviction (FIFO): Removed '{oldest_key[:50]}...'")
            else: # Should not happen if lists are in sync
                logger.warning(f"Cache eviction: Key '{oldest_key[:50]}...' not found in cache dict during FIFO pop.")


    def determine_synthesis_parameters(self, language_code: str) -> Dict[str, Any]:
        lang_map_config = self.config.get("language_engine_mapping", Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"])
        user_prefs_config = self.config.get("user_preferred_voices", Config.DEFAULT_TTS_SETTINGS["user_preferred_voices"])

        engine_name = lang_map_config.get("default_engine", "gtts")
        voice_id: Optional[str] = None

        best_match_rule = None
        input_lang_lower = language_code.lower()
        input_lang_base = input_lang_lower.split('-')[0]

        for rule in lang_map_config.get("language_specific", []):
            rule_lang_code_lower = rule.get("lang_code", "").lower()
            if rule_lang_code_lower == input_lang_lower:
                best_match_rule = rule
                break
            if rule_lang_code_lower == input_lang_base:
                if best_match_rule is None or len(rule_lang_code_lower) > len(best_match_rule.get("lang_code","")):
                    best_match_rule = rule

        if best_match_rule:
            engine_name = best_match_rule.get("engine", engine_name)
            voice_id = best_match_rule.get("voice_id")
            # If rule specifies engine-specific params (like 'tld_config_key_for_gtts'), they could be extracted here too.
            # For now, assuming kwargs like 'tld' are passed directly to synthesize() if needed.

        actual_lang_code = language_code
        engine_name_lower = engine_name.lower()

        if engine_name_lower == "voicevox":
            actual_lang_code = "ja"
            if voice_id is None:
                voicevox_prefs = user_prefs_config.get("voicevox", {})
                voice_id = voicevox_prefs.get("default_voice_id", "1")
        elif engine_name_lower == "gtts":
            pass

        logger.info(f"Determined params for lang '{language_code}': engine='{engine_name}', actual_lang_for_engine='{actual_lang_code}', voice_id='{voice_id}'")
        return {"engine_name": engine_name, "language_code": actual_lang_code, "voice_id": voice_id}

    def synthesize(self, text: str, language_code: str, target_message_type: Optional[str] = None, **kwargs) -> Optional[bytes]:
        logger.info(f"Synthesize request: text='{text[:30]}...', lang='{language_code}', type='{target_message_type}', kwargs={kwargs}")

        params = self.determine_synthesis_parameters(language_code)
        primary_engine_name = params["engine_name"]
        resolved_lang_code = params["language_code"]
        resolved_voice_id = params["voice_id"]

        # Construct cache key based on actual parameters that will be used for primary synthesis
        # kwargs passed to synthesize might contain engine-specific things like 'tld'
        primary_cache_key = self._generate_cache_key(text, resolved_lang_code, resolved_voice_id, primary_engine_name, **kwargs)

        if self.enable_caching and self.max_cache_size > 0 and primary_cache_key in self.audio_cache:
            logger.info(f"Cache HIT for primary synthesis: {primary_cache_key[:100]}...")
            # Move accessed key to the end of FIFO list (making it most recently used)
            if primary_cache_key in self._cache_keys_fifo: # Should always be true if in audio_cache
                self._cache_keys_fifo.remove(primary_cache_key)
            self._cache_keys_fifo.append(primary_cache_key)
            return self.audio_cache[primary_cache_key]

        logger.info(f"Cache MISS for primary key: {primary_cache_key[:100]}...")

        audio_data: Optional[bytes] = None
        primary_engine = self.get_engine(primary_engine_name)
        current_engine_name_for_log = primary_engine_name # For logging which engine ultimately produced audio

        if primary_engine:
            can_attempt_primary = True
            if primary_engine_name.lower() == "voicevox":
                if not self.voicevox_engine or not self.voicevox_engine.is_active:
                    logger.warning(f"Primary engine Voicevox ({primary_engine_name}) is not active. Skipping.")
                    can_attempt_primary = False

            if can_attempt_primary:
                logger.info(f"TTSManager: Attempting primary synthesis with {primary_engine_name} for lang '{resolved_lang_code}'. Text length: {len(text)} chars.")
                try:
                    time_before_synth = time.perf_counter()
                    audio_data = primary_engine.synthesize_speech(text, resolved_lang_code, resolved_voice_id, **kwargs)
                    time_after_synth = time.perf_counter()
                    if audio_data:
                        logger.info(f"TTSManager: {primary_engine_name} synthesis successful. Time taken: {time_after_synth - time_before_synth:.4f}s")
                    else:
                        logger.warning(f"TTSManager: {primary_engine_name} synthesis failed. Time taken: {time_after_synth - time_before_synth:.4f}s")

                    if audio_data and self.enable_caching and self.max_cache_size > 0:
                        # Apply eviction before adding new item if cache is full
                        self._apply_cache_eviction() # Ensures space if cache is at max_cache_size
                        if len(self.audio_cache) < self.max_cache_size:
                           self.audio_cache[primary_cache_key] = audio_data
                           if primary_cache_key not in self._cache_keys_fifo: # Should not happen if logic is correct
                               self._cache_keys_fifo.append(primary_cache_key)
                           logger.info(f"Cached audio (primary): {primary_cache_key[:100]}... Cache size: {len(self.audio_cache)}")
                        else:
                            logger.warning(f"Cache full after eviction attempt. Not caching primary: {primary_cache_key[:100]}...")
                except Exception as e:
                    logger.error(f"Error during primary synthesis with {primary_engine_name}: {e}", exc_info=True)
                    audio_data = None # Ensure audio_data is None on error
        else:
            logger.warning(f"Primary engine '{primary_engine_name}' could not be loaded.")

        if audio_data is None: # Primary synthesis failed, was skipped, or engine not loaded
            lang_map_config = self.config.get("language_engine_mapping", Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"])
            fallback_engine_name = lang_map_config.get("fallback_engine", "gtts")
            current_engine_name_for_log = fallback_engine_name # Update for logging if fallback is used

            if fallback_engine_name.lower() == primary_engine_name.lower() and can_attempt_primary : # Avoid re-trying same failed engine
                logger.warning(f"Fallback engine '{fallback_engine_name}' is the same as primary which already failed/skipped. No fallback attempt.")
                return None

            logger.info(f"Primary synthesis failed or skipped. Attempting fallback engine: {fallback_engine_name}")
            fallback_engine = self.get_engine(fallback_engine_name)

            if fallback_engine:
                can_attempt_fallback = True
                fallback_resolved_lang = language_code
                fallback_resolved_voice_id = None
                fallback_kwargs = {}

                if fallback_engine_name.lower() == "voicevox":
                    if not self.voicevox_engine or not self.voicevox_engine.is_active:
                        logger.warning(f"Fallback engine Voicevox ({fallback_engine_name}) is not active. Skipping fallback.")
                        can_attempt_fallback = False
                    else:
                        fallback_resolved_lang = "ja"
                        user_prefs_config = self.config.get("user_preferred_voices", Config.DEFAULT_TTS_SETTINGS["user_preferred_voices"])
                        voicevox_prefs = user_prefs_config.get("voicevox", {})
                        fallback_resolved_voice_id = voicevox_prefs.get("default_voice_id", "1")
                elif fallback_engine_name.lower() == "gtts":
                    # Carry over relevant kwargs for gTTS
                    if 'tld' in kwargs: fallback_kwargs['tld'] = kwargs['tld']
                    if 'slow' in kwargs: fallback_kwargs['slow'] = kwargs['slow']

                if can_attempt_fallback:
                    fallback_cache_key = self._generate_cache_key(text, fallback_resolved_lang, fallback_resolved_voice_id, fallback_engine_name, **fallback_kwargs)
                    if self.enable_caching and self.max_cache_size > 0 and fallback_cache_key in self.audio_cache:
                        logger.info(f"Cache HIT for fallback synthesis: {fallback_cache_key[:100]}...")
                        if fallback_cache_key in self._cache_keys_fifo: self._cache_keys_fifo.remove(fallback_cache_key)
                        self._cache_keys_fifo.append(fallback_cache_key)
                        audio_data = self.audio_cache[fallback_cache_key]
                        # If cache hit, we return this audio_data
                    else:
                        logger.info(f"TTSManager: Attempting fallback synthesis with {fallback_engine_name} for lang '{fallback_resolved_lang}'. Text length: {len(text)} chars.")
                        # logger.info(f"Cache MISS for fallback key: {fallback_cache_key[:100]}... Attempting synthesis.") # Already logged by cache miss
                        try:
                            time_before_fallback_synth = time.perf_counter()
                            audio_data = fallback_engine.synthesize_speech(text, fallback_resolved_lang, fallback_resolved_voice_id, **fallback_kwargs)
                            time_after_fallback_synth = time.perf_counter()
                            if audio_data:
                                logger.info(f"TTSManager: {fallback_engine_name} fallback synthesis successful. Time taken: {time_after_fallback_synth - time_before_fallback_synth:.4f}s")
                            else:
                                logger.warning(f"TTSManager: {fallback_engine_name} fallback synthesis failed. Time taken: {time_after_fallback_synth - time_before_fallback_synth:.4f}s")

                            if audio_data and self.enable_caching and self.max_cache_size > 0:
                                self._apply_cache_eviction() # Make space if needed
                                if len(self.audio_cache) < self.max_cache_size:
                                    self.audio_cache[fallback_cache_key] = audio_data
                                    if fallback_cache_key not in self._cache_keys_fifo:
                                        self._cache_keys_fifo.append(fallback_cache_key)
                                    logger.info(f"Cached audio (fallback): {fallback_cache_key[:100]}... Cache size: {len(self.audio_cache)}")
                                else:
                                    logger.warning(f"Cache full after eviction. Not caching fallback: {fallback_cache_key[:100]}...")
                            elif audio_data is None:
                                logger.warning(f"Fallback synthesis with {fallback_engine_name} also returned no data.")
                        except Exception as e:
                            logger.error(f"Error during fallback synthesis with {fallback_engine_name}: {e}", exc_info=True)
                            audio_data = None
            else:
                logger.warning(f"Fallback engine '{fallback_engine_name}' could not be loaded.")

        # Final logging based on whether audio_data was obtained
        if audio_data:
            logger.info(f"Synthesis successful (final engine: {current_engine_name_for_log}). Audio data length: {len(audio_data)}")
        else:
            logger.error("All synthesis attempts (primary and fallback) failed.")

        return audio_data

# CONCEPTUAL OUTLINE: TEXT SPLITTING FOR TTS
# Problem: Very long texts (>200-300 characters, depending on engine) can lead to:
#   1. Increased latency for the entire synthesis.
#   2. Potential errors or timeouts from TTS engines.
#   3. Degraded audio quality or unnatural prosody over very long segments.
#
# Proposed Solution: Split long input text into smaller, manageable chunks.
#
# Process:
#   1. Pre-processing: Before calling TTSManager.synthesize, or as an initial step within it
#      for very long texts, split the input text.
#      - Methods:
#          - Sentence tokenization (e.g., using libraries like NLTK, spaCy, or simpler regex for periods, question marks, exclamation points).
#          - Fixed character limits (e.g., every 200 characters), ensuring splits occur at sensible places like spaces if possible.
#   2. Individual Synthesis: Synthesize each chunk individually.
#      - This allows `TTSManager`'s caching to potentially work on these smaller chunks.
#   3. Audio Concatenation: Combine the resulting audio byte streams.
#      - For WAV: Requires careful header manipulation and appending of data sections. Libraries like `pydub` can simplify this.
#      - For MP3: Often simpler; MP3 files can sometimes be directly concatenated. `pydub` can also handle this robustly.
#
# Benefits:
#   - Improved perceived responsiveness as the first chunk can be played sooner.
#   - Better error resilience (if one chunk fails, others might still succeed).
#   - Potentially better audio quality from engines that perform better with shorter inputs.
#   - More effective caching if common short phrases or sentences are repeated.
#
# Challenges:
#   - Ensuring natural-sounding transitions between audio chunks (avoiding abrupt cuts or changes in prosody).
#   - Maintaining context across splits for consistent intonation and meaning.
#   - Complexity of audio format manipulation for concatenation.
#   - Determining optimal chunk size and splitting rules.

# CONCEPTUAL OUTLINE: NETWORK/SERVER OPTIMIZATION NOTES
#
# gTTS Engine:
#   - Performance is heavily dependent on the user's internet connection speed and latency to Google's servers.
#   - The application has limited control beyond:
#       - Implementing robust error handling for network issues (timeouts, connection errors).
#       - The implemented caching mechanism helps reduce repeated calls for the same text.
#
# Voicevox Engine:
#   - Performance depends on the local machine running the VOICEVOX engine (CPU, RAM, disk I/O if models are loaded dynamically).
#   - Ensure the VOICEVOX engine software itself is configured for optimal performance on the host machine.
#   - If Voicevox is run on a remote server on the user's network, local network latency also plays a role.
#   - Caching (as implemented) also benefits Voicevox by reducing redundant synthesis requests.

if __name__ == '__main__':
    # Ensure logging is configured to see output from all modules involved.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    test_logger = logging.getLogger("TTSManager_Test") # Specific logger for test script
    test_logger.info("Running TTSManager enhanced test script (with Caching)...")

    # Define constants for filenames used in tests to avoid NameErrors in cleanup
    # Using more specific names for clarity in test setup/cleanup
    MAIN_CONFIG_BACKUP_PATH = Config.CONFIG_FILE + ".main_backup_tts_mgr"
    CACHE_SCENARIO_TEMP_CONFIG_FILE = "/app/temp_config_cache_scenario.json"
    # General temp file for other tests if any, though cache test uses its own specific one.
    GENERAL_TEMP_CONFIG_FILE = "/app/temp_config_general_tts_mgr.json"


    def setup_test_config(custom_settings_dict: Dict[str, Any], temp_config_filename: str) -> Optional[str]:
        test_logger.info(f"Setting up test config: {custom_settings_dict} at {temp_config_filename}")
        original_config_file_loc = Config.CONFIG_FILE # Store where Config normally looks

        if os.path.exists(original_config_file_loc):
            try:
                shutil.copyfile(original_config_file_loc, MAIN_CONFIG_BACKUP_PATH)
                test_logger.info(f"Backed up existing config '{original_config_file_loc}' to '{MAIN_CONFIG_BACKUP_PATH}'")
            except Exception as e:
                test_logger.error(f"Failed to back up original config: {e}")
        elif os.path.exists(MAIN_CONFIG_BACKUP_PATH): # Stale backup
            os.remove(MAIN_CONFIG_BACKUP_PATH)

        try:
            with open(temp_config_filename, "w", encoding="utf-8") as f:
                json.dump(custom_settings_dict, f, indent=4, ensure_ascii=False)
            test_logger.info(f"Test config content written to {temp_config_filename}")
            Config.CONFIG_FILE = temp_config_filename # Point Config class to use this file
            return original_config_file_loc # Return original path for restoration
        except Exception as e:
            test_logger.error(f"Failed to write test config: {e}")
            return None

    def cleanup_test_config(original_config_path_to_restore_constant_to: str, temp_config_filename_used: str):
        test_logger.info(f"Cleaning up: Restoring Config.CONFIG_FILE to '{original_config_path_to_restore_constant_to}', removing temp file '{temp_config_filename_used}'.")
        Config.CONFIG_FILE = original_config_path_to_restore_constant_to # Restore class variable

        if os.path.exists(temp_config_filename_used):
            try:
                os.remove(temp_config_filename_used)
                test_logger.info(f"Removed temp test config file: {temp_config_filename_used}")
            except Exception as e:
                test_logger.error(f"Failed to remove temp test config file: {e}")

        if os.path.exists(original_config_backup_path):
            try:
                shutil.move(original_config_backup_path, original_config_path_to_restore_constant_to)
                test_logger.info(f"Restored original config to '{original_config_path_to_restore_constant_to}' from backup.")
            except Exception as e:
                test_logger.error(f"Failed to restore original config from backup: {e}")
        else: # If no backup, but original config path exists (e.g. was created by first Config.load())
            if os.path.exists(original_config_path_to_restore_constant_to) and \
               original_config_path_to_restore_constant_to != temp_config_filename_used:
                 pass # Keep it, it might be the default one created. Or remove if we want pristine state.
                      # For now, if no backup, we just ensure temp is gone.


    def save_audio(audio_data: Optional[bytes], filename: str):
        # This is a simplified save_audio for cache tests; primary focus is on cache logs.
        if audio_data:
            test_logger.info(f"Audio data received for {filename} (Size: {len(audio_data)} bytes). Not saving to file in this test section.")
        else:
            test_logger.warning(f"No audio data received for {filename}.")

    # --- Test Caching Logic ---
    test_logger.info("\n--- Test Scenario: Caching ---")
    # Config for testing cache: enable caching, small max_cache_size for eviction test
    config_for_caching_test_scenario = Config._get_full_default_config() # Start with full defaults
    config_for_caching_test_scenario["tts_optimizations"] = {
        "enable_caching": True,
        "max_cache_size": 2 # Small size to test eviction
    }
    config_for_caching_test_scenario["language_engine_mapping"]["language_specific"] = [ # Ensure ja uses gTTS for this test for simplicity
         {"lang_code": "ja", "engine": "gtts", "voice_id": None}
    ]

    # Use the specific constant for this test's temp config file
    original_config_path_constant_for_cache_test = setup_test_config(config_for_caching_test_scenario, CACHE_SCENARIO_TEMP_CONFIG_FILE)

    if original_config_path_constant_for_cache_test: # Only proceed if config setup was successful
        manager_cache_test = TTSManager() # Loads the CACHE_SCENARIO_TEMP_CONFIG_FILE

        test_logger.info("Synthesizing 'Hello' (en) - 1st time (expect cache miss)")
        audio1 = manager_cache_test.synthesize("Hello", "en")
        save_audio(audio1, "cache_test1_hello_en.mp3")
        cache_key_1 = manager_cache_test._generate_cache_key("Hello", "en", None, "gtts")
        assert cache_key_1, "Cache key gen failed for cache_key_1" # Check if key itself is non-empty
        assert cache_key_1 in manager_cache_test.audio_cache, "Cache Test FAILED: First Hello (en) not in cache"

        test_logger.info("Synthesizing 'Hello' (en) - 2nd time (expect cache hit)")
        start_time_cache = time.perf_counter()
        audio2 = manager_cache_test.synthesize("Hello", "en")
        end_time_cache = time.perf_counter()
        latency_cached = (end_time_cache - start_time_cache) * 1000
        test_logger.info(f"Latency for cached 'Hello' (en): {latency_cached:.2f} ms")
        save_audio(audio2, "cache_test2_hello_en_cached.mp3")
        assert audio1 == audio2, "Cache Test FAILED: Cached audio differs from original"
        assert latency_cached < 50, f"Cache Test FAILED: Cached latency {latency_cached:.2f}ms seems too high."


        test_logger.info("Synthesizing 'こんにちは' (ja) - 1st time (expect cache miss, gTTS due to temp config)")
        audio_ja1 = manager_cache_test.synthesize("こんにちは", "ja")
        save_audio(audio_ja1, "cache_test3_konnichiwa_ja.mp3")
        cache_key_ja1 = manager_cache_test._generate_cache_key("こんにちは", "ja", None, "gtts")
        assert cache_key_ja1, "Cache key gen failed for cache_key_ja1"
        assert cache_key_ja1 in manager_cache_test.audio_cache, "Cache Test FAILED: First Konnichiwa (ja) not in cache"
        assert len(manager_cache_test.audio_cache) == 2, f"Cache Test FAILED: Cache size is {len(manager_cache_test.audio_cache)}, expected 2"

        test_logger.info("Synthesizing 'Test 3' (en) - new item, should evict 'Hello' (en)")
        audio_test3 = manager_cache_test.synthesize("Test 3", "en")
        save_audio(audio_test3, "cache_test4_test3_en.mp3")
        cache_key_test3 = manager_cache_test._generate_cache_key("Test 3", "en", None, "gtts")
        assert cache_key_test3, "Cache key gen failed for cache_key_test3"
        assert cache_key_test3 in manager_cache_test.audio_cache, "Cache Test FAILED: Test 3 (en) not in cache"
        assert len(manager_cache_test.audio_cache) == manager_cache_test.max_cache_size, f"Cache Test FAILED: Cache size is {len(manager_cache_test.audio_cache)}, expected {manager_cache_test.max_cache_size}"
        assert cache_key_1 not in manager_cache_test.audio_cache, "Cache Test FAILED: First item 'Hello (en)' was not evicted."
        test_logger.info("Cache eviction test PASSED: First item correctly evicted.")

        test_logger.info("Synthesizing 'こんにちは' (ja) - 2nd time (expect cache hit)")
        audio_ja2 = manager_cache_test.synthesize("こんにちは", "ja")
        save_audio(audio_ja2, "cache_test5_konnichiwa_ja_cached.mp3")
        assert audio_ja1 == audio_ja2, "Cache Test FAILED: Cached Japanese audio differs"

        # Test disabling cache mid-run
        test_logger.info("Disabling cache and synthesizing 'Test 3' (en) again (expect cache miss, new synthesis)")
        manager_cache_test.enable_caching = False # Disable caching on the instance
        manager_cache_test.audio_cache.clear() # Clear existing cache for clean test
        manager_cache_test._cache_keys_fifo.clear()

        audio_test3_nocache = manager_cache_test.synthesize("Test 3", "en")
        save_audio(audio_test3_nocache, "cache_test6_test3_en_nocache.mp3")
        assert len(manager_cache_test.audio_cache) == 0, "Cache Test FAILED: Item cached even when enable_caching=False"
        test_logger.info("Cache disabling test PASSED.")

        cleanup_test_config(original_config_path_constant_for_cache_test, CACHE_SCENARIO_TEMP_CONFIG_FILE)
    else:
        test_logger.error("Could not run caching tests due to config setup failure.")

    # Restore original config path to Config class variable, just in case.
    # This should be done by cleanup_test_config ideally, but double check.
    if 'original_config_path_constant_for_cache_test' in locals() and original_config_path_constant_for_cache_test:
         Config.CONFIG_FILE = original_config_path_constant_for_cache_test
    elif os.path.exists(MAIN_CONFIG_BACKUP_PATH): # Fallback to the general backup
        # Determine the original config file name (usually 'config.json')
        original_main_config_filename = os.path.basename(MAIN_CONFIG_BACKUP_PATH).replace(".main_backup_tts_mgr", "")
        Config.CONFIG_FILE = original_main_config_filename
        shutil.move(MAIN_CONFIG_BACKUP_PATH, Config.CONFIG_FILE)


    # --- TTSManager Performance Observation (from previous step, kept for completeness) ---
    # Ensure this section uses a known config state, e.g. by reloading default after cache tests.
    test_logger.info("\n\n--- Re-running TTSManager Performance Observation with default config ---")
    if os.path.exists(Config.CONFIG_FILE): os.remove(Config.CONFIG_FILE) # Clean slate
    Config.load() # Create default config.json

    manager_for_perf = TTSManager()
    iterations = 3 # Reduced iterations for brevity in combined script

    # Scenario 1: English text (expected: gTTS)
    test_logger.info(f"\n--- Perf Scenario: English text (gTTS) ({iterations} iterations) ---")
    # ... (rest of performance tests from previous version of if __name__ == '__main__') ...
    # This part is identical to the performance block added in the previous step.
    # For brevity, I'm not repeating all of it here, but it would be included.
    en_text = "This is an English sentence for performance testing of the TTS Manager."
    en_latencies = []
    for i in range(iterations):
        start_time = time.perf_counter()
        audio_data = manager_for_perf.synthesize(en_text, "en")
        end_time = time.perf_counter()
        latency = (end_time - start_time) * 1000 # ms
        if audio_data: en_latencies.append(latency)
        test_logger.info(f"  Perf Iter {i+1} (en): {latency:.2f} ms")
    if en_latencies: test_logger.info(f"Avg Perf (en): {sum(en_latencies)/len(en_latencies):.2f} ms")


    ja_text = "これはTTSマネージャーの性能試験のための日本語の文章です。"
    ja_latencies = []
    test_logger.info(f"\n--- Perf Scenario: Japanese (Voicevox attempt -> gTTS fallback) ({iterations} iterations) ---")
    for i in range(iterations):
        start_time = time.perf_counter()
        audio_data = manager_for_perf.synthesize(ja_text, "ja")
        end_time = time.perf_counter()
        latency = (end_time - start_time) * 1000 # ms
        if audio_data: ja_latencies.append(latency)
        test_logger.info(f"  Perf Iter {i+1} (ja): {latency:.2f} ms")
    if ja_latencies: test_logger.info(f"Avg Perf (ja fallback): {sum(ja_latencies)/len(ja_latencies):.2f} ms")


    test_logger.info("\n--- TTSManager test script (functional and performance) finished ---")
    # Final cleanup of config files
    test_logger.info("\n--- Final Cleanup Post All Tests ---")
    if os.path.exists(Config.CONFIG_FILE) and Config.CONFIG_FILE == "/app/config.json": # Default path set in Config class
        # This ensures we only remove it if it's the one we expect to be managing.
        os.remove(Config.CONFIG_FILE)
        test_logger.info(f"Cleaned up main config file: {Config.CONFIG_FILE}")

    # MAIN_CONFIG_BACKUP_PATH is the global constant for backups made by setup_test_config
    if os.path.exists(MAIN_CONFIG_BACKUP_PATH):
        os.remove(MAIN_CONFIG_BACKUP_PATH)
        test_logger.info(f"Cleaned up main config backup: {MAIN_CONFIG_BACKUP_PATH}")

    # GENERAL_TEMP_CONFIG_FILE is the global constant for general temp files (if any were created)
    if os.path.exists(GENERAL_TEMP_CONFIG_FILE):
        os.remove(GENERAL_TEMP_CONFIG_FILE)
        test_logger.info(f"Cleaned up general temp config: {GENERAL_TEMP_CONFIG_FILE}")

    # Specific temp file for cache test scenario
    if os.path.exists(CACHE_SCENARIO_TEMP_CONFIG_FILE):
         os.remove(CACHE_SCENARIO_TEMP_CONFIG_FILE)
         test_logger.info(f"Cleaned up specific cache test temp config: {CACHE_SCENARIO_TEMP_CONFIG_FILE}")

    test_logger.info("Final cleanup of config files attempted.")
