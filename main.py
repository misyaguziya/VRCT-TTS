#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VOICEVOX Connector GUI
CustomTkinterを使用したVOICEVOXの設定GUI
"""

import os
import sys
import threading
import ctypes
from pathlib import Path
import customtkinter as ctk
from typing import Dict, List, Tuple, Optional, Any
import pyaudio
import websocket
import json
import time
import html

from voicevox import VOICEVOXClient
from voicevox_speaker import VoicevoxSpeaker
from config import Config


class VoicevoxConnectorGUI(ctk.CTk):
    """VOICEVOX Connector GUIアプリケーション"""

    def __init__(self) -> None:
        super().__init__()

        # アプリケーションのパスを取得
        if getattr(sys, 'frozen', False):
            self.app_path = os.path.dirname(sys.executable)
        else:
            self.app_path = os.path.dirname(os.path.abspath(__file__))

        # フォントのパスを設定
        fonts_path: str = os.path.join(self.app_path, "fonts", "NotoSansJP-VariableFont_wght.ttf")
        ctypes.windll.gdi32.AddFontResourceW(str(fonts_path))
        self.fonts_name = "Noto Sans JP"
        self.font_normal_14: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=14, weight="normal")
        self.font_normal_12: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=12, weight="normal")

        # アプリの設定
        self.title("VRCT VOICEVOX Connector")
        self.geometry("750x520")

        # ダークモードをデフォルトに設定
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")        # データ保存用の変数
        self.speakers_data: List[Dict[str, Any]] = []
        self.audio_devices: List[Dict[str, Any]] = []
        self.current_character: Optional[Dict[str, Any]] = None
        self.current_style: Optional[int] = None
        self.current_device: Optional[int] = None
        self.current_device_2: Optional[int] = None # For second speaker
        self.speaker_2_enabled: bool = False      # For second speaker
        self.volume: float = 0.8  # デフォルトの音量 (0.0-1.0)
        self.ws_url: str = "ws://127.0.0.1:2231"

        # UI Variables
        self.character_var = ctk.StringVar()
        self.style_var = ctk.StringVar()
        self.device_var = ctk.StringVar()
        self.device_var_2 = ctk.StringVar() # For second speaker
        self.speaker_2_enabled_var = ctk.BooleanVar(value=False) # For second speaker
        self.volume_value_var: Optional[ctk.StringVar] = None
        self.ws_url_var: Optional[ctk.StringVar] = None
        self.ws_button_var: Optional[ctk.StringVar] = None
        self.ws_status_var: Optional[ctk.StringVar] = None
        self.test_text_var: Optional[ctk.StringVar] = None
        self.status_var: Optional[ctk.StringVar] = None


        # WebSocket関連の変数
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.ws_connected: bool = False

        # Playback lock
        self.playback_lock = threading.Lock()

        # 設定を読み込む
        self.load_config()

        # VOICEVOXクライアントの初期化
        self.client: VOICEVOXClient = VOICEVOXClient()

        # UIの作成
        self.create_ui()

        # データの読み込み
        self.load_data()

        # プロトコルハンドラー
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_ui(self) -> None:
        """UIコンポーネントの作成"""
        # Initialize other StringVars that were previously Optional
        self.volume_value_var = ctk.StringVar(value=f"{int(self.volume * 100)}%")
        self.ws_url_var = ctk.StringVar(value=self.ws_url)
        self.ws_button_var = ctk.StringVar(value="WebSocket接続開始")
        self.ws_status_var = ctk.StringVar(value="WebSocket: 未接続")
        self.test_text_var = ctk.StringVar(value="こんにちは、VOICEVOXです。")
        self.status_var = ctk.StringVar(value="準備完了")

        # メインフレーム
        self.main_frame: ctk.CTkFrame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", padx=20, pady=20)

        # タイトルラベル
        title_label: ctk.CTkLabel = ctk.CTkLabel(
            self.main_frame,
            text="VRCT VOICEVOX Connector",
            font=ctk.CTkFont(family=self.fonts_name, size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # コンテンツフレーム
        content_frame: ctk.CTkFrame = ctk.CTkFrame(self.main_frame)
        content_frame.pack(fill="both", padx=10, pady=10)

        # 左右に分割
        left_frame: ctk.CTkFrame = ctk.CTkFrame(content_frame)
        left_frame.pack(side="left", fill="both",
                        expand=True, padx=10, pady=10)

        # 左側: キャラクター選択
        right_frame: ctk.CTkFrame = ctk.CTkFrame(content_frame)
        right_frame.pack(
            side="right",
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )
        char_label: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="キャラクター選択",
            font=self.font_normal_14
        )
        char_label.pack(anchor="w", padx=10, pady=5)

        # キャラクター選択のComboBox
        # self.character_var: ctk.StringVar = ctk.StringVar() # Already initialized
        self.character_dropdown: ctk.CTkComboBox = ctk.CTkComboBox(
            left_frame,
            variable=self.character_var, # Use the initialized variable
            values=["キャラクターを読み込み中..."],
            font=self.font_normal_14,
            dropdown_font=self.font_normal_14,
            width=300,
            state="readonly",
            command=self.on_character_change
        )
        self.character_dropdown.pack(fill="x", padx=10, pady=5)

        style_label_left: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="声のスタイル",
            font=self.font_normal_14
        )
        style_label_left.pack(anchor="w", padx=10, pady=5)

        # self.style_var: ctk.StringVar = ctk.StringVar() # Already initialized
        self.style_dropdown: ctk.CTkComboBox = ctk.CTkComboBox(
            left_frame,
            variable=self.style_var, # Use the initialized variable
            values=["スタイルを読み込み中..."],
            font=self.font_normal_14,
            dropdown_font=self.font_normal_14,
            width=300,
            state="readonly",
            command=self.on_style_change
        )
        self.style_dropdown.pack(fill="x", padx=10, pady=5)

        # オーディオ出力デバイス選択
        device_label: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="出力デバイス",
            font=self.font_normal_14
        )
        device_label.pack(anchor="w", padx=10, pady=5)

        # self.device_var: ctk.StringVar = ctk.StringVar() # Already initialized
        self.device_dropdown: ctk.CTkComboBox = ctk.CTkComboBox(
            left_frame,
            variable=self.device_var, # Use the initialized variable
            values=["デバイスを読み込み中..."],
            font=self.font_normal_14,
            dropdown_font=self.font_normal_14,
            width=300,
            state="readonly",
            command=self.on_device_change
        )
        self.device_dropdown.pack(fill="x", padx=10, pady=5)

        # --- Add UI elements for second speaker ---
        device_label_2: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="第2出力デバイス",
            font=self.font_normal_14
        )
        device_label_2.pack(anchor="w", padx=10, pady=5)

        self.device_dropdown_2: ctk.CTkComboBox = ctk.CTkComboBox(
            left_frame,
            variable=self.device_var_2, # Use the initialized variable
            values=["デバイスを読み込み中..."],
            font=self.font_normal_14,
            dropdown_font=self.font_normal_14,
            width=300,
            state="readonly",
            command=self.on_device_2_change # To be created
        )
        self.device_dropdown_2.pack(fill="x", padx=10, pady=5)

        self.speaker_2_enable_checkbox: ctk.CTkCheckBox = ctk.CTkCheckBox(
            left_frame,
            text="第2スピーカーを有効にする",
            variable=self.speaker_2_enabled_var, # Use the initialized variable
            font=self.font_normal_14,
            command=self.on_speaker_2_enable_change # To be created
        )
        self.speaker_2_enable_checkbox.pack(anchor="w", padx=10, pady=10)
        # --- End of UI elements for second speaker ---

        # 音量調整スライダー
        volume_label: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="音量",
            font=self.font_normal_14
        )
        volume_label.pack(anchor="w", padx=10, pady=5)

        # 音量値表示用のラベル
        # self.volume_value_var: ctk.StringVar = ctk.StringVar(value=f"{int(self.volume * 100)}%") # Already initialized
        volume_value_label: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            textvariable=self.volume_value_var, # Use the initialized variable
            font=self.font_normal_14,
            width=40
        )
        volume_value_label.pack(anchor="e", padx=10)

        # スライダーウィジェット
        self.volume_slider: ctk.CTkSlider = ctk.CTkSlider(
            left_frame,
            from_=0,
            to=1.0,
            number_of_steps=20,
            command=self.on_volume_change
        )
        self.volume_slider.set(self.volume)  # 現在の音量を設定
        self.volume_slider.pack(fill="x", padx=10, pady=5)

        # WebSocket設定
        ws_frame: ctk.CTkFrame = ctk.CTkFrame(right_frame)
        ws_frame.pack(fill="x", padx=10, pady=10)

        ws_label: ctk.CTkLabel = ctk.CTkLabel(
            ws_frame,
            text="WebSocketサーバーURL:",
            font=self.font_normal_14
        )
        ws_label.pack(anchor="w", padx=10, pady=5)

        # self.ws_url_var: ctk.StringVar = ctk.StringVar(value=self.ws_url) # Already initialized
        self.ws_entry: ctk.CTkEntry = ctk.CTkEntry(
            ws_frame,
            width=300,
            font=self.font_normal_14,
            textvariable=self.ws_url_var # Use the initialized variable
        )
        self.ws_entry.pack(fill="x", padx=10, pady=5)

        # WebSocket接続ボタン
        # self.ws_button_var: ctk.StringVar = ctk.StringVar(value="WebSocket接続開始") # Already initialized
        self.ws_button: ctk.CTkButton = ctk.CTkButton(
            ws_frame,
            textvariable=self.ws_button_var, # Use the initialized variable
            font=self.font_normal_14,
            command=self.toggle_websocket_connection,
            fg_color="#1E5631",  # 接続時は緑色
            hover_color="#2E8B57"
        )
        self.ws_button.pack(pady=10)

        # WebSocket接続状態ラベル
        # self.ws_status_var: ctk.StringVar = ctk.StringVar(value="WebSocket: 未接続") # Already initialized
        self.ws_status_label: ctk.CTkLabel = ctk.CTkLabel(
            ws_frame,
            textvariable=self.ws_status_var, # Use the initialized variable
            font=self.font_normal_14,
            text_color="gray"
        )
        self.ws_status_label.pack(pady=5)

        # テスト再生セクション
        test_frame: ctk.CTkFrame = ctk.CTkFrame(right_frame)
        test_frame.pack(fill="x", padx=10, pady=10)

        test_label: ctk.CTkLabel = ctk.CTkLabel(
            test_frame,
            text="テスト再生:",
            font=self.font_normal_14
        )
        test_label.pack(anchor="w", padx=10, pady=5)

        # self.test_text_var: ctk.StringVar = ctk.StringVar(value="こんにちは、VOICEVOXです。") # Already initialized
        self.test_text_entry: ctk.CTkEntry = ctk.CTkEntry(
            test_frame,
            font=self.font_normal_14,
            width=300,
            textvariable=self.test_text_var # Use the initialized variable
        )
        self.test_text_entry.pack(fill="x", padx=10, pady=5)

        self.play_button: ctk.CTkButton = ctk.CTkButton(
            test_frame,
            text="テスト再生",
            command=self.play_test_audio,
            font=self.font_normal_14
        )
        self.play_button.pack(pady=10)

        # ステータスバー
        # self.status_var: ctk.StringVar = ctk.StringVar(value="準備完了") # Already initialized
        self.status_bar: ctk.CTkLabel = ctk.CTkLabel(
            self.main_frame,
            textvariable=self.status_var, # Use the initialized variable
            font=self.font_normal_12,
            height=25,
            anchor="w"
        )
        self.status_bar.pack(fill="x", side="bottom", padx=10)

        # 保存ボタン
        self.save_button: ctk.CTkButton = ctk.CTkButton(
            self.main_frame,
            text="設定を保存",
            command=self.save_config,
            font=self.font_normal_14
        )
        self.save_button.pack(pady=10)

    def load_data(self) -> None:
        """VOICEVOXのスピーカーデータとオーディオデバイスを読み込む"""
        # ステータスの更新
        self.status_var.set("データを読み込み中...")
        self.update()

        # スレッドで非同期に読み込む
        thread = threading.Thread(target=self._load_data_async, daemon=True)
        thread.start()

    def _load_data_async(self) -> None:
        """非同期でデータを読み込む"""
        try:
            # オーディオデバイスの取得
            self.audio_devices = VoicevoxSpeaker.list_audio_devices()

            # VOICEVOX Engineからスピーカー情報を取得
            self.speakers_data = self.client.speakers()

            # UIの更新（メインスレッドで実行）
            self.after(0, self._update_ui_with_data)

        except Exception as e:
            # エラー表示
            self.after(
                0, lambda msg=f"エラー: {str(e)}": self.status_var.set(msg))
            if "speakers_data" not in dir(self) or not self.speakers_data:
                self.after(0, lambda: self.status_var.set(
                    "VOICEVOX Engineに接続できません。起動しているか確認してください。"))

    def _update_ui_with_data(self) -> None:
        """取得したデータでUIを更新する"""
        # オーディオデバイスリストの更新
        device_names: List[str] = [
            "デフォルト"] + [f"{device['name']} (インデックス: {device['index']})" for device in self.audio_devices]
        self.device_dropdown.configure(values=device_names)
        if hasattr(self, 'device_dropdown_2'): # Check if UI element exists
            self.device_dropdown_2.configure(values=device_names)

        # 設定からデバイス選択を復元
        if self.current_device is not None:
            device_name: str = next((
                f"{device['name']} (インデックス: {device['index']})" for device in self.audio_devices if device['index'] == self.current_device), "デフォルト")
            self.device_var.set(device_name)
        else:
            self.device_var.set("デフォルト")

        # 設定から第2デバイス選択を復元
        if hasattr(self, 'device_var_2'): # Check if UI variable exists
            if self.current_device_2 is not None:
                device_name_2: str = next((
                    f"{device['name']} (インデックス: {device['index']})" for device in self.audio_devices if device['index'] == self.current_device_2), "デフォルト")
                self.device_var_2.set(device_name_2)
            else:
                self.device_var_2.set("デフォルト")

        # 第2スピーカー有効状態を復元
        if hasattr(self, 'speaker_2_enabled_var'): # Check if UI variable exists
            self.speaker_2_enabled_var.set(self.speaker_2_enabled)

        # キャラクターリストの更新
        self._update_character_list()

        # ステータスの更新
        self.status_var.set("データの読み込みが完了しました")

    def _update_character_list(self) -> None:
        """キャラクターリストを更新"""
        # キャラクター名のリストを作成
        character_names: List[str] = [
            speaker["name"] for speaker in self.speakers_data]
        self.character_dropdown.configure(values=character_names)

        # 設定から選択されたキャラクターを復元
        if self.current_style is not None:
            for speaker in self.speakers_data:
                for style_info in speaker["styles"]: # Renamed style to style_info
                    if style_info["id"] == self.current_style:
                        self.character_var.set(speaker["name"])
                        self.select_character(speaker)
                        # Found the character and style, break from inner loop
                        return  # Exit early as character is found and processed
        # デフォルト選択（最初のキャラクター）
        elif self.speakers_data:
            self.character_var.set(self.speakers_data[0]["name"])
            self.select_character(self.speakers_data[0])

    def on_character_change(self, choice: str) -> None:
        """キャラクターコンボボックスで選択されたときの処理"""
        if not choice or not self.speakers_data:
            return

        # 選択されたキャラクター名からキャラクターデータを取得
        selected_speaker: Optional[Dict[str, Any]] = next(
            (s for s in self.speakers_data if s["name"] == choice), None)
        if selected_speaker:
            self.select_character(selected_speaker)

    def select_character(self, speaker: Dict[str, Any]) -> None:
        """キャラクターを選択したときの処理"""
        self.current_character = speaker

        # スタイルドロップダウンの更新
        style_values: List[str] = [
            f"{style['name']} (ID: {style['id']})" for style in speaker["styles"]]
        self.style_dropdown.configure(values=style_values)

        # 設定から選択されたスタイルを復元するか、最初のスタイルを選択
        if self.current_style is not None:
            style_found: bool = False
            for i, style_info in enumerate(speaker["styles"]): # Renamed style to style_info
                if style_info["id"] == self.current_style:
                    self.style_var.set(style_values[i])
                    style_found = True
                    break
            if not style_found and style_values:
                # 以前のスタイルが見つからない場合は最初のスタイルを選択
                self.style_var.set(style_values[0])
                self.current_style = speaker["styles"][0]["id"]
        elif style_values:
            self.style_var.set(style_values[0])
            self.current_style = speaker["styles"][0]["id"]

    def on_style_change(self, choice: str) -> None:
        """スタイルが変更されたときの処理"""
        if not choice or not self.current_character:
            return

        try:
            # 選択されたスタイルからIDを取得
            import re
            id_match: Optional[re.Match[str]] = re.search(
                r'\(ID: (\d+)\)', choice)
            if id_match:
                style_id: int = int(id_match.group(1))
                self.current_style = style_id
            else:
                # 正規表現でIDが見つからない場合、キャラクターのスタイルから名前で検索
                style_name: str = choice.split(
                    " (ID:")[0] if " (ID:" in choice else choice
                for style_info in self.current_character["styles"]: # Renamed style to style_info
                    if style_info["name"] == style_name:
                        self.current_style = style_info["id"]
                        break
        except Exception as e:
            print(f"スタイル選択エラー: {str(e)}")
            # エラーが発生した場合でも、選択中のキャラクターの最初のスタイルを設定
            if self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]

    def on_device_change(self, choice: str) -> None:
        """デバイスが変更されたときの処理"""
        if not choice or choice == "デフォルト":
            self.current_device = None
            return

        # 選択されたデバイスからインデックスを取得
        device_index: int = int(choice.split("インデックス: ")[1].rstrip(")"))
        self.current_device = device_index

    def on_device_2_change(self, choice: str) -> None:
        """第2デバイスが変更されたときの処理"""
        if not choice or choice == "デフォルト":
            self.current_device_2 = None
            return
        # 選択されたデバイスからインデックスを取得
        try:
            device_index_2: int = int(choice.split("インデックス: ")[1].rstrip(")"))
            self.current_device_2 = device_index_2
        except (IndexError, ValueError) as e:
            print(f"第2デバイス選択エラー: {str(e)}")
            self.current_device_2 = None
            self.device_var_2.set("デフォルト")


    def on_speaker_2_enable_change(self) -> None:
        """第2スピーカー有効チェックボックスが変更されたときの処理"""
        if hasattr(self, 'speaker_2_enabled_var'):
            self.speaker_2_enabled = self.speaker_2_enabled_var.get()


    def on_volume_change(self, value: float) -> None:
        """スライダーで音量が変更されたときの処理"""
        self.volume = value
        # 音量表示を更新（パーセント表示）
        self.volume_value_var.set(f"{int(value * 100)}%")

    def _play_audio_with_volume(self, speaker: VoicevoxSpeaker, audio_data: bytes) -> None:
        """音量を適用して音声を再生する"""
        try:
            import io
            import wave
            import numpy as np
            import struct

            # WAVデータをバッファに読み込み
            with io.BytesIO(audio_data) as buffer:
                with wave.open(buffer, 'rb') as wf:
                    # WAVファイルのパラメータを取得
                    n_channels = wf.getnchannels()
                    sample_width = wf.getsampwidth()
                    frame_rate = wf.getframerate()
                    n_frames = wf.getnframes()

                    # すべてのフレームを読み込む
                    raw_data = wf.readframes(n_frames)

            # 音声データをnumpy配列に変換
            if sample_width == 2:  # 16bit PCM
                fmt = f"{n_frames * n_channels}h"
                data = np.array(struct.unpack(fmt, raw_data))
                # 音量を適用
                data = (data * self.volume).astype(np.int16)
                # データをバイトに戻す
                modified_raw_data = struct.pack(fmt, *data)

                # 新しいWAVファイルを作成
                with io.BytesIO() as out_buffer:
                    with wave.open(out_buffer, 'wb') as out_wf:
                        out_wf.setnchannels(n_channels)
                        out_wf.setsampwidth(sample_width)
                        out_wf.setframerate(frame_rate)
                        out_wf.writeframes(modified_raw_data)

                    # バッファからバイトデータを取得
                    modified_audio_data = out_buffer.getvalue()

                # 修正したデータを再生
                speaker.play_bytes(modified_audio_data)
            else:
                # サンプル幅が異なる場合はそのまま再生
                speaker.play_bytes(audio_data)

        except Exception as e:
            print(f"音声処理エラー: {str(e)}")
            # エラーが発生した場合は元のデータをそのまま再生
            speaker.play_bytes(audio_data)

    def play_test_audio(self) -> None:
        """テスト音声を再生"""
        # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
        if not self.current_style and self.current_character and self.current_character["styles"]:
            self.current_style = self.current_character["styles"][0]["id"]
            style_name: str = self.current_character["styles"][0]["name"]
            self.status_var.set(f"スタイルが自動選択されました: {style_name}")
        elif not self.current_style:
            self.status_var.set("エラー: スタイルが選択されていません")
            return

        text: str = self.test_text_var.get()
        if not text:
            self.status_var.set("エラー: テキストが入力されていません")
            return

        # ステータスの更新
        self.status_var.set("音声を合成中...")
        self.update()

        # スレッドで非同期に合成と再生
        thread: threading.Thread = threading.Thread(
            target=self._play_audio_async, args=(text,), daemon=True)
        thread.start()

    def _play_audio_async(self, text: str) -> None:
        """非同期で音声合成と再生を行う"""
        self.playback_lock.acquire()
        try:
            # 音声合成用クエリを作成
            # Ensure current_style is not None before proceeding
            if self.current_style is None:
                self.after(0, lambda: self.status_var.set("エラー: スタイルが選択されていません"))
                return
            query: Dict[str, Any] = self.client.audio_query(
                text, self.current_style)

            # 音声を合成
            audio_data: Optional[bytes] = self.client.synthesis(
                query, self.current_style)

            if audio_data:
                # 音声を再生（音量適用）
                speaker: VoicevoxSpeaker = VoicevoxSpeaker(
                    output_device_index=self.current_device,
                    output_device_index_2=self.current_device_2,
                    speaker_2_enabled=self.speaker_2_enabled)
                self._play_audio_with_volume(speaker, audio_data)
                # ステータスの更新
                self.after(0, lambda: self.status_var.set("再生完了"))
            else:
                self.after(0, lambda: self.status_var.set("エラー: 音声合成に失敗"))

        except Exception as e:            # エラー表示
            self.after(
                0, lambda msg=f"エラー: {str(e)}": self.status_var.set(msg))
        finally:
            self.playback_lock.release()

    def load_config(self) -> None:
        """設定ファイルから設定を読み込む"""
        config: Dict[str, Any] = Config.load()
        self.current_style = config.get("speaker_id")
        self.current_device = config.get("device_index")
        self.current_device_2 = config.get("device_index_2") # Load second device
        self.speaker_2_enabled = config.get("speaker_2_enabled", False) # Load second speaker enabled state, default to False
        self.volume = config.get("volume", 0.8)  # デフォルトは0.8
        self.ws_url = config.get("ws_url", "ws://127.0.0.1:2231")

    def save_config(self) -> None:
        """現在の設定を保存"""
        config_data: Dict[str, Any] = {
            "speaker_id": self.current_style,
            "device_index": self.current_device,
            "device_index_2": self.current_device_2, # Save second device
            "speaker_2_enabled": self.speaker_2_enabled, # Save second speaker enabled state
            "volume": self.volume,
            "ws_url": self.ws_url_var.get()
        }
        Config.save(config_data)
        self.ws_url = self.ws_url_var.get()
        self.status_var.set("設定を保存しました")

    def toggle_websocket_connection(self) -> None:
        """WebSocket接続の開始/停止を切り替える"""
        if not self.ws_connected:
            self.start_websocket_connection()
        else:
            self.stop_websocket_connection()

    def start_websocket_connection(self) -> None:
        """WebSocket接続を開始する"""
        # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
        if not self.current_style and self.current_character and self.current_character["styles"]:
            self.current_style = self.current_character["styles"][0]["id"]
            style_name: str = self.current_character["styles"][0]["name"]
            self.status_var.set(f"スタイルが自動選択されました: {style_name}")
        elif not self.current_style:
            self.status_var.set("エラー: スピーカースタイルが選択されていません")
            return

        # URLを取得
        self.ws_url = self.ws_url_var.get()
        if not self.ws_url:
            self.ws_url = "ws://127.0.0.1:2231"
            self.ws_url_var.set(self.ws_url)

        # WebSocketイベントハンドラ
        def on_message(ws: websocket.WebSocketApp, message: str) -> None:
            try:
                data: Dict[str, Any] = json.loads(message)
                if data.get("type") == "SENT" or data.get("type") == "CHAT":
                    received_message: str = data.get("message", "")

                    # エスケープされた日本語文字列をデコード
                    decoded_message: str = html.unescape(received_message)
                    self.after(0, lambda: self.status_var.set(
                        f"受信: {decoded_message[:30]}..."))

                    # 音声合成してスレッドで再生
                    thread: threading.Thread = threading.Thread(
                        target=self._synthesize_and_play, args=(decoded_message,), daemon=True)
                    thread.start()
            except json.JSONDecodeError:
                # JSONデコードエラーは無視する（想定されるケース）
                pass
            except Exception as e:
                self.after(
                    0, lambda msg=f"メッセージ処理エラー: {str(e)}": self.status_var.set(msg))

        def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
            self.after(0, lambda: self.status_var.set(
                f"WebSocketエラー: {error}"))

        def on_close(ws: websocket.WebSocketApp, close_status_code: Optional[int], close_msg: Optional[str]) -> None:
            self.ws_connected = False
            self.after(0, self._update_ws_status_disconnected)

        def on_open(ws: websocket.WebSocketApp) -> None:
            self.ws_connected = True
            self.after(0, self._update_ws_status_connected)

        # WebSocketクライアントの起動
        try:
            self.status_var.set(f"WebSocketサーバーに接続中: {self.ws_url}")
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            # WebSocketクライアントを別スレッドで実行
            self.ws_thread = threading.Thread(
                target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()

        except Exception as e:
            self.status_var.set(f"WebSocket接続エラー: {str(e)}")

    def stop_websocket_connection(self) -> None:
        """WebSocket接続を停止する"""
        if self.ws:
            self.ws.close()
            self.ws = None # Clear the WebSocket object after closing

    def _update_ws_status_connected(self) -> None:
        """WebSocket接続状態のUIを更新（接続時）"""
        self.ws_status_var.set("WebSocket: 接続済み")
        self.ws_status_label.configure(text_color="#4CAF50")  # 緑色
        self.ws_button_var.set("WebSocket接続停止")
        self.ws_button.configure(
            fg_color="#8B0000", hover_color="#B22222")  # 赤色
        self.status_var.set("WebSocketサーバーに接続しました")

    def _update_ws_status_disconnected(self) -> None:
        """WebSocket接続状態のUIを更新（切断時）"""
        self.ws_status_var.set("WebSocket: 未接続")
        self.ws_status_label.configure(text_color="gray")
        self.ws_button_var.set("WebSocket接続開始")
        self.ws_button.configure(
            fg_color="#1E5631", hover_color="#2E8B57")  # 緑色
        self.status_var.set("WebSocket接続を終了しました")

    def _synthesize_and_play(self, text: str) -> None:
        """テキストを音声合成して再生する"""
        self.playback_lock.acquire()
        try:
            # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
            if not self.current_style and self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]
                style_name: str = self.current_character["styles"][0]["name"]
                self.after(0, lambda: self.status_var.set(
                    f"スタイルが自動選択されました: {style_name}"))

            if self.current_style is None: # Explicit check for None
                self.after(0, lambda: self.status_var.set(
                    "エラー: スタイルが選択されていません"))
                return

            # 音声合成用クエリを作成
            query: Dict[str, Any] = self.client.audio_query(
                text, self.current_style)

            # 音声を合成
            audio_data: Optional[bytes] = self.client.synthesis(
                query, self.current_style)

            if audio_data:
                # 音声を再生（音量適用）
                speaker: VoicevoxSpeaker = VoicevoxSpeaker(
                    output_device_index=self.current_device,
                    output_device_index_2=self.current_device_2,
                    speaker_2_enabled=self.speaker_2_enabled)
                self._play_audio_with_volume(speaker, audio_data)
            else:
                self.after(0, lambda: self.status_var.set("エラー: 音声合成に失敗"))


        except Exception as e:
            self.after(
                0, lambda msg=f"音声合成エラー: {str(e)}": self.status_var.set(msg))
        finally:
            self.playback_lock.release()

    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        # WebSocket接続を停止
        self.stop_websocket_connection()

        # アプリケーションを破棄
        self.destroy()


if __name__ == "__main__":
    app = VoicevoxConnectorGUI()
    app.mainloop()
