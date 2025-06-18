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
import logging # Added
import io # Added for playsound with bytes
from playsound import playsound # Added for MP3 playback

# from voicevox import VOICEVOXClient # Removed
from voicevox_speaker import VoicevoxSpeaker # May remove if playsound is sufficient
from config import Config
from tts_engine import GTTSEngine, TTSSynthesisError # Updated import


# Setup basic logging for the main application
# This will also catch logs from tts_engine if its logger is a child of root or configured to propagate
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vrct_connector_main.log", mode='w'), # Log to a file
        logging.StreamHandler(sys.stdout) # Also log to console
    ]
)
logger = logging.getLogger(__name__)


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
        self.ws: Optional[websocket.WebSocketApp] = None # This is for client mode to VRCT
        self.ws_server_thread: Optional[threading.Thread] = None # For server mode from this app
        self.ws_server: Optional[Any] = None # To hold the server instance from websockets.serve
        self.ws_clients: Dict[Any, Any] = {} # To track connected clients if acting as server

        self.ws_connected: bool = False # True if this app is connected as a CLIENT to VRCT
        self.is_server_running: bool = False # True if this app is running as a WebSocket SERVER

        # TTS Engine
        self.tts_engine: GTTSEngine = GTTSEngine()
        logger.info("GTTSEngine initialized.")

        # Default TTS settings (can be updated by TTS_SET_GLOBAL_SETTINGS)
        self.default_tts_language = "en" # Default language for synthesis
        self.default_tts_voice_id = "com" # Default TLD for gTTS, maps to a "voice"

        # TTS Cache
        self.tts_cache: Dict[tuple, bytes] = {}
        self.tts_cache_order: list[tuple] = [] # For FIFO eviction
        self.MAX_CACHE_SIZE = 50 # Max number of items in cache

        # Playback lock
        self.playback_lock = threading.Lock()
        self.clear_audio_requested: bool = False
        # self.active_speaker_instance: Optional[VoicevoxSpeaker] = None # Replaced by simpler playback for now

        # 設定を読み込む
        self.load_config()

        # VOICEVOXクライアントの初期化 - REMOVED
        # self.client: VOICEVOXClient = VOICEVOXClient()
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
        self.ws_button_var = ctk.StringVar(value="Start WebSocket Server") # Changed label
        self.ws_status_var = ctk.StringVar(value="WebSocket Server: Stopped") # Changed label
        self.test_text_var = ctk.StringVar(value="Hello, this is a test.") # Changed default text
        self.status_var = ctk.StringVar(value="Ready. TTS Engine: gTTS") # Updated status

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

            # VOICEVOX Engineからスピーカー情報を取得 - REMOVED
            # self.speakers_data = self.client.speakers()
            # For gTTS, languages/voices are from tts_engine, not dynamically loaded this way
            self.speakers_data = [] # Clear or adapt if UI still uses it
            logger.info("Skipped loading speakers_data from VOICEVOXClient.")

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
        """キャラクターリストを更新 (Adapted for gTTS TLDs as voices)"""
        logger.info("Updating character/voice list for GTTSEngine.")
        # For gTTS, "characters" can be represented by TLDs for different accents/regions.
        # Styles are not directly applicable like in VOICEVOX.

        # Use TLD options as "characters" or "voices"
        # The `self.tts_engine.tld_options` is GTTS_TLD_OPTIONS from tts_engine.py
        # GTTS_TLD_OPTIONS = {'com': 'Default (com)', 'co.uk': 'UK English', ...}

        # We can use the descriptive names for the character dropdown
        # And store the tld_code (e.g., 'co.uk') as the 'id' or style.

        # Let's simplify: Character Dropdown will show available output languages from gTTS.
        # Style Dropdown will show TLD options for the selected language (if applicable, or generic TLDs).

        available_langs = self.tts_engine.get_available_languages()
        self.character_dropdown.configure(values=available_langs)
        if available_langs:
            # Try to restore saved language, else pick first
            saved_lang = self.config.get("gtts_language", self.default_tts_language)
            if saved_lang in available_langs:
                self.character_var.set(saved_lang)
            else:
                self.character_var.set(available_langs[0])
        else:
            self.character_dropdown.configure(values=["No languages available"])
            self.character_var.set("No languages available")

        self.on_character_change(self.character_var.get()) # Trigger style update

    def on_character_change(self, choice: str) -> None:
        """キャラクターコンボボックスで選択されたときの処理 (Language selected for gTTS)"""
        logger.info(f"Language selected: {choice}")
        self.current_selected_language = choice # Store the chosen language (e.g., 'en')

        # "Styles" can be TLDs for gTTS, offering different regional accents
        tld_display_names = [f"{name} ({tld})" for tld, name in self.tts_engine.tld_options.items()]
        self.style_dropdown.configure(values=tld_display_names)

        if tld_display_names:
            saved_tld_name = self.config.get("gtts_tld_name") # e.g., "UK English (co.uk)"
            if saved_tld_name in tld_display_names:
                self.style_var.set(saved_tld_name)
            else:
                # Set to default 'com' TLD
                default_tld_display = f"{self.tts_engine.tld_options['com']} (com)"
                if default_tld_display in tld_display_names:
                     self.style_var.set(default_tld_display)
                else: # Fallback if even default isn't in list (should not happen)
                    self.style_var.set(tld_display_names[0])
        else:
            self.style_dropdown.configure(values=["N/A"])
            self.style_var.set("N/A")

        self.on_style_change(self.style_var.get())


    def on_style_change(self, choice: str) -> None:
        """スタイルが変更されたときの処理 (TLD selected for gTTS)"""
        logger.info(f"Style (TLD) selected: {choice}")
        # Extract TLD code from "Display Name (code)"
        if choice and "(" in choice and choice.endswith(")"):
            try:
                self.current_selected_tld = choice.split('(')[-1][:-1]
                logger.info(f"Selected TLD code: {self.current_selected_tld}")
            except Exception as e:
                logger.error(f"Could not parse TLD from style choice '{choice}': {e}")
                self.current_selected_tld = "com" # Default
        else:
            self.current_selected_tld = "com" # Default

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

    # def _play_audio_with_volume(self, audio_data: bytes, speaker_instance: VoicevoxSpeaker) -> None:
    # This method is problematic for MP3s as direct volume adjustment on bytes is complex.
    # VoicevoxSpeaker was designed for WAV. For MP3s, we'd typically use a library that
    # handles MP3 decoding and playback, and hopefully volume control at the playback stage.
    # For now, we will use `playsound` which doesn't offer easy byte-level volume control.
    # Volume adjustment for MP3s will be considered a future enhancement if playsound doesn't suffice.
    # The existing self.volume (0.0-1.0) won't be applied directly to MP3 bytes here.

    def play_test_audio(self) -> None:
        """テスト音声を再生 (Uses GTTSEngine)"""
        selected_lang = getattr(self, 'current_selected_language', self.default_tts_language)
        selected_tld = getattr(self, 'current_selected_tld', 'com') # Default TLD

        text: str = self.test_text_var.get()
        if not text:
            self.status_var.set("Error: Text is empty")
            logger.error("Test play: Text is empty.")
            return

        logger.info(f"Test play: Text='{text}', Lang='{selected_lang}', TLD='{selected_tld}'")
        self.status_var.set("Synthesizing test audio...")
        self.update()

        thread: threading.Thread = threading.Thread(
            target=self._play_audio_async, args=(text, selected_lang, {"tld": selected_tld}), daemon=True)
        thread.start()

    def _play_audio_async(self, text: str, language_code: str, tts_kwargs: Optional[Dict] = None) -> None:
        """非同期で音声合成と再生を行う (Uses GTTSEngine and playsound)"""
        if tts_kwargs is None:
            tts_kwargs = {}

        logger.info(f"Attempting synthesis: Text='{text[:30]}...', Lang='{language_code}', Kwargs='{tts_kwargs}'")
        self.playback_lock.acquire()
        try:
            if self.clear_audio_requested:
                self.clear_audio_requested = False
                self.status_var.set("Playback cancelled due to clear request.")
                logger.info("Playback cancelled due to clear_audio_requested flag.")
                return

            # Synthesize audio using the TTS engine
            audio_data: Optional[bytes] = self.tts_engine.synthesize_speech(
                text, language_code, **tts_kwargs
            )

            if audio_data:
                logger.info(f"Synthesis successful, got {len(audio_data)} bytes. Attempting playback.")
                # Save to a temporary file to play with playsound
                # TODO: Explore if playsound can play from memory to avoid temp file
                temp_mp3_path = os.path.join(self.app_path, "temp_playback.mp3")
                with open(temp_mp3_path, "wb") as f:
                    f.write(audio_data)

                if self.clear_audio_requested: # Check again before playing
                    logger.info("Playback cancelled just before playing.")
                    if os.path.exists(temp_mp3_path): os.remove(temp_mp3_path)
                    return

                playsound(temp_mp3_path) # This is blocking, ensure it's in a thread for GUI
                logger.info("Playback via playsound finished.")
                if os.path.exists(temp_mp3_path):
                    try:
                        os.remove(temp_mp3_path)
                    except Exception as e:
                        logger.error(f"Error deleting temp playback file: {e}")

                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set("Test playback finished."))
            else:
                logger.error("Synthesis failed, no audio data received.")
                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set("Error: Synthesis failed."))

        except TTSSynthesisError as e:
            logger.error(f"TTSSynthesisError during test playback: {e}")
            if not self.clear_audio_requested:
                self.after(0, lambda msg=f"TTS Error: {e}": self.status_var.set(msg))
        except Exception as e:
            logger.exception("Generic error during test playback audio async.")
            if not self.clear_audio_requested:
                self.after(0, lambda msg=f"Playback Error: {e}": self.status_var.set(msg))
        finally:
            if self.playback_lock.locked():
                self.playback_lock.release()
            logger.info("Playback async task finished.")

    def load_config(self) -> None:
        """設定ファイルから設定を読み込む"""
        config: Dict[str, Any] = Config.load()
        # self.current_style = config.get("speaker_id") # VOICEVOX specific
        self.config = config # Store loaded config
        self.current_selected_language = config.get("gtts_language", self.default_tts_language)
        self.current_selected_tld_name = config.get("gtts_tld_name", f"{self.tts_engine.tld_options.get('com','Default')} (com)")


        self.current_device = config.get("device_index") # Keep for local playback device
        self.current_device_2 = config.get("device_index_2")
        self.speaker_2_enabled = config.get("speaker_2_enabled", False)
        self.current_host = config.get("host_name", "すべて")
        self.current_host_2 = config.get("host_name_2", "すべて")
        self.volume = config.get("volume", 0.8)
        self.ws_url = config.get("ws_url", "ws://127.0.0.1:5000/api/tts") # Changed default port

    def save_config(self) -> None:
        """現在の設定を保存"""
        # Extract TLD code from the full TLD name string for saving if needed
        # For now, saving the full name as selected in dropdown.
        # Or, parse self.current_selected_tld if it's consistently updated.
        config_data: Dict[str, Any] = {
            # "speaker_id": self.current_style, # VOICEVOX specific
            "gtts_language": self.current_selected_language,
            "gtts_tld_name": self.style_var.get(), # Save the display name of TLD
            "device_index": self.current_device,
            "device_index_2": self.current_device_2,
            "speaker_2_enabled": self.speaker_2_enabled,
            "host_name": self.current_host,
            "host_name_2": self.current_host_2,
            "volume": self.volume,
            "ws_url": self.ws_url_var.get() # This URL is for client mode
        }
        Config.save(config_data)
        # self.ws_url = self.ws_url_var.get() # This is for client mode
        self.status_var.set("Settings saved.")
        logger.info("Configuration saved.")

    async def _ws_handler(self, websocket_client, path):
        """Handles individual client connections to our server."""
        logger.info(f"Client connected: {websocket_client.remote_address}")
        self.ws_clients[websocket_client] = None # Store client, value can be state if needed

        try:
            async for message in websocket_client:
                request_id = "unknown" # Default if not found in message
                try:
                    logger.info(f"Received message: {message[:256]}") # Log first 256 chars
                    data = json.loads(message)
                    request_id = data.get("request_id", "unknown")
                    command = data.get("command")

                    response_data = None
                    binary_payload = None

                    if command == "TTS_SYNTHESIZE":
                        text = data.get("text")
                        lang = data.get("language_code", self.default_tts_language)
                        # voice_id could map to TLD or other gTTS params
                        voice_id = data.get("voice_id", self.default_tts_voice_id)

                        # VRCT specific message type handling
                        msg_type = data.get("type") # "SENT", "RECEIVED", "CHAT"
                        if msg_type == "SENT":
                            text_to_synth = data.get("message", "")
                            lang_to_synth = data.get("src_languages", lang)
                        elif msg_type == "RECEIVED":
                            text_to_synth = data.get("translation", "")
                            lang_to_synth = data.get("dst_languages", lang)
                        elif msg_type == "CHAT":
                             text_to_synth = data.get("message", "") # Or translation based on config
                             lang_to_synth = data.get("src_languages", lang)
                        else: # Default to top-level text/lang if type is missing or different
                            text_to_synth = text
                            lang_to_synth = lang

                        if not text_to_synth:
                            raise ValueError("Text for synthesis is empty.")

                        logger.info(f"[{request_id}] TTS_SYNTHESIZE: Text='{text_to_synth[:30]}...', Lang='{lang_to_synth}', Voice='{voice_id}'")

                        # kwargs for synthesize_speech, e.g., mapping voice_id to tld
                        gtts_params = {"tld": voice_id if voice_id in self.tts_engine.tld_options else self.default_tts_voice_id}

                        # Cache key: (text, lang, tld) - ensures variations are cached separately
                        cache_key = (text_to_synth, lang_to_synth, gtts_params["tld"])

                        # Log character count and language for synthesis
                        logger.info(f"[{request_id}] Processing synthesis for lang '{lang_to_synth}', TLD '{gtts_params['tld']}', char count: {len(text_to_synth)}.")

                        if cache_key in self.tts_cache:
                            audio_bytes = self.tts_cache[cache_key]
                            logger.info(f"[{request_id}] Cache HIT for key: {cache_key}. Audio size: {len(audio_bytes)}. Latency: ~0ms (cached).")
                            # Optional: Move key to end of tts_cache_order for LRU, but FIFO is simpler with current list
                        else:
                            logger.info(f"[{request_id}] Cache MISS for key: {cache_key}. Synthesizing...")
                            # Latency for actual synthesis is logged within tts_engine.py's GTTSEngine
                            audio_bytes = self.tts_engine.synthesize_speech(text_to_synth, lang_to_synth, **gtts_params)
                            # logger.info(f"[{request_id}] Synthesis successful, audio size: {len(audio_bytes)}. Storing in cache.") # This part is now in tts_engine
                            logger.info(f"[{request_id}] Storing result in cache. Audio size: {len(audio_bytes)}.")

                            # Add to cache
                            if len(self.tts_cache) >= self.MAX_CACHE_SIZE:
                                oldest_key = self.tts_cache_order.pop(0) # FIFO: remove oldest
                                del self.tts_cache[oldest_key]
                                logger.info(f"Cache full. Evicted oldest key: {oldest_key}")

                            self.tts_cache[cache_key] = audio_bytes
                            self.tts_cache_order.append(cache_key)

                        response_data = {"status": "success", "message": "Audio synthesized", "request_id": request_id, "data": {"audio_format": "mp3"}}
                        binary_payload = audio_bytes
                        # logger.info(f"[{request_id}] Synthesis successful, audio size: {len(audio_bytes)}") # Already logged by hit/miss

                    elif command == "TTS_GET_VOICES":
                        logger.info(f"[{request_id}] TTS_GET_VOICES received.")
                        langs = self.tts_engine.get_available_languages()
                        # Format TLDs as voices
                        voices = [{"id": tld, "name": name, "language": "shared"} for tld, name in self.tts_engine.tld_options.items()]
                        response_data = {"status": "success", "request_id": request_id, "data": {"languages": langs, "voices": voices}}
                        logger.info(f"[{request_id}] Returning {len(langs)} languages and {len(voices)} voices (TLDs).")

                    elif command == "TTS_STOP":
                        logger.info(f"[{request_id}] TTS_STOP received. (Conceptual, playback stop is client-side for remote synthesis)")
                        # If this app were also playing audio locally from WS commands, stop it here.
                        # For now, just acknowledge.
                        self.on_stop_and_clear_audio() # Clears local test playback queue
                        response_data = {"status": "success", "message": "Stop command acknowledged", "request_id": request_id}

                    elif command == "TTS_SET_DEFAULT_VOICE":
                        voice_id = data.get("voice_id")
                        logger.info(f"[{request_id}] TTS_SET_DEFAULT_VOICE: voice_id='{voice_id}'. (Placeholder)")
                        if voice_id in self.tts_engine.tld_options: # Assuming voice_id maps to TLD for gTTS
                            self.default_tts_voice_id = voice_id
                            # Update config if desired to persist this
                            self.status_var.set(f"Default voice (TLD) set to: {voice_id}")
                            response_data = {"status": "success", "message": f"Default voice (TLD) updated to {voice_id}", "request_id": request_id}
                        else:
                            raise ValueError(f"Invalid voice_id (TLD): {voice_id}")


                    elif command == "TTS_SET_GLOBAL_SETTINGS":
                        settings = data.get("settings", {})
                        logger.info(f"[{request_id}] TTS_SET_GLOBAL_SETTINGS: {settings}. (Placeholder)")
                        if "language" in settings:
                            self.default_tts_language = self.tts_engine.get_gtts_lang_code(settings["language"])
                            self.status_var.set(f"Default lang set to: {self.default_tts_language}")
                        # Store other settings as needed, e.g., self.config.update(settings)
                        response_data = {"status": "success", "message": "Global settings updated (partially implemented)", "request_id": request_id}

                    else:
                        logger.warning(f"[{request_id}] Unknown command: {command}")
                        raise ValueError(f"Unknown command: {command}")

                    if response_data:
                        await websocket_client.send(json.dumps(response_data))
                        logger.info(f"[{request_id}] Sent JSON response: {response_data}")
                    if binary_payload:
                        await websocket_client.send(binary_payload)
                        logger.info(f"[{request_id}] Sent binary audio payload.")

                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON message.")
                    await websocket_client.send(json.dumps({"status": "error", "message": "Invalid JSON format", "request_id": "unknown", "code": 1002}))
                except TTSSynthesisError as e:
                    logger.error(f"[{request_id}] TTSSynthesisError: {e}")
                    await websocket_client.send(json.dumps({"status": "error", "message": str(e), "code": 1000, "request_id": request_id}))
                except ValueError as e: # For invalid params or unknown commands
                    logger.error(f"[{request_id}] ValueError: {e}")
                    await websocket_client.send(json.dumps({"status": "error", "message": str(e), "code": 1001, "request_id": request_id}))
                except Exception as e:
                    logger.exception(f"[{request_id}] Unexpected error in on_message handling.")
                    await websocket_client.send(json.dumps({"status": "error", "message": f"Internal server error: {type(e).__name__}", "code": 500, "request_id": request_id}))

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client disconnected: {websocket_client.remote_address}, code={e.code}, reason='{e.reason}'")
        except Exception as e:
            logger.exception(f"Error in WebSocket handler with {websocket_client.remote_address}")
        finally:
            if websocket_client in self.ws_clients:
                del self.ws_clients[websocket_client]
            logger.info(f"Cleaned up client: {websocket_client.remote_address}")


    async def _start_ws_server_async(self):
        """Coroutine to start the WebSocket server."""
        # self.ws_url is like "ws://127.0.0.1:2231"
        # For websockets.serve, we need host and port
        try:
            url_parts = self.ws_url_var.get().replace("ws://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1].split("/")[0]) # Remove any path part for serve

            logger.info(f"Attempting to start WebSocket server on {host}:{port}")
            # The handler needs to be passed to serve, not called directly here.
            self.ws_server = await websockets.serve(self._ws_handler, host, port)
            self.is_server_running = True
            self.after(0, self._update_ws_status_connected) # Update GUI from main thread
            logger.info(f"WebSocket server started on {host}:{port} and listening.")
            await self.ws_server.wait_closed() # Keep it running until explicitly closed
        except Exception as e:
            self.is_server_running = False
            logger.exception("Failed to start WebSocket server.")
            self.after(0, lambda: self.status_var.set(f"Server start error: {e}"))
            self.after(0, self._update_ws_status_disconnected)
        finally:
            self.is_server_running = False
            logger.info("WebSocket server has stopped.")
            self.after(0, self._update_ws_status_disconnected)


    def toggle_websocket_connection(self) -> None:
        """Starts or stops the WebSocket server."""
        if not self.is_server_running:
            logger.info("Toggle: Starting WebSocket server.")
            # Run the server in a new thread
            self.ws_server_thread = threading.Thread(
                target=lambda: asyncio.run(self._start_ws_server_async()),
                daemon=True
            )
            self.ws_server_thread.start()
        else:
            logger.info("Toggle: Stopping WebSocket server.")
            if self.ws_server:
                self.ws_server.close() # This signals wait_closed() to finish
                # self.ws_server_thread.join(timeout=5) # Wait for thread to finish
            self.is_server_running = False
            # Status update will happen in _start_ws_server_async's finally block
            # but can also force it here if needed.
            self._update_ws_status_disconnected()


    def start_websocket_connection(self) -> None:
        """WebSocket接続を開始する (Now starts this app AS A SERVER)"""
        # This method is now effectively replaced by toggle_websocket_connection
        # The old code made this app a client. The new requirement is to be a server.
        # For clarity, I'll rename the button's command to toggle_websocket_connection.
        # The UI elements related to character/style for VOICEVOX are less relevant for gTTS server mode
        # but are kept for now. Language/TLD selection for test button is separate.

        # The server URL input (self.ws_url_var) now defines where THIS server will run.
        # Default was "ws://127.0.0.1:2231", new suggested "ws://127.0.0.1:5000/api/tts"
        # The path part "/api/tts" is not directly used by websockets.serve, it serves on all paths.

        self.toggle_websocket_connection()


    def stop_websocket_connection(self) -> None:
        """WebSocket接続を停止する (Stops this app's SERVER)"""
        # Replaced by toggle_websocket_connection
        self.toggle_websocket_connection()


    def _update_ws_status_connected(self) -> None:
        """WebSocket接続状態のUIを更新（接続時） (Server Started)"""
        self.ws_status_var.set("WebSocket Server: Running")
        self.ws_status_label.configure(text_color="#4CAF50")  # 緑色
        self.ws_button_var.set("Stop WebSocket Server")
        self.ws_button.configure(
            fg_color="#8B0000", hover_color="#B22222")  # 赤色
        self.status_var.set(f"WebSocket Server running at {self.ws_url_var.get()}")
        logger.info(f"WebSocket Server running at {self.ws_url_var.get()}")

    def _update_ws_status_disconnected(self) -> None:
        """WebSocket接続状態のUIを更新（切断時） (Server Stopped)"""
        self.ws_status_var.set("WebSocket Server: Stopped")
        self.ws_status_label.configure(text_color="gray")
        self.ws_button_var.set("Start WebSocket Server")
        self.ws_button.configure(
            fg_color="#1E5631", hover_color="#2E8B57")  # 緑色
        self.status_var.set("WebSocket Server stopped.")
        logger.info("WebSocket Server stopped.")


    def _synthesize_and_play(self, text: str) -> None:
        """テキストを音声合成して再生する (Legacy, called by old WS client mode)"""
        # This method was part of the old client-mode WebSocket handling.
        # It's not directly used by the new server-mode _ws_handler.
        # It can be adapted if local playback of messages received by server is needed.
        # For now, it's similar to play_test_audio's needs.
        logger.warning("_synthesize_and_play (legacy WS client mode) called. Adapting for gTTS test.")

        # Use app's default language/tld for this legacy path for now
        lang = self.current_selected_language # From UI or default
        tld_val = self.current_selected_tld # From UI or default

        # Using _play_audio_async, which is now the main local playback method
        # This needs to be run in a thread if called from a network handler thread
        thread = threading.Thread(target=self._play_audio_async, args=(text, lang, {"tld": tld_val}), daemon=True)
        thread.start()

    def on_stop_and_clear_audio(self) -> None:
        """Stops any local test playback."""
        logger.info("Stop/Clear audio requested.")
        self.status_var.set("Stop request received. Clearing audio...")
        self.update_idletasks()

        self.clear_audio_requested = True # Flag for async playback tasks to check

        # For playsound, stopping is tricky as it's often blocking or uses system calls.
        # If playsound is running in a separate thread managed by this app, we could try to manage that thread.
        # However, playsound(..., block=False) returns immediately and plays in background on some platforms.
        # For now, this primarily relies on the clear_audio_requested flag to prevent new sounds
        # and for already playing sounds, they might finish if not interruptible.
        # This is a known limitation of playsound's control.

        # If VoicevoxSpeaker or a similar controllable player was used:
        # if self.active_speaker_instance:
        #     try:
        #         self.active_speaker_instance.request_stop()
        #         self.status_var.set("Active playback stopped.")
        #         logger.info("Active playback stopped.")
        #     except Exception as e:
        #         self.status_var.set(f"Error stopping speaker: {e}")
        #         logger.error(f"Error stopping speaker: {e}")
        # else:
        #     self.status_var.set("No active playback to stop.")
        #     logger.info("No active playback instance to stop.")
        self.status_var.set("Audio stop requested (effectiveness depends on playback method).")


    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        logger.info("Application closing...")
        # WebSocket接続を停止
        if self.is_server_running and self.ws_server:
            logger.info("Stopping WebSocket server...")
            self.ws_server.close()
            # asyncio.run(self.ws_server.wait_closed()) # Ensure it's closed if run from async context
            if self.ws_server_thread and self.ws_server_thread.is_alive():
                 self.ws_server_thread.join(timeout=2) # Wait for server thread

        # Stop any other threads if necessary
        logger.info("Destroying application window.")
        # アプリケーションを破棄
        self.destroy()


if __name__ == "__main__":
    logger.info("Application starting...")
    # Ensure playsound is installed if using it
    try:
        import playsound
    except ImportError:
        logger.error("playsound library is not installed. Please install it for audio playback.")
        # Optionally, disable playback features or exit

    app = VoicevoxConnectorGUI()
    app.mainloop()
    logger.info("Application exited.")
