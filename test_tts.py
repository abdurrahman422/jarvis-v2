from app.services.speech.tts_service import speak_text


if __name__ == "__main__":
    wav_path = speak_text("Hello boss, Jarvis is ready.")
    print(f"Generated: {wav_path}")
