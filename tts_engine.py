import abc
from gtts import gTTS, gTTSError
import io
import logging

# --- Language Configuration ---
# For now, assume incoming codes are gTTS compatible or use simple common alternatives.
LANGUAGE_MAPPINGS = {
    'en': 'en', 'eng': 'en', 'english': 'en',
    'ja': 'ja', 'jpn': 'ja', 'japanese': 'ja',
    'ko': 'ko', 'kor': 'ko', 'korean': 'ko',
    'fr': 'fr', 'fra': 'fr', 'french': 'fr',
    'es': 'es', 'spa': 'es', 'spanish': 'es',
    'de': 'de', 'deu': 'de', 'german': 'de',
    'zh-cn': 'zh-CN', 'chinese simplified': 'zh-CN',
    'hi': 'hi', 'hin': 'hi', 'hindi': 'hi',
    'ar': 'ar', 'ara': 'ar', 'arabic': 'ar',
    'pt': 'pt', 'por': 'pt', 'portuguese': 'pt',
    'ru': 'ru', 'rus': 'ru', 'russian': 'ru',
    'it': 'it', 'ita': 'it', 'italian': 'it',
    # Add more mappings as needed
}

DEFAULT_LANGUAGE = 'en'

# This list can be expanded based on gTTS's full capabilities.
# Using the list previously returned by GTTSEngine.get_available_languages() as a base.
SUPPORTED_GTTS_LANGUAGES = ['en', 'ja', 'ko', 'fr', 'es', 'de', 'zh-CN', 'hi', 'ar', 'pt', 'ru', 'it']

# Optional: For future "voice variation" via TLD (Top Level Domain for Google)
GTTS_TLD_OPTIONS = {
    'com': 'Default (com)', # Standard
    'us': 'com', # United States (same as com for English)
    'uk': 'co.uk', # United Kingdom
    'au': 'com.au', # Australia
    'ca': 'ca', # Canada
    'jp': 'co.jp', # Japan
    'kr': 'co.kr', # Korea
    'fr': 'fr', # France
    # ... add more as needed
}
# --- End Language Configuration ---

# Setup basic logging for the module if tests are run directly
# For actual application integration, the main app should configure logging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
logger = logging.getLogger(__name__)


class TTSSynthesisError(Exception):
    """Custom exception for TTS synthesis errors."""
    pass

class TTSEngine(abc.ABC):
    """Abstract base class for TTS engines."""
    @abc.abstractmethod
    def __init__(self, config=None):
        """
        Initialize the TTS engine.
        Config is an optional dictionary for engine-specific settings.
        """
        self.config = config
        # Potentially load language configs here if they were passed in config
        # For this example, GTTSEngine loads them directly.

    @abc.abstractmethod
    def synthesize_speech(self, text: str, language_code: str, **kwargs) -> bytes:
        """
        Synthesize speech from text.
        Args:
            text: The text to synthesize.
            language_code: The input language code (e.g., 'en', 'eng', 'japanese').
            **kwargs: Additional engine-specific parameters.
        Returns:
            Audio data as bytes.
        Raises:
            TTSSynthesisError: If synthesis fails.
        """
        pass

    @abc.abstractmethod
    def get_available_languages(self) -> list[str]:
        """
        Get a list of *engine-supported output* language codes.
        These are the codes the engine will actually use for synthesis.
        """
        pass

    @abc.abstractmethod
    def get_engine_name(self) -> str:
        '''Returns the display name of the TTS engine.'''
        pass

    @abc.abstractmethod
    def get_audio_format(self) -> str:
        '''Returns the audio format produced by the engine (e.g., "mp3", "wav").'''
        pass

# It might also be useful to have a method to get "friendly" input language names
# or to check if an input language is supported via mappings.
# For example:
# @abc.abstractmethod
# def get_supported_input_languages(self) -> list[str]:
#     """ Returns a list of language identifiers that can be mapped to an engine language. """
#     pass

