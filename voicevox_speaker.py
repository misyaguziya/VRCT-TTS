#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VOICEVOX Engine APIで生成した音声を特定のスピーカーデバイスで再生するモジュール
"""

import io
import wave
import pyaudio
from typing import Optional, Dict, Union, List


class VoicevoxSpeaker:
    """VOICEVOXの音声を特定のスピーカーデバイスで再生するクラス"""

    def __init__(self, output_device_index: Optional[int] = None, output_device_index_2: Optional[int] = None, speaker_2_enabled: bool = False):
        """
        VoicevoxSpeakerの初期化

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
                # 出力チャンネル数が0より大きい場合、出力デバイスとして使用可能
                if device_info['maxOutputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device_info['name'],
                        'channels': device_info['maxOutputChannels'],
                        'sample_rate': int(device_info['defaultSampleRate'])
                    })
        finally:
            p.terminate()

        return devices

    def play_bytes(self, audio_data: bytes, wait: bool = True) -> None:
        """
        バイトデータを再生する

        Args:
            audio_data (bytes): WAV形式の音声データ
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        self.stop_requested = False
        self.current_stream_1 = None
        self.current_stream_2 = None

        # バイトデータをWaveReadオブジェクトに変換
        with io.BytesIO(audio_data) as f:
            with wave.open(f, 'rb') as wf:
                # WAVファイルから情報を取得
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()

                # ストリームを開く
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

                # データを読み込んで再生
                chunk_size = 1024
                data = wf.readframes(chunk_size)

                try:
                    while len(data) > 0:
                        if self.stop_requested:
                            break
                        if self.current_stream_1: # Check if stream exists before writing
                            self.current_stream_1.write(data)
                        if self.current_stream_2: # Check if stream exists before writing
                            self.current_stream_2.write(data)
                        data = wf.readframes(chunk_size)

                    if wait and not self.stop_requested: # Only stop if not already stopped
                        if self.current_stream_1:
                            self.current_stream_1.stop_stream()
                        if self.current_stream_2:
                            self.current_stream_2.stop_stream()
                finally:
                    if self.current_stream_1:
                        self.current_stream_1.close()
                    if self.current_stream_2:
                        self.current_stream_2.close()
                    # Reset stream attributes after closing
                    self.current_stream_1 = None
                    self.current_stream_2 = None


    def play_file(self, file_path: str, wait: bool = True) -> None:
        """
        ファイルを再生する

        Args:
            file_path (str): WAVファイルのパス
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        self.stop_requested = False
        self.current_stream_1 = None
        self.current_stream_2 = None

        # ファイルを開く
        wf = wave.open(file_path, 'rb')

        try:
            # WAVファイルから情報を取得
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()

            # ストリームを開く
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

            # データを読み込んで再生
            chunk_size = 1024
            data = wf.readframes(chunk_size)

            try:
                while len(data) > 0:
                    if self.stop_requested:
                        break
                    if self.current_stream_1: # Check if stream exists before writing
                        self.current_stream_1.write(data)
                    if self.current_stream_2: # Check if stream exists before writing
                        self.current_stream_2.write(data)
                    data = wf.readframes(chunk_size)

                if wait and not self.stop_requested: # Only stop if not already stopped
                    if self.current_stream_1:
                        self.current_stream_1.stop_stream()
                    if self.current_stream_2:
                        self.current_stream_2.stop_stream()
            finally:
                if self.current_stream_1:
                    self.current_stream_1.close()
                if self.current_stream_2:
                    self.current_stream_2.close()
                 # Reset stream attributes after closing
                self.current_stream_1 = None
                self.current_stream_2 = None
        finally:
            wf.close()

    def request_stop(self) -> None:
        """再生の停止をリクエストする"""
        self.stop_requested = True
        try:
            if self.current_stream_1 and self.current_stream_1.is_active():
                self.current_stream_1.stop_stream()
                self.current_stream_1.close()
        except Exception:
            pass # Ignore errors on stop
        finally:
            self.current_stream_1 = None # Ensure it's cleared

        try:
            if self.current_stream_2 and self.current_stream_2.is_active():
                self.current_stream_2.stop_stream()
                self.current_stream_2.close()
        except Exception:
            pass # Ignore errors on stop
        finally:
            self.current_stream_2 = None # Ensure it's cleared


# 使用例
if __name__ == "__main__":
    # 利用可能なデバイスを表示
    devices: List[Dict[str, Union[int, str, float]]] = VoicevoxSpeaker.list_audio_devices()
    print("利用可能なオーディオデバイス:")
    for i, device_info in enumerate(devices):  # Renamed device to device_info to avoid conflict
        print(
            f"{i}. {device_info['name']} (index: {device_info['index']}, channels: {device_info['channels']})")

    # デバイスを選択（ここでは最初のデバイスを使用）
    if devices:
        speaker: VoicevoxSpeaker = VoicevoxSpeaker(
            output_device_index=int(devices[0]['index']))

        # VOICEVOXクライアントをインポート (同じディレクトリ内のvoicevox.pyから)
        from voicevox import VOICEVOXClient, Dict, Any  # Added Any for vv_speakers

        client: VOICEVOXClient = VOICEVOXClient()

        # スピーカーを取得
        vv_speakers: List[Dict[str, Any]] = client.speakers()
        if vv_speakers:
            speaker_id: int = vv_speakers[0]["styles"][0]["id"]

            # クエリを作成して音声合成
            query: Dict[str, Any] = client.audio_query(
                "こんにちは、テストです。", speaker_id)
            audio_data: Optional[bytes] = client.synthesis(query, speaker_id)

            # 特定のデバイスで再生
            if audio_data:
                print(f"デバイス '{devices[0]['name']}' で再生します...")
                speaker.play_bytes(audio_data)
                print("再生完了")
            else:
                print("音声データの生成に失敗しました。")
    else:
        print("利用可能なオーディオデバイスがありません。")
