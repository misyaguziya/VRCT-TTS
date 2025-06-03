import unittest
from unittest.mock import MagicMock, patch, call
import io
import wave
import os

from voicevox_speaker import VoicevoxSpeaker

# Create dummy WAV data for testing
def create_dummy_wav_data():
    # Creates a very short, silent WAV file in memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00\x00' * 10) # 10 frames of silence
    return buffer.getvalue()

DUMMY_WAV_BYTES = create_dummy_wav_data()
DUMMY_WAV_FILE = "dummy_test_audio.wav"

class TestVoicevoxSpeaker(unittest.TestCase):

    def setUp(self):
        # Create a dummy wav file for file playback tests
        with open(DUMMY_WAV_FILE, "wb") as f:
            f.write(DUMMY_WAV_BYTES)

        # Patch pyaudio before each test
        self.pyaudio_patch = patch('voicevox_speaker.pyaudio.PyAudio')
        self.mock_pyaudio_class = self.pyaudio_patch.start()
        self.mock_pyaudio_instance = self.mock_pyaudio_class.return_value

        # Mock the stream object that open() returns
        self.mock_stream = MagicMock()
        self.mock_pyaudio_instance.open.return_value = self.mock_stream

        # Mock get_format_from_width
        self.mock_pyaudio_instance.get_format_from_width.return_value = 8 # paInt16 for sampwidth 2

    def tearDown(self):
        # Stop the patcher
        self.pyaudio_patch.stop()
        # Remove the dummy wav file
        if os.path.exists(DUMMY_WAV_FILE):
            os.remove(DUMMY_WAV_FILE)

    def test_initialization_default(self):
        speaker = VoicevoxSpeaker()
        self.assertEqual(speaker.output_device_index, None)
        self.assertEqual(speaker.output_device_index_2, None)
        self.assertEqual(speaker.speaker_2_enabled, False)
        self.mock_pyaudio_class.assert_called_once()

    def test_initialization_with_devices(self):
        speaker = VoicevoxSpeaker(output_device_index=1, output_device_index_2=2, speaker_2_enabled=True)
        self.assertEqual(speaker.output_device_index, 1)
        self.assertEqual(speaker.output_device_index_2, 2)
        self.assertEqual(speaker.speaker_2_enabled, True)

    def test_play_bytes_single_speaker_default(self):
        speaker = VoicevoxSpeaker() # speaker_2_enabled is False by default
        speaker.play_bytes(DUMMY_WAV_BYTES)

        self.mock_pyaudio_instance.open.assert_called_once_with(
            format=8, # paInt16
            channels=1,
            rate=44100,
            output=True,
            output_device_index=None
        )
        self.mock_stream.write.assert_called()
        self.mock_stream.stop_stream.assert_called_once()
        self.mock_stream.close.assert_called_once()

    def test_play_bytes_second_speaker_disabled(self):
        speaker = VoicevoxSpeaker(output_device_index=1, output_device_index_2=2, speaker_2_enabled=False)
        speaker.play_bytes(DUMMY_WAV_BYTES)

        self.mock_pyaudio_instance.open.assert_called_once_with(
            format=8,
            channels=1,
            rate=44100,
            output=True,
            output_device_index=1
        )
        self.assertEqual(self.mock_pyaudio_instance.open.call_count, 1) # Ensure only one stream was opened
        self.mock_stream.write.assert_called()

    def test_play_bytes_second_speaker_enabled_and_valid(self):
        speaker = VoicevoxSpeaker(output_device_index=1, output_device_index_2=2, speaker_2_enabled=True)

        # Mock a second stream for the second device
        mock_stream_2 = MagicMock()
        self.mock_pyaudio_instance.open.side_effect = [self.mock_stream, mock_stream_2]

        speaker.play_bytes(DUMMY_WAV_BYTES)

        expected_calls = [
            call(format=8, channels=1, rate=44100, output=True, output_device_index=1),
            call(format=8, channels=1, rate=44100, output=True, output_device_index=2)
        ]
        self.mock_pyaudio_instance.open.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_pyaudio_instance.open.call_count, 2)

        self.mock_stream.write.assert_called()
        mock_stream_2.write.assert_called()
        self.mock_stream.stop_stream.assert_called_once()
        mock_stream_2.stop_stream.assert_called_once()
        self.mock_stream.close.assert_called_once()
        mock_stream_2.close.assert_called_once()

    def test_play_bytes_second_speaker_enabled_but_no_index(self):
        # If speaker_2_enabled is true but no index_2 is provided, it should only play on the primary.
        speaker = VoicevoxSpeaker(output_device_index=1, speaker_2_enabled=True) # output_device_index_2 is None
        speaker.play_bytes(DUMMY_WAV_BYTES)

        self.mock_pyaudio_instance.open.assert_called_once_with(
            format=8,
            channels=1,
            rate=44100,
            output=True,
            output_device_index=1
        )
        self.assertEqual(self.mock_pyaudio_instance.open.call_count, 1)
        self.mock_stream.write.assert_called()

    def test_play_file_second_speaker_enabled_and_valid(self):
        speaker = VoicevoxSpeaker(output_device_index=3, output_device_index_2=4, speaker_2_enabled=True)

        mock_stream_2 = MagicMock()
        self.mock_pyaudio_instance.open.side_effect = [self.mock_stream, mock_stream_2]

        speaker.play_file(DUMMY_WAV_FILE)

        expected_calls = [
            call(format=8, channels=1, rate=44100, output=True, output_device_index=3),
            call(format=8, channels=1, rate=44100, output=True, output_device_index=4)
        ]
        self.mock_pyaudio_instance.open.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(self.mock_pyaudio_instance.open.call_count, 2)

        self.mock_stream.write.assert_called()
        mock_stream_2.write.assert_called()

    def test_play_bytes_no_wait(self):
        speaker = VoicevoxSpeaker(output_device_index=1, output_device_index_2=2, speaker_2_enabled=True)
        mock_stream_2 = MagicMock()
        self.mock_pyaudio_instance.open.side_effect = [self.mock_stream, mock_stream_2]

        speaker.play_bytes(DUMMY_WAV_BYTES, wait=False)

        self.mock_stream.stop_stream.assert_not_called() # Should not be called if wait is False
        mock_stream_2.stop_stream.assert_not_called()
        self.mock_stream.close.assert_called_once()
        mock_stream_2.close.assert_called_once()

    def test_list_audio_devices_calls_pyaudio(self):
        # Reset the main class mock since list_audio_devices creates its own PyAudio instance
        self.pyaudio_patch.stop() # Stop instance-level patch
        pyaudio_class_patch = patch('voicevox_speaker.pyaudio.PyAudio')
        mock_pa_class = pyaudio_class_patch.start()
        mock_pa_instance = mock_pa_class.return_value

        mock_pa_instance.get_device_count.return_value = 1
        mock_pa_instance.get_device_info_by_index.return_value = {
            'name': 'Test Device',
            'maxOutputChannels': 2,
            'defaultSampleRate': 44100,
            'index': 0 # Ensure index is part of the mock
        }

        devices = VoicevoxSpeaker.list_audio_devices()

        mock_pa_class.assert_called_once()
        mock_pa_instance.get_device_count.assert_called_once()
        mock_pa_instance.get_device_info_by_index.assert_called_once_with(0)
        mock_pa_instance.terminate.assert_called_once()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['name'], 'Test Device')

        pyaudio_class_patch.stop()
        self.pyaudio_patch.start() # Restart setup's patcher for other tests

if __name__ == '__main__':
    unittest.main()
