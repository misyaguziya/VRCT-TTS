#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, Any, List
import shutil # For test backup

class Config:
    """設定ファイルの読み書きを行うクラス"""
    CONFIG_FILE = "config.json"

    DEFAULT_TTS_SETTINGS = {
        "language_engine_mapping": {
            "default_engine": "gtts",
            "language_specific": [
                {"lang_code": "ja", "engine": "voicevox", "voice_id": "1"},
                {"lang_code": "ja-JP", "engine": "voicevox", "voice_id": "1"},
                {"lang_code": "en", "engine": "gtts", "voice_id": None},
                {"lang_code": "en-US", "engine": "gtts", "voice_id": None},
                {"lang_code": "en-GB", "engine": "gtts", "voice_id": None},
                {"lang_code": "ko", "engine": "gtts", "voice_id": None},
                {"lang_code": "ko-KR", "engine": "gtts", "voice_id": None}
            ],
            "fallback_engine": "gtts"
        },
        "user_preferred_voices": {
            "gtts": {"default_voice_id": None},
            "voicevox": {"default_voice_id": "1"}
        },
        "tts_optimizations": { # New section for optimizations
            "enable_caching": True,
            "max_cache_size": 100
        }
    }

    DEFAULT_GENERAL_SETTINGS = {
        "speaker_id": 1,
        "device_index": None,
        "device_index_2": None,
        "speaker_2_enabled": False,
        "host_name": "すべて",
        "host_name_2": "すべて",
        "volume": 0.8,
        "ws_url": "ws://127.0.0.1:2231"
    }

    @staticmethod
    def _get_full_default_config() -> Dict[str, Any]:
        defaults = {}
        defaults.update(Config.DEFAULT_GENERAL_SETTINGS)
        defaults.update(Config.DEFAULT_TTS_SETTINGS)
        return defaults

    @staticmethod
    def load() -> Dict[str, Any]:
        full_defaults = Config._get_full_default_config()
        if not os.path.exists(Config.CONFIG_FILE):
            Config.save(full_defaults) # Save defaults if no file exists
            return full_defaults.copy()

        try:
            with open(Config.CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading config file '{Config.CONFIG_FILE}': {e}. Creating with default settings.")
            Config.save(full_defaults) # Save defaults if file is corrupted
            return full_defaults.copy()

        config_updated = False
        # Ensure all top-level default keys exist in loaded_config
        for default_key, default_value_structure in full_defaults.items():
            if default_key not in loaded_config:
                loaded_config[default_key] = default_value_structure
                config_updated = True
            # If the key exists, ensure its type matches the default's type (e.g., dict for mappings)
            # And then ensure all sub-keys from default are present if it's a dict
            elif isinstance(default_value_structure, dict) and isinstance(loaded_config[default_key], dict):
                # For nested dictionaries (like language_engine_mapping and user_preferred_voices)
                current_section = loaded_config[default_key]
                default_section = default_value_structure
                for sub_key, sub_default_value in default_section.items():
                    if sub_key not in current_section:
                        current_section[sub_key] = sub_default_value
                        config_updated = True
                    # Special check for language_specific: if it exists but is not a list, override with default
                    elif sub_key == "language_specific" and not isinstance(current_section.get(sub_key), list):
                        current_section[sub_key] = sub_default_value # sub_default_value is the default list
                        config_updated = True
                    # Ensure sub-dictionaries (like within user_preferred_voices) have their default keys
                    elif isinstance(sub_default_value, dict) and isinstance(current_section.get(sub_key), dict):
                        current_sub_dict = current_section[sub_key]
                        for s_sub_key, s_sub_default_value in sub_default_value.items():
                            if s_sub_key not in current_sub_dict:
                                current_sub_dict[s_sub_key] = s_sub_default_value
                                config_updated = True
                    # If type is wrong for a sub_key that should be a dict, reset to default for that sub_key
                    elif isinstance(sub_default_value, dict) and not isinstance(current_section.get(sub_key), dict):
                         current_section[sub_key] = sub_default_value # Reset sub-section if wrong type
                         config_updated = True

            # Case where a top-level key (that should be a dict, like tts_optimizations) exists but is not a dict
            elif default_key in loaded_config and isinstance(default_value_structure, dict) and \
                 not isinstance(loaded_config[default_key], dict):
                loaded_config[default_key] = default_value_structure # Reset to default dict structure
                config_updated = True

        if config_updated:
            # print(f"Config file '{Config.CONFIG_FILE}' was updated with missing default settings.") # Reduced verbosity
            Config.save(loaded_config) # Save if any defaults were merged

        return loaded_config

    @staticmethod
    def save(config_data: Dict[str, Any]) -> None:
        try:
            with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            # print(f"Configuration saved to {Config.CONFIG_FILE}") # Reduce noise during tests
        except IOError as e:
            print(f"Error saving config file '{Config.CONFIG_FILE}': {e}")


def run_tests():
    print("\n--- Running Config Enhanced Tests ---")
    original_config_backup_path_for_config_test = Config.CONFIG_FILE + ".config_test_backup"

    def backup_config():
        if os.path.exists(Config.CONFIG_FILE):
            shutil.copyfile(Config.CONFIG_FILE, original_config_backup_path_for_config_test)
            return True
        return False

    def restore_config():
        if os.path.exists(original_config_backup_path_for_config_test):
            shutil.move(original_config_backup_path_for_config_test, Config.CONFIG_FILE)
        elif os.path.exists(Config.CONFIG_FILE): # If no backup, remove test one
             os.remove(Config.CONFIG_FILE)


    # Test 0: Clean slate, ensure load creates default config
    print("\n--- Test 0: Clean slate loading ---")
    if os.path.exists(Config.CONFIG_FILE): os.remove(Config.CONFIG_FILE)
    if os.path.exists(original_config_backup_path_for_config_test): os.remove(original_config_backup_path_for_config_test)

    # Config.load() will print "Error loading config file... Creating with default settings." if file doesn't exist,
    # which is expected here. Then it saves and returns defaults.
    config_data_0 = Config.load()
    # print(f"Loaded config (defaults created): {json.dumps(config_data_0, indent=2, ensure_ascii=False)}")
    assert config_data_0 == Config._get_full_default_config(), "Test 0 FAILED: Loaded config not equal to full defaults."
    print("Test 0 PASSED: Default config created and loaded correctly (tts_optimizations included).")


    # Test 1: Load with no existing file (already covered by Test 0, but good to re-verify sequence)
    print("\n--- Test 1: Load with no existing file (verify again) ---")
    if os.path.exists(Config.CONFIG_FILE): os.remove(Config.CONFIG_FILE)

    config_data_1 = Config.load()
    print(f"Loaded config (defaults): {json.dumps(config_data_1['language_engine_mapping'], indent=2, ensure_ascii=False)}")
    assert "language_engine_mapping" in config_data_1
    assert config_data_1["language_engine_mapping"]["default_engine"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"]["default_engine"]
    print("Test 1 PASSED: Default TTS settings correctly loaded on clean load.")

    # Test 2: Modify and save, then reload (standard test)
    print("\n--- Test 2: Modify, save, and reload ---")
    backup_config() # Backup current config (which is default here)
    config_data_1["language_engine_mapping"]["default_engine"] = "voicevox"
    config_data_1["user_preferred_voices"]["voicevox"]["default_voice_id"] = "3"
    Config.save(config_data_1)
    reloaded_config_data_2 = Config.load()
    print(f"Reloaded 'language_engine_mapping': {json.dumps(reloaded_config_data_2['language_engine_mapping'], indent=2, ensure_ascii=False)}")
    print(f"Reloaded 'user_preferred_voices': {json.dumps(reloaded_config_data_2['user_preferred_voices'], indent=2, ensure_ascii=False)}")
    assert reloaded_config_data_2["language_engine_mapping"]["default_engine"] == "voicevox"
    assert reloaded_config_data_2["user_preferred_voices"]["voicevox"]["default_voice_id"] == "3"
    print("Test 2 PASSED: Modified settings saved and reloaded.")
    restore_config() # Restore original (default) for next test

    # Test 3: Partial config - only default_engine specified in language_engine_mapping
    print("\n--- Test 3: Partial config - only default_engine ---")
    backup_config()
    partial_config_3 = {
        "language_engine_mapping": {
            "default_engine": "custom_default"
        },
        "tts_optimizations": { # Test providing partial new settings
            "max_cache_size": 50
            # enable_caching is missing, should be filled by default
        }
    }
    with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(partial_config_3, f)

    loaded_config_3 = Config.load()
    # print(f"Loaded from partial (default_engine only): {json.dumps(loaded_config_3, indent=2, ensure_ascii=False)}")
    lem_3 = loaded_config_3["language_engine_mapping"]
    assert lem_3["default_engine"] == "custom_default", "Test 3 FAILED: custom default_engine not preserved."
    assert lem_3["language_specific"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"]["language_specific"], "Test 3 FAILED: lem.language_specific not filled."
    assert lem_3["fallback_engine"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"]["fallback_engine"], "Test 3 FAILED: lem.fallback_engine not filled."

    optim_3 = loaded_config_3["tts_optimizations"]
    assert optim_3["max_cache_size"] == 50, "Test 3 FAILED: optim.max_cache_size not preserved."
    assert optim_3["enable_caching"] == Config.DEFAULT_TTS_SETTINGS["tts_optimizations"]["enable_caching"], "Test 3 FAILED: optim.enable_caching not filled."

    assert loaded_config_3["user_preferred_voices"] == Config.DEFAULT_TTS_SETTINGS["user_preferred_voices"], "Test 3 FAILED: user_preferred_voices not filled."
    assert loaded_config_3["volume"] == Config.DEFAULT_GENERAL_SETTINGS["volume"], "Test 3 FAILED: general settings (volume) not filled."
    print("Test 3 PASSED: Partial config (default_engine & partial tts_optimizations) correctly merged.")
    restore_config()

    # Test 4: Partial config - user_preferred_voices.voicevox.default_voice_id specified
    print("\n--- Test 4: Partial config - specific user_preferred_voices ---")
    backup_config()
    partial_config_4 = {
        "user_preferred_voices": {
            "voicevox": {
                "default_voice_id": "99"
            }
            # 'gtts' section for user_preferred_voices is missing
        }
    }
    with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(partial_config_4, f)

    loaded_config_4 = Config.load()
    print(f"Loaded from partial (user_preferred_voices.voicevox only): {json.dumps(loaded_config_4, indent=2, ensure_ascii=False)}")
    upv_4 = loaded_config_4["user_preferred_voices"]
    assert upv_4["voicevox"]["default_voice_id"] == "99", "Test 4 FAILED: Custom voicevox default_voice_id not preserved."
    assert "gtts" in upv_4, "Test 4 FAILED: gtts section in user_preferred_voices not filled from default."
    assert upv_4["gtts"]["default_voice_id"] == Config.DEFAULT_TTS_SETTINGS["user_preferred_voices"]["gtts"]["default_voice_id"], "Test 4 FAILED: gtts default_voice_id not filled."
    assert loaded_config_4["language_engine_mapping"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"], "Test 4 FAILED: language_engine_mapping not filled."
    print("Test 4 PASSED: Partial config (specific user_preferred_voices) correctly merged.")
    restore_config()

    # Test 5: language_specific list is valid but different from default
    print("\n--- Test 5: Valid but different language_specific list ---")
    backup_config()
    custom_lang_specific = [
        {"lang_code": "fr", "engine": "gtts", "voice_id": None},
        {"lang_code": "de", "engine": "gtts", "voice_id": "german_voice_example"}
    ]
    config_5 = {
        "language_engine_mapping": {
            "language_specific": custom_lang_specific
        }
    }
    with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config_5, f)

    loaded_config_5 = Config.load()
    print(f"Loaded with custom language_specific: {json.dumps(loaded_config_5['language_engine_mapping'], indent=2, ensure_ascii=False)}")
    # Current design: if 'language_specific' exists and is a list, it's used as is.
    # The sub-keys like 'default_engine' and 'fallback_engine' for language_engine_mapping would be filled from defaults.
    assert loaded_config_5["language_engine_mapping"]["language_specific"] == custom_lang_specific, "Test 5 FAILED: Custom language_specific list not preserved."
    assert loaded_config_5["language_engine_mapping"]["default_engine"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"]["default_engine"], "Test 5 FAILED: default_engine not filled for custom lang_specific."
    print("Test 5 PASSED: Custom valid language_specific list preserved, other parts merged.")
    restore_config()

    # Test 6: Malformed language_specific (already covered in original tests, but good to have)
    print("\n--- Test 6: Malformed language_specific (string instead of list) ---")
    backup_config()
    config_6 = {"language_engine_mapping": {"language_specific": "not-a-list"}}
    with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(config_6, f)
    loaded_config_6 = Config.load()
    print(f"Loaded from malformed language_specific: {json.dumps(loaded_config_6['language_engine_mapping']['language_specific'], indent=2, ensure_ascii=False)}")
    assert loaded_config_6["language_engine_mapping"]["language_specific"] == Config.DEFAULT_TTS_SETTINGS["language_engine_mapping"]["language_specific"], "Test 6 FAILED: Malformed language_specific not overridden by default."
    print("Test 6 PASSED: Malformed language_specific correctly overridden.")
    restore_config()


    print("\n--- Config Enhanced Tests Finished ---")

if __name__ == '__main__':
    run_tests()
