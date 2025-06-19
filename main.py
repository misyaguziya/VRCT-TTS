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
import customtkinter as ctk
from typing import Dict, List, Optional, Any
import websocket
import json
import html
import logging # Added for explicit logging in main.py
import tempfile # For temporary MP3 file
import sys # For platform-specific playback
import time # For delayed cleanup of temp file
import os # For os.system, os.path, os.remove, os.startfile


from voicevox import VOICEVOXClient
from voicevox_speaker import VoicevoxSpeaker
from config import Config
from tts_manager import TTSManager # Added TTSManager import

# Configure a logger for this module
logger = logging.getLogger(__name__)
# Basic config should ideally be set once at application entry point.
# If other modules also call basicConfig, the first one takes precedence.
# For robustness in case this module is run in a context where logging isn't configured:
if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class VoicevoxConnectorGUI(ctk.CTk):
    """VOICEVOX Connector GUIアプリケーション"""

    def __init__(self) -> None:
        super().__init__()
        
        # アプリケーションのバージョン情報
        self.app_version = "v1.1.1"

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
        self.geometry("770x650")

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
        self.current_host: Optional[str] = None   # For host selection
        self.current_host_2: Optional[str] = None # For second speaker host
        self.volume: float = 0.8  # デフォルトの音量 (0.0-1.0)
        self.ws_url: str = "ws://127.0.0.1:2231"

        # UI Variables
        self.character_var = ctk.StringVar()
        self.style_var = ctk.StringVar()
        self.device_var = ctk.StringVar()
        self.device_var_2 = ctk.StringVar() # For second speaker
        self.speaker_2_enabled_var = ctk.BooleanVar(value=False) # For second speaker
        self.host_var = ctk.StringVar()     # For host selection
        self.host_var_2 = ctk.StringVar()   # For second speaker host
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

        # Logging/Monitoring Counters
        self.ws_message_count = 0
        self.sent_type_count = 0
        self.received_type_count = 0
        self.chat_type_count = 0
        self.successful_synthesis_count = 0
        self.failed_synthesis_count = 0

        # Playback lock
        self.playback_lock = threading.Lock()
        self.clear_audio_requested: bool = False
        self.active_speaker_instance: Optional[VoicevoxSpeaker] = None

        # 設定を読み込む
        self.load_config()

        # VOICEVOXクライアントの初期化
        self.client: VOICEVOXClient = VOICEVOXClient() # Retained for direct Voicevox use if any (e.g. test button)

        # TTS Managerの初期化
        self.tts_manager = TTSManager()

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
        self.style_dropdown.pack(fill="x", padx=10, pady=5)        # オーディオ出力デバイス選択
        device_label: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="出力デバイス",
            font=self.font_normal_14
        )
        device_label.pack(anchor="w", padx=10, pady=5)

        # デバイス選択用の水平フレーム
        device_frame: ctk.CTkFrame = ctk.CTkFrame(left_frame)
        device_frame.pack(fill="x", padx=10, pady=5)

        # ホスト選択コンボボックス
        self.host_dropdown: ctk.CTkComboBox = ctk.CTkComboBox(
            device_frame,
            variable=self.host_var,
            values=["ホストを読み込み中..."],
            font=self.font_normal_12,
            dropdown_font=self.font_normal_12,
            width=120,
            state="readonly",
            command=self.on_host_change
        )
        self.host_dropdown.pack(side="left", padx=(0, 5))

        # デバイス選択コンボボックス
        self.device_dropdown: ctk.CTkComboBox = ctk.CTkComboBox(
            device_frame,
            variable=self.device_var,
            values=["デバイスを読み込み中..."],
            font=self.font_normal_12,
            dropdown_font=self.font_normal_12,
            width=170,
            state="readonly",
            command=self.on_device_change
        )
        self.device_dropdown.pack(side="left", fill="x", expand=True)        # --- Add UI elements for second speaker ---
        device_label_2: ctk.CTkLabel = ctk.CTkLabel(
            left_frame,
            text="第2出力デバイス",
            font=self.font_normal_14
        )
        device_label_2.pack(anchor="w", padx=10, pady=5)

        # 第2デバイス選択用の水平フレーム
        device_frame_2: ctk.CTkFrame = ctk.CTkFrame(left_frame)
        device_frame_2.pack(fill="x", padx=10, pady=5)

        # 第2ホスト選択コンボボックス
        self.host_dropdown_2: ctk.CTkComboBox = ctk.CTkComboBox(
            device_frame_2,
            variable=self.host_var_2,
            values=["ホストを読み込み中..."],
            font=self.font_normal_12,
            dropdown_font=self.font_normal_12,
            width=120,
            state="readonly",
            command=self.on_host_2_change
        )
        self.host_dropdown_2.pack(side="left", padx=(0, 5))

        # 第2デバイス選択コンボボックス
        self.device_dropdown_2: ctk.CTkComboBox = ctk.CTkComboBox(
            device_frame_2,
            variable=self.device_var_2,
            values=["デバイスを読み込み中..."],
            font=self.font_normal_12,
            dropdown_font=self.font_normal_12,
            width=170,
            state="readonly",
            command=self.on_device_2_change
        )
        self.device_dropdown_2.pack(side="left", fill="x", expand=True)

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
            text="テスト再生",
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
            font=self.font_normal_14        )
        self.play_button.pack(pady=10)

        # 再生停止とクリアボタン（テスト再生フレームの外、右フレーム直下に配置）
        self.stop_clear_button: ctk.CTkButton = ctk.CTkButton(
            right_frame,  # right_frameに配置（test_frameの外
            text="再生停止とクリア",
            command=self.on_stop_and_clear_audio, # To be implemented
            font=self.font_normal_14,
            fg_color="#B22222", # Firebrick red
            hover_color="#8B0000"  # Darker red
        )
        self.stop_clear_button.pack(pady=10)
        
        # ステータスバーとバージョン情報を配置するフレーム
        status_frame: ctk.CTkFrame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        status_frame.pack(fill="x", side="bottom", padx=10, pady=(5, 0))
        
        # ステータスバー（左寄せ）
        self.status_bar: ctk.CTkLabel = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            font=self.font_normal_12,
            height=25,
            anchor="w"
        )
        self.status_bar.pack(fill="x", side="left", expand=True)
        
        # バージョン情報ラベル（右寄せ）
        version_label: ctk.CTkLabel = ctk.CTkLabel(
            status_frame,
            text=self.app_version,
            font=self.font_normal_12,
            height=25,
            anchor="e"
        )
        version_label.pack(side="right", padx=(10, 0))

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
        # ホストリストの作成
        host_names = list(set([device['host_name'] for device in self.audio_devices]))
        host_names = ["すべて"] + sorted(host_names)
        
        # ホストコンボボックスの更新
        self.host_dropdown.configure(values=host_names)
        self.host_dropdown_2.configure(values=host_names)
        
        # 初期ホスト選択
        if self.current_host is not None and self.current_host in host_names:
            self.host_var.set(self.current_host)
        else:
            self.host_var.set("すべて")
            self.current_host = "すべて"
            
        if self.current_host_2 is not None and self.current_host_2 in host_names:
            self.host_var_2.set(self.current_host_2)
        else:
            self.host_var_2.set("すべて")
            self.current_host_2 = "すべて"

        # デバイスリストを更新
        self._update_device_lists()

        # キャラクターリストの更新
        self._update_character_list()

        # ステータスの更新
        self.status_var.set("データの読み込みが完了しました")

    def _update_device_lists(self) -> None:
        """選択されたホストに基づいてデバイスリストを更新"""
        # 第1デバイス用のデバイスリスト作成
        selected_host = self.host_var.get()
        if selected_host == "すべて":
            filtered_devices = self.audio_devices
        else:
            filtered_devices = [device for device in self.audio_devices if device['host_name'] == selected_host]
        
        device_names: List[str] = ["デフォルト"] + [f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices]
        self.device_dropdown.configure(values=device_names)

        # 設定からデバイス選択を復元
        if self.current_device is not None:
            device_name: str = next((
                f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices if device['index'] == self.current_device), "デフォルト")
            self.device_var.set(device_name)
        else:
            self.device_var.set("デフォルト")

        # 第2デバイス用のデバイスリスト作成
        selected_host_2 = self.host_var_2.get()
        if selected_host_2 == "すべて":
            filtered_devices_2 = self.audio_devices
        else:
            filtered_devices_2 = [device for device in self.audio_devices if device['host_name'] == selected_host_2]
        
        device_names_2: List[str] = ["デフォルト"] + [f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices_2]
        self.device_dropdown_2.configure(values=device_names_2)

        # 設定から第2デバイス選択を復元
        if self.current_device_2 is not None:
            device_name_2: str = next((
                f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices_2 if device['index'] == self.current_device_2), "デフォルト")
            self.device_var_2.set(device_name_2)
        else:
            self.device_var_2.set("デフォルト")

        # 第2スピーカー有効状態を復元
        self.speaker_2_enabled_var.set(self.speaker_2_enabled)

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

        try:            # 選択されたスタイルからIDを取得
            import re
            id_match: Optional[re.Match[str]] = re.search(
                r'\(ID: (\d+)\)', choice)
            if id_match:
                style_id: int = int(id_match.group(1))
                self.current_style = style_id
            else:
                # 正規表現でIDが見つからない場合、キャラクターのスタイルから名前で検索
                style_name: str = choice.split(" (ID:"
                )[0] if " (ID:" in choice else choice
                for style_info in self.current_character["styles"]: # Renamed style to style_info
                    if style_info["name"] == style_name:
                        self.current_style = style_info["id"]
                        break
        except Exception as e:
            print(f"スタイル選択エラー: {str(e)}")
            # エラーが発生した場合でも、選択中のキャラクターの最初のスタイルを設定
            if self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]

    def on_host_change(self, choice: str) -> None:
        """ホストが変更されたときの処理"""
        self.current_host = choice
        self._update_device_lists()

    def on_host_2_change(self, choice: str) -> None:
        """第2ホストが変更されたときの処理"""
        self.current_host_2 = choice
        self._update_device_lists()

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

    def _play_audio_with_volume(self, audio_data: bytes, speaker_instance: VoicevoxSpeaker) -> None:
        """音量を適用して音声を再生する"""
        if self.clear_audio_requested:
            # This function might be entered just as clear is requested.
            # The active speaker's request_stop would be called by the button handler.
            return

        # It's assumed speaker_instance is valid if we reach here,
        # as it's created and passed by the calling methods.
        # However, a check might still be good for robustness if desired,
        # but per current plan, the calling method handles active_speaker_instance lifecycle.

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
                speaker_instance.play_bytes(modified_audio_data)
            else:
                # サンプル幅が異なる場合はそのまま再生
                speaker_instance.play_bytes(audio_data)

        except Exception as e:
            print(f"音声処理エラー: {str(e)}")
            # エラーが発生した場合は元のデータをそのまま再生
            # Check if speaker_instance is not None before using it in except block
            if speaker_instance:
                speaker_instance.play_bytes(audio_data)

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
            if self.clear_audio_requested:
                self.clear_audio_requested = False # Reset flag
                self.status_var.set("オーディオクリアリクエスト受信済み。再生をキャンセルしました。")
                # self.playback_lock.release() # This will be handled by finally
                return

            self.active_speaker_instance = None # Reset before creation

            # 音声合成用クエリを作成
            # Ensure current_style is not None before proceeding
            if self.current_style is None:
                self.after(0, lambda: self.status_var.set("エラー: スタイルが選択されていません"))
                return # playback_lock will be released by finally
            query: Dict[str, Any] = self.client.audio_query(
                text, self.current_style)

            # 音声を合成
            audio_data: Optional[bytes] = self.client.synthesis(
                query, self.current_style)

            if audio_data:
                # 音声を再生（音量適用）
                self.active_speaker_instance = VoicevoxSpeaker(
                    output_device_index=self.current_device,
                    output_device_index_2=self.current_device_2,
                    speaker_2_enabled=self.speaker_2_enabled)
                self._play_audio_with_volume(audio_data, self.active_speaker_instance)                # ステータスの更新
                if not self.clear_audio_requested: # Avoid overwriting clear message
                    self.after(0, lambda: self.status_var.set("再生完了"))
            else:
                if not self.clear_audio_requested: # Avoid overwriting clear message
                    self.after(0, lambda: self.status_var.set("エラー: 音声合成に失敗"))

        except Exception as e:
            # エラー表示
            if not self.clear_audio_requested: # Avoid overwriting clear message
                self.after(
                    0, lambda msg=f"エラー: {str(e)}": self.status_var.set(msg))
        finally:
            self.playback_lock.release()
            self.active_speaker_instance = None

    def load_config(self) -> None:
        """設定ファイルから設定を読み込む"""
        config: Dict[str, Any] = Config.load()
        self.current_style = config.get("speaker_id")
        self.current_device = config.get("device_index")
        self.current_device_2 = config.get("device_index_2") # Load second device
        self.speaker_2_enabled = config.get("speaker_2_enabled", False) # Load second speaker enabled state, default to False
        self.current_host = config.get("host_name", "すべて") # Load host selection
        self.current_host_2 = config.get("host_name_2", "すべて") # Load second host selection
        self.volume = config.get("volume", 0.8)  # デフォルトは0.8
        self.ws_url = config.get("ws_url", "ws://127.0.0.1:2231")

    def save_config(self) -> None:
        """現在の設定を保存"""
        config_data: Dict[str, Any] = {
            "speaker_id": self.current_style,
            "device_index": self.current_device,
            "device_index_2": self.current_device_2, # Save second device
            "speaker_2_enabled": self.speaker_2_enabled, # Save second speaker enabled state
            "host_name": self.current_host, # Save host selection
            "host_name_2": self.current_host_2, # Save second host selection
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
            self.ws_message_count += 1
            logger.debug(f"Raw WebSocket message received: {message}") # Log raw message
            try:
                data: Dict[str, Any] = json.loads(message)
                message_type = data.get("type") # Get type first for counter

                if message_type == "SENT":
                    self.sent_type_count += 1
                elif message_type == "RECEIVED": # This was used in logic below, ensure consistency
                    self.received_type_count += 1
                elif message_type == "CHAT":
                    self.chat_type_count += 1

                # Original logic for SENT or CHAT (now also RECEIVED)
                if data.get("type") == "SENT" or data.get("type") == "CHAT" or data.get("type") == "RECEIVED":
                    # message_type is already defined
                    original_message = html.unescape(data.get("message", ""))
                    translation = html.unescape(data.get("translation", ""))
                    # Provide defaults for src_languages and dst_languages
                    src_languages = data.get("src_languages", ["en"])
                    dst_languages = data.get("dst_languages", ["en"])

                    text_to_synthesize = None
                    lang_to_synthesize_in = None
                    tts_kwargs = {} # For engine-specific params like 'tld'

                    if message_type == "SENT":
                        text_to_synthesize = original_message
                        lang_to_synthesize_in = src_languages[0] if src_languages else "en"
                        # Example: if lang_to_synthesize_in == "en-GB", pass tld for gTTS
                        if lang_to_synthesize_in.lower() == "en-gb":
                            tts_kwargs['tld'] = 'co.uk'
                        self.after(0, lambda: self.status_var.set(f"Synthesizing SENT: {text_to_synthesize[:20]}... in {lang_to_synthesize_in}"))

                    elif message_type == "RECEIVED": # As per plan, this was CHAT, but RECEIVED makes more sense for translation
                        text_to_synthesize = translation if translation else original_message
                        lang_to_synthesize_in = dst_languages[0] if dst_languages else "en"
                        if lang_to_synthesize_in.lower() == "en-gb": # Example for tld
                            tts_kwargs['tld'] = 'co.uk'
                        self.after(0, lambda: self.status_var.set(f"Synthesizing RECEIVED: {text_to_synthesize[:20]}... in {lang_to_synthesize_in}"))

                    elif message_type == "CHAT": # Assuming CHAT uses original message and source language
                        text_to_synthesize = original_message
                        lang_to_synthesize_in = src_languages[0] if src_languages else "en"
                        if lang_to_synthesize_in.lower() == "en-gb":
                            tts_kwargs['tld'] = 'co.uk'
                        self.after(0, lambda: self.status_var.set(f"Synthesizing CHAT: {text_to_synthesize[:20]}... in {lang_to_synthesize_in}"))

                    if text_to_synthesize and lang_to_synthesize_in:
                        # Use TTSManager to get audio_data
                        # Pass tts_kwargs to the synthesize method
                        audio_data = self.tts_manager.synthesize(
                            text_to_synthesize,
                            lang_to_synthesize_in,
                            target_message_type=message_type,
                            **tts_kwargs
                        )

                        if audio_data:
                            # Play the audio_data using existing playback infrastructure
                            # Note: VoicevoxSpeaker expects WAV. gTTS provides MP3.
                            # This will be addressed in a later step. For now, attempt playback.
                            # Create a new speaker instance for this playback to avoid state conflicts
                            # if multiple playbacks overlap or if settings change.
                            # This is a simplified approach; a proper audio manager might be better.
                            temp_speaker_instance = VoicevoxSpeaker(
                                output_device_index=self.current_device,
                                output_device_index_2=self.current_device_2,
                                speaker_2_enabled=self.speaker_2_enabled
                            )

                            # Determine audio format (heuristic)
                            audio_format = "unknown"
                            if audio_data.startswith(b'RIFF'):
                                audio_format = "wav"
                            elif audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb') or \
                                 audio_data.startswith(b'\xff\xf3') or audio_data.startswith(b'\xff\xf2'):
                                audio_format = "mp3"
                            else:
                                # Basic fallback guess: if primary engine was gtts, it's likely mp3.
                                primary_engine_name_for_guess = self.tts_manager.determine_synthesis_parameters(lang_to_synthesize_in)["engine_name"]
                                if primary_engine_name_for_guess.lower() == "gtts":
                                    audio_format = "mp3"
                                    logger.info(f"Could not definitively determine audio format, but primary engine for lang '{lang_to_synthesize_in}' was {primary_engine_name_for_guess}, assuming MP3.")
                                else:
                                    logger.warning(f"Could not determine audio format for playback. Header: {audio_data[:10]!r}. Will attempt playback as raw bytes if VoicevoxSpeaker supports it, or fail.")

                            logger.info(f"Detected audio format: {audio_format} for text '{text_to_synthesize[:20]}...'")

                            # Use a thread for the new _handle_playback method
                            playback_handler_thread = threading.Thread(
                                target=self._handle_playback,
                                args=(audio_data, audio_format),
                                daemon=True
                            )
                            playback_handler_thread.start()
                            # Status update is now part of _handle_playback or can be set here too
                            # self.after(0, lambda: self.status_var.set(f"Playback initiated for: {text_to_synthesize[:20]}..."))
                            self.successful_synthesis_count +=1
                        else:
                            logger.warning(f"WebSocket Handler: TTSManager returned no audio for text '{text_to_synthesize[:30]}' with lang '{lang_to_synthesize_in}'. All synthesis attempts failed.")
                            self.after(0, lambda: self.status_var.set(f"Synthesis failed for: {text_to_synthesize[:20]}..."))
                            self.failed_synthesis_count += 1
                    else:
                        logger.info(f"No text/lang determined for synthesis for message type: {message_type}. Original msg: {original_message[:30]}")
                        self.after(0, lambda: self.status_var.set(f"No action taken for message type: {message_type}"))

                # Periodic logging of counts
                if self.ws_message_count % 10 == 0: # Log every 10 messages
                    logger.info(f"WebSocket Message Stats: Total Received: {self.ws_message_count}, "
                                f"SENT: {self.sent_type_count}, RECEIVED: {self.received_type_count}, CHAT: {self.chat_type_count}, "
                                f"Successful TTS: {self.successful_synthesis_count}, Failed TTS: {self.failed_synthesis_count}")

            except json.JSONDecodeError:
                # JSONデコードエラーは無視する（想定されるケース）
                self.after(0, lambda: self.status_var.set("Error: Received non-JSON WebSocket message."))
                pass # Or log this as an info/debug message
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

    # def _synthesize_and_play(self, text: str) -> None: # This method is now less relevant for WS messages
    #     """テキストを音声合成して再生する (Primarily for test button or direct Voicevox)"""
    #     # This method's direct invocation from WebSocket on_message is removed.
    #     # It can still be used by the "Test Play" button which might directly use self.client (Voicevox).
    #     # If Test Play button should also use TTSManager, this method needs further refactoring.
    #     # For now, keeping its original Voicevox-specific logic for the test button.
    #     self.playback_lock.acquire()
    #     try:
    #         if self.clear_audio_requested:
    #             self.clear_audio_requested = False
    #             self.status_var.set("オーディオクリアリクエスト受信済み。再生をキャンセルしました。")
    #             return

    #         self.active_speaker_instance = None

    #         if not self.current_style and self.current_character and self.current_character["styles"]:
    #             self.current_style = self.current_character["styles"][0]["id"]
    #             style_name: str = self.current_character["styles"][0]["name"]
    #             if not self.clear_audio_requested:
    #                 self.after(0, lambda: self.status_var.set(
    #                     f"スタイルが自動選択されました: {style_name}"))

    #         if self.current_style is None:
    #             if not self.clear_audio_requested:
    #                 self.after(0, lambda: self.status_var.set(
    #                     "エラー: スタイルが選択されていません (VOICEVOX Test Play)"))
    #             return

    #         query: Dict[str, Any] = self.client.audio_query(text, self.current_style)
    #         audio_data: Optional[bytes] = self.client.synthesis(query, self.current_style)

    #         if audio_data:
    #             self.active_speaker_instance = VoicevoxSpeaker(
    #                 output_device_index=self.current_device,
    #                 output_device_index_2=self.current_device_2,
    #                 speaker_2_enabled=self.speaker_2_enabled)
    #             self._play_audio_with_volume(audio_data, self.active_speaker_instance)
    #         else:
    #             if not self.clear_audio_requested:
    #                 self.after(0, lambda: self.status_var.set("エラー: 音声合成に失敗 (VOICEVOX Test Play)"))

    #     except Exception as e:
    #         if not self.clear_audio_requested:
    #             self.after(
    #                 0, lambda msg=f"音声合成エラー (VOICEVOX Test Play): {str(e)}": self.status_var.set(msg))
    #     finally:
    #         self.playback_lock.release()
    #         self.active_speaker_instance = None

    def _handle_playback(self, audio_data: bytes, audio_format: str) -> None:
        """Handles playback of audio data based on its format."""
        logger.info(f"Handling playback for format: {audio_format}")
        self.after(0, lambda: self.status_var.set(f"Playing {audio_format.upper()} audio..."))

        if audio_format == "wav":
            logger.info("Playing WAV audio using VoicevoxSpeaker.")
            try:
                speaker_instance = VoicevoxSpeaker(
                    output_device_index=self.current_device,
                    output_device_index_2=self.current_device_2,
                    speaker_2_enabled=self.speaker_2_enabled
                )
                self._play_audio_with_volume(audio_data, speaker_instance) # This is blocking if its internal 'wait' is True
                self.after(0, lambda: self.status_var.set("WAV playback finished."))
                logger.info("WAV playback attempt finished.")
            except Exception as e:
                logger.error(f"Error during WAV playback with VoicevoxSpeaker: {e}", exc_info=True)
                self.after(0, lambda: self.status_var.set("Error playing WAV."))

        elif audio_format == "mp3":
            logger.info("Attempting to play MP3 audio using OS-dependent player.")
            tmp_mp3_filename = None
            try:
                # Use NamedTemporaryFile from 'tempfile' module
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
                    tmpfile.write(audio_data)
                    tmp_mp3_filename = tmpfile.name

                logger.info(f"Temporary MP3 file created: {tmp_mp3_filename}")

                playback_command_logged = False
                if sys.platform == "win32":
                    os.startfile(tmp_mp3_filename) # Non-blocking
                    logger.info(f"Windows: Initiated playback with os.startfile for {tmp_mp3_filename}.")
                elif sys.platform == "darwin": # macOS
                    os.system(f"afplay '{tmp_mp3_filename}'") # Blocking
                    logger.info(f"macOS: Executed afplay for {tmp_mp3_filename}.")
                    playback_command_logged = True
                else: # Linux and other POSIX
                    if os.system("command -v mpg123 >/dev/null 2>&1") == 0:
                        os.system(f"mpg123 -q '{tmp_mp3_filename}'") # Blocking
                        logger.info(f"Linux: Executed mpg123 for {tmp_mp3_filename}.")
                        playback_command_logged = True
                    elif os.system("command -v play >/dev/null 2>&1") == 0: # SoX play command
                        os.system(f"play -q '{tmp_mp3_filename}'") # Blocking
                        logger.info(f"Linux: Executed play (SoX) for {tmp_mp3_filename}.")
                        playback_command_logged = True
                    else: # Fallback to xdg-open (Linux) or open (macOS, though afplay should be preferred)
                        logger.warning("No specific MP3 player (mpg123, play, afplay) found. Using system open.")
                        if sys.platform == "darwin": os.system(f"open '{tmp_mp3_filename}'") # Non-blocking
                        else: os.system(f"xdg-open '{tmp_mp3_filename}'") # Non-blocking
                        logger.info(f"Fallback: Initiated playback with system open for {tmp_mp3_filename}.")

                self.after(0, lambda: self.status_var.set("MP3 playback initiated."))
                if playback_command_logged or sys.platform == "win32": # If a blocking call finished or windows non-blocking
                    # For blocking calls, this means playback is done.
                    # For os.startfile, it means it was launched.
                    pass # logging already done for these cases

                # Simple delay for non-blocking players to have a chance to play,
                # before the file is potentially deleted. This is a pragmatic compromise.
                # A more robust solution would involve process monitoring.
                # For blocking players, this delay happens after they finish.
                time.sleep(5) # Allow some time for playback

            except Exception as e:
                logger.error(f"Error in MP3 playback: {e}", exc_info=True)
                self.after(0, lambda: self.status_var.set("Error playing MP3."))
            finally:
                if tmp_mp3_filename and os.path.exists(tmp_mp3_filename):
                    try:
                        # Add a bit more delay before deletion for non-blocking players
                        if sys.platform == "win32" or not playback_command_logged : time.sleep(5)
                        os.remove(tmp_mp3_filename)
                        logger.info(f"Cleaned up temporary MP3 file: {tmp_mp3_filename}")
                    except Exception as e_remove:
                        logger.error(f"Error cleaning up temporary MP3 file {tmp_mp3_filename}: {e_remove}")
        else:
            logger.warning(f"Cannot play audio of unknown format: {audio_format}. Data starts with: {audio_data[:10]!r}")
            self.after(0, lambda: self.status_var.set(f"Cannot play unknown format: {audio_format}"))


    def on_stop_and_clear_audio(self) -> None:
        self.status_var.set("停止リクエスト受信。オーディオをクリア・停止処理を開始します...")
        self.update_idletasks() # Ensure status message updates immediately

        self.clear_audio_requested = True

        if self.active_speaker_instance:
            # print("Stop/Clear: Attempting to stop active speaker instance.")
            try:
                self.active_speaker_instance.request_stop()
                self.status_var.set("アクティブな再生を停止しました。")
            except Exception as e:
                # print(f"Stop/Clear: Error stopping active speaker: {e}")
                self.status_var.set(f"スピーカー停止エラー: {e}")
        else:
            # print("Stop/Clear: No active speaker instance to stop.")
            self.status_var.set("停止するアクティブな再生はありません。")

    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        # WebSocket接続を停止
        self.stop_websocket_connection()

        # アプリケーションを破棄
        self.destroy()


if __name__ == "__main__":
    app = VoicevoxConnectorGUI()
    app.mainloop()
