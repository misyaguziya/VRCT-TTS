#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VOICEVOX Engine APIで生成した音声を特定のスピーカーデバイスで再生するモジュール
"""

from audio_player import AudioPlayer
from voicevox import VOICEVOXClient
from typing import Dict, Any, List, Union


class VoicevoxSpeaker:
    """VOICEVOXの音声を特定のスピーカーデバイスで再生するクラス"""

    def __init__(self, player: AudioPlayer, client: VOICEVOXClient):
        """
        VoicevoxSpeakerの初期化

        Args:
            player (AudioPlayer): オーディオ再生を処理するAudioPlayerインスタンス
            client (VOICEVOXClient): VOICEVOX APIと通信するためのクライアント
        """
        self.player = player
        self.client = client

    def get_audio_data(self, text: str, speaker_id: int) -> bytes | None:
        """
        指定されたテキストをVOICEVOXで音声合成してWAVデータを返す

        Args:
            text (str): 読み上げるテキスト
            speaker_id (int): VOICEVOXのキャラクターID

        Returns:
            bytes | None: 音声データ(WAV形式)
        """
        query = self.client.audio_query(text, speaker_id)
        audio_data = self.client.synthesis(query, speaker_id)
        return audio_data

    def speak(self, text: str, speaker_id: int, wait: bool = True) -> None:
        """
        指定されたテキストをVOICEVOXで音声合成して再生する

        Args:
            text (str): 読み上げるテキスト
            speaker_id (int): VOICEVOXのキャラクターID
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        audio_data = self.get_audio_data(text, speaker_id)
        if audio_data:
            self.play_bytes(audio_data, wait=wait)

    def play_bytes(self, audio_data: bytes, wait: bool = True) -> None:
        """
        WAV形式のバイトデータを再生する

        Args:
            audio_data (bytes): 再生するWAVデータ
            wait (bool, optional): 再生が終了するまで待機するかどうか。デフォルトはTrue。
        """
        self.player.play_wav_bytes(audio_data, wait=wait)

    def request_stop(self) -> None:
        """再生の停止をリクエストする"""
        self.player.request_stop()


# 使用例
if __name__ == "__main__":
    # 利用可能なデバイスを表示
    devices: List[Dict[str, Union[int, str, float]]] = AudioPlayer.list_audio_devices()
    print("利用可能なオーディオデバイス:")
    for i, device_info in enumerate(devices):
        print(
            f"{i}. {device_info['name']} (index: {device_info['index']}, channels: {device_info['channels']})")

    # デバイスを選択（ここでは最初のデバイスを使用）
    if devices:
        audio_player = AudioPlayer(output_device_index=int(devices[0]['index']))
        voicevox_client = VOICEVOXClient()
        speaker = VoicevoxSpeaker(player=audio_player, client=voicevox_client)

        # スピーカーを取得
        vv_speakers: List[Dict[str, Any]] = voicevox_client.speakers()
        if vv_speakers:
            speaker_id: int = vv_speakers[0]["styles"][0]["id"]

            # 特定のデバイスで再生
            print(f"デバイス '{devices[0]['name']}' で再生します...")
            speaker.speak("こんにちは、テストです。", speaker_id)
            print("再生完了")
        else:
            print("VOICEVOXからスピーカーが取得できませんでした。")
    else:
        print("利用可能なオーディオデバイスがありません。")
