import time
from gtts import gTTS
from playsound import playsound
import os

def text_to_speech_and_play(text, lang_code, filename_prefix):
    """
    Synthesizes text to speech, saves to an MP3 file, measures latency,
    and attempts to play the audio.
    """
    filepath = f"{filename_prefix}_{lang_code}.mp3"
    print(f"Synthesizing '{text[:30]}...' in {lang_code} to {filepath}")

    try:
        start_time = time.time()
        tts = gTTS(text=text, lang=lang_code)
        tts.save(filepath)
        end_time = time.time()
        synthesis_duration = end_time - start_time
        print(f"Successfully saved {filepath}. Synthesis time: {synthesis_duration:.4f} seconds.")

        # Attempt to play the sound
        print(f"Attempting to play {filepath}...")
        playsound(filepath)
        # Adding a small delay to ensure playback can be perceived if it's very short
        # or to allow playsound to finish before the script potentially ends or prints more.
        # This might not be strictly necessary depending on playsound's behavior.
        time.sleep(1)
        print(f"Playback of {filepath} likely finished or is in progress in background.")
        return filepath, synthesis_duration
    except Exception as e:
        print(f"Error during TTS or playback for {lang_code}: {e}")
        # If playsound is the issue, the file might still be created.
        if os.path.exists(filepath):
            return filepath, synthesis_duration if 'synthesis_duration' in locals() else -1
        return None, -1

def main():
    test_phrases = [
        ("Hello, this is a test of gTTS in English.", "en", "english_test"),
        ("こんにちは、これは日本語でのgTTSのテストです。", "ja", "japanese_test"),
        ("안녕하세요, 이것은 한국어로 진행되는 gTTS 테스트입니다.", "ko", "korean_test"),
        ("Bonjour, ceci est un test de gTTS en français.", "fr", "french_test"),
    ]

    synthesis_times = {}
    generated_files = []

    for text, lang, prefix in test_phrases:
        generated_file, duration = text_to_speech_and_play(text, lang, prefix)
        if generated_file:
            generated_files.append(generated_file)
        if duration != -1:
            synthesis_times[lang] = duration
        print("-" * 30)

    # Longer text example
    long_text_en = (
        "This is a longer sentence to test the performance of gTTS for more substantial text. "
        "We are checking how long it takes to synthesize and save this audio."
    )
    print("Testing with longer English text...")
    generated_file, duration = text_to_speech_and_play(long_text_en, "en", "long_english_test")
    if generated_file:
        generated_files.append(generated_file)
    if duration != -1:
        synthesis_times["en_long"] = duration
    print("-" * 30)

    print("\n--- Summary ---")
    print("Generated MP3 files:")
    for f in generated_files:
        print(f"- {f}")

    print("\nSynthesis times (seconds):")
    for lang, time_taken in synthesis_times.items():
        print(f"- {lang}: {time_taken:.4f}")

    print("\nNote: Playback functionality depends on system audio capabilities and 'playsound' library integration.")
    print("If you don't hear audio, check your system's audio output and 'playsound' dependencies (like GStreamer on Linux).")

if __name__ == "__main__":
    main()
