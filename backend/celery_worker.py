import json
import os
import tempfile
import wave

from pydub import AudioSegment
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from vosk import KaldiRecognizer, Model

from celery_app import celery


@celery.task
def audio_to_pdf(audio_path, output_folder, member_id):
    # 1️⃣ Load Vosk model
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(BASE_DIR, "..", "vosk-model-small-en-us-0.15")
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            "Vosk model not found! Download from https://alphacephei.com/vosk/models"
        )
    model = Model(model_path)

    # 2️⃣ Convert MP3 to WAV if needed
    ext = os.path.splitext(audio_path)[1].lower()
    if ext == ".mp3":
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sound = AudioSegment.from_mp3(audio_path)
        sound = sound.set_channels(1).set_frame_rate(16000)
        sound.export(tmp_wav.name, format="wav")
        audio_path_to_use = tmp_wav.name
    else:
        audio_path_to_use = audio_path

    # 3️⃣ Open WAV file
    wf = wave.open(audio_path_to_use, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        raise ValueError("Audio must be WAV mono PCM")

    # 4️⃣ Recognize speech for entire file
    rec = KaldiRecognizer(model, wf.getframerate())
    full_text = []

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            full_text.append(result.get("text", ""))

    # Add final partial result
    final_result = json.loads(rec.FinalResult())
    full_text.append(final_result.get("text", ""))

    wf.close()

    # Remove temporary WAV if created
    if ext == ".mp3":
        os.unlink(tmp_wav.name)

    # 5️⃣ Combine all text into a single string
    full_text_str = " ".join(full_text).strip()

    # 6️⃣ Save text to PDF
    os.makedirs(output_folder, exist_ok=True)
    pdf_path = os.path.join(
        output_folder, os.path.splitext(os.path.basename(audio_path))[0] + ".pdf"
    )

    c = canvas.Canvas(pdf_path, pagesize=letter)
    text_obj = c.beginText(50, 750)
    text_obj.setFont("Helvetica", 12)

    # Split text into lines that fit the page width
    max_chars_per_line = 90
    for i in range(0, len(full_text_str), max_chars_per_line):
        line = full_text_str[i:i + max_chars_per_line]
        text_obj.textLine(line)

    c.drawText(text_obj)
    c.save()

    return pdf_path
