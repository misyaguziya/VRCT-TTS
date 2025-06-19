#!/usr/bin/env python3
from gtts import gTTS
import time

languages = {
    "en": "Hello",
    "ja": "こんにちは",
    "ko": "안녕하세요",
    "fr": "Bonjour",
}

long_texts = {
    "en": "This is a longer sentence to test the performance of gTTS audio generation.",
    "ja": "これは、gTTS音声生成のパフォーマンスをテストするためのより長い文です。",
    "ko": "이것은 gTTS 오디오 생성 성능을 테스트하기 위한 더 긴 문장입니다.",
    "fr": "Ceci est une phrase plus longue pour tester les performances de la génération audio gTTS.",
}

def synthesize_and_measure(text, lang, filename_prefix):
    start_time = time.time()
    tts = gTTS(text=text, lang=lang)
    tts.save(f"{filename_prefix}_{lang}.mp3")
    end_time = time.time()
    latency = end_time - start_time
    return latency

if __name__ == "__main__":
    for lang, short_text in languages.items():
        short_latency = synthesize_and_measure(short_text, lang, "short_test")
        print(f"Latency for short text ({lang}): {short_latency:.4f} seconds")

        long_text = long_texts[lang]
        long_latency = synthesize_and_measure(long_text, lang, "long_test")
        print(f"Latency for long text ({lang}): {long_latency:.4f} seconds")
        print("-" * 30)
