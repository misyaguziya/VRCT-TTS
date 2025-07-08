#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音声データを特定のスピーカーデバイスで再生する共通モジュール
"""

import io
import wave
import pyaudiowpatch as pyaudio
import threading
from typing import Optional, Dict, Union, List

class AudioPlayer:
    """音声データを特定のスピーカーデバイスで再生するクラス"""

    def __init__(self, output_device_index: Optional[int] = None, output_device_index_2: Optional[int] = None, speaker_2_enabled: bool = False):
        """
        AudioPlayerの初期化

        Args:
            output_device_index (Optional[int], optional):
                出力デバイスのインデックス。Noneの場合はデフォルトデバイスを使用。
                利用可能なデバイスは list_audio_devices() で確認できます。
            output_device_index_2 (Optional[int], optional):
                2番目の出力デバイスのインデックス。Noneの場合は使用しない。
            speaker_2_enabled (bool, optional):
                2番目のスピーカー出力を有効にするかどうか。デフォルトはFalse。
        """
        self.output_device_index = output_device_index
        self.output_device_index_2 = output_device_index_2
        self.speaker_2_enabled = speaker_2_enabled
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
