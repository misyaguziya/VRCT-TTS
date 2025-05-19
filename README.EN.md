# VRCT-VOICEVOX-Connector

## Speech Recognition and Voice Synthesis Tool Using VRCT and VOICEVOX

This is a demo application that uses the VOICEVOX engine to synthesize speech and output it through speakers.
It supports two execution modes: an interactive mode with text input and a WebSocket mode that receives messages from external applications.

## Overview

This application provides the following features:

- Interactive mode that synthesizes voice from input text
- WebSocket mode that receives messages from external applications (e.g., VRCT) and automatically synthesizes voice
- Ability to select the output from multiple audio devices
- Support for all VOICEVOX characters and styles
- Saving and reusing settings (device, speaker, WebSocket URL, etc.)

## Requirements

- Python 3.8 or higher
- VOICEVOX Engine (requires separate installation)
- Required Python libraries (listed in requirements.txt)

## Installation

### 1. Clone or download the repository

```bash
git clone https://github.com/misyaguziya/VRCT-VOICEVOX-Connector.git
cd VRCT-VOICEVOX-Connector
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Alternatively, you can install and build using the included build.bat:

```bash
./build.bat
```

### 3. Install and start the VOICEVOX Engine

1. Download and extract the VOICEVOX Engine from the [website](https://github.com/VOICEVOX/voicevox_engine)
2. Start the VOICEVOX Engine
3. Verify that the VOICEVOX Engine is running (the service is provided at http://127.0.0.1:50021 by default)

## Usage

### Running the application

```bash
python main.py
```

Or, if using the built executable:

```bash
dist\VTVV-Connector\VTVV-Connector.exe
```

### Selecting Execution Mode

When starting, you can choose between two modes:

1. **Interactive Demo** - Synthesizes voice directly from text input in the console
2. **WebSocket Client Demo** - Automatically synthesizes voice by receiving messages from a WebSocket server

### How to Use the Interactive Demo

1. Select an audio output device (press Enter for the default device)
2. Select a VOICEVOX character and style to use
3. Enter the text you want to synthesize
4. Choose whether to save the audio as a file, if needed
5. Enter `q` to exit

### How to Use the WebSocket Client Demo

This mode is designed to work with [VRCT](https://github.com/misyaguziya/VRCT) (translation/transcription chat tool for VRChat). It receives WebSocket messages sent by VRCT and automatically synthesizes speech.

1. Launch VRCT and enable the WebSocket server (default: `ws://127.0.0.1:2231`)
2. Confirm or change the WebSocket server URL (uses the same default as VRCT: `ws://127.0.0.1:2231`)
3. Select an audio output device
4. Select a VOICEVOX character and style to use
5. Wait for messages from the WebSocket server (the program will automatically receive messages from VRCT and synthesize voice)
6. Press `Ctrl+C` to exit

## Saving and Reusing Settings

The application saves the following settings in the `config.json` file and can reuse them on the next startup:

- Selected audio device
- Selected VOICEVOX character and style
- WebSocket server URL (for WebSocket mode)

You can choose whether to use the previous settings when starting the application.

## File Structure

- `main.py` - Main application file
- `voicevox.py` - VOICEVOX API client
- `voicevox_speaker.py` - Audio output and device management
- `config.py` - Saving and loading settings
- `config.json` - Saved settings (automatically generated)
- `requirements.txt` - Dependency list
- `build.bat` - Build script

## Build Method

You can create a standalone executable using PyInstaller by running the included `build.bat`:

```bash
build.bat
```

After the build completes, the executable and necessary resources will be generated in the `dist\VRCT-VOICEVOX-Connector` folder.

## Integration with VRChat

The WebSocket client mode is primarily designed for integration with VRCT. VRCT is a tool that transcribes voices in VRChat and sends the text strings via WebSocket. This application receives those strings and converts them to voice using VOICEVOX.

1. Install and launch VRCT
2. Enable the WebSocket server in VRCT settings (default: `ws://127.0.0.1:2231`)
3. When you have a conversation in VRChat, VRCT transcribes the content and sends it via WebSocket
4. This application receives the message and reads it aloud in the voice of the configured VOICEVOX character

This integration allows you to play back voices heard in VRChat in the voice of your chosen character.

If receiving WebSocket messages from other applications, you will need to match the message format used by VRCT.

## Notes

- The VOICEVOX Engine must be running
- In WebSocket mode, a WebSocket server must be running at the specified URL
- The generated voice is output from the selected audio device

## License

This project is provided as open source under the MIT license. When using VOICEVOX, please adhere to its terms of use.

## Acknowledgements

This application uses [VOICEVOX](https://voicevox.hiroshiba.jp/). Thanks to the developers of VOICEVOX and the voice providers.
