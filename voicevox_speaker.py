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

    def __init__(self, output_device_index: Optional[int] = None):
        """
        VoicevoxSpeakerの初期化

        Args:
            output_device_index (Optional[int], optional): 
                出力デバイスのインデックス。Noneの場合はデフォルトデバイスを使用。
                利用可能なデバイスは list_audio_devices() で確認できます。
        """
        self.output_device_index = output_device_index
        self.p = pyaudio.PyAudio()

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
        # バイトデータをWaveReadオブジェクトに変換
        with io.BytesIO(audio_data) as f:
            with wave.open(f, 'rb') as wf:
                # WAVファイルから情報を取得
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                rate = wf.getframerate()

                # ストリームを開く
                stream = self.p.open(
                    format=self.p.get_format_from_width(width),
                    channels=channels,
                    rate=rate,
                    output=True,
                    output_device_index=self.output_device_index
                )

                # データを読み込んで再生
                chunk_size = 1024
                data = wf.readframes(chunk_size)

                try:
                    while len(data) > 0:
                        stream.write(data)
                        data = wf.readframes(chunk_size)

                    if wait:
                        # バッファ内のデータ再生完了まで待機
                        stream.stop_stream()
                finally:
                    stream.close()

    def play_file(self, file_path: str, wait: bool = True) -> None:
        """
        ファイルを再生する

        Args:
            file_path (str): WAVファイルのパス
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        # ファイルを開く
        wf = wave.open(file_path, 'rb')

        try:
            # WAVファイルから情報を取得
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()

            # ストリームを開く
            stream = self.p.open(
                format=self.p.get_format_from_width(width),
                channels=channels,
                rate=rate,
                output=True,
                output_device_index=self.output_device_index
            )

            # データを読み込んで再生
            chunk_size = 1024
            data = wf.readframes(chunk_size)

            try:
                while len(data) > 0:
                    stream.write(data)
                    data = wf.readframes(chunk_size)

                if wait:
                    # バッファ内のデータ再生完了まで待機
                    stream.stop_stream()
            finally:
                stream.close()
        finally:
            wf.close()


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
