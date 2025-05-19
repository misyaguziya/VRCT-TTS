#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VOICEVOX Connector GUI
CustomTkinterを使用したVOICEVOXの設定GUI
"""

import os
import threading
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

    def __init__(self):
        super().__init__()

        # アプリの設定
        self.title("VRCT VOICEVOX Connector")
        self.geometry("750x520")

        # ダークモードをデフォルトに設定
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # データ保存用の変数
        self.speakers_data = []
        self.audio_devices = []
        self.current_character = None
        self.current_style = None
        self.current_device = None
        self.ws_url = "ws://127.0.0.1:2231"

        # WebSocket関連の変数
        self.ws = None
        self.ws_thread = None
        self.ws_connected = False

        # 設定を読み込む
        self.load_config()

        # VOICEVOXクライアントの初期化
        self.client = VOICEVOXClient()

        # UIの作成
        self.create_ui()

        # データの読み込み
        self.load_data()

        # プロトコルハンドラー
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_ui(self):
        """UIコンポーネントの作成"""
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", padx=20, pady=20)

        # タイトルラベル
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="VRCT VOICEVOX Connector",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)

        # コンテンツフレーム
        content_frame = ctk.CTkFrame(self.main_frame)
        content_frame.pack(fill="both", padx=10, pady=10)

        # 左右に分割
        left_frame = ctk.CTkFrame(content_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # 左側: キャラクター選択
        right_frame = ctk.CTkFrame(content_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        char_label = ctk.CTkLabel(
            left_frame,
            text="キャラクター選択",
            font=ctk.CTkFont(size=14, weight="normal")
        )
        char_label.pack(anchor="w", padx=10, pady=5)

        # キャラクター選択のComboBox
        self.character_var = ctk.StringVar()
        self.character_dropdown = ctk.CTkComboBox(
            left_frame,
            variable=self.character_var,
            values=["キャラクターを読み込み中..."],
            width=300,
            state="readonly",
            command=self.on_character_change
        )
        self.character_dropdown.pack(fill="x", padx=10, pady=5)

        style_label_left = ctk.CTkLabel(left_frame, text="声のスタイル")
        style_label_left.pack(anchor="w", padx=10, pady=5)

        self.style_var = ctk.StringVar()
        self.style_dropdown = ctk.CTkComboBox(
            left_frame,
            variable=self.style_var,
            values=["スタイルを読み込み中..."],
            width=300,
            state="readonly",
            command=self.on_style_change
        )
        self.style_dropdown.pack(fill="x", padx=10, pady=5)

        # オーディオ出力デバイス選択
        device_label = ctk.CTkLabel(left_frame, text="出力デバイス")
        device_label.pack(anchor="w", padx=10, pady=5)

        self.device_var = ctk.StringVar()
        self.device_dropdown = ctk.CTkComboBox(
            left_frame,
            variable=self.device_var,
            values=["デバイスを読み込み中..."],
            width=300,
            state="readonly",
            command=self.on_device_change
        )
        self.device_dropdown.pack(fill="x", padx=10, pady=5)

        # WebSocket設定
        ws_frame = ctk.CTkFrame(right_frame)
        ws_frame.pack(fill="x", padx=10, pady=10)

        ws_label = ctk.CTkLabel(ws_frame, text="WebSocketサーバーURL:")
        ws_label.pack(anchor="w", padx=10, pady=5)

        self.ws_url_var = ctk.StringVar(value=self.ws_url)
        self.ws_entry = ctk.CTkEntry(
            ws_frame,
            width=300,
            textvariable=self.ws_url_var
        )
        self.ws_entry.pack(fill="x", padx=10, pady=5)

        # WebSocket接続ボタン
        self.ws_button_var = ctk.StringVar(value="WebSocket接続開始")
        self.ws_button = ctk.CTkButton(
            ws_frame,
            textvariable=self.ws_button_var,
            command=self.toggle_websocket_connection,
            fg_color="#1E5631",  # 接続時は緑色
            hover_color="#2E8B57"
        )
        self.ws_button.pack(pady=10)

        # WebSocket接続状態ラベル
        self.ws_status_var = ctk.StringVar(value="WebSocket: 未接続")
        self.ws_status_label = ctk.CTkLabel(
            ws_frame,
            textvariable=self.ws_status_var,
            text_color="gray"
        )
        self.ws_status_label.pack(pady=5)

        # テスト再生セクション
        test_frame = ctk.CTkFrame(right_frame)
        test_frame.pack(fill="x", padx=10, pady=10)

        test_label = ctk.CTkLabel(test_frame, text="テスト再生:")
        test_label.pack(anchor="w", padx=10, pady=5)

        self.test_text_var = ctk.StringVar(value="こんにちは、VOICEVOXです。")
        self.test_text_entry = ctk.CTkEntry(
            test_frame,
            width=300,
            textvariable=self.test_text_var
        )
        self.test_text_entry.pack(fill="x", padx=10, pady=5)

        self.play_button = ctk.CTkButton(
            test_frame,
            text="テスト再生",
            command=self.play_test_audio
        )
        self.play_button.pack(pady=10)

        # ステータスバー
        self.status_var = ctk.StringVar(value="準備完了")
        self.status_bar = ctk.CTkLabel(
            self.main_frame,
            textvariable=self.status_var,
            height=25,
            anchor="w"
        )
        self.status_bar.pack(fill="x", side="bottom", padx=10)

        # 保存ボタン
        self.save_button = ctk.CTkButton(
            self.main_frame,
            text="設定を保存",
            command=self.save_config
        )
        self.save_button.pack(pady=10)

    def load_data(self):
        """VOICEVOXのスピーカーデータとオーディオデバイスを読み込む"""
        # ステータスの更新
        self.status_var.set("データを読み込み中...")
        self.update()

        # スレッドで非同期に読み込む
        thread = threading.Thread(target=self._load_data_async, daemon=True)
        thread.start()

    def _load_data_async(self):
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
            self.after(0, lambda msg=f"エラー: {str(e)}": self.status_var.set(msg))
            if "speakers_data" not in dir(self) or not self.speakers_data:
                self.after(0, lambda: self.status_var.set("VOICEVOX Engineに接続できません。起動しているか確認してください。"))

    def _update_ui_with_data(self):
        """取得したデータでUIを更新する"""
        # オーディオデバイスリストの更新
        device_names = ["デフォルト"] + [f"{device['name']} (インデックス: {device['index']})" for device in self.audio_devices]
        self.device_dropdown.configure(values=device_names)

        # 設定からデバイス選択を復元
        if self.current_device is not None:
            device_name = next((
                f"{device['name']} (インデックス: {device['index']})" for device in self.audio_devices if device['index'] == self.current_device), "デフォルト")
            self.device_var.set(device_name)
        else:
            self.device_var.set("デフォルト")

        # キャラクターリストの更新
        self._update_character_list()

        # ステータスの更新
        self.status_var.set("データの読み込みが完了しました")

    def _update_character_list(self):
        """キャラクターリストを更新"""
        # キャラクター名のリストを作成
        character_names = [speaker["name"] for speaker in self.speakers_data]
        self.character_dropdown.configure(values=character_names)

        # 設定から選択されたキャラクターを復元
        if self.current_style is not None:
            for speaker in self.speakers_data:
                for style in speaker["styles"]:
                    if style["id"] == self.current_style:
                        self.character_var.set(speaker["name"])
                        self.select_character(speaker)
                        break
        # デフォルト選択（最初のキャラクター）
        elif self.speakers_data:
            self.character_var.set(self.speakers_data[0]["name"])
            self.select_character(self.speakers_data[0])

    def on_character_change(self, choice):
        """キャラクターコンボボックスで選択されたときの処理"""
        if not choice or not self.speakers_data:
            return

        # 選択されたキャラクター名からキャラクターデータを取得
        selected_speaker = next((s for s in self.speakers_data if s["name"] == choice), None)
        if selected_speaker:
            self.select_character(selected_speaker)

    def select_character(self, speaker):
        """キャラクターを選択したときの処理"""
        self.current_character = speaker

        # スタイルドロップダウンの更新
        style_values = [f"{style['name']} (ID: {style['id']})" for style in speaker["styles"]]
        self.style_dropdown.configure(values=style_values)

        # 設定から選択されたスタイルを復元するか、最初のスタイルを選択
        if self.current_style is not None:
            style_found = False
            for i, style in enumerate(speaker["styles"]):
                if style["id"] == self.current_style:
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
            
    def on_style_change(self, choice):
        """スタイルが変更されたときの処理"""
        if not choice or not self.current_character:
            return

        try:
            # 選択されたスタイルからIDを取得
            import re
            id_match = re.search(r'\(ID: (\d+)\)', choice)
            if id_match:
                style_id = int(id_match.group(1))
                self.current_style = style_id
            else:
                # 正規表現でIDが見つからない場合、キャラクターのスタイルから名前で検索
                style_name = choice.split(" (ID:")[0] if " (ID:" in choice else choice
                for style in self.current_character["styles"]:
                    if style["name"] == style_name:
                        self.current_style = style["id"]
                        break
        except Exception as e:
            print(f"スタイル選択エラー: {str(e)}")
            # エラーが発生した場合でも、選択中のキャラクターの最初のスタイルを設定
            if self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]

    def on_device_change(self, choice):
        """デバイスが変更されたときの処理"""
        if not choice or choice == "デフォルト":
            self.current_device = None
            return

        # 選択されたデバイスからインデックスを取得
        device_index = int(choice.split("インデックス: ")[1].rstrip(")"))
        self.current_device = device_index

    def play_test_audio(self):
        """テスト音声を再生"""
        # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
        if not self.current_style and self.current_character and self.current_character["styles"]:
            self.current_style = self.current_character["styles"][0]["id"]
            style_name = self.current_character["styles"][0]["name"]
            self.status_var.set(f"スタイルが自動選択されました: {style_name}")
        elif not self.current_style:
            self.status_var.set("エラー: スタイルが選択されていません")
            return

        text = self.test_text_var.get()
        if not text:
            self.status_var.set("エラー: テキストが入力されていません")
            return

        # ステータスの更新
        self.status_var.set("音声を合成中...")
        self.update()

        # スレッドで非同期に合成と再生
        thread = threading.Thread(target=self._play_audio_async, args=(text,), daemon=True)
        thread.start()

    def _play_audio_async(self, text):
        """非同期で音声合成と再生を行う"""
        try:
            # 音声合成用クエリを作成
            query = self.client.audio_query(text, self.current_style)

            # 音声を合成
            audio_data = self.client.synthesis(query, self.current_style)

            # 音声を再生
            speaker = VoicevoxSpeaker(output_device_index=self.current_device)
            speaker.play_bytes(audio_data)

            # ステータスの更新
            self.after(0, lambda: self.status_var.set("再生完了"))

        except Exception as e:
            # エラー表示
            self.after(0, lambda msg=f"エラー: {str(e)}": self.status_var.set(msg))

    def load_config(self):
        """設定ファイルから設定を読み込む"""
        config = Config.load()
        self.current_style = config.get("speaker_id")
        self.current_device = config.get("device_index")
        self.ws_url = config.get("ws_url", "ws://127.0.0.1:2231")

    def save_config(self):
        """現在の設定を保存"""
        config_data = {
            "speaker_id": self.current_style,
            "device_index": self.current_device,
            "ws_url": self.ws_url_var.get()
        }
        Config.save(config_data)
        self.ws_url = self.ws_url_var.get()
        self.status_var.set("設定を保存しました")

    def toggle_websocket_connection(self):
        """WebSocket接続の開始/停止を切り替える"""
        if not self.ws_connected:
            self.start_websocket_connection()
        else:
            self.stop_websocket_connection()

    def start_websocket_connection(self):
        """WebSocket接続を開始する"""
        # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
        if not self.current_style and self.current_character and self.current_character["styles"]:
            self.current_style = self.current_character["styles"][0]["id"]
            style_name = self.current_character["styles"][0]["name"]
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
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get("type") == "SENT" or data.get("type") == "CHAT":
                    received_message = data.get("message", "")

                    # エスケープされた日本語文字列をデコード
                    decoded_message = html.unescape(received_message)
                    self.after(0, lambda: self.status_var.set(f"受信: {decoded_message[:30]}..."))

                    # 音声合成してスレッドで再生
                    thread = threading.Thread(target=self._synthesize_and_play, args=(decoded_message,), daemon=True)
                    thread.start()
            except json.JSONDecodeError:
                pass
            except Exception as e:
                self.after(0, lambda msg=f"メッセージ処理エラー: {str(e)}": self.status_var.set(msg))

        def on_error(ws, error):
            self.after(0, lambda: self.status_var.set(f"WebSocketエラー: {error}"))

        def on_close(ws, close_status_code, close_msg):
            self.ws_connected = False
            self.after(0, self._update_ws_status_disconnected)

        def on_open(ws):
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
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()

        except Exception as e:
            self.status_var.set(f"WebSocket接続エラー: {str(e)}")

    def stop_websocket_connection(self):
        """WebSocket接続を停止する"""
        if self.ws:
            self.ws.close()
            self.ws = None

    def _update_ws_status_connected(self):
        """WebSocket接続状態のUIを更新（接続時）"""
        self.ws_status_var.set("WebSocket: 接続済み")
        self.ws_status_label.configure(text_color="#4CAF50")  # 緑色
        self.ws_button_var.set("WebSocket接続停止")
        self.ws_button.configure(fg_color="#8B0000", hover_color="#B22222")  # 赤色
        self.status_var.set("WebSocketサーバーに接続しました")

    def _update_ws_status_disconnected(self):
        """WebSocket接続状態のUIを更新（切断時）"""
        self.ws_status_var.set("WebSocket: 未接続")
        self.ws_status_label.configure(text_color="gray")
        self.ws_button_var.set("WebSocket接続開始")
        self.ws_button.configure(fg_color="#1E5631", hover_color="#2E8B57")  # 緑色
        self.status_var.set("WebSocket接続を終了しました")

    def _synthesize_and_play(self, text):
        """テキストを音声合成して再生する"""
        try:
            # スタイルIDが設定されているか確認し、されていない場合は現在のキャラクターの最初のスタイルを選択
            if not self.current_style and self.current_character and self.current_character["styles"]:
                self.current_style = self.current_character["styles"][0]["id"]
                style_name = self.current_character["styles"][0]["name"]
                self.after(0, lambda: self.status_var.set(f"スタイルが自動選択されました: {style_name}"))

            if not self.current_style:
                self.after(0, lambda: self.status_var.set("エラー: スタイルが選択されていません"))
                return

            # 音声合成用クエリを作成
            query = self.client.audio_query(text, self.current_style)

            # 音声を合成
            audio_data = self.client.synthesis(query, self.current_style)

            # 音声を再生
            speaker = VoicevoxSpeaker(output_device_index=self.current_device)
            speaker.play_bytes(audio_data)

        except Exception as e:
            self.after(0, lambda msg=f"音声合成エラー: {str(e)}": self.status_var.set(msg))

    def on_closing(self):
        """アプリケーション終了時の処理"""
        # WebSocket接続を停止
        self.stop_websocket_connection()

        # アプリケーションを破棄
        self.destroy()


if __name__ == "__main__":
    app = VoicevoxConnectorGUI()
    app.mainloop()