class GTTSEngine(TTSEngine):
    """TTS Engine implementation using Google Text-to-Speech (gTTS)."""

    def __init__(self, config=None):
        super().__init__(config)
        # Language configurations are loaded from the module level for this example
        self.language_mappings = LANGUAGE_MAPPINGS
        self.default_language = DEFAULT_LANGUAGE
        self.supported_gtts_languages = SUPPORTED_GTTS_LANGUAGES
        self.tld_options = GTTS_TLD_OPTIONS
        logger.info("GTTSEngine initialized with pre-defined language configurations.")

    def get_gtts_lang_code(self, input_lang_code: str) -> str:
        """
        Maps an input language code (potentially non-standard) to a gTTS-compatible one.
        Falls back to default language if mapping fails or mapped language is not supported.
        """
        normalized_input = input_lang_code.lower().strip()
        gtts_code = self.language_mappings.get(normalized_input)

        if gtts_code and gtts_code in self.supported_gtts_languages:
            logger.info(f"Input lang '{input_lang_code}' mapped to gTTS code '{gtts_code}'.")
            return gtts_code
        elif gtts_code: # Mapped but not in our explicit supported list
            logger.warning(
                f"Input lang '{input_lang_code}' mapped to '{gtts_code}', "
                f"which is not in SUPPORTED_GTTS_LANGUAGES. Falling back to default '{self.default_language}'."
            )
            return self.default_language
        else: # Not found in mappings
            logger.warning(
                f"Input lang '{input_lang_code}' not found in LANGUAGE_MAPPINGS. "
                f"Falling back to default '{self.default_language}'."
            )
            return self.default_language

    def synthesize_speech(self, text: str, language_code: str, **kwargs) -> bytes:
        """
        Synthesizes text to speech using gTTS.
        Args:
            text: The text to synthesize.
            language_code: The *input* language code (e.g., 'en', 'eng', 'japanese').
            **kwargs: Can include 'tld' (e.g., 'co.uk') or a 'voice'/'region'
                      identifier that can be mapped to a tld.
        Returns:
            MP3 audio data as bytes.
        Raises:
            TTSSynthesisError: If gTTS fails to synthesize.
        """
        actual_gtts_lang_code = self.get_gtts_lang_code(language_code)

        if not text:
            raise TTSSynthesisError("Input text cannot be empty.")

        try:
            # Handle TLD: if 'tld' is directly in kwargs, use it.
            # Otherwise, if 'voice' or 'region' is in kwargs, try to map it from self.tld_options.
            tld = kwargs.get('tld')
            if not tld:
                voice_or_region = kwargs.get('voice', kwargs.get('region'))
                if voice_or_region:
                    tld = self.tld_options.get(voice_or_region.lower(), self.tld_options.get(voice_or_region.upper()))

            # Default TLD if none is found or specified
            tld = tld or 'com'

            logger.info(f"Synthesizing with gTTS: text='{text[:30]}...', lang='{actual_gtts_lang_code}', tld='{tld}'")

            # lang_check=True is default and recommended.
            tts = gTTS(text=text, lang=actual_gtts_lang_code, tld=tld, lang_check=True)
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            audio_bytes = mp3_fp.getvalue()

            if not audio_bytes:
                logger.error("gTTS returned empty audio data.")
                raise TTSSynthesisError("gTTS returned empty audio data.")
            logger.info(f"Successfully synthesized {len(audio_bytes)} bytes.")
            return audio_bytes
        except gTTSError as e:
            logger.error(f"gTTS error during synthesis: {e} (lang: {actual_gtts_lang_code}, tld: {tld})")
            raise TTSSynthesisError(f"gTTS error: {str(e)} (lang: {actual_gtts_lang_code}, tld: {tld})")
        except Exception as e:
            logger.exception("An unexpected error occurred during gTTS synthesis.")
            raise TTSSynthesisError(f"An unexpected error occurred during gTTS synthesis: {str(e)}")

    def get_available_languages(self) -> list[str]:
        """
        Returns the list of gTTS-compatible language codes explicitly supported by this engine's configuration.
        """
        return self.supported_gtts_languages

    def get_engine_name(self) -> str:
        return "gTTS"

    def get_audio_format(self) -> str:
        return "mp3"

