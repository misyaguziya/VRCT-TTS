# VRCT-TTS-Connector (gTTS Edition)

## VRCTとgTTS (Google Text-to-Speech) の連携による多言語音声合成ツール

VRCT (VRChat Transcription / Translation tool) と連携し、gTTSを使用してリアルタイムで多言語の音声合成を行うためのアプリケーションです。
このコネクタはWebSocketサーバーとして動作し、VRCTや他のアプリケーションからのリクエストに応じて音声合成を行い、音声データを返します。

**重要: このアプリケーションはgTTSを使用するため、音声合成時にアクティブなインターネット接続が必要です。**

## 概要

このアプリケーションは以下の機能を提供します：

- **多言語対応:** gTTSがサポートする多くの言語で音声合成が可能です（例:英語、日本語、韓国語、フランス語など）。
- **WebSocketサーバー:** WebSocket経由で外部アプリケーション（例：VRCT）からのリクエストを受け付け、音声合成結果を返します。
- **音声バリエーション(TLD):** gTTSのTLD（Top-Level Domain）オプションを使用し、同じ言語でも地域アクセントのバリエーションを選択できます（例: 'en' で 'com', 'co.uk', 'com.au'など）。
- **設定GUI:**
    - WebSocketサーバーのURL（ホスト・ポート）を設定。
    - テスト再生用の言語とTLD（声のバリエーション）を選択。
    - テキスト入力による直接テスト再生。
    - 音量調整（ローカルテスト再生用）。
- **設定の保存と再利用:** GUIで設定した内容は `config.json` に保存され、次回起動時に読み込まれます。
- **オーディオキャッシュ:** 一度合成した音声はキャッシュされ、同じテキスト・言語・TLDの次回リクエスト時には高速に応答します。

## 必要条件

- Python 3.11以上 (推奨)
- 必要なPythonライブラリ（`requirements.txt`に記載）
- アクティブなインターネット接続（gTTSの利用に必須）
- VRCT（連携する場合）または他のWebSocketクライアント

## インストール方法

### 1. リポジトリをクローンまたはダウンロードする

```bash
git clone https://github.com/your-repo/VRCT-TTS-Connector.git # Replace with actual repo URL if forked/changed
cd VRCT-TTS-Connector
```

### 2. 依存関係をインストールする

仮想環境の作成を推奨します:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows
```

その後、ライブラリをインストールします:
```bash
pip install -r requirements.txt
```

## 使用方法

### アプリケーションの実行

```bash
python main.py
```
または、ビルドされた実行ファイルを使用する場合（`build.bat`等で作成後）：
```bash
dist\VTVV-Connector\VTVV-Connector.exe # Example path
```

アプリケーションはグラフィカルインターフェース（GUI）モードで起動します。

## グラフィカルインターフェース (GUI)

- **WebSocketサーバーURL:** サーバーを起動するホストとポートを指定します (例: `ws://127.0.0.1:8765`)。
- **Start/Stop WebSocket Server:** このボタンで内蔵WebSocketサーバーを開始・停止します。クライアントはこのURLに接続します。
- **キャラクター選択 (Language):** テスト再生用の言語を選択します (例: 'en', 'ja')。
- **声のスタイル (TLD/Voice):** テスト再生用のTLD（アクセント/地域バリエーション）を選択します (例: 'Default (com)', 'UK (co.uk)')。
- **出力デバイス / 第2出力デバイス:** ローカルでのテスト再生に使用するオーディオデバイスを選択します（`playsound`ライブラリの挙動に依存し、通常はデフォルトデバイスが使用されます）。
- **音量:** ローカルテスト再生時の音量です（`playsound`でのMP3再生では現在適用されません）。
- **テスト再生:** 入力したテキストを上記の言語・TLD設定で合成し、ローカルで再生します。
- **設定を保存:** 現在のUI設定（WebSocket URL、テスト用言語/TLD選択など）を `config.json` に保存します。

## WebSocketサーバー機能

アプリケーションを起動後、「Start WebSocket Server」ボタンを押すと、指定されたURLでWebSocketサーバーが起動します。VRCTや他のカスタムクライアントからこのサーバーに接続してTTS機能を利用できます。

### APIエンドポイント

- **URL:** GUIで設定したWebSocketサーバーURL (例: `ws://127.0.0.1:8765` - パスなし)

### コマンドとレスポンス

クライアントはJSON形式のメッセージをサーバーに送信します。サーバーからの応答もJSON形式ですが、`TTS_SYNTHESIZE`成功時はJSON応答の後にバイナリ音声データフレームが続きます。

**共通応答フィールド:**
- `status`: "success" または "error"
- `request_id`: クライアントが送信したリクエストID（エコーバック）
- `message`: 処理結果に関するメッセージ（エラー時は詳細）
- `code` (エラー時): エラーコード (例: 1000:合成エラー, 1001:無効なパラメータ, 1002:JSONデコードエラー, 500:内部サーバーエラー)
- `data` (成功時): コマンド固有のデータペイロード

**サポートされるコマンド:**

