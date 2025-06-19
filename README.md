# VRCT-TTS-Connector (Dual Engine: gTTS & VOICEVOX)

## VRCTとgTTS/VOICEVOXの連携による多言語・高品質音声合成ツール

VRCT (VRChat Transcription / Translation tool) と連携し、リアルタイムで音声合成を行うためのアプリケーションです。
このコネクタは**gTTS (Google Text-to-Speech)**による多言語オンライン音声合成と、**VOICEVOX**による高品質な日本語ローカル音声合成の両方をサポートします。
アプリケーションはWebSocketサーバーとして動作し、VRCTや他のカスタムクライアントからのリクエストに応じて、選択されたTTSエンジンを使用して音声合成を行い、音声データを返します。

**重要な注意点:**
-   **gTTSの利用:** 音声合成時にアクティブなインターネット接続が必要です。
-   **VOICEVOXの利用:** ローカルシステム上でVOICEVOXエンジン（バージョン0.14以降推奨）を起動し、アクセス可能（デフォルトURL: `http://127.0.0.1:50021`）にしておく必要があります。

## 主な機能

-   **デュアルTTSエンジン対応:**
    -   **gTTS:** Google翻訳のTTSを利用した多言語対応（オンライン必須）。
    -   **VOICEVOX:** ローカルエンジンを利用した高品質な日本語音声合成。
-   **UIによるエンジン選択:** GUI上で使用するTTSエンジン（gTTSまたはVOICEVOX）を簡単に切り替え可能。
-   **動的な音声オプション:** 選択したエンジンに応じて、利用可能な言語/キャラクターやスタイル/地域アクセントのオプションがGUIに表示されます。
-   **WebSocketサーバー:** 外部アプリケーションからのリクエストをWebSocket経由で受け付け、音声合成結果（MP3またはWAV）を返します。
-   **音声バリエーション:**
    -   gTTS: TLD（Top-Level Domain）オプションによる地域アクセントの選択。
    -   VOICEVOX: キャラクターとスタイルの選択。
-   **設定GUI:**
    -   WebSocketサーバーのURL（ホスト・ポート）設定。
    -   アクティブTTSエンジンの選択と、エンジンごとの音声設定（言語、TLD、キャラクター、スタイル）。
    -   テスト再生機能、音量調整（ローカルテスト再生用）。
-   **設定の保存と再利用:** GUIでの設定は `config.json` に保存され、次回起動時に読み込まれます。
-   **オーディオキャッシュ:** 合成された音声はキャッシュされ、同じリクエストには高速に応答します（エンジンごと、テキスト、言語、音声パラメータでキー生成）。

## 必要条件

-   Python 3.11以上 (推奨)
-   必要なPythonライブラリ（`requirements.txt`に記載）
-   **gTTS利用時:** アクティブなインターネット接続。
-   **VOICEVOX利用時:** ローカルでVOICEVOXエンジンが起動しており、`http://127.0.0.1:50021` (デフォルト) でアクセス可能であること。
-   VRCT（連携する場合）または他のWebSocketクライアント。

## インストール方法

### 1. リポジトリをクローンまたはダウンロード

```bash
# Replace with actual repo URL if forked/changed
git clone https://github.com/your-repo/VRCT-TTS-Connector.git
cd VRCT-TTS-Connector
```

### 2. 依存関係をインストール

仮想環境の作成を強く推奨します:
```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows (cmd.exe):
# venv\Scripts\activate.bat
# Windows (PowerShell):
# venv\Scripts\Activate.ps1
```

ライブラリをインストール:
```bash
pip install -r requirements.txt
```

### 3. VOICEVOX エンジン (VOICEVOXを利用する場合)

