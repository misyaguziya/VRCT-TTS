# -*- coding: utf-8 -*-
"""
VOICEVOX Engine APIのPythonラッパー
"""

import requests
from typing import List, Dict, Union, Optional, BinaryIO
from enum import Enum


class WordTypes(str, Enum):
    """品詞の列挙型"""
    PROPER_NOUN = "PROPER_NOUN"  # 固有名詞
    COMMON_NOUN = "COMMON_NOUN"  # 普通名詞
    VERB = "VERB"  # 動詞
    ADJECTIVE = "ADJECTIVE"  # 形容詞
    SUFFIX = "SUFFIX"  # 語尾


class CorsPolicyMode(str, Enum):
    """CORSの許可モード"""
    ALL = "all"
    LOCALAPPS = "localapps"


class VOICEVOXClient:
    """
    VOICEVOX Engine APIのクライアント
    """

    def __init__(self, host: str = "localhost", port: int = 50021):
        """
        VOICEVOXクライアントの初期化

        Args:
            host (str, optional): ホスト名. Defaults to "localhost".
            port (int, optional): ポート番号. Defaults to 50021.
        """
        self.base_url = f"http://{host}:{port}"

    # クエリ作成関連のAPI

    def audio_query(self, text: str, speaker: int, core_version: Optional[str] = None) -> Dict[str, Any]:
        """
        音声合成用のクエリを作成する

        Args:
            text (str): 合成するテキスト
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: 音声合成用のクエリ
        """
        params: Dict[str, Union[str, int]] = {
            "text": text,
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(f"{self.base_url}/audio_query", params=params)
        response.raise_for_status()
        return response.json()

    def audio_query_from_preset(
        self, text: str, preset_id: int, core_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        音声合成用のクエリをプリセットを用いて作成する

        Args:
            text (str): 合成するテキスト
            preset_id (int): プリセットID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: 音声合成用のクエリ
        """
        params: Dict[str, Union[str, int]] = {
            "text": text,
            "preset_id": preset_id
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/audio_query_from_preset", params=params)
        response.raise_for_status()
        return response.json()

    def accent_phrases(
        self, text: str, speaker: int, is_kana: bool = False, core_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        テキストからアクセント句を得る

        Args:
            text (str): テキスト
            speaker (int): スピーカーID
            is_kana (bool, optional): 入力がAquesTalk風記法かどうか. Defaults to False.
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: アクセント句のリスト
        """
        params: Dict[str, Union[str, int, bool]] = {
            "text": text,
            "speaker": speaker,
            "is_kana": is_kana
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/accent_phrases", params=params)
        response.raise_for_status()
        return response.json()

    def mora_data(
        self, accent_phrases: List[Dict[str, Any]], speaker: int, core_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        アクセント句から音高・音素長を得る

        Args:
            accent_phrases (List[Dict[str, Any]]): アクセント句のリスト
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: 更新されたアクセント句のリスト
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/mora_data",
            params=params,
            json=accent_phrases
        )
        response.raise_for_status()
        return response.json()

    def mora_length(
        self, accent_phrases: List[Dict[str, Any]], speaker: int, core_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        アクセント句から音素長を得る

        Args:
            accent_phrases (List[Dict[str, Any]]): アクセント句のリスト
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: 更新されたアクセント句のリスト
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/mora_length",
            params=params,
            json=accent_phrases
        )
        response.raise_for_status()
        return response.json()

    def mora_pitch(
        self, accent_phrases: List[Dict[str, Any]], speaker: int, core_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        アクセント句から音高を得る

        Args:
            accent_phrases (List[Dict[str, Any]]): アクセント句のリスト
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: 更新されたアクセント句のリスト
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/mora_pitch",
            params=params,
            json=accent_phrases
        )
        response.raise_for_status()
        return response.json()

    # 音声合成関連のAPI

    def synthesis(
        self,
        audio_query: Dict[str, Any],
        speaker: int,
        enable_interrogative_upspeak: bool = True,
        core_version: Optional[str] = None,
        output_file: Optional[BinaryIO] = None
    ) -> Union[bytes, None]:
        """
        音声合成する

        Args:
            audio_query (Dict[str, Any]): 音声合成用のクエリ
            speaker (int): スピーカーID
            enable_interrogative_upspeak (bool, optional): 疑問系のテキストで語尾を自動調整するか. Defaults to True.
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        params: Dict[str, Union[str, int, bool]] = {
            "speaker": speaker,
            "enable_interrogative_upspeak": enable_interrogative_upspeak
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/synthesis",
            params=params,
            json=audio_query
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    def cancellable_synthesis(
        self,
        audio_query: Dict[str, Any],
        speaker: int,
        core_version: Optional[str] = None,
        output_file: Optional[BinaryIO] = None
    ) -> Union[bytes, None]:
        """
        音声合成する（キャンセル可能）

        Args:
            audio_query (Dict[str, Any]): 音声合成用のクエリ
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/cancellable_synthesis",
            params=params,
            json=audio_query
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    def multi_synthesis(
        self,
        audio_queries: List[Dict[str, Any]],
        speaker: int,
        core_version: Optional[str] = None,
        output_file: Optional[BinaryIO] = None
    ) -> Union[bytes, None]:
        """
        複数まとめて音声合成する

        Args:
            audio_queries (List[Dict[str, Any]]): 音声合成用のクエリのリスト
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/multi_synthesis",
            params=params,
            json=audio_queries
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    # 歌唱合成関連のAPI

    def sing_frame_audio_query(
        self, score: Dict[str, Any], speaker: int, core_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        歌唱音声合成用のクエリを作成する

        Args:
            score (Dict[str, Any]): 楽譜情報
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: 歌唱音声合成用のクエリ
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/sing_frame_audio_query",
            params=params,
            json=score
        )
        response.raise_for_status()
        return response.json()

    def sing_frame_f0(
        self, score: Dict[str, Any], frame_audio_query: Dict[str, Any], speaker: int, core_version: Optional[str] = None
    ) -> List[float]:
        """
        楽譜・歌唱音声合成用のクエリからフレームごとの基本周波数を得る

        Args:
            score (Dict[str, Any]): 楽譜情報
            frame_audio_query (Dict[str, Any]): 歌唱音声合成用のクエリ
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[float]: フレームごとの基本周波数
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        request_data = {
            "score": score,
            "frame_audio_query": frame_audio_query
        }

        response = requests.post(
            f"{self.base_url}/sing_frame_f0",
            params=params,
            json=request_data
        )
        response.raise_for_status()
        return response.json()

    def sing_frame_volume(
        self, score: Dict[str, Any], frame_audio_query: Dict[str, Any], speaker: int, core_version: Optional[str] = None
    ) -> List[float]:
        """
        楽譜・歌唱音声合成用のクエリからフレームごとの音量を得る

        Args:
            score (Dict[str, Any]): 楽譜情報
            frame_audio_query (Dict[str, Any]): 歌唱音声合成用のクエリ
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[float]: フレームごとの音量
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        request_data = {
            "score": score,
            "frame_audio_query": frame_audio_query
        }

        response = requests.post(
            f"{self.base_url}/sing_frame_volume",
            params=params,
            json=request_data
        )
        response.raise_for_status()
        return response.json()

    def frame_synthesis(
        self,
        frame_audio_query: Dict[str, Any],
        speaker: int,
        core_version: Optional[str] = None,
        output_file: Optional[BinaryIO] = None
    ) -> Union[bytes, None]:
        """
        歌唱音声合成を行う

        Args:
            frame_audio_query (Dict[str, Any]): 歌唱音声合成用のクエリ
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/frame_synthesis",
            params=params,
            json=frame_audio_query
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    # モーフィング関連のAPI

    def morphable_targets(
        self, base_style_ids: List[int], core_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        指定したスタイルに対してモーフィングが可能か判定する

        Args:
            base_style_ids (List[int]): ベーススタイルIDのリスト
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: モーフィング可能かどうかの情報
        """
        params: Dict[str, str] = {}
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/morphable_targets",
            params=params,
            json=base_style_ids
        )
        response.raise_for_status()
        return response.json()

    def synthesis_morphing(
        self,
        audio_query: Dict[str, Any],
        base_speaker: int,
        target_speaker: int,
        morph_rate: float,
        core_version: Optional[str] = None,
        output_file: Optional[BinaryIO] = None
    ) -> Union[bytes, None]:
        """
        2種類のスタイルでモーフィングした音声を合成する

        Args:
            audio_query (Dict[str, Any]): 音声合成用のクエリ
            base_speaker (int): ベーススピーカーID
            target_speaker (int): ターゲットスピーカーID
            morph_rate (float): モーフィングの割合 (0.0〜1.0)
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        if not 0.0 <= morph_rate <= 1.0:
            raise ValueError("morph_rate must be between 0.0 and 1.0")

        params: Dict[str, Union[str, int, float]] = {
            "base_speaker": base_speaker,
            "target_speaker": target_speaker,
            "morph_rate": morph_rate
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/synthesis_morphing",
            params=params,
            json=audio_query
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    # その他のユーティリティAPI

    def connect_waves(self, waves: List[str], output_file: Optional[BinaryIO] = None) -> Union[bytes, None]:
        """
        base64エンコードされた複数のwavデータを一つに結合する

        Args:
            waves (List[str]): base64エンコードされたwavデータのリスト
            output_file (Optional[BinaryIO], optional): 出力ファイル. Defaults to None.

        Returns:
            Union[bytes, None]: 音声データ(output_fileがNoneの場合)
        """
        response = requests.post(
            f"{self.base_url}/connect_waves",
            json=waves
        )
        response.raise_for_status()

        if output_file is not None:
            output_file.write(response.content)
            return None
        return response.content

    def validate_kana(self, text: str) -> bool:
        """
        テキストがAquesTalk 風記法に従っているか判定する

        Args:
            text (str): 判定する文字列

        Returns:
            bool: 判定結果
        """
        params = {
            "text": text
        }
        response = requests.post(
            f"{self.base_url}/validate_kana", params=params)
        response.raise_for_status()
        return response.json()

    def initialize_speaker(
        self, speaker: int, skip_reinit: bool = False, core_version: Optional[str] = None
    ) -> None:
        """
        指定されたスタイルを初期化する

        Args:
            speaker (int): スピーカーID
            skip_reinit (bool, optional): 既に初期化済みのスタイルの再初期化をスキップするか. Defaults to False.
            core_version (Optional[str], optional): コアバージョン. Defaults to None.
        """
        params: Dict[str, Union[str, int, bool]] = {
            "speaker": speaker,
            "skip_reinit": skip_reinit
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.post(
            f"{self.base_url}/initialize_speaker", params=params)
        response.raise_for_status()

    def is_initialized_speaker(self, speaker: int, core_version: Optional[str] = None) -> bool:
        """
        指定されたスタイルが初期化されているかどうかを返す

        Args:
            speaker (int): スピーカーID
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            bool: 初期化済みかどうか
        """
        params: Dict[str, Union[str, int]] = {
            "speaker": speaker
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(
            f"{self.base_url}/is_initialized_speaker", params=params)
        response.raise_for_status()
        return response.json()

    def supported_devices(self, core_version: Optional[str] = None) -> Dict:
        """
        対応デバイスの一覧を取得する

        Args:
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: 対応デバイスの情報
        """
        params: Dict[str, str] = {}
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(
            f"{self.base_url}/supported_devices", params=params)
        response.raise_for_status()
        return response.json()

    # プリセット関連のAPI

    def get_presets(self) -> List[Dict[str, Any]]:
        """
        エンジンが保持しているプリセットの設定を返す

        Returns:
            List[Dict[str, Any]]: プリセットのリスト
        """
        response = requests.get(f"{self.base_url}/presets")
        response.raise_for_status()
        return response.json()

    def add_preset(self, preset: Dict[str, Any]) -> int:
        """
        新しいプリセットを追加する

        Args:
            preset (Dict[str, Any]): 新しいプリセット

        Returns:
            int: 追加したプリセットのプリセットID
        """
        response = requests.post(f"{self.base_url}/add_preset", json=preset)
        response.raise_for_status()
        return response.json()

    def update_preset(self, preset: Dict[str, Any]) -> int:
        """
        既存のプリセットを更新する

        Args:
            preset (Dict[str, Any]): 更新するプリセット

        Returns:
            int: 更新したプリセットのプリセットID
        """
        response = requests.post(f"{self.base_url}/update_preset", json=preset)
        response.raise_for_status()
        return response.json()

    def delete_preset(self, preset_id: int) -> None:
        """
        既存のプリセットを削除する

        Args:
            preset_id (int): 削除するプリセットのプリセットID
        """
        params = {
            "id": preset_id
        }
        response = requests.post(
            f"{self.base_url}/delete_preset", params=params)
        response.raise_for_status()

    # スピーカー情報関連のAPI

    def speakers(self, core_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        喋れるキャラクターの情報の一覧を返す

        Args:
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: キャラクター情報のリスト
        """
        params: Dict[str, str] = {}
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(f"{self.base_url}/speakers", params=params)
        response.raise_for_status()
        return response.json()

    def speaker_info(
        self, speaker_uuid: str, resource_format: str = "base64", core_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        UUIDで指定された喋れるキャラクターの情報を返す

        Args:
            speaker_uuid (str): キャラクターのUUID
            resource_format (str, optional): リソースの形式. "base64" または "url". Defaults to "base64".
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: キャラクターの追加情報
        """
        params: Dict[str, str] = {
            "speaker_uuid": speaker_uuid,
            "resource_format": resource_format
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(f"{self.base_url}/speaker_info", params=params)
        response.raise_for_status()
        return response.json()

    def singers(self, core_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        歌えるキャラクターの情報の一覧を返す

        Args:
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            List[Dict[str, Any]]: キャラクター情報のリスト
        """
        params: Dict[str, str] = {}
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(f"{self.base_url}/singers", params=params)
        response.raise_for_status()
        return response.json()

    def singer_info(
        self, speaker_uuid: str, resource_format: str = "base64", core_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        UUIDで指定された歌えるキャラクターの情報を返す

        Args:
            speaker_uuid (str): キャラクターのUUID
            resource_format (str, optional): リソースの形式. "base64" または "url". Defaults to "base64".
            core_version (Optional[str], optional): コアバージョン. Defaults to None.

        Returns:
            Dict[str, Any]: キャラクターの追加情報
        """
        params: Dict[str, str] = {
            "speaker_uuid": speaker_uuid,
            "resource_format": resource_format
        }
        if core_version is not None:
            params["core_version"] = core_version

        response = requests.get(f"{self.base_url}/singer_info", params=params)
        response.raise_for_status()
        return response.json()

    # ユーザー辞書関連のAPI

    def get_user_dict_words(self) -> Dict[str, Any]:
        """
        ユーザー辞書に登録されている単語の一覧を返す

        Returns:
            Dict[str, Any]: 単語のUUIDとその詳細
        """
        response = requests.get(f"{self.base_url}/user_dict")
        response.raise_for_status()
        return response.json()

    def add_user_dict_word(
        self,
        surface: str,
        pronunciation: str,
        accent_type: int,
        word_type: Optional[WordTypes] = None,
        priority: Optional[int] = None
    ) -> str:
        """
        ユーザー辞書に言葉を追加する

        Args:
            surface (str): 言葉の表層形
            pronunciation (str): 言葉の発音（カタカナ）
            accent_type (int): アクセント型（音が下がる場所を指す）
            word_type (Optional[WordTypes], optional): 品詞. Defaults to None.
            priority (Optional[int], optional): 単語の優先度（0から10までの整数）. Defaults to None.

        Returns:
            str: 追加された言葉のUUID
        """
        params: Dict[str, Union[str, int]] = {
            "surface": surface,
            "pronunciation": pronunciation,
            "accent_type": accent_type
        }
        if word_type is not None:
            params["word_type"] = word_type.value
        if priority is not None:
            if not 0 <= priority <= 10:
                raise ValueError("priority must be between 0 and 10")
            params["priority"] = priority

        response = requests.post(
            f"{self.base_url}/user_dict_word", params=params)
        response.raise_for_status()
        return response.json()

    def rewrite_user_dict_word(
        self,
        word_uuid: str,
        surface: str,
        pronunciation: str,
        accent_type: int,
        word_type: Optional[WordTypes] = None,
        priority: Optional[int] = None
    ) -> None:
        """
        ユーザー辞書に登録されている言葉を更新する

        Args:
            word_uuid (str): 更新する言葉のUUID
            surface (str): 言葉の表層形
            pronunciation (str): 言葉の発音（カタカナ）
            accent_type (int): アクセント型（音が下がる場所を指す）
            word_type (Optional[WordTypes], optional): 品詞. Defaults to None.
            priority (Optional[int], optional): 単語の優先度（0から10までの整数）. Defaults to None.
        """
        params: Dict[str, Union[str, int]] = {
            "surface": surface,
            "pronunciation": pronunciation,
            "accent_type": accent_type
        }
        if word_type is not None:
            params["word_type"] = word_type.value
        if priority is not None:
            if not 0 <= priority <= 10:
                raise ValueError("priority must be between 0 and 10")
            params["priority"] = priority

        response = requests.put(
            f"{self.base_url}/user_dict_word/{word_uuid}", params=params)
        response.raise_for_status()

    def delete_user_dict_word(self, word_uuid: str) -> None:
        """
        ユーザー辞書に登録されている言葉を削除する

        Args:
            word_uuid (str): 削除する言葉のUUID
        """
        response = requests.delete(
            f"{self.base_url}/user_dict_word/{word_uuid}")
        response.raise_for_status()

    def import_user_dict_words(self, import_dict_data: Dict[str, Any], override: bool = False) -> None:
        """
        他のユーザー辞書をインポートする

        Args:
            import_dict_data (Dict[str, Any]): インポートするユーザー辞書のデータ
            override (bool, optional): 重複したエントリがあった場合、上書きするかどうか. Defaults to False.
        """
        params: Dict[str, bool] = {
            "override": override
        }
        response = requests.post(
            f"{self.base_url}/import_user_dict",
            params=params,
            json=import_dict_data
        )
        response.raise_for_status()

    # バージョン情報関連のAPI

    def version(self) -> str:
        """
        エンジンのバージョンを取得する

        Returns:
            str: バージョン
        """
        response = requests.get(f"{self.base_url}/version")
        response.raise_for_status()
        return response.json()

    def core_versions(self) -> List[str]:
        """
        利用可能なコアのバージョン一覧を取得する

        Returns:
            List[str]: コアバージョンのリスト
        """
        response = requests.get(f"{self.base_url}/core_versions")
        response.raise_for_status()
        return response.json()

    def engine_manifest(self) -> Dict[str, Any]:
        """
        エンジンマニフェストを取得する

        Returns:
            Dict[str, Any]: エンジンマニフェスト
        """
        response = requests.get(f"{self.base_url}/engine_manifest")
        response.raise_for_status()
        return response.json()

    # 設定関連のAPI

    def setting_post(self, cors_policy_mode: CorsPolicyMode, allow_origin: Optional[str] = None) -> None:
        """
        設定を更新する

        Args:
            cors_policy_mode (CorsPolicyMode): CORS許可モード
            allow_origin (Optional[str], optional): 許可するオリジン. Defaults to None.
        """
        data: Dict[str, str] = {
            "cors_policy_mode": cors_policy_mode.value
        }
        if allow_origin is not None:
            data["allow_origin"] = allow_origin

        response = requests.post(
            f"{self.base_url}/setting",
            data=data
        )
        response.raise_for_status()


# 簡易使用例
if __name__ == "__main__":
    client = VOICEVOXClient()
    # スピーカー一覧を取得
    speakers = client.speakers()
    print(f"利用可能なスピーカー: {len(speakers)}")

    # 最初のスピーカーで音声合成のサンプル
    if speakers:
        speaker_id = speakers[0]["styles"][0]["id"]
        # 音声合成用のクエリを作成
        query = client.audio_query("こんにちは、VOICEVOXです。", speaker_id)
        # 音声合成を実行して保存
        with open("output.wav", "wb") as f:
            client.synthesis(query, speaker_id, output_file=f)
        print("output.wav に音声を保存しました。")