# --- VOICEVOX Engine Implementation ---
# Assuming voicevox.py (VOICEVOXClient) is in the same directory or accessible
try:
    from voicevox import VOICEVOXClient
    import requests # VOICEVOXClient uses requests
    VOICEVOX_AVAILABLE = True
except ImportError:
    logger.warning("VOICEVOXClient could not be imported. VoicevoxEngine will not be available.")
    VOICEVOXClient = None # Placeholder if not available
    VOICEVOX_AVAILABLE = False

if VOICEVOX_AVAILABLE:
    class VoicevoxEngine(TTSEngine):
        """TTS Engine implementation using a local VOICEVOX engine."""

        def __init__(self, config=None):
            super().__init__(config)
            # TODO: Allow host/port to be configured via self.config
            self.host = self.config.get("voicevox_host", "127.0.0.1") if self.config else "127.0.0.1"
            self.port = self.config.get("voicevox_port", 50021) if self.config else 50021

            # Construct the base URL for the client
            base_url = f"http://{self.host}:{self.port}"
            self.voicevox_client = VOICEVOXClient(base_url=base_url)

            # Default speaker ID (e.g., Zundamon - Normal)
            # This can also be made configurable via self.config
            self.default_speaker_id = self.config.get("voicevox_default_speaker_id", 3) if self.config else 3
            logger.info(f"VoicevoxEngine initialized. Host: {self.host}, Port: {self.port}, Default Speaker ID: {self.default_speaker_id}")

        def get_engine_name(self) -> str:
            return "VOICEVOX"

        def get_audio_format(self) -> str:
            return "wav"

        def synthesize_speech(self, text: str, language_code: str, **kwargs) -> bytes:
            logger.info(f"VoicevoxEngine attempting synthesis: Text='{text[:30]}...', Lang='{language_code}'")

            if not language_code.lower().startswith('ja'):
                logger.warning("VoicevoxEngine primarily supports Japanese. Synthesis might fail or produce incorrect results.")
                # Depending on strictness, could raise TTSSynthesisError or attempt anyway.
                # For now, let's attempt, as some models might handle other inputs gracefully (though unlikely for speech).
                # raise TTSSynthesisError("VOICEVOX primarily supports Japanese.")

            speaker_id = kwargs.get('speaker_id', kwargs.get('voice_id', self.default_speaker_id))
            # Ensure speaker_id is an integer
            try:
                speaker_id = int(speaker_id)
            except ValueError:
                logger.warning(f"Invalid speaker_id format: '{speaker_id}'. Falling back to default: {self.default_speaker_id}")
                speaker_id = self.default_speaker_id

            logger.info(f"Using speaker_id: {speaker_id}")

            if not text:
                raise TTSSynthesisError("Input text cannot be empty for VOICEVOX.")

            try:
                query = self.voicevox_client.audio_query(text, speaker_id)
                wav_bytes = self.voicevox_client.synthesis(query, speaker_id)
                if not wav_bytes:
                    logger.error("VOICEVOX returned empty audio data.")
                    raise TTSSynthesisError("VOICEVOX returned empty audio data.")
                logger.info(f"VOICEVOX synthesis successful, audio size: {len(wav_bytes)} bytes.")
                return wav_bytes
            except requests.exceptions.RequestException as e:
                logger.error(f"VOICEVOX API connection error: {e}")
                raise TTSSynthesisError(f"VOICEVOX API connection error: {str(e)}")
            except Exception as e: # Catch other potential errors from VOICEVOXClient
                logger.exception("An unexpected error occurred during VOICEVOX synthesis.")
                raise TTSSynthesisError(f"VOICEVOX error: {str(e)}")

        def get_available_languages(self) -> list[str]:
            return ['ja'] # VOICEVOX is primarily Japanese

        def get_voicevox_speakers(self) -> list:
            """
            Retrieves the list of available speakers and their styles from the VOICEVOX engine.
            Returns:
                A list of speaker information dicts, or an empty list if an error occurs.
            """
            try:
                logger.info("Attempting to fetch speakers from VOICEVOX engine...")
                speakers = self.voicevox_client.speakers()
                if speakers:
                    logger.info(f"Successfully fetched {len(speakers)} speakers from VOICEVOX.")
                else:
                    logger.warning("VOICEVOX returned no speakers, or an empty list.")
                return speakers if speakers else []
            except requests.exceptions.RequestException as e:
                logger.error(f"Could not connect to VOICEVOX engine to get speakers: {e}")
                return []
            except Exception as e:
                logger.exception("An unexpected error occurred while fetching VOICEVOX speakers.")
                return []
