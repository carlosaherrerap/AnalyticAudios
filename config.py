"""
Configuración del sistema de filtrado de audios
"""
import os
from pathlib import Path


RUTA = "E:/ProcesoAudios/2025/sandIA/AGUAFRIA"

FFMPEG_PATH = "E:/ProcesoAudios/2025/sandIA/ffmpeg/bin"

# Rutas base
BASE_DIR = Path(__file__).parent

# Nuevas carpetas de salida según filtros
PRIMER_FILTRO_DIR = "PRIMER_FILTRO"
SEGUNDO_FILTRO_DIR = "SEGUNDO_FILTRO"
TERCER_FILTRO_DIR = "TERCER_FILTRO"
EVIDENCIAS_DIR = "EVIDENCIAS"

# Configuración de prefijos para renombrar archivos
PREFIXES = {
    "peso_minimo": "pm_",
    "duracion_minima": "dm_",
    "palabras_insuficientes": "000_", 
    "hablantes_insuficientes": "111_",
    "evidencias_validas": "ev_"
}

# Configuración de audio
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,  # mono
    "format": "s16le",  # PCM S16LE
    "min_size_kb": 45,  # 45KB mínimo
    "min_size_bytes": 45 * 1024,  # 45KB en bytes
    "min_duration_seconds": 5.0  # Mínimo 5 segundos
}

# Configuración VAD
VAD_CONFIG = {
    "mode": 3,  # 0=quality, 1=low bitrate, 2=aggressive, 3=very aggressive
    "frame_duration_ms": 30,
    "min_voiced_ratio": 0.05  # Mínimo 5% de voz detectada
}

# Configuración de transcripción
TRANSCRIPTION_CONFIG = {
    "model_size": "small",  # tiny, base, small, medium, large
    "language": "es",
    "device": "cpu",  # cpu o cuda
    "compute_type": "int8",  # int8, int8_float16, int16, float16, float32
    "min_words": 10,  # Mínimo 10 palabras en la transcripción
    "noise_reduction": True  # Aplicar reducción de ruido
}

# Configuración de diarización
DIARIZATION_CONFIG = {
    "min_speakers": 2,  # Requiere mínimo 2 hablantes
    "max_speakers": 10,
    "min_duration": 0.5  # segundos mínimos para considerar un segmento
}

# Palabras clave para detección - TERCER FILTRO
KEYWORDS = {
    # Palabras/frases que indican error o buzón de voz (van a TERCER_FILTRO)
    "error_tercer_filtro": [
        "no lo conozco", "no la conozco",
        "número equivocado",
        "aló aló aló", "aló? aló? aló?",
        "llamar a este número",
        "es un familiar no", "¿es un familiar? no",
        "buzon", "buzón", "buzon de voz", "deje su mensaje", 
        "dejar mensaje", "mensaje después del tono", "tono"
    ],
    # Palabras/frases que indican evidencia válida (van a EVIDENCIAS con prefijo ev_)
    "evidencias_validas": [
        "ya pagué", "ya pague",
        "he hablado con mi asesor", "he hablado con mi asesora",
        "he hablado con el asesor", "he hablado con la asesora",
        "si. soy yo", "sí. soy yo",
        "quien habla", "¿quien habla?",
        "nombre de su asesor",
        "le puede decir que tiene una deuda", "¡le puede decir que tiene una deuda?"
    ]
}

# Configuración de detección AMD (Answering Machine Detection)
AMD_CONFIG = {
    "beep_freq_min": 800,  # Hz mínima para beep
    "beep_freq_max": 1200,  # Hz máxima para beep
    "beep_duration_min": 0.3,  # segundos mínimos
    "silence_duration_min": 2.0,  # segundos de silencio largo
    "early_voice_threshold": 3.0  # segundos desde inicio para considerar "early voice"
}

# Filtro de nombre de archivo
FILENAME_FILTER = {
    "required_block_index": 3,  # Índice 0-based del bloque (4to bloque = índice 3)
    "required_value": "19"
}