1.  **`TTS_SYNTHESIZE`**
    *   **説明:** 指定されたテキストを音声合成します。
    *   **リクエストパラメータ:**
        *   `command`: "TTS_SYNTHESIZE" (必須)
        *   `request_id`: 文字列 (必須、クライアント追跡用)
        *   `type`: 文字列 (必須、"SENT", "RECEIVED", "CHAT" - VRCT連携用)
        *   `message`: 文字列 (typeが"SENT"または"CHAT"の場合の原文)
        *   `translation`: 文字列 (typeが"RECEIVED"の場合の翻訳文)
        *   `src_languages`: 文字列 (typeが"SENT"または"CHAT"の場合の原文言語コード)
        *   `dst_languages`: 文字列 (typeが"RECEIVED"の場合の翻訳文言語コード)
        *   `text`: 文字列 (typeに基づかない直接指定の場合、フォールバック)
        *   `language_code`: 文字列 (typeに基づかない直接指定の場合の言語コード、フォールバック)
        *   `voice_id`: 文字列 (オプション、使用するTLDを指定。例: "com", "co.uk")
    *   **成功時JSON応答:** `{"status": "success", "message": "Audio synthesized", "request_id": "...", "data": {"audio_format": "mp3"}}`
    *   **成功時バイナリ応答:** 上記JSONの後、MP3音声データを含むバイナリフレーム。
    *   **エラー時JSON応答:** `{"status": "error", "message": "...", "request_id": "...", "code": ...}`

2.  **`TTS_GET_VOICES`**
    *   **説明:** 利用可能な言語と「ボイス」（TLDオプション）のリストを取得します。
    *   **リクエストパラメータ:**
        *   `command`: "TTS_GET_VOICES" (必須)
        *   `request_id`: 文字列 (必須)
    *   **成功時JSON応答:**
        ```json
        {
          "status": "success",
          "request_id": "...",
          "data": {
            "languages": ["en", "ja", "ko", ...],
            "voices": [
              {"id": "com", "name": "Default (com)", "language": "shared"},
              {"id": "co.uk", "name": "UK (co.uk)", "language": "shared"},
              ...
            ]
          }
        }
        ```
        (`language: "shared"` はTLDが複数の言語に適用可能であることを示します)

3.  **`TTS_STOP`**
    *   **説明:** 現在ローカルでテスト再生中の音声を停止しようとします（進行中のgTTSネットワークリクエストのキャンセルは不可）。
    *   **リクエストパラメータ:**
        *   `command`: "TTS_STOP" (必須)
        *   `request_id`: 文字列 (必須)
    *   **成功時JSON応答:** `{"status": "success", "message": "Stop command acknowledged", "request_id": "..."}`

4.  **`TTS_SET_DEFAULT_VOICE`** (プレースホルダー的実装)
    *   **説明:** サーバーのデフォルトボイス（TLD）を設定します。
    *   **リクエストパラメータ:**
        *   `command`: "TTS_SET_DEFAULT_VOICE" (必須)
        *   `request_id`: 文字列 (必須)
        *   `voice_id`: 文字列 (必須、設定するTLD。例: "co.uk")
    *   **成功時JSON応答:** `{"status": "success", "message": "Default voice (TLD) updated to ...", "request_id": "..."}`

5.  **`TTS_SET_GLOBAL_SETTINGS`** (プレースホルダー的実装)
    *   **説明:** サーバーのグローバルTTS設定（例: デフォルト言語）を行います。
    *   **リクエストパラメータ:**
        *   `command`: "TTS_SET_GLOBAL_SETTINGS" (必須)
        *   `request_id`: 文字列 (必須)
        *   `settings`: オブジェクト (例: `{"language": "ja"}`)
    *   **成功時JSON応答:** `{"status": "success", "message": "Global settings updated (partially implemented)", "request_id": "..."}`


## 設定の保存と再利用

アプリケーションは以下の設定を `config.json` ファイルに保存し、次回起動時に再利用します：
- WebSocketサーバーのURL
- テスト再生用の選択言語 (`gtts_language`)
- テスト再生用の選択TLD表示名 (`gtts_tld_name`)
- ローカル再生用のオーディオデバイス設定（`device_index`など、主にVoicevoxSpeaker由来だが保持）
- 音量 (`volume`)

## ファイル構成

- `main.py` - メインアプリケーションファイル (GUIおよびWebSocketサーバーロジック)
- `tts_engine.py` - TTSエンジン抽象化レイヤー (`TTSEngine`, `GTTSEngine`クラス)
- `config.py` - 設定の保存と読み込み
- `config.json` - 保存された設定（自動生成）
- `requirements.txt` - 依存関係リスト
- `build.bat` - （オプション）ビルドスクリプト
- `vrct_connector_main.log` - `main.py` のログファイル（自動生成）

## ビルド方法

同梱の `build.bat` を実行することで、PyInstallerを使用してスタンドアローンの実行ファイルを作成できます（`pyinstaller`が`requirements.txt`に含まれている場合）。

```bash
build.bat
```
ビルドが完了すると、`dist`フォルダ内に実行可能なアプリケーションが生成されます。

## 注意事項

- **インターネット接続が必須です。** gTTSはGoogleのオンラインサービスを利用するため、音声合成には常時インターネット接続が必要です。
- ファイアウォールが `main.py` やPythonによるネットワークアクセスをブロックしていないことを確認してください。
- WebSocketサーバーのポートが他のアプリケーションで使用されていないことを確認してください。
- ローカルでのテスト再生音量は、`playsound`ライブラリの制限により、GUIの音量スライダーでは調整されない場合があります。

## ライセンス

このプロジェクトはMITライセンスでオープンソースとして提供されています。gTTSの利用に関してはGoogleの利用規約に従ってください。

## 謝辞

- このアプリケーションは `gTTS` ライブラリおよびGoogle Text-to-Speechサービスを利用しています。
- UIには `customtkinter` を使用しています。
- WebSocketサーバー機能には `websockets` ライブラリを、テスト再生には `playsound` ライブラリを使用しています。
