#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VRCT-TTS GUI
CustomTkinterを使用したVRCT-TTSの設定GUI
"""

import os
import sys
import threading
import ctypes
import customtkinter as ctk
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import websocket
import json
import html
import re
import struct
import io
import wave
import numpy as np

from voicevox import VOICEVOXClient
from audio_player import AudioPlayer
from voicevox_speaker import VoicevoxSpeaker
from gTTS_speaker import gTTSSpeaker
from vrct_languages import vrct_lang_dict
from config import Config
from language import texts


class VRCTTTSConnectorGUI(ctk.CTk):
    """VRCT-TTSアプリケーション"""

    # ------------------------------------------------------------------
    # UIテーマトークン (モダンなフラットデザイン用の統一パレット / 余白)
    # ------------------------------------------------------------------
    COL_BG            = "#17181c"   # ウィンドウ背景
    COL_CARD          = "#22242b"   # カード表面
    COL_INPUT         = "#2c2f38"   # 入力欄 / コンボボックス表面
    COL_BORDER        = "#3a3e49"   # 罫線
    COL_TEXT          = "#e9eaee"   # 本文
    COL_TEXT_MUTED    = "#9a9ca6"   # 補助テキスト
    COL_ACCENT        = "#6c7cff"   # アクセント (インディゴ)
    COL_ACCENT_HOVER  = "#5a67e6"
    COL_SUCCESS       = "#3ba55d"   # 接続
    COL_SUCCESS_HOVER = "#31894e"
    COL_DANGER        = "#e5544b"   # 切断 / 停止
    COL_DANGER_HOVER  = "#c5443c"
    RADIUS            = 12          # カードの角丸
    RADIUS_SM         = 8           # 入力欄 / ボタンの角丸
    PAD               = 16          # カード内側の基準余白
    GAP               = 10          # 要素間の基準間隔

    def __init__(self) -> None:
        super().__init__()

        # アプリケーションのバージョン情報
        self.app_version = "v1.2.0"

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
        # タイポグラフィスケール
        self.font_title: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=20, weight="bold")
        self.font_card_title: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=14, weight="bold")
        self.font_label: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=12, weight="normal")
        self.font_body: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=13, weight="normal")
        self.font_button: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=13, weight="bold")
        self.font_caption: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=11, weight="normal")

        # アプリの設定
        self.title("VRCT-TTS")
        self.geometry("880x858")
        self.minsize(width=840, height=740)

        # ダークモードをデフォルトに設定
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.COL_BG)
        self.speakers_data: List[Dict[str, Any]] = []
        self.audio_devices: List[Dict[str, Any]] = []
        self.current_character: Optional[Dict[str, Any]] = None
        self.current_style: Optional[int] = None
        self.current_device: Optional[int] = None
        self.current_device_2: Optional[int] = None
        self.speaker_2_enabled: bool = False
        self.current_host: Optional[str] = None
        self.current_host_2: Optional[str] = None
        self.volume: float = 0.8  # デフォルトの音量 (0.0-1.0)
        self.speed: float = 1.0 # デフォルトの再生速度 (0.5-2.0)
        self.ws_url: str = "ws://127.0.0.1:2231"
        self.ws_token: str = ""
        self.gtts_lang: str = "English"
        self.source_tts_engine: str = "VOICEVOX"
        self.dest_tts_engine: str = "gTTS"
        self.play_source: bool = False
        self.play_dest: bool = True
        self.language: str = "English"

        # UI Variables
        self.character_var = ctk.StringVar()
        self.style_var = ctk.StringVar()
        self.device_var = ctk.StringVar()
        self.device_var_2 = ctk.StringVar()
        self.speaker_2_enabled_var = ctk.BooleanVar(value=False)
        self.host_var = ctk.StringVar()
        self.host_var_2 = ctk.StringVar()
        self.gtts_lang_var = ctk.StringVar()
        self.source_tts_engine_var = ctk.StringVar()
        self.dest_tts_engine_var = ctk.StringVar()
        self.play_source_var = ctk.BooleanVar()
        self.play_dest_var = ctk.BooleanVar()
        self.language_var = ctk.StringVar()
        self.volume_value_var: Optional[ctk.StringVar] = None
        self.speed_value_var: Optional[ctk.StringVar] = None
        self.ws_url_var: Optional[ctk.StringVar] = None
        self.ws_token_var: Optional[ctk.StringVar] = None
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
        self.clear_audio_requested: bool = False
        self.active_speaker_instance: Optional[Union[VoicevoxSpeaker, gTTSSpeaker]] = None

        # 設定を読み込む
        self.load_config()

        # UIテキスト
        self.texts = texts

        # VOICEVOXクライアントの初期化
        self.client: VOICEVOXClient = VOICEVOXClient()

        # gTTSでサポートされている言語のリストを作成
        self.gtts_supported_languages: Dict[str, str] = self._create_gtts_lang_list()

        # UIの作成
        self.create_ui()

        # データの読み込み
        self.load_data()

        # プロトコルハンドラー
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_gtts_lang_list(self) -> Dict[str, str]:
        """gTTSでサポートされている言語の辞書を作成する"""
        gtts_langs = gTTSSpeaker.list_supported_languages()
        # gtts_langsは {'af': 'Afrikaans', ...} の形式なので、値とキーを反転させる
        gtts_lang_names = {v.lower(): k for k, v in gtts_langs.items()}

        supported_languages = {}
        for name, code in vrct_lang_dict.items():
            # 中国語の特殊ケースを処理
            if name == "Chinese Simplified":
                if "chinese (simplified)" in gtts_lang_names:
                    supported_languages[name] = gtts_lang_names["chinese (simplified)"]
                elif "chinese (mandarin)" in gtts_lang_names:
                    supported_languages[name] = gtts_lang_names["chinese (mandarin)"]
            elif name == "Chinese Traditional":
                if "chinese (mandarin/taiwan)" in gtts_lang_names:
                    supported_languages[name] = gtts_lang_names["chinese (mandarin/taiwan)"]
            elif name.lower() in gtts_lang_names:
                supported_languages[name] = gtts_lang_names[name.lower()]

        return supported_languages

    def _card(self, parent: Any) -> "ctk.CTkFrame":
        """統一スタイルのカード (セクション) フレームを生成する"""
        return ctk.CTkFrame(parent, corner_radius=self.RADIUS, fg_color=self.COL_CARD)

    def _card_title(self, parent: Any, text: str) -> "ctk.CTkLabel":
        """カード見出し (太字) を配置して返す"""
        lbl = ctk.CTkLabel(
            parent, text=text, font=self.font_card_title,
            text_color=self.COL_TEXT, anchor="w",
        )
        lbl.pack(fill="x", padx=self.PAD, pady=(12, 6))
        return lbl

    def _sub_label(self, parent: Any, text: str, top: Optional[int] = None) -> "ctk.CTkLabel":
        """入力欄の上に置く補助ラベル (小さめ・グレー) を配置して返す"""
        lbl = ctk.CTkLabel(
            parent, text=text, font=self.font_label,
            text_color=self.COL_TEXT_MUTED, anchor="w",
        )
        lbl.pack(fill="x", padx=self.PAD, pady=(6 if top is None else top, 3))
        return lbl

    def create_ui(self) -> None:
        """UIコンポーネントの作成"""
        # Initialize other StringVars that were previously Optional
        self.volume_value_var = ctk.StringVar(value=f"{int(self.volume * 100)}%")
        self.speed_value_var = ctk.StringVar(value=f"x{self.speed:.2f}")
        self.ws_url_var = ctk.StringVar(value=self.ws_url)
        self.ws_url_var.trace_add("write", lambda *args: self.save_config())
        self.ws_token_var = ctk.StringVar(value=self.ws_token)
        self.ws_token_var.trace_add("write", lambda *args: self.save_config())
        self.ws_button_var = ctk.StringVar(value="WebSocket接続開始")
        self.ws_status_var = ctk.StringVar(value="WebSocket: 未接続")
        self.test_text_var = ctk.StringVar(value="こんにちは")
        self.status_var = ctk.StringVar(value="準備完了")

        # ================= ルートレイアウト =================
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=14, pady=14)
        self.main_frame = outer

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            header, text="VRCT-TTS", font=self.font_title,
            text_color=self.COL_TEXT, anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            header, text="VRCT WebSocket → TTS", font=self.font_caption,
            text_color=self.COL_TEXT_MUTED, anchor="w",
        ).pack(side="left", padx=(10, 0), pady=(7, 0))

        # ステータスバー (中央コンテンツより先に bottom へ確保)
        status_frame = ctk.CTkFrame(outer, fg_color="transparent")
        status_frame.pack(fill="x", side="bottom", pady=(14, 0))

        # ================= 2カラムのコンテンツ =================
        content_frame = ctk.CTkFrame(outer, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_columnconfigure(0, weight=1, uniform="cols")
        content_frame.grid_columnconfigure(1, weight=1, uniform="cols")
        content_frame.grid_rowconfigure(0, weight=1)

        left_column_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_column_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_column_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_column_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # 共通ウィジェットスタイル
        self._entry_kw = dict(
            height=34, corner_radius=self.RADIUS_SM, border_width=1,
            border_color=self.COL_BORDER, fg_color=self.COL_INPUT, font=self.font_body,
        )
        self._combo_kw = dict(
            height=34, corner_radius=self.RADIUS_SM, border_width=1,
            border_color=self.COL_BORDER, fg_color=self.COL_INPUT,
            button_color=self.COL_INPUT, button_hover_color=self.COL_BORDER,
            dropdown_fg_color=self.COL_CARD, dropdown_hover_color=self.COL_ACCENT,
            dropdown_text_color=self.COL_TEXT, text_color=self.COL_TEXT,
            font=self.font_body, dropdown_font=self.font_body, state="readonly",
        )
        self._btn_kw = dict(
            height=36, corner_radius=self.RADIUS_SM, font=self.font_button,
            fg_color=self.COL_ACCENT, hover_color=self.COL_ACCENT_HOVER,
        )
        self._check_kw = dict(
            font=self.font_body, fg_color=self.COL_ACCENT, hover_color=self.COL_ACCENT_HOVER,
            checkbox_width=20, checkbox_height=20, corner_radius=5,
            border_width=2, border_color=self.COL_BORDER,
        )
        self._slider_kw = dict(
            progress_color=self.COL_ACCENT, button_color=self.COL_ACCENT,
            button_hover_color=self.COL_ACCENT_HOVER, fg_color=self.COL_INPUT,
        )
        pad = self.PAD
        gap = 8

        # ---------------- WebSocket カード ----------------
        ws_card = self._card(left_column_frame)
        ws_card.pack(fill="x", pady=(0, gap))
        self._card_title(ws_card, "WebSocket")

        self.ws_label = self._sub_label(ws_card, "WebSocketサーバーURL", top=0)
        self.ws_entry = ctk.CTkEntry(ws_card, textvariable=self.ws_url_var, **self._entry_kw)
        self.ws_entry.pack(fill="x", padx=pad, pady=(0, gap))

        self.ws_token_label = self._sub_label(ws_card, "WebSocketトークン（任意）")
        self.ws_token_entry = ctk.CTkEntry(ws_card, textvariable=self.ws_token_var, **self._entry_kw)
        self.ws_token_entry.pack(fill="x", padx=pad, pady=(0, gap))

        self.ws_button = ctk.CTkButton(
            ws_card, textvariable=self.ws_button_var, command=self.toggle_websocket_connection,
            **{**self._btn_kw, "fg_color": self.COL_SUCCESS, "hover_color": self.COL_SUCCESS_HOVER},
        )
        self.ws_button.pack(fill="x", padx=pad, pady=(4, gap))

        self.ws_status_label = ctk.CTkLabel(
            ws_card, textvariable=self.ws_status_var, font=self.font_caption,
            text_color=self.COL_TEXT_MUTED, anchor="w",
        )
        self.ws_status_label.pack(fill="x", padx=pad, pady=(0, 12))

        # ---------------- デバイス カード ----------------
        dev_card = self._card(right_column_frame)
        dev_card.pack(fill="x", pady=(0, gap))
        self._card_title(dev_card, "出力デバイス")

        self.device_label = self._sub_label(dev_card, "出力デバイス", top=0)
        device_frame = ctk.CTkFrame(dev_card, fg_color="transparent")
        device_frame.pack(fill="x", padx=pad, pady=(0, gap))
        self.host_dropdown = ctk.CTkComboBox(
            device_frame, variable=self.host_var, values=["ホストを読み込み中..."],
            width=132, command=self.on_host_change, **self._combo_kw,
        )
        self.host_dropdown.pack(side="left", padx=(0, 8))
        self.device_dropdown = ctk.CTkComboBox(
            device_frame, variable=self.device_var, values=["デバイスを読み込み中..."],
            command=self.on_device_change, **self._combo_kw,
        )
        self.device_dropdown.pack(side="left", fill="x", expand=True)

        self.device_label_2 = self._sub_label(dev_card, "第2出力デバイス")
        device_frame_2 = ctk.CTkFrame(dev_card, fg_color="transparent")
        device_frame_2.pack(fill="x", padx=pad, pady=(0, gap))
        self.host_dropdown_2 = ctk.CTkComboBox(
            device_frame_2, variable=self.host_var_2, values=["ホストを読み込み中..."],
            width=132, command=self.on_host_2_change, **self._combo_kw,
        )
        self.host_dropdown_2.pack(side="left", padx=(0, 8))
        self.device_dropdown_2 = ctk.CTkComboBox(
            device_frame_2, variable=self.device_var_2, values=["デバイスを読み込み中..."],
            command=self.on_device_2_change, **self._combo_kw,
        )
        self.device_dropdown_2.pack(side="left", fill="x", expand=True)

        self.speaker_2_enable_checkbox = ctk.CTkCheckBox(
            dev_card, text="第2スピーカーを有効にする", variable=self.speaker_2_enabled_var,
            command=self.on_speaker_2_enable_change, **self._check_kw,
        )
        self.speaker_2_enable_checkbox.pack(anchor="w", padx=pad, pady=(4, 12))

        # ---------------- VOICEVOX カード ----------------
        vv_card = self._card(right_column_frame)
        vv_card.pack(fill="x", pady=(0, gap))
        self.voicevox_settings_label = self._card_title(vv_card, "VOICEVOX設定")

        self.char_label = self._sub_label(vv_card, "キャラクター選択", top=0)
        self.character_dropdown = ctk.CTkComboBox(
            vv_card, variable=self.character_var, values=["キャラクターを読み込み中..."],
            command=self.on_character_change, **self._combo_kw,
        )
        self.character_dropdown.pack(fill="x", padx=pad, pady=(0, gap))

        self.style_label_left = self._sub_label(vv_card, "声のスタイル")
        self.style_dropdown = ctk.CTkComboBox(
            vv_card, variable=self.style_var, values=["スタイルを読み込み中..."],
            command=self.on_style_change, **self._combo_kw,
        )
        self.style_dropdown.pack(fill="x", padx=pad, pady=(0, 12))

        # ---------------- TTSエンジン カード ----------------
        tts_frame = self._card(left_column_frame)
        tts_frame.pack(fill="x", pady=(0, gap))
        self._card_title(tts_frame, "TTSエンジン")

        self.source_tts_label = self._sub_label(tts_frame, "翻訳前 (Source) のTTS設定", top=0)
        self.source_tts_engine_dropdown = ctk.CTkComboBox(
            tts_frame, variable=self.source_tts_engine_var, values=["VOICEVOX", "gTTS"],
            command=self.on_source_tts_engine_change, **self._combo_kw,
        )
        self.source_tts_engine_dropdown.pack(fill="x", padx=pad, pady=(0, 6))
        self.play_source_checkbox = ctk.CTkCheckBox(
            tts_frame, text="翻訳前のテキストを再生する", variable=self.play_source_var,
            command=self.on_play_source_change, **self._check_kw,
        )
        self.play_source_checkbox.pack(anchor="w", padx=pad, pady=(2, gap))

        self.dest_tts_label = self._sub_label(tts_frame, "翻訳後 (Destination) のTTS設定")
        self.dest_tts_engine_dropdown = ctk.CTkComboBox(
            tts_frame, variable=self.dest_tts_engine_var, values=["gTTS", "VOICEVOX"],
            command=self.on_dest_tts_engine_change, **self._combo_kw,
        )
        self.dest_tts_engine_dropdown.pack(fill="x", padx=pad, pady=(0, 6))
        self.play_dest_checkbox = ctk.CTkCheckBox(
            tts_frame, text="翻訳後のテキストを再生する", variable=self.play_dest_var,
            command=self.on_play_dest_change, **self._check_kw,
        )
        self.play_dest_checkbox.pack(anchor="w", padx=pad, pady=(2, 12))

        # ---------------- 音響 カード ----------------
        volume_frame = self._card(left_column_frame)
        volume_frame.pack(fill="x", pady=(0, gap))
        self._card_title(volume_frame, "音響")

        vol_row = ctk.CTkFrame(volume_frame, fg_color="transparent")
        vol_row.pack(fill="x", padx=pad)
        self.volume_label = ctk.CTkLabel(
            vol_row, text="音量", font=self.font_label,
            text_color=self.COL_TEXT_MUTED, anchor="w",
        )
        self.volume_label.pack(side="left")
        ctk.CTkLabel(
            vol_row, textvariable=self.volume_value_var, font=self.font_label,
            text_color=self.COL_TEXT, anchor="e",
        ).pack(side="right")
        self.volume_slider = ctk.CTkSlider(
            volume_frame, from_=0, to=1.0, number_of_steps=20,
            command=self.on_volume_change, **self._slider_kw,
        )
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(fill="x", padx=pad, pady=(6, gap))

        spd_row = ctk.CTkFrame(volume_frame, fg_color="transparent")
        spd_row.pack(fill="x", padx=pad)
        self.speed_label = ctk.CTkLabel(
            spd_row, text="再生速度", font=self.font_label,
            text_color=self.COL_TEXT_MUTED, anchor="w",
        )
        self.speed_label.pack(side="left")
        ctk.CTkLabel(
            spd_row, textvariable=self.speed_value_var, font=self.font_label,
            text_color=self.COL_TEXT, anchor="e",
        ).pack(side="right")
        self.speed_slider = ctk.CTkSlider(
            volume_frame, from_=0.5, to=2.0, number_of_steps=30,
            command=self.on_speed_change, **self._slider_kw,
        )
        self.speed_slider.set(self.speed)
        self.speed_slider.pack(fill="x", padx=pad, pady=(6, 12))

        # ---------------- テスト再生 カード ----------------
        test_frame = self._card(right_column_frame)
        test_frame.pack(fill="x")
        self.test_label = self._card_title(test_frame, "再生")

        self.test_text_entry = ctk.CTkEntry(test_frame, textvariable=self.test_text_var, **self._entry_kw)
        self.test_text_entry.pack(fill="x", padx=pad, pady=(0, gap))

        self.gtts_lang_label = self._sub_label(test_frame, "gTTS言語 (テスト用)")
        self.gtts_lang_dropdown = ctk.CTkComboBox(
            test_frame, variable=self.gtts_lang_var,
            values=list(self.gtts_supported_languages.keys()),
            command=self.on_gtts_lang_change, **self._combo_kw,
        )
        self.gtts_lang_dropdown.pack(fill="x", padx=pad, pady=(0, gap))

        replay_frame = ctk.CTkFrame(test_frame, fg_color="transparent")
        replay_frame.pack(fill="x", padx=pad, pady=(0, gap))
        self.play_button = ctk.CTkButton(
            replay_frame, text="再生 (VOICEVOX)",
            command=lambda: self.play_test_audio("VOICEVOX"), **self._btn_kw,
        )
        self.play_button.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.play_gtts_button = ctk.CTkButton(
            replay_frame, text="再生 (gTTS)",
            command=lambda: self.play_test_audio("gTTS"), **self._btn_kw,
        )
        self.play_gtts_button.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.stop_clear_button = ctk.CTkButton(
            test_frame, text="再生停止とクリア",
            command=self.on_stop_and_clear_audio,
            **{**self._btn_kw, "fg_color": "transparent", "hover_color": self.COL_DANGER_HOVER,
               "text_color": self.COL_DANGER, "border_width": 1, "border_color": self.COL_DANGER},
        )
        self.stop_clear_button.pack(fill="x", padx=pad, pady=(0, 12))

        # ================= ステータスバーの中身 =================
        self.status_bar = ctk.CTkLabel(
            status_frame, textvariable=self.status_var, font=self.font_caption,
            text_color=self.COL_TEXT_MUTED, height=24, anchor="w",
        )
        self.status_bar.pack(fill="x", side="left", expand=True)

        version_label: ctk.CTkLabel = ctk.CTkLabel(
            status_frame, text=self.app_version, font=self.font_caption,
            text_color=self.COL_TEXT_MUTED, height=24, anchor="e",
        )
        version_label.pack(side="right", padx=(10, 0))

        self.language_dropdown = ctk.CTkComboBox(
            status_frame, variable=self.language_var, values=["English", "日本語"],
            width=118, height=28, command=self.on_language_change,
            **{k: v for k, v in self._combo_kw.items() if k != "height"},
        )
        self.language_dropdown.pack(side="right")
        self.language_var.set(self.language)

        self.update_ui_text()

    def _load_data_async(self) -> None:
        """非同期でデータを読み込む"""
        try:
            # オーディオデバイスの取得
            self.audio_devices = AudioPlayer.list_audio_devices()
            # UIの更新（メインスレッドで実行）
            self.after(0, self._update_ui_with_audio_devices)
        except Exception as e:
            # エラー表示
            self.after(
                0, lambda msg=f"{self.texts[self.language]['status_audio_device_error']}{str(e)}": self.status_var.set(msg))

        try:
            # VOICEVOX Engineからスピーカー情報を取得
            self.speakers_data = self.client.speakers()
            # UIの更新（メインスレッドで実行）
            self.after(0, self._update_ui_with_voicevox_speakers)
            self.after(0, lambda: self.status_var.set(self.texts[self.language]["status_voicevox_loaded"]))
        except Exception:
            # エラー表示
            self.after(
                0, lambda: self.status_var.set(self.texts[self.language]["status_voicevox_connection_error"]))
            self.after(0, self._disable_voicevox_ui)

    def _update_ui_with_audio_devices(self) -> None:
        """取得したオーディオデバイスデータでUIを更新する"""
        # ホストリストの作成
        host_names = list(set([device['host_name'] for device in self.audio_devices]))
        host_names = [self.texts[self.language]["host_all"]] + sorted(host_names)

        # ホストコンボボックスの更新
        self.host_dropdown.configure(values=host_names)
        self.host_dropdown_2.configure(values=host_names)

        # 初期ホスト選択
        if self.current_host is not None and self.current_host in host_names:
            self.host_var.set(self.current_host)
        else:
            self.host_var.set(self.texts[self.language]["host_all"])
            self.current_host = self.texts[self.language]["host_all"]

        if self.current_host_2 is not None and self.current_host_2 in host_names:
            self.host_var_2.set(self.current_host_2)
        else:
            self.host_var_2.set(self.texts[self.language]["host_all"])
            self.current_host_2 = self.texts[self.language]["host_all"]

        # デバイスリストを更新
        self._update_device_lists()
        self.status_var.set(self.texts[self.language]["status_audio_device_loaded"])

    def _update_ui_with_voicevox_speakers(self) -> None:
        """取得したVOICEVOXスピーカーデータでUIを更新する"""
        # キャラクターリストの更新
        self._update_character_list()
        # VOICEVOX UIを有効化
        self.character_dropdown.configure(state="readonly")
        self.style_dropdown.configure(state="readonly")
        self.play_button.configure(state="normal")

    def _disable_voicevox_ui(self) -> None:
        """VOICEVOX関連のUIを無効化する"""
        self.character_dropdown.configure(values=[self.texts[self.language]["status_voicevox_unavailable"]], state="disabled")
        self.style_dropdown.configure(values=[self.texts[self.language]["status_voicevox_unavailable"]], state="disabled")
        self.character_var.set(self.texts[self.language]["status_voicevox_unavailable"])
        self.style_var.set(self.texts[self.language]["status_voicevox_unavailable"])
        self.play_button.configure(state="disabled")
        # 翻訳前後のTTSエンジン選択でVOICEVOXが選択されていたらgTTSに変更する
        if self.source_tts_engine_var.get() == "VOICEVOX":
            self.source_tts_engine_var.set("gTTS")
            self.on_source_tts_engine_change("gTTS")
        if self.dest_tts_engine_var.get() == "VOICEVOX":
            self.dest_tts_engine_var.set("gTTS")
            self.on_dest_tts_engine_change("gTTS")

    def _update_device_lists(self) -> None:
        """選択されたホストに基づいてデバイスリストを更新"""
        # 第1デバイス用のデバイスリスト作成
        selected_host = self.host_var.get()
        if selected_host == self.texts[self.language]["host_all"]:
            filtered_devices = self.audio_devices
        else:
            filtered_devices = [device for device in self.audio_devices if device['host_name'] == selected_host]

        device_names: List[str] = [f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices]
        self.device_dropdown.configure(values=device_names)

        # 設定からデバイス選択を復元
        if self.current_device is not None:
            device_name: str = next((
                f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices if device['index'] == self.current_device), "")
            if device_name:
                self.device_var.set(device_name)
            elif device_names:
                self.device_var.set(device_names[0])
                self.on_device_change(device_names[0])
        elif device_names:
            self.device_var.set(device_names[0])
            self.on_device_change(device_names[0])

        # 第2デバイス用のデバイスリスト作成
        selected_host_2 = self.host_var_2.get()
        if selected_host_2 == self.texts[self.language]["host_all"]:
            filtered_devices_2 = self.audio_devices
        else:
            filtered_devices_2 = [device for device in self.audio_devices if device['host_name'] == selected_host_2]

        device_names_2: List[str] = [f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices_2]
        self.device_dropdown_2.configure(values=device_names_2)

        # 設定から第2デバイス選択を復元
        if self.current_device_2 is not None:
            device_name_2: str = next((
                f"{device['name']} (インデックス: {device['index']})" for device in filtered_devices_2 if device['index'] == self.current_device_2), "")
            if device_name_2:
                self.device_var_2.set(device_name_2)
            elif device_names_2:
                self.device_var_2.set(device_names_2[0])
                self.on_device_2_change(device_names_2[0])
        elif device_names_2:
            self.device_var_2.set(device_names_2[0])
            self.on_device_2_change(device_names_2[0])

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
                for style_info in speaker["styles"]:
                    if style_info["id"] == self.current_style:
                        self.character_var.set(speaker["name"])
                        self.select_character(speaker)
                        return
        # デフォルト選択（最初のキャラクター）
        elif self.speakers_data:
            self.character_var.set(self.speakers_data[0]["name"])
            self.select_character(self.speakers_data[0])

    def load_data(self) -> None:
        """VOICEVOXのスピーカーデータとオーディオデバイスを読み込む"""
        # ステータスの更新
        self.status_var.set(self.texts[self.language]["status_loading_data"])
        self.update()

        # スレッドで非同期に読み込む
        thread = threading.Thread(target=self._load_data_async, daemon=True)
        thread.start()

    def on_character_change(self, choice: str) -> None:
        """キャラクターコンボボックスで選択されたときの処理"""
        if not choice or not self.speakers_data:
            return

        # 選択されたキャラクター名からキャラクターデータを取得
        selected_speaker: Optional[Dict[str, Any]] = next(
            (s for s in self.speakers_data if s["name"] == choice), None)
        if selected_speaker:
            self.select_character(selected_speaker)
        self.save_config()

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
            for i, style_info in enumerate(speaker["styles"]):
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
        self.save_config()

    def on_style_change(self, choice: str) -> None:
        """スタイルが変更されたときの処理"""
        if not choice or not self.current_character:
            return

        # 選択されたスタイルからIDを取得
        try:
            id_match: Optional[re.Match[str]] = re.search(
                r'\(ID: (\d+)\)', choice)
            if id_match:
                style_id: int = int(id_match.group(1))
                self.current_style = style_id
            else:
                # 正規表現でIDが見つからない場合、キャラクターのスタイルから名前で検索
                style_name: str = choice.split(" (ID:"
                )[0] if " (ID:" in choice else choice
                for style_info in self.current_character["styles"]:
                    if style_info["name"] == style_name:
                        self.current_style = style_info["id"]
                        break
        except Exception as e:
            print(f"スタイル選択エラー: {str(e)}")
            # エラーが発生した場合でも、選択中のキャラクターの最初のスタイルを設定
            if self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]
        self.save_config()

    def on_source_tts_engine_change(self, choice: str) -> None:
        """翻訳前のTTSエンジンが変更されたときの処理"""
        self.source_tts_engine = choice
        self.save_config()

    def on_dest_tts_engine_change(self, choice: str) -> None:
        """翻訳後のTTSエンジンが変更されたときの処理"""
        self.dest_tts_engine = choice
        self.save_config()

    def on_play_source_change(self) -> None:
        """「翻訳前を再生」チェックボックスが変更されたときの処理"""
        self.play_source = self.play_source_var.get()
        self.save_config()

    def on_play_dest_change(self) -> None:
        """「翻訳後を再生」チェックボックスが変更されたときの処理"""
        self.play_dest = self.play_dest_var.get()
        self.save_config()

    def on_gtts_lang_change(self, choice: str) -> None:
        """gTTSの言語が変更されたときの処理"""
        self.gtts_lang = choice
        self.save_config()

    def on_host_change(self, choice: str) -> None:
        """ホストが変更されたときの処理"""
        self.current_host = choice
        self._update_device_lists()
        self.save_config()

    def on_host_2_change(self, choice: str) -> None:
        """第2ホストが変更されたときの処理"""
        self.current_host_2 = choice
        self._update_device_lists()
        self.save_config()

    def on_device_change(self, choice: str) -> None:
        """デバイスが変更されたときの処理"""
        if not choice:
            self.current_device = None
            self.save_config()
            return

        # 選択されたデバイスからインデックスを取得
        try:
            device_index: int = int(choice.split("インデックス: ")[1].rstrip(")"))
            self.current_device = device_index
        except (IndexError, ValueError):
            self.current_device = None
        self.save_config()

    def on_device_2_change(self, choice: str) -> None:
        """第2デバイスが変更されたときの処理"""
        if not choice:
            self.current_device_2 = None
            self.save_config()
            return
        # 選択されたデバイスからインデックスを取得
        try:
            device_index_2: int = int(choice.split("インデックス: ")[1].rstrip(")"))
            self.current_device_2 = device_index_2
        except (IndexError, ValueError) as e:
            print(f"第2デバイス選択エラー: {str(e)}")
            self.current_device_2 = None
        self.save_config()


    def on_speaker_2_enable_change(self) -> None:
        """第2スピーカー有効チェックボックスが変更されたときの処理"""
        if hasattr(self, 'speaker_2_enabled_var'):
            self.speaker_2_enabled = self.speaker_2_enabled_var.get()
        self.save_config()


    def on_volume_change(self, value: float) -> None:
        """スライダーで音量が変更されたときの処理"""
        self.volume = value
        # 音量表示を更新（パーセント表示）
        self.volume_value_var.set(f"{int(value * 100)}%")
        self.save_config()

    def on_speed_change(self, value: float) -> None:
        """スライダーで再生速度が変更されたときの処理"""
        self.speed = value
        self.speed_value_var.set(f"x{value:.2f}")
        self.save_config()

    def on_language_change(self, choice: str) -> None:
        """言語が変更されたときの処理"""
        old_lang_all_text = self.texts[self.language]["host_all"]
        self.language = choice
        new_lang_all_text = self.texts[self.language]["host_all"]

        # If the current host was "All", update it to the new language's "All"
        if self.current_host == old_lang_all_text:
            self.current_host = new_lang_all_text
            self.host_var.set(new_lang_all_text)

        if self.current_host_2 == old_lang_all_text:
            self.current_host_2 = new_lang_all_text
            self.host_var_2.set(new_lang_all_text)

        self.save_config()
        self.update_ui_text()

    def update_ui_text(self) -> None:
        """UIのテキストを現在の言語に更新する"""
        lang = self.language
        self.title(self.texts[lang]["app_title"])
        self.ws_label.configure(text=self.texts[lang]["websocket_server_url"])
        self.ws_token_label.configure(text=self.texts[lang]["websocket_token"])
        self.ws_button_var.set(self.texts[lang]["connect_websocket"] if not self.ws_connected else self.texts[lang]["disconnect_websocket"])
        self.ws_status_var.set(self.texts[lang]["websocket_status_disconnected"])
        self.device_label.configure(text=self.texts[lang]["output_device"])
        self.device_label_2.configure(text=self.texts[lang]["secondary_output_device"])
        self.speaker_2_enable_checkbox.configure(text=self.texts[lang]["enable_secondary_speaker"])
        self.voicevox_settings_label.configure(text=self.texts[lang]["voicevox_settings"])
        self.char_label.configure(text=self.texts[lang]["character_selection"])
        self.style_label_left.configure(text=self.texts[lang]["voice_style"])
        self.source_tts_label.configure(text=self.texts[lang]["source_tts_settings"])
        self.play_source_checkbox.configure(text=self.texts[lang]["play_source_text"])
        self.dest_tts_label.configure(text=self.texts[lang]["dest_tts_settings"])
        self.play_dest_checkbox.configure(text=self.texts[lang]["play_dest_text"])
        self.volume_label.configure(text=self.texts[lang]["volume"])
        self.speed_label.configure(text=self.texts[lang]["speed"])
        self.test_label.configure(text=self.texts[lang]["playback"])
        self.gtts_lang_label.configure(text=self.texts[lang]["gtts_language_for_test"])
        self.play_button.configure(text=self.texts[lang]["play_voicevox"])
        self.play_gtts_button.configure(text=self.texts[lang]["play_gtts"])
        self.stop_clear_button.configure(text=self.texts[lang]["stop_and_clear"])
        self.status_var.set(self.texts[lang]["status_ready"])

        # ホストリストの更新
        host_names = [self.texts[self.language]["host_all"]] + sorted(list(set([device['host_name'] for device in self.audio_devices])))
        self.host_dropdown.configure(values=host_names)
        self.host_dropdown_2.configure(values=host_names)

        self._update_device_lists()

    def _process_audio(self, audio_data: bytes, speaker_instance: Union[VoicevoxSpeaker, gTTSSpeaker], engine: str) -> None:
        """音量と再生速度を適用して音声を再生する"""
        if self.clear_audio_requested:
            return

        try:
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

            # 音量を適用
            if sample_width == 2:  # 16bit PCM
                fmt = f"{n_frames * n_channels}h"
                data = np.array(struct.unpack(fmt, raw_data))
                # 音量を適用
                data = (data * self.volume).astype(np.int16)
                # データをバイトに戻す
                modified_raw_data = struct.pack(fmt, *data)
            else:
                modified_raw_data = raw_data

            # gTTSの場合、再生速度を適用 (フレームレートを変更)
            if engine == "gTTS":
                new_frame_rate = int(frame_rate * self.speed)
            else:
                new_frame_rate = frame_rate

            # 新しいWAVファイルを作成
            with io.BytesIO() as out_buffer:
                with wave.open(out_buffer, 'wb') as out_wf:
                    out_wf.setnchannels(n_channels)
                    out_wf.setsampwidth(sample_width)
                    out_wf.setframerate(new_frame_rate)
                    out_wf.writeframes(modified_raw_data)

                # バッファからバイトデータを取得
                processed_audio_data = out_buffer.getvalue()

            # 修正したデータを再生
            speaker_instance.play_bytes(processed_audio_data)

        except Exception as e:
            print(f"音声処理エラー: {str(e)}")
            # エラーが発生した場合は元のデータをそのまま再生
            if speaker_instance:
                speaker_instance.player.play_wav_bytes(audio_data)

    def play_test_audio(self, engine: str) -> None:
        """テスト音声を再生"""
        if engine == "VOICEVOX":
            # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
            if not self.current_style and self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]
                style_name: str = self.current_character["styles"][0]["name"]
                self.status_var.set(f"{self.texts[self.language]['status_style_auto_selected']}{style_name}")
            elif not self.current_style:
                self.status_var.set(self.texts[self.language]["error_no_style_selected"])
                return

        text: str = self.test_text_var.get()
        if not text:
            self.status_var.set(self.texts[self.language]["error_no_text_input"])
            return

        # ステータスの更新
        self.status_var.set(self.texts[self.language]["status_synthesizing"])
        self.update()

        # スレッドで非同期に合成と再生
        thread: threading.Thread = threading.Thread(
            target=self._play_audio_async, args=(text, engine), daemon=True)
        thread.start()

    def _play_audio_async(self, text: str, engine: str, lang: Optional[str] = None) -> None:
        """非同期で音声合成と再生を行う"""
        self.playback_lock.acquire()
        try:
            if self.clear_audio_requested:
                self.clear_audio_requested = False
                self.status_var.set("オーディオクリアリクエスト受信済み。再生をキャンセルしました。")
                return

            self.active_speaker_instance = None # Reset before creation
            audio_player = AudioPlayer(
                output_device_index=self.current_device,
                output_device_index_2=self.current_device_2,
                speaker_2_enabled=self.speaker_2_enabled
            )

            audio_data = None
            speaker_instance = None

            if engine == "VOICEVOX":
                if self.current_style is None:
                    self.after(0, lambda: self.status_var.set(self.texts[self.language]["error_no_style_selected"]))
                    return
                
                temp_speaker = VoicevoxSpeaker(player=audio_player, client=self.client)
                audio_data = temp_speaker.get_audio_data(text, self.current_style, speed=self.speed)
                speaker_instance = temp_speaker

            elif engine == "gTTS":
                lang_code = lang
                if lang_code is None:
                    lang_name = self.gtts_lang
                    lang_code = self.gtts_supported_languages.get(lang_name, "en")

                temp_speaker = gTTSSpeaker(player=audio_player)
                audio_data = temp_speaker.get_audio_data(text, lang=lang_code)
                speaker_instance = temp_speaker

            if audio_data and speaker_instance:
                self.active_speaker_instance = speaker_instance
                self._process_audio(audio_data, self.active_speaker_instance, engine)

            if not self.clear_audio_requested:
                self.after(0, lambda: self.status_var.set(self.texts[self.language]["status_playback_complete"]))

        except Exception as e:
            # エラー表示
            if not self.clear_audio_requested:
                self.after(
                    0, lambda msg=f"{self.texts[self.language]['error_synthesis']}{str(e)}": self.status_var.set(msg))
        finally:
            self.playback_lock.release()
            self.active_speaker_instance = None

    def load_config(self) -> None:
        """設定ファイルから設定を読み込む"""
        config: Dict[str, Any] = Config.load()
        self.current_style = config.get("speaker_id")
        self.current_device = config.get("device_index")
        self.current_device_2 = config.get("device_index_2")
        self.speaker_2_enabled = config.get("speaker_2_enabled", False)
        self.current_host = config.get("host_name", "すべて")
        self.current_host_2 = config.get("host_name_2", "すべて")
        self.volume = config.get("volume", 0.8)  # デフォルトは0.8
        self.speed = config.get("speed", 1.0) # デフォルトは1.0
        self.ws_url = config.get("ws_url", "ws://127.0.0.1:2231")
        self.ws_token = config.get("ws_token", "")
        self.gtts_lang = config.get("gtts_lang", "English")
        self.source_tts_engine = config.get("source_tts_engine", "VOICEVOX")
        self.dest_tts_engine = config.get("dest_tts_engine", "gTTS")
        self.play_source = config.get("play_source", False)
        self.play_dest = config.get("play_dest", True)
        self.language = config.get("language", "English")

        # UI変数の設定
        self.gtts_lang_var.set(self.gtts_lang)
        self.source_tts_engine_var.set(self.source_tts_engine)
        self.dest_tts_engine_var.set(self.dest_tts_engine)
        self.play_source_var.set(self.play_source)
        self.play_dest_var.set(self.play_dest)
        self.language_var.set(self.language)

    def save_config(self) -> None:
        """現在の設定を保存""" 
        config_data: Dict[str, Any] = {
            "speaker_id": self.current_style,
            "device_index": self.current_device,
            "device_index_2": self.current_device_2,
            "speaker_2_enabled": self.speaker_2_enabled,
            "host_name": self.current_host,
            "host_name_2": self.current_host_2,
            "volume": self.volume,
            "speed": self.speed,
            "ws_url": self.ws_url_var.get(),
            "ws_token": self.ws_token_var.get(),
            "gtts_lang": self.gtts_lang,
            "source_tts_engine": self.source_tts_engine,
            "dest_tts_engine": self.dest_tts_engine,
            "play_source": self.play_source,
            "play_dest": self.play_dest,
            "language": self.language,
        }
        Config.save(config_data)
        self.ws_url = self.ws_url_var.get()
        self.ws_token = self.ws_token_var.get()
        self.status_var.set(self.texts[self.language]["config_saved"])

    def _build_ws_url(self) -> str:
        """接続用のWebSocket URLを組み立てる。

        VRCT側のトークン認証に対応するため、トークンが設定されていれば
        URLに ``?token=...`` を付与する。URLに既に token クエリが含まれる
        場合（VRCTの「WebSocket URL（クリックでコピー）」で取得した完全な
        URLを貼り付けたケース）は、そのURLをそのまま使う。
        """
        base_url = self.ws_url_var.get().strip() or "ws://127.0.0.1:2231"
        token = self.ws_token_var.get().strip()
        if not token:
            return base_url

        parts = urlsplit(base_url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        if any(key == "token" and value for key, value in query):
            return base_url

        query = [(key, value) for key, value in query if key != "token"]
        query.append(("token", token))
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

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
            self.status_var.set(f"{self.texts[self.language]['status_style_auto_selected']}{style_name}")
        elif not self.current_style:
            self.status_var.set(self.texts[self.language]["error_no_style_selected"])
            return

        # URLを取得
        self.ws_url = self.ws_url_var.get()
        if not self.ws_url:
            self.ws_url = "ws://127.0.0.1:2231"
            self.ws_url_var.set(self.ws_url)

        # トークン認証に対応: URL に ?token=... を付与した接続用URLを組み立てる
        connect_url = self._build_ws_url()

        # WebSocketイベントハンドラ
        def on_message(ws: websocket.WebSocketApp, message: str) -> None:
            try:
                data: Dict[str, Any] = json.loads(message)
                if data.get("type") not in ["SENT", "CHAT", "RECEIVED"]:
                    return

                if data.get("type") in ["SENT", "CHAT"]:
                    # 元言語が日本語の場合
                    if data.get("src_languages", {}).get("1", {}).get("language") == "Japanese":
                        source_message = data.get("message", "")
                        source_lang_name = "Japanese"
                        translations = data.get("translation", [])
                        dest_message = translations[0] if translations else ""
                        dest_lang_name = data.get("dst_languages", {}).get("1", {}).get("language", "English")
                    # 元言語が日本語以外の場合
                    else:
                        source_message = data.get("message", "")
                        source_lang_name = data.get("src_languages", {}).get("1", {}).get("language", "English")
                        dest_message = ""
                        dest_lang_name = "Japanese" # デフォルトの宛先は日本語
                        translations = data.get("translation", [])
                        dst_languages = data.get("dst_languages", {})
                        for i in range(1, 4):
                            lang_info = dst_languages.get(str(i), {})
                            if lang_info.get("language") == "Japanese" and len(translations) > i - 1:
                                dest_message = translations[i - 1]
                                break

                    # メッセージをデコード
                    source_message = html.unescape(source_message)
                    dest_message = html.unescape(dest_message)

                    self.after(0, lambda: self.status_var.set(
                        f"{self.texts[self.language]['status_received_message']}{source_message[:30]}... / {dest_message[:30]}..."))

                    # 音声合成と再生
                    thread = threading.Thread(
                        target=self._synthesize_and_play_from_ws,
                        args=(source_message, dest_message, source_lang_name, dest_lang_name),
                        daemon=True
                    )
                    thread.start()

            except json.JSONDecodeError:
                pass  # 無視
            except Exception as e:
                self.after(0, lambda msg=f"{self.texts[self.language]['error_message_processing']}{e}": self.status_var.set(msg))

        def on_error(ws: websocket.WebSocketApp, error: Exception) -> None:
            # VRCT のトークン認証に失敗すると、ハンドシェイク時に 403 が返る
            if "403" in str(error) or "Forbidden" in str(error):
                msg = self.texts[self.language]["error_ws_forbidden"]
            else:
                msg = f"WebSocketエラー: {error}"
            self.after(0, lambda: self.status_var.set(msg))

        def on_close(ws: websocket.WebSocketApp, close_status_code: Optional[int], close_msg: Optional[str]) -> None:
            self.ws_connected = False
            self.after(0, self._update_ws_status_disconnected)

        def on_open(ws: websocket.WebSocketApp) -> None:
            self.ws_connected = True
            self.after(0, self._update_ws_status_connected)

        # WebSocketクライアントの起動
        try:
            self.status_var.set(f"{self.texts[self.language]['status_ws_connecting']}{self.ws_url}")
            self.ws = websocket.WebSocketApp(
                connect_url,
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
            self.ws = None

    def _update_ws_status_connected(self) -> None:
        """WebSocket接続状態のUIを更新（接続時）"""
        self.ws_status_var.set(self.texts[self.language]["websocket_status_connected"])
        self.ws_status_label.configure(text_color=self.COL_SUCCESS)
        self.ws_button_var.set(self.texts[self.language]["disconnect_websocket"])
        self.ws_button.configure(
            fg_color=self.COL_DANGER, hover_color=self.COL_DANGER_HOVER)
        self.status_var.set(self.texts[self.language]["status_ws_connected"])

    def _update_ws_status_disconnected(self) -> None:
        """WebSocket接続状態のUIを更新（切断時）"""
        self.ws_status_var.set(self.texts[self.language]["websocket_status_disconnected"])
        self.ws_status_label.configure(text_color=self.COL_TEXT_MUTED)
        self.ws_button_var.set(self.texts[self.language]["connect_websocket"])
        self.ws_button.configure(
            fg_color=self.COL_SUCCESS, hover_color=self.COL_SUCCESS_HOVER)
        self.status_var.set(self.texts[self.language]["status_ws_disconnected"])

    def _synthesize_and_play_from_ws(self, source_text: str, dest_text: str, source_lang_name: str, dest_lang_name: str) -> None:
        """WebSocketから受け取ったテキストを音声合成して再生する"""
        # 翻訳前の再生
        if self.play_source and source_text:
            source_engine = self.source_tts_engine
            source_lang_code = "ja" if source_engine == "VOICEVOX" else self.gtts_supported_languages.get(source_lang_name)
            if source_lang_code:
                self._play_audio_async(source_text, source_engine, lang=source_lang_code)
            else:
                self.after(0, lambda: self.status_var.set(f"{self.texts[self.language]['error_gtts_unsupported_source']}{source_lang_name}"))

        # 翻訳後の再生
        if self.play_dest and dest_text:
            dest_engine = self.dest_tts_engine
            dest_lang_code = "ja" if dest_engine == "VOICEVOX" else self.gtts_supported_languages.get(dest_lang_name)
            if dest_lang_code:
                self._play_audio_async(dest_text, dest_engine, lang=dest_lang_code)
            else:
                self.after(0, lambda: self.status_var.set(f"{self.texts[self.language]['error_gtts_unsupported_dest']}{dest_lang_name}"))

    def _synthesize_and_play(self, text: str) -> None:
        """テキストを音声合成して再生する"""
        self.playback_lock.acquire()
        try:
            if self.clear_audio_requested:
                self.clear_audio_requested = False
                self.status_var.set("オーディオクリアリクエスト受信済み。再生をキャンセルしました。")
                return

            self.active_speaker_instance = None

            # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
            if not self.current_style and self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]
                style_name: str = self.current_character["styles"][0]["name"]
                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set(
                        f"{self.texts[self.language]['status_style_auto_selected']}{style_name}"))

            if self.current_style is None:
                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set(
                        self.texts[self.language]["error_no_style_selected"]))
                return

            # 音声合成用クエリを作成
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
                self._play_audio_with_volume(audio_data, self.active_speaker_instance)
            else:
                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set("エラー: 音声合成に失敗"))


        except Exception as e:
            if not self.clear_audio_requested:
                self.after(
                    0, lambda msg=f"{self.texts[self.language]['error_synthesis']}{str(e)}": self.status_var.set(msg))
        finally:
            self.playback_lock.release()
            self.active_speaker_instance = None

    def on_stop_and_clear_audio(self) -> None:
        self.status_var.set(self.texts[self.language]["status_stop_request_received"])
        self.update_idletasks()

        self.clear_audio_requested = True

        if self.active_speaker_instance:
            try:
                self.active_speaker_instance.request_stop()
                self.status_var.set(self.texts[self.language]["status_active_playback_stopped"])
            except Exception as e:
                self.status_var.set(f"{self.texts[self.language]['error_speaker_stop']}{e}")
        else:
            self.status_var.set(self.texts[self.language]["status_no_active_playback"])

    def on_closing(self) -> None:
        """アプリケーション終了時の処理"""
        # WebSocket接続を停止
        self.stop_websocket_connection()

        # アプリケーションを破棄
        self.destroy()


if __name__ == "__main__":
    app = VRCTTTSConnectorGUI()
    app.mainloop()
