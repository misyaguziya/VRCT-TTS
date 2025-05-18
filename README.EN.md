# VRCT-VOICEVOX-Connector

## Voice Synthesis Tool with Speech Recognition Integration between VRCT and VOICEVOX

This is a demo application that performs voice synthesis using VOICEVOX CORE and outputs through speakers.
It supports two operation modes: an interactive mode for text input and a message reception mode using WebSocket from external applications.

## Overview

This application provides the following features:

- Interactive mode for entering text and performing voice synthesis
- Mode to receive messages from external applications (e.g., VRCT) via WebSocket and automatically perform voice synthesis
- Option to select output destination from multiple audio devices
- Support for all VOICEVOX characters and styles
- Saving and reusing settings (device, speaker, WebSocket URL, etc.)

## Requirements

- Python 3.8 or higher
- VOICEVOX CORE (requires separate installation)
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

Or you can use the included build.bat to install and build:

```bash
./build.bat
```

### 3. Install and launch VOICEVOX CORE

1. Download and extract VOICEVOX CORE from the [site](https://github.com/VOICEVOX/voicevox_core)
2. Launch VOICEVOX CORE
3. Confirm that VOICEVOX CORE is running (by default, the service is provided at http://127.0.0.1:50021)

## Usage

### Running the Application

```bash
python main.py
```

Or, if using the built executable:

```bash
dist\VRCT-VOICEVOX-Connector\VRCT-VOICEVOX-Connector.exe
```

### Selecting Operation Mode

You can choose from the following two modes at startup:

1. **Interactive Demo** - Perform voice synthesis by directly entering text from the console
2. **WebSocket Client Demo** - Automatically perform voice synthesis by receiving messages from a WebSocket server

### How to Use the Interactive Demo

1. Select an audio output device (press Enter for the default device)
2. Select the VOICEVOX character and style to use
3. Enter the text you want to synthesize
4. Choose whether to save the audio as a file if needed
5. Enter `q` to exit

### How to Use the WebSocket Client Demo

This mode is designed for integration with [VRCT](https://github.com/misyaguziya/VRCT) (a translation/transcription chat tool for VRChat). It receives WebSocket messages sent by VRCT and automatically performs voice synthesis.

1. Launch VRCT and enable the WebSocket server (default: `ws://127.0.0.1:2231`)
2. Confirm or change the WebSocket server URL (uses the same default as VRCT: `ws://127.0.0.1:2231`)
3. Select an audio output device
4. Select the VOICEVOX character and style to use
5. Wait for messages from the WebSocket server (the program will automatically receive messages from VRCT and perform voice synthesis)
6. Press `Ctrl+C` to exit

## Saving and Reusing Settings

The application saves the following settings in a `config.json` file and can reuse them the next time it starts:

- Selected audio device
- Selected VOICEVOX character and style
- WebSocket server URL (for WebSocket mode)

You can choose whether to use the previous settings when starting.

## File Structure

- `main.py` - Main application file
- `voicevox.py` - VOICEVOX API client
- `voicevox_speaker.py` - Audio output and device management
- `config.py` - Save and load settings
- `config.json` - Saved settings (auto-generated)
- `requirements.txt` - Dependency list
- `build.bat` - Build script

## How to Build

Run the included `build.bat` to create a standalone executable using PyInstaller:

```bash
build.bat
```

After the build is complete, an executable file and necessary resources will be generated in the `dist\VRCT-VOICEVOX-Connector` folder.

## VRChat Integration

The WebSocket client mode is primarily designed for integration with VRCT. VRCT is a tool that transcribes audio from VRChat into text and sends that text via WebSocket. This application receives the text and converts it to speech using VOICEVOX.

1. Install and launch VRCT
2. Enable the WebSocket server in VRCT settings (default: `ws://127.0.0.1:2231`)
3. When conversations occur in VRChat, VRCT transcribes the content and sends it via WebSocket
4. This application receives the messages and reads them aloud in the voice of the configured VOICEVOX character

This integration makes it possible to reproduce audio heard in VRChat in the voice of a configured character.

If receiving WebSocket messages from other applications, the message format needs to match that of VRCT.

## Notes

- VOICEVOX CORE must be running
- In WebSocket mode, a WebSocket server must be running at the specified URL
- Generated audio is output from the selected audio device

## License

This project is provided as open source under the MIT license. Please use VOICEVOX in accordance with its terms of use.

## Acknowledgments

This application uses [VOICEVOX](https://voicevox.hiroshiba.jp/). Thanks to the developers of VOICEVOX and the voice actors.
