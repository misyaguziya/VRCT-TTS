#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gTTSで生成した音声を特定のスピーカーデバイスで再生するモジュール
"""

import io
import wave
import miniaudio
from typing import Optional, Dict
from gtts import gTTS, lang
from audio_player import AudioPlayer

class gTTSSpeaker:
    """gTTSの音声を特定のスピーカーデバイスで再生するクラス"""

    def __init__(self, player: AudioPlayer, lang: str = "ja"):
        """
        gTTSSpeakerの初期化

        Args:
            player (AudioPlayer): オーディオ再生を処理するAudioPlayerインスタンス
            lang (str, optional): gTTSで使用する言語。デフォルトは "ja" (日本語)。
        """
        self.player = player
        self.lang = lang

    @staticmethod
    def list_supported_languages() -> Dict[str, str]:
        """
        gTTSでサポートされている言語の一覧を取得する

        Returns:
            Dict[str, str]: 言語コードをキー、言語名を値とする辞書
        """
        return lang.tts_langs()

    def speak(self, text: str, lang: Optional[str] = None, wait: bool = True) -> None:
        """
        指定されたテキストを音声合成して再生する

        Args:
            text (str): 読み上げるテキスト
            lang (Optional[str], optional): 使用する言語。Noneの場合はインスタンスのデフォルト言語を使用。
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        current_lang = lang if lang else self.lang

        # gTTSでMP3データを生成
        mp3_fp = io.BytesIO()
        tts = gTTS(text=text, lang=current_lang)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # miniaudioでMP3をデコードし、WAV形式のバイトデータを作成
        decoded = miniaudio.decode(mp3_fp.read())
        wav_fp = io.BytesIO()
        with wave.open(wav_fp, "wb") as wf:
            wf.setnchannels(decoded.nchannels)
            wf.setsampwidth(decoded.sample_width)
            wf.setframerate(decoded.sample_rate)
            wf.writeframes(decoded.samples)
        wav_fp.seek(0)

        # WAVデータを再生
        self.player.play_wav_bytes(wav_fp.read(), wait=wait)

    def request_stop(self) -> None:
        """再生の停止をリクエストする"""
        self.player.request_stop()

# 使用例
if __name__ == "__main__":
    # 対応言語一覧を表示
    supported_langs = gTTSSpeaker.list_supported_languages()
    print("対応言語数:", len(supported_langs))
    print("対応言語:")
    for lang_code, lang_name in supported_langs.items():
        print(f"- {lang_code}: {lang_name}")

    # 利用可能なデバイスを表示
    devices = AudioPlayer.list_audio_devices()
    print("\n利用可能なオーディオデバイス:")
    for i, device_info in enumerate(devices):
        print(
            f"{i}. {device_info['name']} (index: {device_info['index']}, channels: {device_info['channels']})")

    # デバイスを選択
    if devices:
        audio_player = AudioPlayer(output_device_index=int(devices[0]['index']))
        speaker = gTTSSpeaker(player=audio_player)

        # 日本語で再生
        print(f"\nデバイス '{devices[0]['name']}' で日本語のテスト音声を再生します...")
        speaker.speak("こんにちは、これはテストです。", lang="ja")
        print("再生完了")

        # 英語で再生
        print(f"\nデバイス '{devices[0]['name']}' で英語のテスト音声を再生します...")
        speaker.speak("Hello, this is a test.", lang="en")
        print("再生完了")

        # 非対応言語のテスト
        print("\n--- 非対応言語のテスト ---")
        try:
            print("非対応言語 'Amharic (am)' での再生を試みます...")
            # This should fail
            speaker.speak("This is a test with an unsupported language.", lang="am")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            print("非対応言語が正しく処理されているようです。")

    else:
        print("\n利用可能なオーディオデバイスがありません。")

