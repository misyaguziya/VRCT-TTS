import json
import os
from typing import Dict, Any


class Config:
    """設定の管理クラス"""

    CONFIG_FILE = "config.json"

    @staticmethod
    def load() -> Dict[str, Any]:
        """
        設定ファイルから設定を読み込む

        Returns:
            Dict[str, Any]: 設定の辞書
        """
        if not os.path.exists(Config.CONFIG_FILE):
            return {}

        try:
            with open(Config.CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"設定の読み込み中にエラーが発生しました: {e}")
            return {}

    @staticmethod
    def save(config_data: Dict[str, Any]) -> None:
        """
        設定を設定ファイルに保存する

        Args:
            config_data (Dict[str, Any]): 保存する設定の辞書
        """
        try:
            with open(Config.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print(f"設定を {Config.CONFIG_FILE} に保存しました")
        except Exception as e:
            print(f"設定の保存中にエラーが発生しました: {e}")

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        特定の設定値を取得する

        Args:
            key (str): 設定のキー
            default (Any, optional): 設定が存在しない場合のデフォルト値

        Returns:
            Any: 設定値、またはデフォルト値
        """
        config = Config.load()
        return config.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        特定の設定値を設定して保存する

        Args:
            key (str): 設定のキー
            value (Any): 設定値
        """
        config = Config.load()
        config[key] = value
        Config.save(config)

    @staticmethod
    def update(new_config: Dict[str, Any]) -> None:
        """
        複数の設定値を更新して保存する

        Args:
            new_config (Dict[str, Any]): 更新する設定の辞書
        """
        config = Config.load()
        config.update(new_config)
        Config.save(config)
