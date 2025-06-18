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
    print("\nAll GTTSEngine tests finished. Check logs and output files.")
