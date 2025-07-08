# VRCT-TTS

**VRCT-TTS: 多言語対応音声合成アプリケーション**

VRCTとVOICEVOXエンジンを連携させ、リアルタイム翻訳された音声メッセージを高品質な音声で再生するデスクトップアプリケーションです。VOICEVOX（日本語）とgTTS（多言語）の両方のTTSエンジンに対応し、翻訳前と翻訳後の音声を個別に制御できます。

## 🎯 主な機能

### 🌍 多言語対応
- **バイリンガルUI**: 英語・日本語の完全対応（設定即時切り替え）
- **翻訳前・翻訳後音声**: 原文と翻訳文を別々のTTSエンジンで再生
- **gTTS多言語サポート**: 60以上の言語に対応

### 🎵 高度な音声制御
- **デュアル出力対応**: メイン・サブの2つのオーディオデバイスに同時出力
- **リアルタイム音量・速度調整**: スライダーで即座に調整
- **ホスト別デバイス管理**: オーディオドライバごとのデバイス分類

### 🔌 WebSocket連携
- **リアルタイム通信**: VRCTからの翻訳メッセージをリアルタイム受信
- **柔軟なTTSエンジン選択**: 原文・翻訳文で異なるエンジンを使用可能
- **自動言語検出**: メッセージの言語を自動判定してTTSエンジンを選択

### ⚙️ 設定管理
- **即時自動保存**: 設定変更時に自動保存（手動保存不要）
- **詳細設定**: キャラクター、スタイル、デバイス、音量、速度を個別保存
- **言語設定の永続化**: UIの言語設定も保存

## 📋 必要条件

- **Python**: 3.8以上
- **VOICEVOX Engine**: 別途インストールが必要（日本語音声合成用）
- **OS**: Windows（pyaudiowpatch使用）

## 🚀 インストール方法

### 1. リポジトリの取得
```bash
git clone https://github.com/misyaguziya/VRCT-TTS.git
cd VRCT-TTS
```

### 2. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 3. VOICEVOX Engineの準備
1. [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine)をダウンロード
2. エンジンを起動（デフォルト: `http://127.0.0.1:50021`）

## 🎮 使用方法

### 基本の起動
```bash
python main.py
```

### 実行ファイルの使用（ビルド後）
```bash
dist\VRCT-TTS\VRCT-TTS.exe
```

## 🖥️ UIガイド

### メイン画面の構成
```
┌─────────────────────────────────────────────────────────────┐
│ VRCT-TTS                                                    │
├─────────────────┬───────────────────────────────────────────┤
│ WebSocket設定   │ TTS設定                                   │
│ ・サーバーURL   │ ・翻訳前エンジン選択                      │
│ ・接続/切断     │ ・翻訳後エンジン選択                      │
│                 │ ・再生有効/無効                           │
│ オーディオ設定  │                                           │
│ ・メイン出力    │ 音量・速度制御                            │
│ ・サブ出力      │ ・音量スライダー (0-100%)                 │
│ ・第2スピーカー │ ・速度スライダー (0.5x-2.0x)             │
│                 │                                           │
│ VOICEVOX設定    │ テスト再生                                │
│ ・キャラクター  │ ・テキスト入力                            │
│ ・声のスタイル  │ ・gTTS言語選択                           │
│                 │ ・VOICEVOX/gTTS再生ボタン                │
├─────────────────┴───────────────────────────────────────────┤
│ [停止・クリア]                                              │
├─────────────────────────────────────────────────────────────┤
│ ステータス表示    │ [言語切替] │ バージョン情報          │
└─────────────────────────────────────────────────────────────┘
```

### 主要機能の説明

#### 🌐 WebSocket連携
1. **URL設定**: VRCTのWebSocketサーバーURL（デフォルト: `ws://127.0.0.1:2231`）
2. **接続管理**: ワンクリックで接続・切断
3. **メッセージ処理**: JSON形式のメッセージを自動解析

#### 🔊 オーディオ設定
- **ホスト選択**: オーディオドライバー別の出力先選択
- **デバイス選択**: 具体的な出力デバイスの指定
- **デュアル出力**: メインとサブの2つのデバイスへの同時出力

#### 🎭 VOICEVOX設定
- **キャラクター選択**: 利用可能な全キャラクターから選択
- **スタイル選択**: 選択したキャラクターの声質バリエーション

