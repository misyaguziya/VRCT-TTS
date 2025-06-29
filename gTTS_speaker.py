#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gTTSで生成した音声を特定のスピーカーデバイスで再生するモジュール
"""

import io
import wave
import pyaudiowpatch as pyaudio
import threading
import miniaudio
from typing import Optional, Dict, Union, List
from gtts import gTTS, lang

class gTTSSpeaker:
    """gTTSの音声を特定のスピーカーデバイスで再生するクラス"""

    def __init__(self, output_device_index: Optional[int] = None, output_device_index_2: Optional[int] = None, speaker_2_enabled: bool = False, lang: str = "ja"):
        """
        gTTSSpeakerの初期化

        Args:
            output_device_index (Optional[int], optional):
                出力デバイスのインデックス。Noneの場合はデフォルトデバイスを使用。
                利用可能なデバイスは list_audio_devices() で確認できます。
            output_device_index_2 (Optional[int], optional):
                2番目の出力デバイスのインデックス。Noneの場合は使用しない。
            speaker_2_enabled (bool, optional):
                2番目のスピーカー出力を有効にするかどうか。デフォルトはFalse。
            lang (str, optional):
                gTTSで使用する言語。デフォルトは "ja" (日本語)。
        """
        self.output_device_index = output_device_index
        self.output_device_index_2 = output_device_index_2
        self.speaker_2_enabled = speaker_2_enabled
        self.lang = lang
        self.p = pyaudio.PyAudio()
        self.stop_requested: bool = False
        self.current_stream_1: Optional[pyaudio.Stream] = None
        self.current_stream_2: Optional[pyaudio.Stream] = None
        self._stream_lock = threading.Lock()

    def __del__(self) -> None:
        """クリーンアップ処理"""
        if hasattr(self, 'p') and self.p:
            self.p.terminate()

    @staticmethod
    def list_audio_devices() -> List[Dict[str, Union[int, str, float]]]:
        """
        利用可能なオーディオデバイスの一覧を取得する

        Returns:
            List[Dict[str, Union[int, str, float]]]: デバイス情報のリスト
        """
        p = pyaudio.PyAudio()
        devices: List[Dict[str, Union[int, str, float]]] = []

        try:
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info['maxOutputChannels'] > 0:
                    device_name = device_info['name']
                    if isinstance(device_name, str):
                        try:
                            if all(ord(c) >= 32 and ord(c) <= 126 or ord(c) >= 160 for c in device_name):
                                fixed_name = device_name
                            else:
                                try:
                                    device_bytes = device_name.encode('latin1')
                                    fixed_name = device_bytes.decode('cp932', errors='replace')
                                except (UnicodeDecodeError, UnicodeEncodeError):
                                    try:
                                        device_bytes = device_name.encode('latin1')
                                        fixed_name = device_bytes.decode('utf-8', errors='replace')
                                    except (UnicodeDecodeError, UnicodeEncodeError):
                                        fixed_name = ''.join(c if ord(c) >= 32 and ord(c) <= 126 or ord(c) >= 160 else '?' for c in device_name)
                                        if not fixed_name.strip():
                                            fixed_name = f"Audio Device {i}"
                        except Exception:
                            fixed_name = f"Audio Device {i}"
                    else:
                        fixed_name = str(device_name)
                    
                    host_api_index = device_info['hostApi']
                    host_info = p.get_host_api_info_by_index(host_api_index)
                    host_name = host_info['name']

                    devices.append({
                        'index': i,
                        'name': fixed_name,
                        'channels': device_info['maxOutputChannels'],
                        'sample_rate': int(device_info['defaultSampleRate']),
                        'host_api_index': host_api_index,
                        'host_name': host_name
                    })
        finally:
            p.terminate()

        return devices

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
        self.play_wav_bytes(wav_fp.read(), wait=wait)

    def play_wav_bytes(self, audio_data: bytes, wait: bool = True) -> None:
        """
        WAV形式のバイトデータを再生する

        Args:
            audio_data (bytes): WAV形式の音声データ
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        with self._stream_lock:
            self.stop_requested = False
            self.current_stream_1 = None
            self.current_stream_2 = None

        with io.BytesIO(audio_data) as f:
            with wave.open(f, 'rb') as wf:
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()

                with self._stream_lock:
                    if self.stop_requested:
                        return

                    self.current_stream_1 = self.p.open(
                        format=self.p.get_format_from_width(width),
                        channels=channels,
                        rate=rate,
                        output=True,
                        output_device_index=self.output_device_index
                    )
                    if self.speaker_2_enabled and self.output_device_index_2 is not None:
                        self.current_stream_2 = self.p.open(
                            format=self.p.get_format_from_width(width),
                            channels=channels,
                            rate=rate,
                            output=True,
                            output_device_index=self.output_device_index_2
                        )

                chunk_size = 1024
                data = wf.readframes(chunk_size)

                try:
                    while len(data) > 0:
                        with self._stream_lock:
                            if self.stop_requested:
                                break
                            if self.current_stream_1:
                                self.current_stream_1.write(data)
                            if self.current_stream_2:
                                self.current_stream_2.write(data)
                        data = wf.readframes(chunk_size)

                    if wait and not self.stop_requested:
                        with self._stream_lock:
                            if self.current_stream_1:
                                self.current_stream_1.stop_stream()
                            if self.current_stream_2:
                                self.current_stream_2.stop_stream()
                finally:
                    with self._stream_lock:
                        if self.current_stream_1:
                            try:
                                self.current_stream_1.close()
                            except Exception:
                                pass
                        if self.current_stream_2:
                            try:
                                self.current_stream_2.close()
                            except Exception:
                                pass
                        self.current_stream_1 = None
                        self.current_stream_2 = None

    def request_stop(self) -> None:
        """再生の停止をリクエストする"""
        with self._stream_lock:
            self.stop_requested = True
            try:
                if self.current_stream_1 and self.current_stream_1.is_active():
                    self.current_stream_1.stop_stream()
            except Exception:
                pass

            try:
                if self.current_stream_2 and self.current_stream_2.is_active():
                    self.current_stream_2.stop_stream()
            except Exception:
                pass

# 使用例
if __name__ == "__main__":
    # 対応言語一覧を表示
    supported_langs = gTTSSpeaker.list_supported_languages()
    print("対応言語:")
    for lang_code, lang_name in supported_langs.items():
        print(f"- {lang_code}: {lang_name}")

    # 利用可能なデバイスを表示
    devices = gTTSSpeaker.list_audio_devices()
    print("\n利用可能なオーディオデバイス:")
    for i, device_info in enumerate(devices):
        print(
            f"{i}. {device_info['name']} (index: {device_info['index']}, channels: {device_info['channels']})")

    # デバイスを選択
    if devices:
        speaker = gTTSSpeaker(output_device_index=int(devices[1]['index']))

        # 日本語で再生
        print(f"\nデバイス '{devices[1]['name']}' で日本語のテスト音声を再生します...")
        speaker.speak("こんにちは、これはテストです。", lang="ja")
        print("再生完了")

        # 英語で再生
        print(f"\nデバイス '{devices[1]['name']}' で英語のテスト音声を再生します...")
        speaker.speak("Hello, this is a test.", lang="en")
        print("再生完了")
    else:
        print("\n利用可能なオーディオデバイスがありません。")
