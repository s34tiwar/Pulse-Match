import pyaudio
import wave
import speech_recognition as sr
import time

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100 # 8000Hz from google thingy
CHUNK = 1024
RECORD_SECONDS = 22  # Duration of recording after detection
OUTPUT_FILENAME = "recorded_audio_conversation.wav"

def detect_and_record():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    print("Listening for voice...")

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)  # Calibrate to ambient noise
        while True:
            try:
                # recognition to detect voice
                audio_data = recognizer.listen(source, timeout=1, phrase_time_limit=2)
                # Attempt recognition 
                recognizer.recognize_google(audio_data)
                print("Voice detected! Starting recording...")
                record_audio()
                break
            except sr.UnknownValueError:
                # No voice detected; continue listening
                continue
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")
                break

def record_audio():
    audio = pyaudio.PyAudio()

    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    print("Recording audio...")

    frames = []
    start_time = time.time()

    while time.time() - start_time < RECORD_SECONDS:
        data = stream.read(CHUNK)
        frames.append(data)

    print("Recording complete.")
    
    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(OUTPUT_FILENAME, 'wb') as wave_file:
        wave_file.setnchannels(CHANNELS)
        wave_file.setsampwidth(audio.get_sample_size(FORMAT))
        wave_file.setframerate(RATE)
        wave_file.writeframes(b''.join(frames))
    
    print(f"Audio saved as {OUTPUT_FILENAME}")

if __name__ == "__main__":
    detect_and_record()