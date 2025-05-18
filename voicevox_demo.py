import websocket
import json
import threading
import time
import html
from voicevox import VOICEVOXClient
from voicevox_speaker import VoicevoxSpeaker

# ...existing code...
def list_devices_and_speakers():
    """利用可能なデバイスとVOICEVOXのスピーカーを一覧表示する"""
    # オーディオデバイスの一覧を取示
    devices = VoicevoxSpeaker.list_audio_devices()
    print("\n=== 利用可能なオーディオデバイス ===")
    for i, device in enumerate(devices):
        print(f"{i}. {device['name']} (index: {device['index']}, channels: {device['channels']})")

    # VOICEVOXスピーカーの一覧を表示
    client = VOICEVOXClient()
    try:
        vv_speakers = client.speakers()
        print("\n=== 利用可能なVOICEVOXスピーカー ===")
        for speaker in vv_speakers:
            print(f"キャラクター: {speaker['name']}")
            for style in speaker["styles"]:
                print(f"  - スタイルID: {style['id']}, 名前: {style['name']}")
    except Exception as e:
        print(f"\nVOICEVOX Engineに接続できませんでした。エンジンが起動しているか確認してください。\nエラー: {e}")

    return devices


def synthesize_and_play(text: str, speaker_id: int, device_index: int = None, save_file: bool = False):
    """
    テキストを音声合成し、指定デバイスで再生する
    
    Args:
        text (str): 合成するテキスト
        speaker_id (int): VOICEVOXのスピーカーID
        device_index (int, optional): 出力デバイスのインデックス。Noneの場合はデフォルトデバイス。
        save_file (bool, optional): 音声ファイルを保存するかどうか。デフォルトはFalse。
    """
    client = VOICEVOXClient()
    speaker = VoicevoxSpeaker(output_device_index=device_index)
    
    print(f"\n「{text}」を合成します...")
    
    # 音声合成用クエリを作成
    query = client.audio_query(text, speaker_id)
    
    # 音声を合成
    audio_data = client.synthesis(query, speaker_id)
    
    # 必要に応じてファイルに保存
    if save_file:
        file_path = "voicevox_output.wav"
        with open(file_path, "wb") as f:
            f.write(audio_data)
        print(f"音声を {file_path} に保存しました")
    
    # 指定デバイスで再生
    device_name = "デフォルト" if device_index is None else f"インデックス {device_index}"
    print(f"デバイス '{device_name}' で再生します...")
    speaker.play_bytes(audio_data)
    print("再生完了")


def interactive_demo():
    """対話式で音声合成と再生を行うデモ"""
    # デバイスとスピーカーのリストを取得
    devices = list_devices_and_speakers()
    
    # VOICEVOXエンジンに接続
    client = VOICEVOXClient()
    
    try:
        # スピーカーの取得を試みる
        speakers = client.speakers()
    except Exception:
        print("\nVOICEVOX Engineに接続できません。エンジンが起動しているか確認してください。")
        return
        
    # デバイスの選択
    device_index = None
    if devices:
        choice = input("\nオーディオデバイスを選択してください (番号を入力、デフォルトはEnterキー): ")
        if choice.strip():
            try:
                device_index = devices[int(choice)]["index"]
            except (ValueError, IndexError):
                print("無効な選択です。デフォルトデバイスを使用します。")
    
    # スピーカーIDの選択
    speaker_id = None
    if speakers:
        print("\nスピーカーを選択してください:")
        available_styles = []
        for speaker in speakers:
            for style in speaker["styles"]:
                idx = len(available_styles)
                available_styles.append((style["id"], f"{speaker['name']} - {style['name']}"))
                print(f"{idx}. {available_styles[-1][1]} (ID: {style['id']})")
        
        choice = input("スピーカー番号を入力: ")
        try:
            speaker_id = available_styles[int(choice)][0]
        except (ValueError, IndexError):
            if speakers and speakers[0]["styles"]:
                speaker_id = speakers[0]["styles"][0]["id"]
                print(f"デフォルトスピーカーを使用します: {speakers[0]['name']} - {speakers[0]['styles'][0]['name']}")
            else:
                print("有効なスピーカーがありません。")
                return
    else:
        print("利用可能なスピーカーがありません。")
        return
    
    # テキスト入力と音声合成
    while True:
        text = input("\n合成するテキストを入力してください (終了するには 'q' を入力): ")
        if text.lower() == 'q':
            break
            
        save_file = input("音声をファイルとして保存しますか？ (y/n, デフォルトはn): ").lower() == 'y'
        
        synthesize_and_play(text, speaker_id, device_index, save_file)