#### 🎚️ 音響制御
- **音量制御**: 0-100%のリアルタイム調整
- **速度制御**: 0.5倍速-2.0倍速の再生速度調整（gTTSのみ）

## 🔧 設定ファイル

アプリケーションは `config.json` に以下の設定を自動保存します：

```json
{
  "speaker_id": 1,
  "device_index": 0,
  "device_index_2": 1,
  "speaker_2_enabled": false,
  "host_name": "All",
  "host_name_2": "All",
  "volume": 0.8,
  "speed": 1.0,
  "ws_url": "ws://127.0.0.1:2231",
  "gtts_lang": "English",
  "source_tts_engine": "VOICEVOX",
  "dest_tts_engine": "gTTS",
  "play_source": false,
  "play_dest": true,
  "language": "English"
}
```

## 📁 プロジェクト構成

```
VRCT-TTS/
├── main.py                 # メインアプリケーション（GUI）
├── voicevox.py            # VOICEVOX Engine APIクライアント
├── voicevox_speaker.py    # VOICEVOX音声再生クラス
├── gTTS_speaker.py        # gTTS音声再生クラス
├── audio_player.py        # オーディオデバイス管理・再生
├── config.py              # 設定管理クラス
├── language.py            # 多言語UI文字列定義
├── vrct_languages.py      # VRCT対応言語マッピング
├── requirements.txt       # Python依存関係
├── build.bat              # ビルドスクリプト
├── VRCT-TTS.spec         # PyInstallerビルド設定
└── fonts/                 # UIフォント
    └── NotoSansJP-VariableFont_wght.ttf
```

## 🏗️ ビルド方法

### スタンドアローン実行ファイルの作成
```bash
build.bat
```

または手動でのビルド：
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --onedir --clean --name VRCT-TTS --noconsole main.py --add-data "./fonts:fonts"
```

ビルド完了後、`dist\VRCT-TTS\` フォルダに実行ファイルが生成されます。

## 🔗 VRCT連携の詳細

### サポートするメッセージフォーマット
```json
{
  "type": "SENT",
  "message": "Hello world",
  "src_languages": {"1": {"language": "English"}},
  "dst_languages": {"1": {"language": "Japanese"}},
  "translation": ["こんにちは世界"]
}
```

### TTS再生フロー
1. **メッセージ受信**: WebSocketからJSONメッセージを受信
2. **言語判定**: 原文・翻訳文の言語を識別
3. **エンジン選択**: 設定に基づいてTTSエンジンを選択
4. **音声合成**: 選択されたエンジンで音声生成
5. **デバイス出力**: 指定されたオーディオデバイスで再生

## 🌟 高度な機能

### デュアルTTSエンジン
- **原文用エンジン**: VOICEVOX（日本語）またはgTTS（多言語）
- **翻訳文用エンジン**: gTTS（多言語）またはVOICEVOX（日本語）
- **個別制御**: 原文・翻訳文の再生を個別にオン/オフ

### リアルタイム音響調整
- **音量調整**: 全エンジン共通の音量制御
- **速度調整**: gTTSの再生速度をリアルタイム変更
- **即座反映**: スライダー操作で設定即座に適用

### インテリジェントなデバイス管理
- **ホスト分類**: DirectSound、WASAPI、MMEなどドライバー別管理
- **自動選択**: デバイス未選択時の自動選択機能
- **設定復元**: 前回使用デバイスの自動復元

## ⚠️ 注意事項

- **VOICEVOX Engine**: 必ず事前に起動しておく必要があります
- **音声ファイル**: 一時的な音声データはメモリ内で処理されます
- **ネットワーク**: gTTSはインターネット接続が必要です
- **パフォーマンス**: 長時間の連続使用時はメモリ使用量にご注意ください

## 📝 ライセンス

このプロジェクトはMITライセンスで提供されています。

**使用ライブラリとその制約：**
- [VOICEVOX](https://voicevox.hiroshiba.jp/): 各キャラクターの利用規約に従ってください
- gTTS: Google Translate APIの利用規約に従ってください

## 🙏 謝辞

- **VOICEVOX**: 高品質な日本語音声合成エンジンを提供
- **gTTS**: Google Translate APIによる多言語音声合成
- **VRCT**: VRChat翻訳ツールとの連携機能を提供
