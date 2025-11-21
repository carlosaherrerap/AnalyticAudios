"""
Módulo principal de procesamiento de audio
"""
import os
import json
import subprocess
import shutil
import webrtcvad
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import librosa
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torch

import config


class AudioProcessor:
    """Procesador principal de audios"""
    
    def __init__(self):
        self.vad = webrtcvad.Vad(config.VAD_CONFIG["mode"])
        self.whisper_model = None
        self.diarization_pipeline = None
        self._initialize_models()
        
    def _initialize_models(self):
        """Inicializa los modelos de ML"""
        print("Inicializando modelos...")
        try:
            # Whisper para transcripción
            self.whisper_model = WhisperModel(
                config.TRANSCRIPTION_CONFIG["model_size"],
                device=config.TRANSCRIPTION_CONFIG["device"],
                compute_type=config.TRANSCRIPTION_CONFIG["compute_type"]
            )
            print("✓ Whisper inicializado")
        except Exception as e:
            print(f"⚠ Error inicializando Whisper: {e}")
            
        try:
            # Pyannote para diarización
            # Nota: Requiere token de HuggingFace para modelos pre-entrenados
            # Alternativa: usar modelo local o configurar token
            self.diarization_pipeline = None  # Se inicializará si hay token
            print("⚠ Pyannote requiere configuración de token (opcional)")
        except Exception as e:
            print(f"⚠ Error inicializando Pyannote: {e}")
    
    def check_filename_filter(self, filename: str) -> bool:
        """
        Verifica si el archivo cumple con el filtro de nombre
        Formato esperado: YYYYMMDD-HHMMSS-agt-XX-XXX-XXXXXXXXX.ext
        Bloque 4 (índice 3) debe ser "19"
        """
        try:
            name_without_ext = Path(filename).stem
            parts = name_without_ext.split('-')
            
            # Debug: mostrar los bloques encontrados (solo los primeros 3 archivos)
            if not hasattr(self, '_debug_count'):
                self._debug_count = 0
            
            if self._debug_count < 3:
                print(f"  [DEBUG] Archivo: {filename}")
                print(f"  [DEBUG] Partes: {parts}")
                print(f"  [DEBUG] Total partes: {len(parts)}")
                if len(parts) > config.FILENAME_FILTER["required_block_index"]:
                    print(f"  [DEBUG] Bloque {config.FILENAME_FILTER['required_block_index'] + 1} (índice {config.FILENAME_FILTER['required_block_index']}): '{parts[config.FILENAME_FILTER['required_block_index']]}'")
                    print(f"  [DEBUG] Buscando: '{config.FILENAME_FILTER['required_value']}'")
                self._debug_count += 1
            
            # Verificar que tenga suficientes bloques
            required_index = config.FILENAME_FILTER["required_block_index"]
            if len(parts) <= required_index:
                return False
            
            # Obtener el valor del bloque requerido
            block_value = parts[required_index].strip()  # Eliminar espacios si los hay
            
            # Comparar
            matches = block_value == config.FILENAME_FILTER["required_value"]
            
            return matches
            
        except Exception as e:
            print(f"  ⚠ Error verificando nombre de archivo {filename}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def check_file_size(self, filepath: Path) -> Tuple[bool, int]:
        """Verifica el tamaño del archivo (mínimo 45KB)"""
        size_bytes = filepath.stat().st_size
        
        if size_bytes == 0:
            return False, 0
        
        # Verificar tamaño mínimo (45KB)
        min_size = config.AUDIO_CONFIG.get("min_size_bytes", 45 * 1024)
        if size_bytes < min_size:
            return False, size_bytes
                
        return True, size_bytes
    
    def apply_noise_reduction(self, wav_path: Path, output_path: Path) -> bool:
        """
        Aplica reducción de ruido al audio usando librosa
        """
        try:
            import librosa
            import soundfile as sf
            from scipy import signal
            
            # Cargar audio
            y, sr = librosa.load(str(wav_path), sr=None)
            
            # Aplicar filtro de paso alto para eliminar ruido de baja frecuencia
            # Filtro Butterworth de paso alto a 80Hz
            sos = signal.butter(10, 80, 'hp', fs=sr, output='sos')
            y_filtered = signal.sosfilt(sos, y)
            
            # Normalizar para evitar clipping
            y_filtered = librosa.util.normalize(y_filtered)
            
            # Guardar audio procesado
            sf.write(str(output_path), y_filtered, sr)
            return True
            
        except Exception as e:
            print(f"  ⚠ Error aplicando reducción de ruido: {e}")
            # Si falla, copiar el original
            try:
                shutil.copy2(str(wav_path), str(output_path))
                return True
            except:
                return False
    
    def convert_to_wav(self, input_path: Path, output_path: Path, apply_noise_reduction: bool = False) -> bool:
        """
        Convierte audio a WAV 16k mono PCM S16LE usando ffmpeg
        """
        try:
            # Asegurar que el directorio de salida existe
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Verificar que el archivo de entrada existe
            if not input_path.exists():
                print(f"  ⚠ Archivo de entrada no existe: {input_path}")
                return False
            
            # Usar la ruta de ffmpeg de config si está disponible
            ffmpeg_cmd = config.FFMPEG_PATH if config.FFMPEG_PATH else "ffmpeg"
            
            # Verificar que ffmpeg esté disponible
            try:
                subprocess.run(
                    [ffmpeg_cmd, "-version"], 
                    capture_output=True, 
                    timeout=5, 
                    check=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                print(f"  ⚠ ffmpeg no está disponible en: {ffmpeg_cmd}")
                return False
            
            # Convertir usando rutas absolutas
            input_abs = str(input_path.resolve())
            output_abs = str(output_path.resolve())
            
            # Usar la ruta de ffmpeg de config si está disponible
            ffmpeg_cmd = config.FFMPEG_PATH if config.FFMPEG_PATH else "ffmpeg"
            
            cmd = [
                ffmpeg_cmd, "-y", "-i", input_abs,
                "-ar", str(config.AUDIO_CONFIG["sample_rate"]),
                "-ac", str(config.AUDIO_CONFIG["channels"]),
                "-acodec", "pcm_s16le",
                "-loglevel", "error",  # Reducir output de ffmpeg
                output_abs
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Error desconocido de ffmpeg"
                print(f"  ⚠ Error en ffmpeg: {error_msg[:100]}")
                return False
            
            # Verificar que el archivo de salida se creó
            if not output_path.exists():
                print(f"  ⚠ Archivo de salida no se creó: {output_path}")
                return False
            
            # Aplicar reducción de ruido si está habilitada
            if apply_noise_reduction and config.TRANSCRIPTION_CONFIG.get("noise_reduction", False):
                temp_clean = output_path.parent / f"{output_path.stem}_clean.wav"
                if self.apply_noise_reduction(output_path, temp_clean):
                    # Reemplazar el archivo original con el limpio
                    temp_clean.replace(output_path)
                
            return True
            
        except subprocess.TimeoutExpired:
            print(f"  ⚠ Timeout al convertir {input_path.name}")
            return False
        except Exception as e:
            print(f"  ⚠ Error convirtiendo {input_path.name}: {str(e)[:100]}")
            return False
    
    def detect_voice_activity(self, wav_path: Path) -> Tuple[float, bool]:
        """
        Detecta actividad de voz usando webrtcvad
        Retorna: (voiced_ratio, has_voice)
        """
        try:
            audio_data, sample_rate = sf.read(str(wav_path))
            
            # Convertir a int16 si es necesario
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Asegurar que es mono
            if len(audio_data.shape) > 1:
                audio_data = audio_data[:, 0]
            
            frame_duration_ms = config.VAD_CONFIG["frame_duration_ms"]
            frame_size = int(sample_rate * frame_duration_ms / 1000)
            
            total_frames = 0
            voiced_frames = 0
            
            for i in range(0, len(audio_data) - frame_size, frame_size):
                frame = audio_data[i:i + frame_size]
                frame_bytes = frame.tobytes()
                
                total_frames += 1
                if self.vad.is_speech(frame_bytes, sample_rate):
                    voiced_frames += 1
            
            if total_frames == 0:
                return 0.0, False
                
            voiced_ratio = voiced_frames / total_frames
            has_voice = voiced_ratio >= config.VAD_CONFIG["min_voiced_ratio"]
            
            return voiced_ratio, has_voice
            
        except Exception as e:
            print(f"Error en VAD: {e}")
            return 0.0, False
    
    def transcribe_audio(self, wav_path: Path) -> Tuple[Optional[str], bool]:
        """
        Transcribe el audio usando Whisper (con reducción de ruido si está habilitada)
        Retorna: (transcript, success)
        """
        if not self.whisper_model:
            return None, False
        
        # Si la reducción de ruido está habilitada, ya se aplicó en convert_to_wav
        # El archivo wav_path ya debería estar limpio
        try:
            segments, info = self.whisper_model.transcribe(
                str(wav_path),
                language=config.TRANSCRIPTION_CONFIG["language"]
            )
            
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text.strip())
            
            transcript = " ".join(transcript_parts)
            return transcript, True
            
        except Exception as e:
            print(f"  ⚠ Error en transcripción: {e}")
            return None, False
    
    def detect_beep(self, wav_path: Path) -> bool:
        """
        Detecta beep de buzón de voz analizando frecuencias
        """
        try:
            y, sr = librosa.load(str(wav_path), sr=None)
            
            # Analizar primeros 5 segundos
            max_time = min(5.0, len(y) / sr)
            y_early = y[:int(max_time * sr)]
            
            # FFT para detectar frecuencias
            fft = np.fft.fft(y_early)
            freqs = np.fft.fftfreq(len(fft), 1/sr)
            magnitude = np.abs(fft)
            
            # Buscar picos en el rango de beep
            beep_range = (freqs >= config.AMD_CONFIG["beep_freq_min"]) & \
                        (freqs <= config.AMD_CONFIG["beep_freq_max"])
            
            if np.any(beep_range):
                peak_magnitude = np.max(magnitude[beep_range])
                # Si hay un pico significativo, probablemente es un beep
                if peak_magnitude > np.mean(magnitude) * 3:
                    return True
                    
            return False
            
        except Exception as e:
            print(f"Error detectando beep: {e}")
            return False
    
    def detect_keywords(self, transcript: str) -> Dict[str, bool]:
        """
        Detecta palabras clave en la transcripción según los nuevos filtros
        """
        transcript_lower = transcript.lower()
        
        results = {
            "has_error_tercer_filtro": False,
            "has_evidencias_validas": False
        }
        
        # Buscar keywords de error (TERCER_FILTRO)
        for keyword in config.KEYWORDS["error_tercer_filtro"]:
            if keyword.lower() in transcript_lower:
                results["has_error_tercer_filtro"] = True
                break
        
        # Buscar keywords de evidencias válidas (EVIDENCIAS con prefijo ev_)
        for keyword in config.KEYWORDS["evidencias_validas"]:
            if keyword.lower() in transcript_lower:
                results["has_evidencias_validas"] = True
                break
        
        return results
    
    def count_words(self, text: str) -> int:
        """Cuenta el número de palabras en un texto"""
        if not text or not text.strip():
            return 0
        return len(text.split())
    
    def diarize_speakers(self, wav_path: Path) -> Tuple[int, bool]:
        """
        Diariza el audio para contar hablantes
        Retorna: (speaker_count, success)
        """
        if not self.diarization_pipeline:
            # Fallback: usar heurística basada en análisis de energía y silencios
            try:
                y, sr = librosa.load(str(wav_path), sr=None)
                
                # Calcular energía por ventanas
                frame_length = int(sr * 0.025)  # 25ms
                hop_length = int(sr * 0.010)    # 10ms
                
                # Energía RMS
                rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
                
                # Umbral para detectar voz (percentil 30)
                threshold = np.percentile(rms, 30)
                
                # Detectar segmentos de voz
                voice_segments = rms > threshold
                
                # Contar cambios significativos (posibles cambios de hablante)
                # Basado en variaciones grandes de energía
                if len(voice_segments) > 10:
                    # Detectar cambios bruscos que podrían indicar cambio de hablante
                    energy_changes = np.abs(np.diff(rms))
                    change_threshold = np.percentile(energy_changes, 75)
                    significant_changes = np.sum(energy_changes > change_threshold)
                    
                    # Estimar número de hablantes (heurística)
                    # Si hay muchos cambios, probablemente hay 2+ hablantes
                    if significant_changes > len(rms) * 0.1:
                        return 2, True  # Probablemente 2 hablantes
                    else:
                        return 1, True  # Probablemente 1 hablante
                else:
                    return 1, True
                    
            except Exception as e:
                print(f"Error en diarización fallback: {e}")
                return 1, True  # Asumir 1 hablante por defecto
        
        try:
            diarization = self.diarization_pipeline(str(wav_path))
            
            speakers = set()
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.add(speaker)
            
            speaker_count = len(speakers)
            return speaker_count, True
            
        except Exception as e:
            print(f"Error en diarización: {e}")
            # Fallback a heurística básica
            try:
                y, sr = librosa.load(str(wav_path), sr=None)
                rms = librosa.feature.rms(y=y)[0]
                energy_changes = np.abs(np.diff(rms))
                change_threshold = np.percentile(energy_changes, 75)
                significant_changes = np.sum(energy_changes > change_threshold)
                if significant_changes > len(rms) * 0.1:
                    return 2, True
                return 1, True
            except:
                return 1, True
    
    def process_audio(self, input_path: Path, temp_dir: Path) -> Dict:
        """
        Procesa un archivo de audio completo con la nueva lógica de 3 filtros
        """
        result = {
            "file": str(input_path.name),
            "duration": 0.0,
            "bytes": 0,
            "voiced_ratio": 0.0,
            "speaker_count": 0,
            "transcript": "",
            "word_count": 0,
            "tags": [],
            "notes": [],
            "status": "unknown",
            "filter_stage": None,  # "primer_filtro", "segundo_filtro", "tercer_filtro", "evidencias"
            "filter_reason": None,  # Razón específica del filtro
            "prefix": None  # Prefijo a agregar al nombre
        }
        
        # ========== PRIMER FILTRO ==========
        # 1. Verificar tamaño (> 45KB)
        size_ok, size_bytes = self.check_file_size(input_path)
        result["bytes"] = size_bytes
        
        if not size_ok:
            if size_bytes == 0:
                result["filter_stage"] = "primer_filtro"
                result["filter_reason"] = "peso_cero"
                result["prefix"] = config.PREFIXES["peso_minimo"]
            else:
                result["filter_stage"] = "primer_filtro"
                result["filter_reason"] = "peso_insuficiente"
                result["prefix"] = config.PREFIXES["peso_minimo"]
            result["status"] = "primer_filtro_failed"
            return result
        
        # 2. Convertir a WAV (con reducción de ruido si está habilitada)
        temp_wav = temp_dir / f"{input_path.stem}.wav"
        apply_noise = config.TRANSCRIPTION_CONFIG.get("noise_reduction", False)
        if not self.convert_to_wav(input_path, temp_wav, apply_noise_reduction=apply_noise):
            result["filter_stage"] = "primer_filtro"
            result["filter_reason"] = "conversion_failed"
            result["status"] = "primer_filtro_failed"
            return result
        
        # 3. Obtener duración y verificar (> 5 segundos)
        if temp_wav.exists():
            try:
                y, sr = librosa.load(str(temp_wav), sr=None)
                result["duration"] = len(y) / sr
            except Exception as e:
                print(f"  ⚠ Error obteniendo duración: {e}")
                result["filter_stage"] = "primer_filtro"
                result["filter_reason"] = "error_duracion"
                result["status"] = "primer_filtro_failed"
                return result
        
        if result["duration"] < config.AUDIO_CONFIG["min_duration_seconds"]:
            result["filter_stage"] = "primer_filtro"
            result["filter_reason"] = "duracion_insuficiente"
            result["prefix"] = config.PREFIXES["duracion_minima"]
            result["status"] = "primer_filtro_failed"
            return result
        
        # Si pasó el primer filtro, continuar al segundo
        
        # ========== SEGUNDO FILTRO ==========
        # 4. VAD (verificar que hay voz)
        voiced_ratio, has_voice = self.detect_voice_activity(temp_wav)
        result["voiced_ratio"] = voiced_ratio
        
        if not has_voice:
            result["filter_stage"] = "segundo_filtro"
            result["filter_reason"] = "sin_voz"
            result["status"] = "segundo_filtro_failed"
            return result
        
        # 5. Transcripción
        transcript, trans_ok = self.transcribe_audio(temp_wav)
        if not trans_ok or not transcript:
            result["filter_stage"] = "segundo_filtro"
            result["filter_reason"] = "transcripcion_fallida"
            result["status"] = "segundo_filtro_failed"
            return result
        
        result["transcript"] = transcript
        result["word_count"] = self.count_words(transcript)
        
        # 6. Verificar mínimo de palabras (>= 10)
        if result["word_count"] < config.TRANSCRIPTION_CONFIG["min_words"]:
            result["filter_stage"] = "segundo_filtro"
            result["filter_reason"] = "palabras_insuficientes"
            result["prefix"] = config.PREFIXES["palabras_insuficientes"]
            result["status"] = "segundo_filtro_failed"
            return result
        
        # 7. Diarización (verificar 2 hablantes)
        speaker_count, diar_ok = self.diarize_speakers(temp_wav)
        result["speaker_count"] = speaker_count
        
        if speaker_count < config.DIARIZATION_CONFIG["min_speakers"]:
            result["filter_stage"] = "segundo_filtro"
            result["filter_reason"] = "hablantes_insuficientes"
            result["prefix"] = config.PREFIXES["hablantes_insuficientes"]
            result["status"] = "segundo_filtro_failed"
            return result
        
        # Si pasó el segundo filtro, continuar al tercer filtro
        
        # ========== TERCER FILTRO ==========
        # 8. Detección de keywords y beep
        keywords = self.detect_keywords(transcript)
        has_beep = self.detect_beep(temp_wav)
        
        # Verificar si tiene palabras de error o buzón de voz
        has_error_tercer = keywords["has_error_tercer_filtro"] or has_beep
        
        if has_error_tercer:
            result["filter_stage"] = "tercer_filtro"
            result["filter_reason"] = "error_o_buzon"
            result["status"] = "tercer_filtro_failed"
            result["tags"].append("error_tercer_filtro")
            return result
        
        # Si no tiene errores, va a EVIDENCIAS
        result["filter_stage"] = "evidencias"
        result["status"] = "evidencias"
        
        # Verificar si tiene palabras clave de evidencias válidas
        if keywords["has_evidencias_validas"]:
            result["prefix"] = config.PREFIXES["evidencias_validas"]
            result["tags"].append("evidencias_validas")
        
        return result

