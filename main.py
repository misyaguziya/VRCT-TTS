#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VRCT TTS Connector GUI
Now supports multiple TTS engines (gTTS, VOICEVOX).
Handles MP3 and WAV playback for test audio.
"""

import os
import sys
import threading
import ctypes
import customtkinter as ctk
from typing import Dict, List, Optional, Any
import json
import html
import logging
import io
from playsound import playsound # For MP3 playback
import asyncio
import websockets # For WebSocket server
import numpy as np # For WAV volume processing
import wave # For WAV processing
import struct # For WAV processing


from voicevox_speaker import VoicevoxSpeaker # For WAV playback and device listing
from config import Config
from tts_engine import TTSEngine, GTTSEngine, VoicevoxEngine, TTSSynthesisError, VOICEVOX_AVAILABLE
from tts_engine import GTTS_TLD_OPTIONS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vrct_connector_main.log", mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VoicevoxConnectorGUI(ctk.CTk):
    """VRCT TTS Connector GUI Application"""

    def __init__(self) -> None:
        super().__init__()
        
        self.app_version = "v1.2.1" # Version update for playback changes

        if getattr(sys, 'frozen', False):
            self.app_path = os.path.dirname(sys.executable)
        else:
            self.app_path = os.path.dirname(os.path.abspath(__file__))

        fonts_path: str = os.path.join(self.app_path, "fonts", "NotoSansJP-VariableFont_wght.ttf")
        if os.path.exists(fonts_path):
            try:
                ctypes.windll.gdi32.AddFontResourceW(str(fonts_path))
                self.fonts_name = "Noto Sans JP"
            except OSError as e:
                logger.error(f"Failed to load font: {e}. Using system default.")
                self.fonts_name = "System"
        else:
            logger.warning(f"Font file not found at {fonts_path}. Using system default.")
            self.fonts_name = "System"

        self.font_normal_14: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=14, weight="normal")
        self.font_normal_12: ctk.CTkFont = ctk.CTkFont(family=self.fonts_name, size=12, weight="normal")

        self.title("VRCT TTS Connector")
        self.geometry("770x750")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.audio_devices: List[Dict[str, Any]] = []
        self.current_device_index: Optional[int] = None # Stores numerical index for PyAudio
        self.current_device_index_2: Optional[int] = None
        self.speaker_2_enabled: bool = False
        self.current_host: Optional[str] = None
        self.current_host_2: Optional[str] = None
        self.volume: float = 0.8
        self.ws_url: str = "ws://127.0.0.1:8765"

        # UI Variables
        self.device_var = ctk.StringVar()
        self.device_var_2 = ctk.StringVar()
        self.speaker_2_enabled_var = ctk.BooleanVar(value=False)
        self.host_var = ctk.StringVar()
        self.host_var_2 = ctk.StringVar()
        self.volume_value_var = ctk.StringVar()
        self.ws_url_var = ctk.StringVar()
        self.ws_button_var = ctk.StringVar()
        self.ws_status_var = ctk.StringVar()
        self.test_text_var = ctk.StringVar()
        self.status_var = ctk.StringVar()

        self.ws_server_thread: Optional[threading.Thread] = None
        self.ws_server: Optional[Any] = None
        self.ws_clients: Dict[Any, Any] = {}
        self.is_server_running: bool = False

        logger.info("Initializing TTS Engines...")
        self.gtts_engine = GTTSEngine()
        logger.info("GTTSEngine instance created.")
        self.voicevox_engine = VoicevoxEngine()
        if VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None:
            logger.info("VoicevoxEngine instance created successfully.")
        else:
            logger.warning("VoicevoxEngine could not be fully initialized.")

        # Audio Player for VOICEVOX WAVs (and device listing)
        self.voicevox_audio_player: Optional[VoicevoxSpeaker] = None
        try:
            self.voicevox_audio_player = VoicevoxSpeaker()
            logger.info("VoicevoxSpeaker instance for audio playback/device listing created.")
        except Exception as e:
            logger.error(f"Failed to initialize VoicevoxSpeaker for playback/device listing: {e}")
            # App can continue, but Voicevox playback via VoicevoxSpeaker and device listing will be affected.

        self.default_tts_language = "en"
        self.default_gtts_tld = "com"
        self.default_voicevox_speaker_id = 3

        self.current_tts_engine_name = "gTTS"
        self.selected_engine_var = ctk.StringVar(value=self.current_tts_engine_name)

        self.gtts_selected_language = self.default_tts_language
        self.gtts_language_var = ctk.StringVar(value=self.gtts_selected_language)
        self.gtts_selected_tld_code = self.default_gtts_tld
        self.gtts_tld_display_var = ctk.StringVar(value=f"{GTTS_TLD_OPTIONS.get(self.default_gtts_tld, 'Default (com)')} ({self.default_gtts_tld})")

        self.voicevox_characters: List[str] = []
        self.voicevox_styles: List[str] = []
        self.voicevox_character_var = ctk.StringVar()
        self.voicevox_style_var = ctk.StringVar()
        self.voicevox_selected_speaker_name: Optional[str] = None
        self.voicevox_selected_style_id: Optional[int] = self.default_voicevox_speaker_id

        self.tts_cache: Dict[tuple, bytes] = {}
        self.tts_cache_order: list[tuple] = []
        self.MAX_CACHE_SIZE = 50

        self.playback_lock = threading.Lock()
        self.clear_audio_requested: bool = False

        self.config = {}
        self.load_config()

        self.create_ui()
        self.update_voice_options_for_active_engine()

        self.load_data()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_ui(self) -> None:
        logger.info("Creating UI...")
        self.volume_value_var.set(f"{int(self.volume * 100)}%")
        self.ws_url_var.set(self.ws_url)
        self.ws_button_var.set("Start WebSocket Server")
        self.ws_status_var.set("WebSocket Server: Stopped")
        self.test_text_var.set("Hello, this is a test.")
        self.status_var.set(f"Ready. Active Engine: {self.current_tts_engine_name}")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ws_control_frame = ctk.CTkFrame(self.main_frame)
        ws_control_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(ws_control_frame, text="WebSocket Server URL:", font=self.font_normal_14).pack(side="left", padx=5)
        ctk.CTkEntry(ws_control_frame, textvariable=self.ws_url_var, font=self.font_normal_14, width=250).pack(side="left", expand=True, fill="x", padx=5)
        self.ws_button = ctk.CTkButton(ws_control_frame, textvariable=self.ws_button_var, font=self.font_normal_14, command=self.toggle_websocket_connection)
        self.ws_button.pack(side="left", padx=5)
        self.ws_status_label = ctk.CTkLabel(ws_control_frame, textvariable=self.ws_status_var, font=self.font_normal_12, text_color="gray")
        self.ws_status_label.pack(side="left", padx=5)
        self._update_ws_status_disconnected()

        engine_frame = ctk.CTkFrame(self.main_frame)
        engine_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(engine_frame, text="TTS Engine:", font=self.font_normal_14).pack(side="left", padx=5)
        
        self.gtts_radio = ctk.CTkRadioButton(engine_frame, text="gTTS", variable=self.selected_engine_var, value="gTTS", command=self.on_engine_selected, font=self.font_normal_14)
        self.gtts_radio.pack(side="left", padx=5)
        
        vv_radio_state = "normal" if (VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None) else "disabled"
        self.voicevox_radio = ctk.CTkRadioButton(engine_frame, text="VOICEVOX", variable=self.selected_engine_var, value="VOICEVOX", command=self.on_engine_selected, font=self.font_normal_14, state=vv_radio_state)
        self.voicevox_radio.pack(side="left", padx=5)
        
        self.dynamic_tts_options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.dynamic_tts_options_frame.pack(fill="x", padx=5, pady=0)

        self.gtts_settings_frame = ctk.CTkFrame(self.dynamic_tts_options_frame, fg_color="transparent")
        ctk.CTkLabel(self.gtts_settings_frame, text="Language:", font=self.font_normal_14).pack(side="left", padx=5)
        self.gtts_language_menu = ctk.CTkOptionMenu(self.gtts_settings_frame, variable=self.gtts_language_var, values=["en"], font=self.font_normal_14, command=self.on_gtts_setting_changed)
        self.gtts_language_menu.pack(side="left", padx=5)
        ctk.CTkLabel(self.gtts_settings_frame, text="Region/Accent (TLD):", font=self.font_normal_14).pack(side="left", padx=5)
        self.gtts_tld_menu = ctk.CTkOptionMenu(self.gtts_settings_frame, variable=self.gtts_tld_display_var, values=["com"], font=self.font_normal_14, command=self.on_gtts_setting_changed)
        self.gtts_tld_menu.pack(side="left", padx=5)

        self.voicevox_settings_frame = ctk.CTkFrame(self.dynamic_tts_options_frame, fg_color="transparent")
        ctk.CTkLabel(self.voicevox_settings_frame, text="Character:", font=self.font_normal_14).pack(side="left", padx=5)
        self.voicevox_character_menu = ctk.CTkOptionMenu(self.voicevox_settings_frame, variable=self.voicevox_character_var, values=["N/A"], font=self.font_normal_14, command=self.on_voicevox_character_selected)
        self.voicevox_character_menu.pack(side="left", padx=5)
        ctk.CTkLabel(self.voicevox_settings_frame, text="Style:", font=self.font_normal_14).pack(side="left", padx=5)
        self.voicevox_style_menu = ctk.CTkOptionMenu(self.voicevox_settings_frame, variable=self.voicevox_style_var, values=["N/A"], font=self.font_normal_14, command=self.on_voicevox_style_selected)
        self.voicevox_style_menu.pack(side="left", padx=5)

        common_settings_frame = ctk.CTkFrame(self.main_frame)
        common_settings_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(common_settings_frame, text="Output Device:", font=self.font_normal_14).pack(side="left", padx=5)
        self.device_dropdown = ctk.CTkComboBox(common_settings_frame, variable=self.device_var, values=["Default"], font=self.font_normal_12, width=200, state="readonly", command=self.on_device_change)
        self.device_dropdown.pack(side="left", padx=5)
        ctk.CTkLabel(common_settings_frame, text="Volume:", font=self.font_normal_14).pack(side="left", padx=5)
        self.volume_slider = ctk.CTkSlider(common_settings_frame, from_=0, to=1.0, number_of_steps=20, command=self.on_volume_change)
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(side="left", padx=5)
        ctk.CTkLabel(common_settings_frame, textvariable=self.volume_value_var, font=self.font_normal_14, width=40).pack(side="left", padx=5)

        test_frame = ctk.CTkFrame(self.main_frame)
        test_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(test_frame, text="Test Text:", font=self.font_normal_14).pack(side="left", padx=5)
        ctk.CTkEntry(test_frame, textvariable=self.test_text_var, font=self.font_normal_14, width=300).pack(side="left", expand=True, fill="x", padx=5)
        ctk.CTkButton(test_frame, text="Play Test Audio", command=self.play_test_audio, font=self.font_normal_14).pack(side="left", padx=5)
        ctk.CTkButton(test_frame, text="Stop/Clear", command=self.on_stop_and_clear_audio, font=self.font_normal_14, fg_color="#B22222", hover_color="#8B0000").pack(side="left", padx=5)

        bottom_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", side="bottom", padx=5, pady=5)
        self.status_bar = ctk.CTkLabel(bottom_frame, textvariable=self.status_var, font=self.font_normal_12, height=25, anchor="w")
        self.status_bar.pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(bottom_frame, text="Save Settings", command=self.save_config, font=self.font_normal_14).pack(side="right", padx=5)
        ctk.CTkLabel(bottom_frame, text=self.app_version, font=self.font_normal_12, height=25, anchor="e").pack(side="right", padx=5)

        logger.info("UI creation complete.")

    def load_data(self) -> None:
        self.status_var.set("Loading audio devices...")
        self.update()
        thread = threading.Thread(target=self._load_data_async, daemon=True)
        thread.start()

    def _load_data_async(self) -> None:
        try:
            if self.voicevox_audio_player:
                 self.audio_devices = self.voicevox_audio_player.list_audio_devices()
                 logger.info("Audio devices loaded.")
            else:
                logger.warning("VoicevoxSpeaker not initialized, cannot load audio devices.")
                self.audio_devices = []
            self.after(0, self._update_ui_with_data)
        except Exception as e:
            logger.exception("Error loading audio devices.")
            self.after(0, lambda: self.status_var.set(f"Error loading audio devices: {e}"))

    def _update_ui_with_data(self) -> None:
        host_names = ["Default Host"]
        if self.audio_devices:
             host_names_from_devices = list(set(d.get('host_name', 'Default Host') for d in self.audio_devices if d)) # Filter out None
             if host_names_from_devices:
                host_names = ["All Hosts"] + sorted(host_names_from_devices)
        
        self.host_dropdown.configure(values=host_names)
        self.host_dropdown_2.configure(values=host_names)
        
        if not self.host_var.get() and host_names: self.host_var.set(host_names[0])
        if not self.host_var_2.get() and host_names: self.host_var_2.set(host_names[0])

        self._update_device_lists()
        self.status_var.set(f"Ready. Active Engine: {self.current_tts_engine_name}")

    def _update_device_lists(self) -> None:
        device_names = ["Default Output Device"]
        if self.audio_devices:
            device_names.extend([f"{d['name']} (Index: {d['index']})" for d in self.audio_devices if d]) # Filter out None
        
        self.device_dropdown.configure(values=device_names)
        self.device_dropdown_2.configure(values=device_names)

        # Restore saved device or set to default
        dev_idx_str = f" (Index: {self.current_device_index})"
        found_dev = next((d_name for d_name in device_names if dev_idx_str in d_name), None)
        if self.current_device_index is not None and found_dev: self.device_var.set(found_dev)
        else: self.device_var.set(device_names[0])

        dev_idx_2_str = f" (Index: {self.current_device_index_2})"
        found_dev_2 = next((d_name for d_name in device_names if dev_idx_2_str in d_name), None)
        if self.current_device_index_2 is not None and found_dev_2: self.device_var_2.set(found_dev_2)
        else: self.device_var_2.set(device_names[0])

        self.speaker_2_enabled_var.set(self.speaker_2_enabled)

    def get_active_engine(self) -> Optional[TTSEngine]:
        engine_name = self.selected_engine_var.get()
        if engine_name == "VOICEVOX":
            if VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None:
                logger.debug("Returning VoicevoxEngine as active engine.")
                return self.voicevox_engine
            else:
                logger.error("VOICEVOX engine selected but not available/initialized. Falling back to gTTS.")
                self.selected_engine_var.set("gTTS")
                self.current_tts_engine_name = "gTTS"
                return self.gtts_engine
        elif engine_name == "gTTS":
            logger.debug("Returning GTTSEngine as active engine.")
            return self.gtts_engine
        else:
            logger.warning(f"Unknown TTS engine name: {engine_name}. Defaulting to gTTS.")
            self.selected_engine_var.set("gTTS")
            self.current_tts_engine_name = "gTTS"
            return self.gtts_engine

    def on_engine_selected(self, selected_engine_name: Optional[str] = None):
        if selected_engine_name is None:
             selected_engine_name = self.selected_engine_var.get()

        self.current_tts_engine_name = selected_engine_name
        logger.info(f"TTS Engine selected: {self.current_tts_engine_name}")
        self.status_var.set(f"Active engine: {self.current_tts_engine_name}")
        self._update_dynamic_ui_elements()

    def _update_dynamic_ui_elements(self):
        active_engine_name = self.current_tts_engine_name
        logger.info(f"Updating dynamic UI for engine: {active_engine_name}")

        if active_engine_name == "gTTS":
            self.gtts_settings_frame.pack(fill="x", padx=5, pady=2)
            self.voicevox_settings_frame.pack_forget()

            langs = self.gtts_engine.get_available_languages()
            self.gtts_language_menu.configure(values=langs)
            if self.gtts_selected_language in langs:
                self.gtts_language_var.set(self.gtts_selected_language)
            elif langs:
                self.gtts_language_var.set(langs[0])
                self.gtts_selected_language = langs[0]

            tld_display_names = [f"{desc} ({code})" for code, desc in GTTS_TLD_OPTIONS.items()]
            self.gtts_tld_menu.configure(values=tld_display_names)
            current_tld_display = f"{GTTS_TLD_OPTIONS.get(self.gtts_selected_tld_code, 'Default (com)')} ({self.gtts_selected_tld_code})"
            if current_tld_display in tld_display_names:
                self.gtts_tld_display_var.set(current_tld_display)
            elif tld_display_names:
                self.gtts_tld_display_var.set(tld_display_names[0])
                try: self.gtts_selected_tld_code = tld_display_names[0].split('(')[-1][:-1]
                except: self.gtts_selected_tld_code = self.default_gtts_tld

        elif active_engine_name == "VOICEVOX":
            self.voicevox_settings_frame.pack(fill="x", padx=5, pady=2)
            self.gtts_settings_frame.pack_forget()

            if VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None:
                vv_speakers_data = self.voicevox_engine.get_voicevox_speakers()
                if vv_speakers_data:
                    self.voicevox_characters = sorted(list(set(s['name'] for s in vv_speakers_data)))
                    self.voicevox_character_menu.configure(values=self.voicevox_characters)
                    if self.voicevox_selected_speaker_name in self.voicevox_characters:
                        self.voicevox_character_var.set(self.voicevox_selected_speaker_name)
                    elif self.voicevox_characters:
                        self.voicevox_character_var.set(self.voicevox_characters[0])
                        self.voicevox_selected_speaker_name = self.voicevox_characters[0]
                    self._update_voicevox_styles_dropdown()
                else:
                    self.voicevox_character_menu.configure(values=["No Speakers Found"])
                    self.voicevox_style_menu.configure(values=["N/A"])
            else:
                self.voicevox_character_menu.configure(values=["VOICEVOX N/A"])
                self.voicevox_style_menu.configure(values=["N/A"])
        else:
            self.gtts_settings_frame.pack_forget()
            self.voicevox_settings_frame.pack_forget()
        logger.info("Dynamic UI elements updated.")

    def _update_voicevox_styles_dropdown(self):
        if not (VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None and self.current_tts_engine_name == "VOICEVOX"):
            self.voicevox_style_menu.configure(values=["N/A"])
            return

        selected_char_name = self.voicevox_character_var.get()
        speakers_data = self.voicevox_engine.get_voicevox_speakers()

        styles_for_char = []
        for speaker in speakers_data:
            if speaker['name'] == selected_char_name:
                styles_for_char = speaker.get('styles', [])
                break

        self.voicevox_styles = [f"{s['name']} ({s['id']})" for s in styles_for_char]
        self.voicevox_style_menu.configure(values=self.voicevox_styles)

        current_style_display = ""
        for style_display in self.voicevox_styles:
            if f"({self.voicevox_selected_style_id})" in style_display:
                current_style_display = style_display
                break

        if current_style_display in self.voicevox_styles:
            self.voicevox_style_var.set(current_style_display)
        elif self.voicevox_styles:
            self.voicevox_style_var.set(self.voicevox_styles[0])
            try: self.voicevox_selected_style_id = int(self.voicevox_styles[0].split('(')[-1][:-1])
            except: self.voicevox_selected_style_id = self.default_voicevox_speaker_id
        else:
            self.voicevox_style_var.set("N/A")
            self.voicevox_selected_style_id = self.default_voicevox_speaker_id

    def on_gtts_setting_changed(self, choice: Optional[str] = None):
        self.gtts_selected_language = self.gtts_language_var.get()
        tld_display_name = self.gtts_tld_display_var.get()
        if tld_display_name and "(" in tld_display_name and tld_display_name.endswith(")"):
            try: self.gtts_selected_tld_code = tld_display_name.split('(')[-1][:-1]
            except: self.gtts_selected_tld_code = self.default_gtts_tld
        else: self.gtts_selected_tld_code = self.default_gtts_tld
        logger.info(f"gTTS settings changed: Lang='{self.gtts_selected_language}', TLD='{self.gtts_selected_tld_code}'")

    def on_voicevox_character_selected(self, choice: Optional[str] = None):
        self.voicevox_selected_speaker_name = self.voicevox_character_var.get()
        logger.info(f"VOICEVOX character selected: {self.voicevox_selected_speaker_name}")
        self._update_voicevox_styles_dropdown()

    def on_voicevox_style_selected(self, choice: Optional[str] = None):
        style_display_name = self.voicevox_style_var.get()
        if style_display_name and "(" in style_display_name and style_display_name.endswith(")"):
            try: self.voicevox_selected_style_id = int(style_display_name.split('(')[-1][:-1])
            except: self.voicevox_selected_style_id = self.default_voicevox_speaker_id
        else: self.voicevox_selected_style_id = self.default_voicevox_speaker_id
        logger.info(f"VOICEVOX style ID selected: {self.voicevox_selected_style_id}")

    def on_character_change(self, choice: str) -> None:
        active_engine_name = self.selected_engine_var.get()
        if active_engine_name == "gTTS":
            self.on_gtts_setting_changed(choice)
        elif active_engine_name == "VOICEVOX":
            self.on_voicevox_character_selected(choice)

    def on_style_change(self, choice: str) -> None:
        active_engine_name = self.selected_engine_var.get()
        if active_engine_name == "gTTS":
            self.on_gtts_setting_changed(choice)
        elif active_engine_name == "VOICEVOX":
            self.on_voicevox_style_selected(choice)

    def on_host_change(self, choice: str) -> None:
        self.current_host = choice
        self._update_device_lists()

    def on_host_2_change(self, choice: str) -> None:
        self.current_host_2 = choice
        self._update_device_lists()

    def on_device_change(self, choice: str) -> None:
        if not choice or choice == "Default Output Device":
            self.current_device_index = None; return
        try: self.current_device_index = int(choice.split("Index: ")[1].rstrip(")"))
        except: self.current_device_index = None

    def on_device_2_change(self, choice: str) -> None:
        if not choice or choice == "Default Output Device":
            self.current_device_index_2 = None; return
        try: self.current_device_index_2 = int(choice.split("Index: ")[1].rstrip(")"))
        except: self.current_device_index_2 = None

    def on_speaker_2_enable_change(self) -> None:
        if hasattr(self, 'speaker_2_enabled_var'):
            self.speaker_2_enabled = self.speaker_2_enabled_var.get()

    def on_volume_change(self, value: float) -> None:
        self.volume = value
        self.volume_value_var.set(f"{int(value * 100)}%")

    def _process_wav_for_volume(self, audio_data_wav: bytes) -> bytes:
        """Applies volume adjustment to WAV audio data bytes."""
        if not audio_data_wav: return b''
        try:
            with io.BytesIO(audio_data_wav) as buffer:
                with wave.open(buffer, 'rb') as wf:
                    n_channels, sampwidth, framerate, n_frames, _, _ = wf.getparams()
                    raw_data = wf.readframes(n_frames)

            if sampwidth == 2:  # 16-bit PCM
                fmt = f"{n_frames * n_channels}h"
                data = np.array(struct.unpack(fmt, raw_data), dtype=np.int16)
                processed_data = np.clip(data * self.volume, -32768, 32767).astype(np.int16)
                modified_raw_data = struct.pack(fmt, *processed_data)

                with io.BytesIO() as out_buffer:
                    with wave.open(out_buffer, 'wb') as out_wf:
                        out_wf.setparams((n_channels, sampwidth, framerate, n_frames, "NONE", "not compressed"))
                        out_wf.writeframes(modified_raw_data)
                    return out_buffer.getvalue()
            else:
                logger.warning(f"Volume adjustment not applied: unsupported sample width {sampwidth}.")
                return audio_data_wav
        except ImportError:
            logger.error("Numpy import failed, cannot apply volume adjustment to WAV.")
            return audio_data_wav
        except Exception as e:
            logger.exception(f"Error processing WAV for volume: {e}")
            return audio_data_wav

    def play_test_audio(self) -> None:
        active_engine = self.get_active_engine()
        if not active_engine:
            self.status_var.set("Error: No active TTS engine.")
            logger.error("Test play: No active TTS engine found.")
            return

        text: str = self.test_text_var.get()
        if not text:
            self.status_var.set("Error: Text is empty")
            logger.error("Test play: Text is empty.")
            return

        tts_kwargs = {}
        selected_lang_for_tts = ""
        engine_display_name = active_engine.get_engine_name()

        if "VOICEVOX" in engine_display_name and engine_display_name != "VOICEVOX (Unavailable)":
            selected_lang_for_tts = "ja"
            tts_kwargs["speaker_id"] = self.voicevox_selected_style_id
            logger.info(f"Test play (VOICEVOX): Lang='{selected_lang_for_tts}', SpeakerID='{tts_kwargs['speaker_id']}'")
        elif engine_display_name == "gTTS":
            selected_lang_for_tts = self.gtts_language_var.get()
            tts_kwargs["tld"] = self.gtts_selected_tld_code
            logger.info(f"Test play (gTTS): Lang='{selected_lang_for_tts}', TLD='{tts_kwargs['tld']}'")
        else:
             logger.error(f"Test play: Unknown or unavailable engine '{engine_display_name}'.")
             self.status_var.set(f"Error: Engine {engine_display_name} not usable.")
             return

        self.status_var.set(f"Synthesizing with {engine_display_name}...")
        self.update()

        thread: threading.Thread = threading.Thread(
            target=self._play_audio_async, args=(text, selected_lang_for_tts, tts_kwargs), daemon=True)
        thread.start()

    def _play_audio_async(self, text: str, language_code: str, tts_kwargs: Optional[Dict] = None) -> None:
        active_engine = self.get_active_engine()
        if not active_engine:
            logger.error("_play_audio_async: No active TTS engine.")
            self.after(0, lambda: self.status_var.set("Error: No TTS Engine"))
            return

        if tts_kwargs is None: tts_kwargs = {}

        logger.info(f"Engine '{active_engine.get_engine_name()}' attempting synthesis: Text='{text[:30]}...', Lang='{language_code}', Kwargs='{tts_kwargs}'")
        self.playback_lock.acquire()
        try:
            if self.clear_audio_requested:
                self.clear_audio_requested = False
                self.status_var.set("Playback cancelled.")
                logger.info("Playback cancelled due to clear_audio_requested flag.")
                return

            audio_data: Optional[bytes] = active_engine.synthesize_speech(text, language_code, **tts_kwargs)

            if audio_data:
                engine_display_name = active_engine.get_engine_name()
                audio_format = active_engine.get_audio_format()
                logger.info(f"Synthesis successful ({engine_display_name}, format: {audio_format}), got {len(audio_data)} bytes.")

                if self.clear_audio_requested:
                    logger.info("Playback cancelled after synthesis, before playback processing.")
                    return

                if "VOICEVOX" in engine_display_name and audio_format == "wav" and self.voicevox_audio_player:
                    logger.info("Processing WAV for VOICEVOX playback with volume and device selection.")
                    processed_audio_data = self._process_wav_for_volume(audio_data)

                    selected_device_idx = self.current_device_index

                    self.voicevox_audio_player.set_output_device(selected_device_idx)
                    logger.info(f"VOICEVOX player using device index: {selected_device_idx if selected_device_idx is not None else 'default'}")

                    self.voicevox_audio_player.play_bytes(processed_audio_data)
                    logger.info("VOICEVOX playback finished via VoicevoxSpeaker.")

                elif audio_format == "mp3":
                    logger.info("Playing MP3 via playsound (temp file).")
                    temp_audio_filename = f"temp_playback.{audio_format}"
                    temp_audio_path = os.path.join(self.app_path, temp_audio_filename)
                    with open(temp_audio_path, "wb") as f: f.write(audio_data)

                    if self.clear_audio_requested:
                        logger.info("Playback cancelled just before playsound.")
                        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
                        return

                    playsound(temp_audio_path, True)
                    logger.info(f"MP3 playback via playsound finished for {temp_audio_path}.")
                    if os.path.exists(temp_audio_path):
                        try: os.remove(temp_audio_path)
                        except Exception as e: logger.error(f"Error deleting temp file '{temp_audio_path}': {e}")

                else:
                    logger.info(f"Playing unknown/fallback format {audio_format} via playsound (temp file).")
                    temp_audio_filename = f"temp_playback.{audio_format}"
                    temp_audio_path = os.path.join(self.app_path, temp_audio_filename)
                    with open(temp_audio_path, "wb") as f: f.write(audio_data)

                    if self.clear_audio_requested:
                        logger.info("Playback cancelled just before fallback playsound.")
                        if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
                        return

                    playsound(temp_audio_path, True)
                    logger.info(f"Fallback playback via playsound finished for {temp_audio_path}.")
                    if os.path.exists(temp_audio_path):
                        try: os.remove(temp_audio_path)
                        except Exception as e: logger.error(f"Error deleting temp file '{temp_audio_path}': {e}")

                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set("Test playback finished."))
            else:
                logger.error("Synthesis failed, no audio data received.")
                if not self.clear_audio_requested:
                    self.after(0, lambda: self.status_var.set("Error: Synthesis failed."))

        except TTSSynthesisError as e:
            logger.error(f"TTSSynthesisError during test playback: {e}")
            if not self.clear_audio_requested:
                self.after(0, lambda msg=f"TTS Error: {str(e)[:100]}": self.status_var.set(msg))
        except Exception as e:
            logger.exception("Generic error during test playback audio async.")
            if not self.clear_audio_requested:
                self.after(0, lambda msg=f"Playback Error: {str(e)[:100]}": self.status_var.set(msg))
        finally:
            if self.playback_lock.locked(): self.playback_lock.release()
            logger.info("Playback async task finished.")

    def load_config(self) -> None:
        config_dict: Dict[str, Any] = Config.load()
        self.config = config_dict

        self.current_tts_engine_name = self.config.get("active_tts_engine", "gTTS")
        self.selected_engine_var.set(self.current_tts_engine_name)
        logger.info(f"Loaded active_tts_engine from config: {self.current_tts_engine_name}")

        self.gtts_selected_language = self.config.get("gtts_selected_language", self.default_tts_language)
        self.gtts_language_var.set(self.gtts_selected_language)
        self.gtts_selected_tld_code = self.config.get("gtts_selected_tld_code", self.default_gtts_tld)
        from tts_engine import GTTS_TLD_OPTIONS as ENGINE_GTTS_TLD_OPTIONS_LC
        self.gtts_tld_display_var.set(f"{ENGINE_GTTS_TLD_OPTIONS_LC.get(self.gtts_selected_tld_code, 'Default (com)')} ({self.gtts_selected_tld_code})")

        self.voicevox_selected_speaker_name = self.config.get("voicevox_selected_character_name", "")
        self.voicevox_character_var.set(self.voicevox_selected_speaker_name)
        self.voicevox_selected_style_id = self.config.get("voicevox_selected_style_id", self.default_voicevox_speaker_id)

        self.current_device_index = self.config.get("device_index") # Ensure this is numerical index
        self.current_device_index_2 = self.config.get("device_index_2")
        self.speaker_2_enabled = self.config.get("speaker_2_enabled", False)
        self.current_host = self.config.get("host_name", "すべて")
        self.current_host_2 = self.config.get("host_name_2", "すべて")
        self.volume = self.config.get("volume", 0.8)
        self.ws_url = self.config.get("ws_url", "ws://127.0.0.1:8765")
        if hasattr(self, 'ws_url_var') and self.ws_url_var:
            self.ws_url_var.set(self.ws_url)


    def save_config(self) -> None:
        config_data: Dict[str, Any] = {
            "active_tts_engine": self.selected_engine_var.get(),
            "gtts_selected_language": self.gtts_language_var.get(),
            "gtts_selected_tld_code": self.gtts_selected_tld_code,
            "voicevox_selected_character_name": self.voicevox_character_var.get(),
            "voicevox_selected_style_id": self.voicevox_selected_style_id,
            "device_index": self.current_device_index, # Save numerical index
            "device_index_2": self.current_device_index_2,
            "speaker_2_enabled": self.speaker_2_enabled,
            "host_name": self.current_host,
            "host_name_2": self.current_host_2,
            "volume": self.volume,
            "ws_url": self.ws_url_var.get()
        }
        Config.save(config_data)
        self.status_var.set("Settings saved.")
        logger.info("Configuration saved.")

    async def _ws_handler(self, websocket_client, path):
        logger.info(f"Client connected: {websocket_client.remote_address}")
        self.ws_clients[websocket_client] = None

        try:
            async for message in websocket_client:
                request_id = "unknown"
                try:
                    logger.info(f"Received message: {message[:256]}")
                    data = json.loads(message)
                    request_id = data.get("request_id", "unknown")
                    command = data.get("command")

                    response_data = None
                    binary_payload = None
                    active_engine = self.get_active_engine()
                    if not active_engine:
                        raise TTSSynthesisError("No active TTS engine configured on server.")

                    if command == "TTS_SYNTHESIZE":
                        text_to_synth = data.get("text")
                        lang_to_synth = data.get("language_code")
                        voice_id_param = data.get("voice_id")

                        msg_type = data.get("type")
                        if msg_type == "SENT":
                            text_to_synth = data.get("message", text_to_synth or "")
                            lang_to_synth = data.get("src_languages", lang_to_synth)
                        elif msg_type == "RECEIVED":
                            text_to_synth = data.get("translation", text_to_synth or "")
                            lang_to_synth = data.get("dst_languages", lang_to_synth)
                        elif msg_type == "CHAT":
                             text_to_synth = data.get("message", text_to_synth or "")
                             lang_to_synth = data.get("src_languages", lang_to_synth)

                        if not text_to_synth: raise ValueError("Text for synthesis is empty.")
                        if not lang_to_synth:
                            # Use UI selected default for the active engine if not provided in request
                            if active_engine.get_engine_name() == "gTTS":
                                lang_to_synth = self.gtts_language_var.get()
                            elif "VOICEVOX" in active_engine.get_engine_name():
                                lang_to_synth = "ja" # Voicevox is Japanese
                            else: # Fallback
                                lang_to_synth = self.default_tts_language

                        synthesis_kwargs = {}
                        engine_display_name = active_engine.get_engine_name()

                        if "VOICEVOX" in engine_display_name and engine_display_name != "VOICEVOX (Unavailable)":
                            try:
                                synthesis_kwargs["speaker_id"] = int(voice_id_param) if voice_id_param is not None else self.voicevox_selected_style_id # Use UI default if not provided
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid voice_id '{voice_id_param}' for VOICEVOX, using UI default {self.voicevox_selected_style_id}")
                                synthesis_kwargs["speaker_id"] = self.voicevox_selected_style_id
                            lang_to_synth = "ja"
                        elif engine_display_name == "gTTS":
                            from tts_engine import GTTS_TLD_OPTIONS as ENGINE_GTTS_TLD_OPTIONS_WS
                            synthesis_kwargs["tld"] = voice_id_param if voice_id_param in ENGINE_GTTS_TLD_OPTIONS_WS else self.gtts_selected_tld_code # Use UI default
                        else:
                            raise TTSSynthesisError(f"Engine {engine_display_name} not supported for synthesis.")

                        cache_key_voice_param = synthesis_kwargs.get('tld') if engine_display_name == "gTTS" else synthesis_kwargs.get('speaker_id')
                        cache_key = (engine_display_name, text_to_synth, lang_to_synth, cache_key_voice_param)

                        logger.info(f"[{request_id}] Synthesis task: Engine='{engine_display_name}', Lang='{lang_to_synth}', CharCount='{len(text_to_synth)}', VoiceParams='{synthesis_kwargs}'. CacheKey='{cache_key}'")

                        if cache_key in self.tts_cache:
                            audio_bytes = self.tts_cache[cache_key]
                            logger.info(f"[{request_id}] Cache HIT. Audio size: {len(audio_bytes)}. Latency: ~0ms.")
                        else:
                            logger.info(f"[{request_id}] Cache MISS. Synthesizing...")
                            audio_bytes = active_engine.synthesize_speech(text_to_synth, lang_to_synth, **synthesis_kwargs)
                            logger.info(f"[{request_id}] Synthesis done. Storing in cache. Audio size: {len(audio_bytes)}.")

                            if len(self.tts_cache) >= self.MAX_CACHE_SIZE:
                                oldest_key = self.tts_cache_order.pop(0)
                                del self.tts_cache[oldest_key]
                                logger.info(f"Cache full. Evicted oldest key: {oldest_key}")

                            self.tts_cache[cache_key] = audio_bytes
                            self.tts_cache_order.append(cache_key)

                        response_data = {"status": "success", "message": "Audio synthesized", "request_id": request_id, "data": {"audio_format": active_engine.get_audio_format()}}
                        binary_payload = audio_bytes

                    elif command == "TTS_GET_VOICES":
                        logger.info(f"[{request_id}] TTS_GET_VOICES received.")
                        active_engine_gv = self.get_active_engine()
                        if not active_engine_gv: raise TTSSynthesisError("No active TTS engine for GET_VOICES.")

                        engine_name_gv = active_engine_gv.get_engine_name()
                        langs = active_engine_gv.get_available_languages()
                        voices_data = []
                        if "VOICEVOX" in engine_name_gv and engine_name_gv != "VOICEVOX (Unavailable)":
                            vv_speakers = self.voicevox_engine.get_voicevox_speakers()
                            for speaker_info in vv_speakers:
                                for style in speaker_info.get("styles", []):
                                    voices_data.append({
                                        "id": str(style["id"]),
                                        "name": f"{speaker_info['name']} - {style['name']}",
                                        "language": "ja"
                                    })
                        elif engine_name_gv == "gTTS":
                            from tts_engine import GTTS_TLD_OPTIONS as ENGINE_GTTS_TLD_OPTIONS_GV
                            voices_data = [{"id": tld, "name": name, "language": "shared"} for tld, name in ENGINE_GTTS_TLD_OPTIONS_GV.items()]

                        response_data = {"status": "success", "request_id": request_id, "data": {"engine": engine_name_gv, "languages": langs, "voices": voices_data}}
                        logger.info(f"[{request_id}] Returning data for engine '{engine_name_gv}': {len(langs)} languages and {len(voices_data)} voices.")

                    elif command == "TTS_STOP":
                        logger.info(f"[{request_id}] TTS_STOP received.")
                        self.on_stop_and_clear_audio()
                        response_data = {"status": "success", "message": "Stop command acknowledged", "request_id": request_id}

                    elif command == "TTS_SET_DEFAULT_VOICE":
                        voice_id_param = data.get("voice_id")
                        lang_param = data.get("language_code")
                        logger.info(f"[{request_id}] TTS_SET_DEFAULT_VOICE: voice_id='{voice_id_param}', lang='{lang_param}'.")

                        active_engine_sdv = self.get_active_engine()
                        if not active_engine_sdv: raise TTSSynthesisError("No active engine to set default voice for.")
                        engine_name_sdv = active_engine_sdv.get_engine_name()

                        if "gTTS" in engine_name_sdv:
                            from tts_engine import GTTS_TLD_OPTIONS as ENGINE_GTTS_TLD_OPTIONS_SDV
                            if voice_id_param in ENGINE_GTTS_TLD_OPTIONS_SDV:
                                self.gtts_selected_tld_code = voice_id_param
                                self.gtts_tld_display_var.set(f"{ENGINE_GTTS_TLD_OPTIONS_SDV.get(voice_id_param, '')} ({voice_id_param})")
                                msg = f"Default gTTS TLD set to {voice_id_param}."
                                if lang_param:
                                    self.gtts_selected_language = self.gtts_engine.get_gtts_lang_code(lang_param)
                                    self.gtts_language_var.set(self.gtts_selected_language)
                                    msg += f" Default gTTS language set to {self.gtts_selected_language}."
                                self.status_var.set(msg)
                                response_data = {"status": "success", "message": msg, "request_id": request_id}
                            else: raise ValueError(f"Invalid TLD '{voice_id_param}' for gTTS.")
                        elif "VOICEVOX" in engine_name_sdv and engine_name_sdv != "VOICEVOX (Unavailable)":
                            if voice_id_param and voice_id_param.isdigit():
                                self.voicevox_selected_style_id = int(voice_id_param)
                                # This updates the internal default, UI will reflect if VOICEVOX is active and char list is refreshed.
                                self.default_voicevox_speaker_id = int(voice_id_param)
                                self.after(0, self._update_dynamic_ui_elements) # Refresh UI
                                msg = f"Default Voicevox Style ID set to {voice_id_param}."
                                self.status_var.set(msg)
                                response_data = {"status": "success", "message": msg, "request_id": request_id}
                            else: raise ValueError(f"Invalid Speaker ID '{voice_id_param}' for VOICEVOX.")
                        else:
                            raise ValueError(f"Cannot set default voice for inactive or unavailable engine: {engine_name_sdv}")
                        if response_data: self.save_config()


                    elif command == "TTS_SET_GLOBAL_SETTINGS":
                        settings = data.get("settings", {})
                        logger.info(f"[{request_id}] TTS_SET_GLOBAL_SETTINGS: {settings}.")
                        if "active_engine" in settings:
                            engine_choice = settings["active_engine"]
                            if engine_choice == "gTTS" or (engine_choice == "VOICEVOX" and VOICEVOX_AVAILABLE and hasattr(self.voicevox_engine, 'voicevox_client') and self.voicevox_engine.voicevox_client is not None):
                                self.selected_engine_var.set(engine_choice)
                                self.on_engine_selected(engine_choice)
                                logger.info(f"Active TTS engine switched to: {self.current_tts_engine_name} by client request.")
                            else:
                                logger.warning(f"Client requested active engine '{engine_choice}' which is not available. No change.")
                        if "default_language" in settings: # This will apply to gTTS default language
                            lang_code = self.gtts_engine.get_gtts_lang_code(settings["default_language"])
                            self.default_tts_language = lang_code
                            self.gtts_selected_language = lang_code # Update current selection too
                            self.gtts_language_var.set(lang_code)
                            logger.info(f"Default/Current gTTS language set to: {lang_code}")

                        response_data = {"status": "success", "message": "Global settings processed.", "request_id": request_id}
                        self.save_config() # Save any changes made

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
                except ValueError as e:
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
        try:
            url_parts = self.ws_url_var.get().replace("ws://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1].split("/")[0])

            logger.info(f"Attempting to start WebSocket server on {host}:{port}")
            self.ws_server = await websockets.serve(self._ws_handler, host, port)
            self.is_server_running = True
            self.after(0, self._update_ws_status_connected)
            logger.info(f"WebSocket server started on {host}:{port} and listening.")
            await self.ws_server.wait_closed()
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
            self.ws_server_thread = threading.Thread(
                target=lambda: asyncio.run(self._start_ws_server_async()),
                daemon=True
            )
            self.ws_server_thread.start()
        else:
            logger.info("Toggle: Stopping WebSocket server.")
            if self.ws_server:
                self.ws_server.close()
            self.is_server_running = False
            self._update_ws_status_disconnected()


    def start_websocket_connection(self) -> None: # Legacy name, now toggles server
        self.toggle_websocket_connection()


    def stop_websocket_connection(self) -> None: # Legacy name, now toggles server
        self.toggle_websocket_connection()


    def _update_ws_status_connected(self) -> None:
        self.ws_status_var.set("WebSocket Server: Running")
        self.ws_status_label.configure(text_color="#4CAF50")
        self.ws_button_var.set("Stop WebSocket Server")
        self.ws_button.configure(fg_color="#8B0000", hover_color="#B22222")
        self.status_var.set(f"WebSocket Server running at {self.ws_url_var.get()}")
        logger.info(f"WebSocket Server running at {self.ws_url_var.get()}")

    def _update_ws_status_disconnected(self) -> None:
        self.ws_status_var.set("WebSocket Server: Stopped")
        self.ws_status_label.configure(text_color="gray")
        self.ws_button_var.set("Start WebSocket Server")
        self.ws_button.configure(fg_color="#1E5631", hover_color="#2E8B57")
        self.status_var.set("WebSocket Server stopped.")
        logger.info("WebSocket Server stopped.")


    def _synthesize_and_play(self, text: str) -> None: # This was for the old client mode's on_message
        logger.warning("_synthesize_and_play (legacy for client mode) called. Adapting for current active engine test playback.")
        active_engine = self.get_active_engine()
        if not active_engine:
            logger.error("Legacy _synthesize_and_play: No active engine selected.")
            return

        tts_kwargs = {}
        lang_code_for_synth = ""
        engine_display_name = active_engine.get_engine_name()

        if "VOICEVOX" in engine_display_name and engine_display_name != "VOICEVOX (Unavailable)":
            lang_code_for_synth = "ja"
            tts_kwargs["speaker_id"] = self.voicevox_selected_style_id
        elif engine_display_name == "gTTS":
            lang_code_for_synth = self.gtts_language_var.get()
            tts_kwargs["tld"] = self.gtts_selected_tld_code
        else:
            logger.error(f"Cannot synthesize with engine {engine_display_name}")
            return

        thread = threading.Thread(target=self._play_audio_async, args=(text, lang_code_for_synth, tts_kwargs), daemon=True)
        thread.start()

    def on_stop_and_clear_audio(self) -> None:
        logger.info("Stop/Clear audio requested.")
        self.status_var.set("Stop request received. Clearing audio...")
        self.update_idletasks()
        self.clear_audio_requested = True
        if self.voicevox_audio_player and hasattr(self.voicevox_audio_player, 'is_playing') and self.voicevox_audio_player.is_playing():
            try:
                self.voicevox_audio_player.request_stop()
                logger.info("Requested stop for VoicevoxSpeaker playback.")
            except Exception as e:
                logger.error(f"Error stopping VoicevoxSpeaker: {e}")
        self.status_var.set("Audio stop requested.")


    def on_closing(self) -> None:
        logger.info("Application closing...")
        self.save_config()
        if self.is_server_running and self.ws_server:
            logger.info("Stopping WebSocket server...")
            self.ws_server.close()
            if self.ws_server_thread and self.ws_server_thread.is_alive():
                 self.ws_server_thread.join(timeout=2)

        logger.info("Destroying application window.")
        self.destroy()


if __name__ == "__main__":
    logger.info("Application starting...")
    try:
        import playsound
    except ImportError:
        logger.error("playsound library is not installed. Please install it for audio playback.")

    app = VoicevoxConnectorGUI()
    app.mainloop()
    logger.info("Application exited.")
