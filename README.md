# VRCT-VOICEVOX-Connector

## VRCTとVOICEVOXの連携による音声認識による音声合成ツール

VOICEVOX エンジンを使用して音声合成を行い、スピーカーから出力するデモアプリケーションです。
テキスト入力による対話式モードとWebSocketを使用した外部アプリケーションからのメッセージ受信モードの2つの実行モードをサポートしています。

## 概要

このアプリケーションは以下の機能を提供します：

- テキストを入力して音声合成を行う対話式モード
- WebSocketを通じて外部アプリケーション（例：VRCT）からのメッセージを受信し、自動的に音声合成を行うモード
- 複数のオーディオデバイスから出力先を選択可能
- VOICEVOXの全キャラクターとスタイルに対応
- 設定の保存と再利用（デバイス、話者、WebSocket URLなど）

## 必要条件

- Python 3.8以上
- VOICEVOX エンジン（別途インストールが必要）
- 必要なPythonライブラリ（requirements.txtに記載）

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

### 実行モードの選択

起動時に次の2つのモードから選択できます：

1. **対話式デモ** - コンソールから直接テキストを入力して音声合成を行います
2. **WebSocketクライアントデモ** - WebSocketサーバーからのメッセージを受信して自動的に音声合成します

### 対話式デモの使用方法

1. オーディオ出力デバイスを選択（デフォルトデバイスの場合は Enter キー）
2. 使用するVOICEVOXキャラクターとスタイルを選択
3. 合成したいテキストを入力
4. 必要に応じて音声をファイルとして保存するかどうかを選択
5. 終了するには `q` を入力

### WebSocketクライアントデモの使用方法

このモードは [VRCT](https://github.com/misyaguziya/VRCT)（VRChat用翻訳/文字起こしチャットツール）との連携を前提としています。VRCTが送信するWebSocketメッセージを受信して自動的に音声合成を行います。

1. VRCTを起動し、WebSocketサーバーを有効にする（デフォルト: `ws://127.0.0.1:2231`）
2. WebSocketサーバーのURLを確認または変更（デフォルトでVRCTと同じ `ws://127.0.0.1:2231` を使用）
3. オーディオ出力デバイスを選択
4. 使用するVOICEVOXキャラクターとスタイルを選択
5. WebSocketサーバーからのメッセージを待機（プログラムは自動的にVRCTからのメッセージを受信して音声合成を行います）
6. 終了するには `Ctrl+C` を押す

## 設定の保存と再利用

アプリケーションは以下の設定を `config.json` ファイルに保存し、次回起動時に再利用することができます：

- 選択したオーディオデバイス
- 選択したVOICEVOXキャラクターとスタイル
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

ビルドが完了すると、`dist\VRCT-VOICEVOX-Connector` フォルダに実行ファイルと必要なリソースが生成されます。

## VRChatとの連携

WebSocketクライアントモードは、主にVRCTとの連携を前提としています。VRCTは、VRChat内の音声を文字に起こし、その文字列をWebSocketを通じて送信するツールです。このアプリケーションはその文字列を受け取り、VOICEVOXを使用して音声に変換します。

1. VRCTをインストールして起動する
2. VRCTの設定でWebSocketサーバーを有効にする（デフォルト: `ws://127.0.0.1:2231`）
3. VRChat内で会話を行うと、VRCTがその内容を文字に起こし、WebSocketで送信
4. 本アプリケーションがメッセージを受信し、設定したVOICEVOXキャラクターの声で読み上げ

この連携により、VRChat内で聞いた音声を、設定したキャラクターの声で再生することが可能になります。

その他のアプリケーションからのWebSocketメッセージを受信する場合は、メッセージ形式をVRCTに合わせる必要があります。

## 注意事項

- VOICEVOX エンジンが起動している必要があります
- WebSocketモードでは、指定したURLでWebSocketサーバーが稼働している必要があります
- 生成された音声は、選択したオーディオデバイスから出力されます

## ライセンス

このプロジェクトはMITライセンスでオープンソースとして提供されています。VOICEVOXについては利用規約に従った使用を行ってください。

## 謝辞

このアプリケーションは[VOICEVOX](https://voicevox.hiroshiba.jp/)を使用しています。VOICEVOXの開発者および話者の方々に感謝いたします。