def websocket_client_demo():
    """WebSocketクライアントとして受信したメッセージを音声合成するデモ"""
    # デバイスとスピーカーのリストを取得
    devices = list_devices_and_speakers()
    
    # VOICEVOXエンジンに接続
    client = VOICEVOXClient()
    
    try:
        # スピーカーの取得を試みる
        speakers = client.speakers()
    except Exception:
        print("\nVOICEVOX Engineに接続できません。エンジンが起動しているか確認してください。")
        return
        
    # デバイスの選択
    device_index = None
    if devices:
        choice = input("\nオーディオデバイスを選択してください (番号を入力、デフォルトはEnterキー): ")
        if choice.strip():
            try:
                device_index = devices[int(choice)]["index"]
            except (ValueError, IndexError):
                print("無効な選択です。デフォルトデバイスを使用します。")
    
    # スピーカーIDの選択
    speaker_id = None
    if speakers:
        print("\nスピーカーを選択してください:")
        available_styles = []
        for speaker in speakers:
            for style in speaker["styles"]:
                idx = len(available_styles)
                available_styles.append((style["id"], f"{speaker['name']} - {style['name']}"))
                print(f"{idx}. {available_styles[-1][1]} (ID: {style['id']})")
        
        choice = input("スピーカー番号を入力: ")
        try:
            speaker_id = available_styles[int(choice)][0]
        except (ValueError, IndexError):
            if speakers and speakers[0]["styles"]:
                speaker_id = speakers[0]["styles"][0]["id"]
                print(f"デフォルトスピーカーを使用します: {speakers[0]['name']} - {speakers[0]['styles'][0]['name']}")
            else:
                print("有効なスピーカーがありません。")
                return
    else:
        print("利用可能なスピーカーがありません。")
        return
    
    # WebSocket接続設定
    ws_url = "ws://127.0.0.1:2231"
    
    # WebSocketイベントハンドラ
    def on_message(ws, message):
        try:
            data = json.loads(message)
            if data.get("type") == "SENT":
                received_message = data.get("message", "")
                
                # エスケープされた日本語文字列をデコード
                decoded_message = html.unescape(received_message)
                print(f"\n受信したメッセージ: {decoded_message}")
                
                # 音声合成して再生
                synthesize_and_play(decoded_message, speaker_id, device_index, False)
        except json.JSONDecodeError as e:
            print(f"JSONデコードエラー: {e}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
    
    def on_error(ws, error):
        print(f"WebSocket エラー: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"WebSocket接続が閉じられました - ステータスコード: {close_status_code}, メッセージ: {close_msg}")
    
    def on_open(ws):
        print(f"WebSocket接続が確立されました: {ws_url}")
        print("メッセージ受信待機中... (終了するには Ctrl+C を押してください)")
    
    # WebSocketクライアントの起動
    print(f"\nWebSocketサーバーに接続します: {ws_url}")
    ws = websocket.WebSocketApp(ws_url,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)
    
    # WebSocketクライアントを別スレッドで実行
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # メインスレッドを継続（Ctrl+Cで終了するまで）
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n終了します...")
        ws.close()

if __name__ == "__main__":
    print("===== VOICEVOX音声合成とスピーカー出力のデモ =====")
    print("注意: VOICEVOX Engineが起動している必要があります")
    
    print("\n実行モードを選択してください:")
    print("1. 対話式デモ")
    print("2. WebSocketクライアントデモ")
    
    choice = input("選択 (1または2): ")
    
    if choice == "2":
        websocket_client_demo()
    else:
        interactive_demo()