1.  [公式サイト](https://voicevox.hiroshiba.jp/)または[GitHubリポジトリ](https://github.com/VOICEVOX/voicevox_engine)からVOICEVOXエンジンをダウンロードし、インストール/展開します。
2.  VOICEVOXエンジンを起動します。
3.  エンジンがデフォルトURL (`http://127.0.0.1:50021`) でサービスを提供していることを確認します。

## 使用方法

### アプリケーションの実行

```bash
python main.py
```
ビルド済みの実行ファイルを使用する場合（`build.bat`等で作成後）:
```bash
dist\VTVV-Connector\VTVV-Connector.exe # Windowsでの例
```
アプリケーションはGUIモードで起動します。

## グラフィカルインターフェース (GUI)

-   **WebSocketサーバーURL:** このコネクタが起動するWebSocketサーバーのホストとポートを指定します (例: `ws://127.0.0.1:8765`)。
-   **Start/Stop WebSocket Server Button:** 内蔵WebSocketサーバーを開始・停止します。外部クライアントはこのURLに接続します。
-   **TTS Engine Radiobuttons ("gTTS" / "VOICEVOX"):** 使用する音声合成エンジンを選択します。VOICEVOXオプションは、エンジンが利用可能な場合にのみ有効になります。
-   **Dynamic Settings Area:**
    -   **gTTS選択時:**
        -   **gTTS Language:** gTTSで利用する言語を選択します（例: 'en', 'ja'）。
        -   **Region/Accent (TLD):** gTTSのTLD（トップレベルドメイン）を選択し、地域アクセントを調整します（例: 'Default (com)', 'UK (co.uk)'）。
    -   **VOICEVOX選択時:**
        -   **VOICEVOX Character:** 利用可能なVOICEVOXキャラクターを選択します。リストはVOICEVOXエンジンから動的に取得されます（エンジンが起動していない場合は表示されません）。
        -   **VOICEVOX Style:** 選択したキャラクターの利用可能なスタイルを選択します。
-   **Output Device:** ローカルでのテスト再生に使用するオーディオ出力デバイスを選択します。VOICEVOX利用時はこのデバイスが使用されます。`playsound` (gTTS再生時) は通常システムのデフォルトデバイスを使用します。
-   **Volume:** ローカルテスト再生時の音量です。VOICEVOX再生時は適用されますが、`playsound`でのMP3再生では現在直接適用されません。
-   **Test Text Entry & "Play Test Audio" Button:** 入力したテキストを、現在選択されているエンジンと音声設定で合成し、ローカルで再生します。
-   **Status Bar:** アプリケーションの状態やエラーメッセージを表示します。
-   **Save Settings Button:** 現在のUI設定（選択中エンジン、各エンジンの音声設定、WebSocket URLなど）を `config.json` に保存します。

*(ここにGUIのスクリーンショットを挿入すると、ユーザーの理解を助けます。例: エンジン選択、gTTS設定、VOICEVOX設定)*

## WebSocketサーバー機能

「Start WebSocket Server」ボタンを押すと、指定されたURLでWebSocketサーバーが起動します。

### APIエンドポイント

-   **URL:** GUIで設定したWebSocketサーバーURL (例: `ws://127.0.0.1:8765`)

### コマンドとレスポンス

クライアントはJSON形式のメッセージをサーバーに送信します。サーバーからの応答もJSON形式です。`TTS_SYNTHESIZE`成功時は、JSON応答の後にバイナリ音声データフレーム（MP3またはWAV）が続きます。

**共通応答フィールド:**
-   `status`: `"success"` または `"error"`
-   `request_id`: クライアントが送信したリクエストID
-   `message`: 処理結果に関するメッセージ
-   `code` (エラー時): エラーコード (例: `1000`:合成エラー, `1001`:無効なパラメータ, `1002`:JSONエラー, `500`:内部サーバーエラー)
-   `data` (成功時): コマンド固有のペイロード

**サポートされるコマンド:**

1.  **`TTS_SYNTHESIZE`**
    *   **説明:** テキストを音声合成。サーバー側でUI設定されているアクティブエンジンを使用。
    *   **リクエストパラメータ:**
        *   `command`: `"TTS_SYNTHESIZE"`
        *   `request_id`: 文字列 (必須)
        *   `type`: 文字列 ("SENT", "RECEIVED", "CHAT" - VRCT連携用。テキストと取得元を指定)
        *   `message`: 文字列 (typeが"SENT"または"CHAT"の場合の原文)
        *   `translation`: 文字列 (typeが"RECEIVED"の場合の翻訳文)
        *   `src_languages`: 文字列 (typeが"SENT"または"CHAT"の場合の原文言語コード)
        *   `dst_languages`: 文字列 (typeが"RECEIVED"の場合の翻訳文言語コード)
        *   `text`: 文字列 (上記type指定がない場合の直接テキスト指定)
        *   `language_code`: 文字列 (上記type指定がない場合の直接言語指定)
        *   `voice_id`: 文字列 (オプション。アクティブエンジンがgTTSならTLD、VOICEVOXならスタイルIDとして解釈。無効ならサーバーUIのデフォルトを使用)
    *   **成功時JSON応答:** `{"status": "success", ..., "data": {"audio_format": "mp3" or "wav"}}`
    *   **成功時バイナリ応答:** 上記JSONの後、MP3/WAV音声データ。

2.  **`TTS_GET_VOICES`**
    *   **説明:** サーバーの現在アクティブなTTSエンジンで利用可能な言語とボイスのリストを取得。
    *   **リクエストパラメータ:**
        *   `command`: `"TTS_GET_VOICES"`
        *   `request_id`: 文字列
    *   **成功時JSON応答 (`data`フィールド内):**
        *   `engine`: アクティブなエンジンの名前 ("gTTS" or "VOICEVOX")
        *   `languages`: 利用可能な言語コードのリスト (例: `["en", "ja", ...]`)
        *   `voices`: ボイス情報のリスト。
            *   gTTSの場合: `[{"id": "com", "name": "Default (com)", "language": "shared"}, ...]` (TLDリスト)
            *   VOICEVOXの場合: `[{"id": "3", "name": "ずんだもん - ノーマル", "language": "ja"}, ...]` (スピーカースタイルリスト)

3.  **`TTS_STOP`**
    *   **説明:** サーバー側で現在ローカルテスト再生中の音声を停止。
    *   **リクエストパラメータ:**
        *   `command`: `"TTS_STOP"`
        *   `request_id`: 文字列
    *   **成功時JSON応答:** `{"status": "success", "message": "Stop command acknowledged", ...}`

4.  **`TTS_SET_DEFAULT_VOICE`**
    *   **説明:** サーバーの現在アクティブなTTSエンジンのデフォルトボイスを設定 (UI設定に反映)。
    *   **リクエストパラメータ:**
        *   `command`: `"TTS_SET_DEFAULT_VOICE"`
        *   `request_id`: 文字列
        *   `voice_id`: 文字列 (gTTSならTLDコード、VOICEVOXならスタイルID)
        *   `language_code`: 文字列 (オプション、gTTSの場合にデフォルト言語も設定)
    *   **成功時JSON応答:** `{"status": "success", "message": "Default voice/style updated for [engine].", ...}`

5.  **`TTS_SET_GLOBAL_SETTINGS`**
    *   **説明:** サーバーのグローバル設定を変更。
    *   **リクエストパラメータ:**
        *   `command`: `"TTS_SET_GLOBAL_SETTINGS"`
        *   `request_id`: 文字列
        *   `settings`: オブジェクト (例: `{"active_engine": "VOICEVOX"}` または `{"default_language": "en"}`)
    *   **成功時JSON応答:** `{"status": "success", "message": "Global settings processed.", ...}`

## 設定の保存と再利用 (`config.json`)

アプリケーションは以下の主要な設定を `config.json` に保存します：
-   `active_tts_engine`: 現在選択されているTTSエンジン名 ("gTTS" または "VOICEVOX")
-   `gtts_selected_language`: gTTS用に選択された言語コード
-   `gtts_selected_tld_code`: gTTS用に選択されたTLDコード
-   `voicevox_selected_character_name`: VOICEVOX用に選択されたキャラクター名
-   `voicevox_selected_style_id`: VOICEVOX用に選択されたスタイルID
-   `ws_url`: WebSocketサーバーのURL
-   `device_index`, `device_index_2`, `speaker_2_enabled`, `host_name`, `host_name_2`, `volume`: オーディオデバイスと音量設定

## ファイル構成

-   `main.py`: メインアプリケーション (GUI、WebSocketサーバー)
-   `tts_engine.py`: TTSエンジン抽象化 (`TTSEngine`, `GTTSEngine`, `VoicevoxEngine`)
-   `voicevox.py`: (もしあれば)オリジナルのVOICEVOX APIクライアント (現在は`tts_engine.py`内の`VoicevoxEngine`が担当)
-   `voicevox_speaker.py`: オーディオデバイス列挙、WAV再生機能
-   `config.py`: 設定の保存/読み込み
-   `requirements.txt`: 依存ライブラリ
-   `vrct_connector_main.log`: アプリケーションのメインログファイル

## ビルド方法

PyInstallerを使用する場合、同梱の `build.bat` が利用できます（Windows）。他のOSでは適宜PyInstallerコマンドを調整してください。
```bash
build.bat
```
`dist`フォルダ内に実行可能ファイルが生成されます。

## 注意事項

-   **インターネット接続:** gTTS利用時は必須です。
-   **VOICEVOXエンジン:** VOICEVOX利用時は、事前にローカルでVOICEVOXエンジンを起動しておく必要があります。
-   **ファイアウォール:** Pythonやアプリケーションがネットワーク通信（特にWebSocketサーバーポートの開放）を許可されているか確認してください。
-   **ポート競合:** WebSocketサーバー用のポートが他のアプリケーションで使用中でないか確認してください。
-   **テスト再生音量:** gTTS (MP3) のテスト再生時、GUIの音量スライダーは現在適用されません。VOICEVOX (WAV) のテスト再生時は適用されます。

## ライセンス

このプロジェクトはMITライセンスです。gTTSはGoogleのサービス、VOICEVOXは該当ソフトウェアの利用規約に従ってください。

## 謝辞

-   `gTTS` ライブラリと Google Text-to-Speech
-   `VOICEVOX` プロジェクトおよびその開発者・音声提供者
-   `customtkinter`, `websockets`, `playsound` 等のライブラリ開発者
