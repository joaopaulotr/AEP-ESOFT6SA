from openai import OpenAI

client = OpenAI()

def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
    return transcription.text

def text_to_speech(text: str, output_file_path: str) -> None:
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )
    with open(output_file_path, "wb") as audio_file:
        audio_file.write(response.audio)