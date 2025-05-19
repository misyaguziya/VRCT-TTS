# VRCT-VOICEVOX-Connector

## VRCTとVOICEVOXの連携による音声認識による音声合成ツール

VRCTの文字起こし機能 と VOICEVOX エンジンの音声合成の接続を行い、マイクの文字起こし結果をVOICEVOXの音声でスピーカーから出力するデモアプリケーションです。
テキスト入力による再生モードとWebSocketを使用した外部アプリケーションからのメッセージ受信モードの2つの実行モードをサポートしています。

## 概要

このアプリケーションは以下の機能を提供します：

- グラフィカルインターフェースによる直感的な操作
- WebSocketを通じて外部アプリケーション（例：VRCT）からのメッセージを受信し、自動的に音声合成を行うモード
- VOICEVOXの全キャラクターとスタイルに対応
- 設定の保存と再利用（デバイス、話者、音量、WebSocket URLなど）

## 必要条件

- Python 3.8以上
- VOICEVOX エンジン（別途ダウンロードが必要）
- 必要なPythonライブラリ（requirements.txtに記載）
- VRCT（別途ダウンロードが必要）

## インストール方法

### 1. リポジトリをクローンまたはダウンロードする

```bash
git clone https://github.com/misyaguziya/VRCT-VOICEVOX-Connector.git
cd VRCT-VOICEVOX-Connector
```

### 2. 依存関係をインストールする

```bash
pip install -r requirements.txt
```

または、同梱のbuild.batを使用してインストールとビルドを行うこともできます：

```bash
./build.bat
```

### 3. VOICEVOX エンジンをインストールして起動する

1. [サイト](https://github.com/VOICEVOX/voicevox_engine)からVOICEVOX エンジンをダウンロードして展開
2. VOICEVOX エンジンを起動
3. VOICEVOX エンジンが起動していることを確認（デフォルトでは http://127.0.0.1:50021 でサービスが提供されます）

## 使用方法

### アプリケーションの実行

```bash
python main.py
```

または、ビルドされた実行ファイルを使用する場合：

```bash
dist\VTVV-Connector\VTVV-Connector.exe
```

アプリケーションはグラフィカルインターフェース（GUI）モードで起動します。

## グラフィカルインターフェース

アプリケーションはGUIモードで動作し、以下の機能を視覚的に操作できます：

- 出力デバイスの選択（ドロップダウンリスト）
- VOICEVOXキャラクターとスタイルの選択
- 音量調整スライダー（0%〜100%）
- テキスト入力エリアによる直接テキスト入力と音声合成
- WebSocketサーバーの設定と接続状態表示
- 設定の保存と読み込み

GUIモードでは、直感的な操作で各種設定を調整しながら音声合成を行うことができます。音量調整スライダーを使うことで、リアルタイムに出力音声の大きさをコントロールすることが可能です。また、テキストエリアから直接テキストを入力して音声合成することもできます。

### WebSocketクライアント機能の使用方法

この機能は [VRCT](https://github.com/misyaguziya/VRCT)（VRChat用翻訳/文字起こしチャットツール）との連携を前提としています。VRCTが送信するWebSocketメッセージを受信して自動的に音声合成を行います。

1. VRCTを起動し、WebSocketサーバーを有効にする（デフォルト: `ws://127.0.0.1:2231`）
2. アプリケーションのGUIでWebSocketサーバーのURLを確認または変更（デフォルトでVRCTと同じ `ws://127.0.0.1:2231` を使用）
3. GUIでオーディオ出力デバイスを選択
4. GUIで使用するVOICEVOXキャラクターとスタイルを選択
5. 必要に応じてスライダーで音量を調整（デフォルト: 80%）
6. 「接続」ボタンをクリックしてWebSocketサーバーに接続
7. WebSocketサーバーからのメッセージを待機（プログラムは自動的にVRCTからのメッセージを受信して音声合成を行います）

## 設定の保存と再利用

アプリケーションは以下の設定を `config.json` ファイルに保存し、次回起動時に再利用することができます：

- 選択したオーディオデバイス
- 選択したVOICEVOXキャラクターとスタイル
- 設定した音量レベル
- WebSocketサーバーのURL (WebSocketモードの場合)

起動時に前回の設定を使用するかどうかを選択できます。

## ファイル構成

- `main.py` - メインアプリケーションファイル
- `voicevox.py` - VOICEVOX APIクライアント
- `voicevox_speaker.py` - オーディオ出力とデバイス管理
- `config.py` - 設定の保存と読み込み
- `config.json` - 保存された設定（自動生成）
- `requirements.txt` - 依存関係リスト
- `build.bat` - ビルドスクリプト

## ビルド方法

同梱の `build.bat` を実行することで、PyInstallerを使用してスタンドアローンの実行ファイルを作成できます：

```bash
build.bat
```

ビルドが完了すると、`dist\VTVV-Connector` フォルダに実行ファイルと必要なリソースが生成されます。

## 注意事項

- VOICEVOX エンジンが起動している必要があります
- WebSocketモードでは、指定したURLでWebSocketサーバーが稼働している必要があります
- 生成された音声は、選択したオーディオデバイスから出力されます

## ライセンス

このプロジェクトはMITライセンスでオープンソースとして提供されています。VOICEVOXについては利用規約に従った使用を行ってください。

## 謝辞

このアプリケーションは[VOICEVOX](https://voicevox.hiroshiba.jp/)を使用しています。VOICEVOXの開発者および話者の方々に感謝いたします。