else: # Handles VOICEVOX_AVAILABLE = False
    class VoicevoxEngine(TTSEngine): # type: ignore # Create a dummy class if not available
        def __init__(self, config=None):
            super().__init__(config)
            logger.error("VoicevoxEngine is not available due to missing VOICEVOXClient or dependencies.")
        def get_engine_name(self) -> str: return "VOICEVOX (Unavailable)"
        def get_audio_format(self) -> str: return "wav"
        def synthesize_speech(self, text: str, language_code: str, **kwargs) -> bytes:
            raise TTSSynthesisError("VoicevoxEngine is not available.")
        def get_available_languages(self) -> list[str]: return []
        def get_voicevox_speakers(self) -> list: return []


if __name__ == "__main__":
    # Configure logger for direct script execution (if not configured by an app)
    if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger.info("--- Starting GTTSEngine Tests ---")
    engine = GTTSEngine()

    logger.info("Testing get_available_languages():")
    languages = engine.get_available_languages()
    logger.info(f"Available languages: {languages}")
    print(f"Available (supported gTTS) languages: {languages}")


    logger.info("\n--- Testing get_gtts_lang_code() ---")
    test_codes = {
        "English": "en", "eng": "en", "japanese": "ja", "Jpn": "ja",
        "UnsupportedLang": "xx", " german ": "de" # Test normalization
    }
    for name, code in test_codes.items():
        mapped_code = engine.get_gtts_lang_code(code)
        logger.info(f"Input: '{code}' ({name}) -> Mapped: '{mapped_code}'")
        print(f"Input: '{code}' ({name}) -> Mapped: '{mapped_code}'")


    logger.info("\n--- Testing synthesize_speech() ---")
    test_cases = [
        {"text": "Hello world", "lang": "en", "file": "test_gtts_lang_en.mp3"},
        {"text": "こんにちは世界", "lang": "japanese", "file": "test_gtts_lang_ja.mp3"},
        {"text": "This should use default language", "lang": "nonexistent", "file": "test_gtts_lang_default.mp3"},
        {"text": "Hello with UK accent", "lang": "en", "kwargs": {"tld": "co.uk"}, "file": "test_gtts_lang_en_uk.mp3"},
        {"text": "Hello with US accent (via region)", "lang": "en", "kwargs": {"region": "US"}, "file": "test_gtts_lang_en_us_region.mp3"},
    ]

    for case in test_cases:
        output_filename = case["file"]
        try:
            logger.info(f"Synthesizing: text='{case['text']}', lang='{case['lang']}', kwargs={case.get('kwargs', {})}")
            print(f"\nSynthesizing: text='{case['text']}', lang='{case['lang']}', kwargs={case.get('kwargs', {})}")

            audio_data = engine.synthesize_speech(case["text"], case["lang"], **case.get("kwargs", {}))

            with open(output_filename, "wb") as f:
                f.write(audio_data)
            logger.info(f"Successfully synthesized and saved to {output_filename} ({len(audio_data)} bytes).")
            print(f"Successfully synthesized and saved to {output_filename} ({len(audio_data)} bytes).")
        except TTSSynthesisError as e:
            logger.error(f"TTSSynthesisError for '{case['text']}': {e}")
            print(f"TTSSynthesisError for '{case['text']}': {e}")
        except Exception as e: # Catch any other unexpected errors
            logger.exception(f"Unexpected error for '{case['text']}': {e}")
            print(f"Unexpected error for '{case['text']}': {e}")

    logger.info("\n--- Testing Error Conditions ---")
    # Test error case: empty text
    try:
        logger.info("Testing with empty text...")
        print("\nTesting with empty text...")
        engine.synthesize_speech("", "en")
    except TTSSynthesisError as e:
        logger.info(f"Correctly caught TTSSynthesisError for empty text: {e}")
        print(f"Correctly caught TTSSynthesisError for empty text: {e}")

    logger.info("--- GTTSEngine Tests Completed ---")
    print("\nAll GTTSEngine tests finished.")

    logger.info("\n--- Starting VoicevoxEngine Tests ---")
    # Check if VoicevoxEngine is truly available or if it's the dummy version
    if VOICEVOX_AVAILABLE:
        vv_engine = VoicevoxEngine()
        logger.info(f"VoicevoxEngine instantiated. Engine Name: {vv_engine.get_engine_name()}")
        print(f"\nEngine Name: {vv_engine.get_engine_name()}")
        logger.info(f"Audio Format: {vv_engine.get_audio_format()}")
        print(f"Audio Format: {vv_engine.get_audio_format()}")

        vv_langs = vv_engine.get_available_languages()
        logger.info(f"Available languages for VOICEVOX: {vv_langs}")
        print(f"Available languages for VOICEVOX: {vv_langs}")

        logger.info("Attempting to get VOICEVOX speakers...")
        speakers_list = vv_engine.get_voicevox_speakers()
        if speakers_list:
            logger.info(f"Found {len(speakers_list)} speakers/groups in VOICEVOX.")
            print(f"Found {len(speakers_list)} speakers/groups in VOICEVOX. First few: {speakers_list[:2]}")
            # Attempt synthesis only if speakers are found and engine seems responsive
            test_text_vv = "こんにちは、これはボイスボックスエンジンのテストです。"
            # Use a speaker ID from the fetched list if possible, otherwise default.
            # Speaker ID 3 is often Zundamon Normal.
            speaker_id_to_test = 3
            if speakers_list and speakers_list[0]['styles']:
                 # Try to use a valid ID from the fetched list, e.g., first style of first speaker
                 # This is just an example, more robust selection might be needed.
                 # speaker_id_to_test = speakers_list[0]['styles'][0]['id']
                 pass # Keep default 3 for now as it's common

            output_filename_vv = "test_voicevox_engine_output.wav"
            try:
                logger.info(f"Synthesizing with VOICEVOX: '{test_text_vv}', Speaker ID: {speaker_id_to_test}")
                print(f"\nSynthesizing with VOICEVOX: '{test_text_vv}', Speaker ID: {speaker_id_to_test}")
                audio_data_vv = vv_engine.synthesize_speech(test_text_vv, "ja", speaker_id=speaker_id_to_test)
                with open(output_filename_vv, "wb") as f:
                    f.write(audio_data_vv)
                logger.info(f"Successfully synthesized VOICEVOX audio and saved to {output_filename_vv} ({len(audio_data_vv)} bytes).")
                print(f"Successfully synthesized VOICEVOX audio and saved to {output_filename_vv}.")
            except TTSSynthesisError as e:
                logger.error(f"TTSSynthesisError during VOICEVOX synthesis test: {e}")
                print(f"TTSSynthesisError during VOICEVOX synthesis test: {e} (This is expected if VOICEVOX engine is not running)")
            except Exception as e:
                logger.exception(f"Unexpected error during VOICEVOX synthesis test: {e}")
                print(f"Unexpected error during VOICEVOX synthesis test: {e}")
        else:
            logger.warning("Could not retrieve VOICEVOX speakers. Skipping synthesis test.")
            print("Could not retrieve VOICEVOX speakers. Skipping synthesis test. (Is VOICEVOX engine running on http://127.0.0.1:50021 ?)")
    else:
        logger.warning("VoicevoxEngine is not available (VOICEVOXClient import failed). Skipping VoicevoxEngine tests.")
        print("\nVoicevoxEngine is not available. Skipping VoicevoxEngine tests.")

    logger.info("--- All Engine Tests Completed ---")
    print("\nAll engine tests finished. Check logs and any output files.")
