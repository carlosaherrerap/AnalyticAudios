"""
Script principal de procesamiento de audios
Ejecuta el pipeline completo de filtrado 
"""
import os
import sys
import shutil
import json
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
import pandas as pd

import config
from audio_processor import AudioProcessor


def setup_directories(base_dir: Path):
    """Crea las carpetas necesarias según los nuevos filtros"""
    base_dir.mkdir(exist_ok=True)
    
    # Nuevas carpetas según filtros
    primer_filtro_dir = base_dir / config.PRIMER_FILTRO_DIR
    segundo_filtro_dir = base_dir / config.SEGUNDO_FILTRO_DIR
    tercer_filtro_dir = base_dir / config.TERCER_FILTRO_DIR
    evidencias_dir = base_dir / config.EVIDENCIAS_DIR
    
    primer_filtro_dir.mkdir(exist_ok=True)
    segundo_filtro_dir.mkdir(exist_ok=True)
    tercer_filtro_dir.mkdir(exist_ok=True)
    evidencias_dir.mkdir(exist_ok=True)
    
    # Carpeta temporal
    temp_dir = base_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    return primer_filtro_dir, segundo_filtro_dir, tercer_filtro_dir, evidencias_dir, temp_dir


def copy_file_with_prefix(file_path: Path, dest_dir: Path, prefix: str = None):
    """
    COPIA archivo a la carpeta de destino con prefijo opcional (NO elimina el original)
    """
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Construir nombre del archivo
        if prefix:
            new_name = f"{prefix}{file_path.name}"
        else:
            new_name = file_path.name
        
        dest_path = dest_dir / new_name
        
        # Si ya existe, agregar timestamp
        if dest_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if prefix:
                new_name = f"{prefix}{stem}_{timestamp}{suffix}"
            else:
                new_name = f"{stem}_{timestamp}{suffix}"
            dest_path = dest_dir / new_name
        
        # COPIAR en lugar de mover (preserva el original)
        shutil.copy2(str(file_path), str(dest_path))
        return True
    except Exception as e:
        print(f"  ⚠ Error copiando archivo: {e}")
        return False


def process_folder(input_dir_path: Path, base_dir: Path):
    """
    Procesa todos los audios de una carpeta
    """
    print(f"\n{'='*60}")
    print(f"Procesando carpeta: {input_dir_path}")
    print(f"{'='*60}\n")
    
    if not input_dir_path.exists():
        print(f"⚠ La carpeta no existe: {input_dir_path}")
        print(f"   Verifica la variable RUTA en config.py")
        return
    
    input_dir = input_dir_path
    
    # El tamaño mínimo ya está configurado en config.py (45KB)
    # No necesitamos calcularlo dinámicamente
    
    # Configurar directorios
    primer_filtro_dir, segundo_filtro_dir, tercer_filtro_dir, evidencias_dir, temp_dir = setup_directories(base_dir)
    
    # Verificar ffmpeg antes de empezar
    print("Verificando ffmpeg...")
    import subprocess
    import shutil
    
    ffmpeg_path = None
    
    def find_ffmpeg_exe(path_str):
        """Busca ffmpeg.exe en una ruta (puede ser directorio o archivo)"""
        path = Path(path_str)
        if not path.exists():
            return None
        
        # Si es un archivo y es ffmpeg.exe, usarlo
        if path.is_file() and path.name.lower() in ['ffmpeg.exe', 'ffmpeg']:
            return str(path.resolve())
        
        # Si es un directorio, buscar ffmpeg.exe dentro
        if path.is_dir():
            # Buscar en el directorio actual
            exe_path = path / "ffmpeg.exe"
            if exe_path.exists():
                return str(exe_path.resolve())
            # Buscar en subdirectorio bin
            exe_path = path / "bin" / "ffmpeg.exe"
            if exe_path.exists():
                return str(exe_path.resolve())
        
        return None
    
    # 1. Intentar usar la ruta especificada en config
    if config.FFMPEG_PATH:
        found_path = find_ffmpeg_exe(config.FFMPEG_PATH)
        if found_path:
            ffmpeg_path = found_path
            print(f"✓ Usando ffmpeg de: {ffmpeg_path}")
        else:
            print(f"⚠ La ruta especificada en config.FFMPEG_PATH no contiene ffmpeg.exe: {config.FFMPEG_PATH}")
            ffmpeg_path = None
    
    # 2. Buscar ffmpeg en PATH
    if not ffmpeg_path:
        ffmpeg_cmd = shutil.which("ffmpeg")
        if ffmpeg_cmd:
            ffmpeg_path = ffmpeg_cmd
            print(f"✓ ffmpeg encontrado en PATH: {ffmpeg_path}")
        else:
            # 3. Buscar en ubicaciones comunes de Windows y proyecto
            print("  Buscando ffmpeg en ubicaciones comunes...")
            base_dir = Path(__file__).parent.resolve()
            common_paths = [
                # Ruta del proyecto (donde el usuario lo copió)
                base_dir / "ffmpeg" / "bin" / "ffmpeg.exe",
                base_dir / "ffmpeg" / "ffmpeg.exe",
                # Ubicaciones comunes del sistema
                Path("C:/ffmpeg/bin/ffmpeg.exe"),
                Path("C:/ffmpeg/ffmpeg.exe"),
                Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
                Path("C:/Program Files (x86)/ffmpeg/bin/ffmpeg.exe"),
                Path(os.path.expanduser("~/ffmpeg/bin/ffmpeg.exe")),
                Path(os.path.expanduser("~/AppData/Local/ffmpeg/bin/ffmpeg.exe")),
            ]
            
            for path in common_paths:
                if path.exists():
                    ffmpeg_path = str(path.resolve())
                    print(f"✓ ffmpeg encontrado en: {ffmpeg_path}")
                    break
    
    # 4. Verificar que ffmpeg funciona
    if ffmpeg_path:
        # Verificar que el archivo existe y es ejecutable
        ffmpeg_file = Path(ffmpeg_path)
        if not ffmpeg_file.exists():
            print(f"⚠ El archivo ffmpeg no existe: {ffmpeg_path}")
            ffmpeg_path = None
        elif not ffmpeg_file.is_file():
            print(f"⚠ La ruta no es un archivo: {ffmpeg_path}")
            ffmpeg_path = None
        else:
            try:
                # Intentar ejecutar ffmpeg
                result = subprocess.run(
                    [ffmpeg_path, "-version"], 
                    capture_output=True, 
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    # Guardar la ruta en config para uso futuro
                    if not config.FFMPEG_PATH or config.FFMPEG_PATH != ffmpeg_path:
                        print(f"  💡 Tip: Agrega esto a config.py para evitar búsquedas:")
                        print(f"     FFMPEG_PATH = r\"{ffmpeg_path}\"")
                    print("✓ ffmpeg funciona correctamente")
                else:
                    print(f"⚠ ffmpeg encontrado pero retornó código de error: {result.returncode}")
                    if result.stderr:
                        print(f"   Error: {result.stderr.decode('utf-8', errors='ignore')[:200]}")
                    ffmpeg_path = None
            except PermissionError as e:
                print(f"⚠ Error de permisos al ejecutar ffmpeg: {e}")
                print(f"   Ruta: {ffmpeg_path}")
                print(f"   Intenta ejecutar Python como administrador o verifica permisos del archivo")
                ffmpeg_path = None
            except FileNotFoundError:
                print(f"⚠ No se puede encontrar ffmpeg en: {ffmpeg_path}")
                ffmpeg_path = None
            except Exception as e:
                print(f"⚠ Error ejecutando ffmpeg: {e}")
                print(f"   Tipo de error: {type(e).__name__}")
                print(f"   Ruta intentada: {ffmpeg_path}")
                # Intentar sin CREATE_NO_WINDOW como fallback
                try:
                    print("   Intentando sin flags especiales...")
                    result = subprocess.run(
                        [ffmpeg_path, "-version"], 
                        capture_output=True, 
                        timeout=10
                    )
                    if result.returncode == 0:
                        print("✓ ffmpeg funciona (sin flags especiales)")
                    else:
                        ffmpeg_path = None
                except:
                    ffmpeg_path = None
    
    # 5. Si no se encontró, mostrar instrucciones
    if not ffmpeg_path:
        print("\n" + "="*60)
        print("❌ ERROR: ffmpeg no encontrado")
        print("="*60)
        print("\nOpciones para instalar ffmpeg en Windows:")
        print("\n1. DESCARGAR E INSTALAR:")
        print("   - Ve a: https://www.gyan.dev/ffmpeg/builds/")
        print("   - Descarga: ffmpeg-release-essentials.zip")
        print("   - Extrae en: C:\\ffmpeg")
        print("   - Agrega C:\\ffmpeg\\bin al PATH del sistema")
        print("\n2. USAR CHOCOLATEY (si lo tienes instalado):")
        print("   choco install ffmpeg")
        print("\n3. ESPECIFICAR RUTA MANUAL:")
        print("   Edita config.py y agrega la ruta completa al ejecutable:")
        print("   FFMPEG_PATH = r\"C:\\ffmpeg\\bin\\ffmpeg.exe\"")
        print("   O si lo copiaste al proyecto:")
        base_dir = Path(__file__).parent.resolve()
        print(f"   FFMPEG_PATH = r\"{base_dir}\\ffmpeg\\bin\\ffmpeg.exe\"")
        print("\n4. VERIFICAR PERMISOS:")
        print("   Si ves 'Acceso denegado', intenta:")
        print("   - Ejecutar Python como administrador")
        print("   - Verificar que el archivo ffmpeg.exe no esté bloqueado")
        print("   - Copiar ffmpeg a una carpeta sin restricciones")
        print("\n" + "="*60 + "\n")
        return
    
    # Guardar la ruta encontrada para uso en audio_processor
    config.FFMPEG_PATH = ffmpeg_path
    
    # Inicializar procesador
    processor = AudioProcessor()
    
    # Obtener todos los archivos de audio
    audio_extensions = {'.mp3', '.wav', '.gsm', '.m4a', '.flac', '.ogg'}
    audio_files = [
        f for f in input_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    
    print(f"Encontrados {len(audio_files)} archivos de audio")
    
    # Mostrar algunos ejemplos de nombres de archivos
    if len(audio_files) > 0:
        print(f"\nEjemplos de nombres de archivos encontrados:")
        for i, f in enumerate(audio_files[:10], 1):  # Mostrar más ejemplos
            parts = f.stem.split('-')
            print(f"  {i}. {f.name}")
            print(f"     Partes ({len(parts)} bloques): {parts}")
            if len(parts) > 3:
                print(f"     Bloque 4 (índice 3): '{parts[3]}' (buscando: '19')")
                if parts[3] == '19':
                    print(f"     ✓ ESTE DEBERÍA PASAR EL FILTRO")
            else:
                print(f"     ⚠ No tiene suficientes bloques (necesita al menos 4)")
        print()
    
    # Filtrar por nombre (bloque 4 = 19)
    print("Aplicando filtro de nombre (bloque 4 debe ser '19')...")
    filtered_files = []
    no_match_count = 0
    match_count = 0
    
    for f in audio_files:
        if processor.check_filename_filter(f.name):
            filtered_files.append(f)
            match_count += 1
            if match_count <= 5:  # Mostrar primeros 5 que pasan
                parts = f.stem.split('-')
                print(f"  ✓ {f.name} - Bloque 4: '{parts[3] if len(parts) > 3 else 'N/A'}'")
        else:
            no_match_count += 1
            if no_match_count <= 5:  # Mostrar primeros 5 que NO pasan
                parts = f.stem.split('-')
                bloque4 = parts[3] if len(parts) > 3 else 'NO_TIENE'
                print(f"  ✗ {f.name} - Bloque 4: '{bloque4}' (esperado: '19')")
    
    print(f"\nArchivos que pasan filtro de nombre (bloque 4 = 19): {len(filtered_files)}")
    
    if len(filtered_files) == 0 and len(audio_files) > 0:
        print(f"\n⚠⚠⚠ ADVERTENCIA: Ningún archivo pasó el filtro de nombre ⚠⚠⚠")
        print(f"   Total archivos revisados: {len(audio_files)}")
        print(f"   Archivos que NO pasan: {no_match_count}")
        print(f"\n   Verifica que los archivos tengan el formato correcto:")
        print(f"   YYYYMMDD-HHMMSS-agt-19-XXX-XXXXXXXXX.ext")
        print(f"   El bloque 4 (después de 'agt') debe ser exactamente '19'")
        
        # Analizar patrones comunes
        print(f"\n   Análisis de patrones en los primeros 20 archivos:")
        bloque4_values = {}
        for f in audio_files[:20]:
            parts = f.stem.split('-')
            if len(parts) > 3:
                valor = parts[3]
                bloque4_values[valor] = bloque4_values.get(valor, 0) + 1
        
        if bloque4_values:
            print(f"   Valores encontrados en bloque 4:")
            for valor, count in sorted(bloque4_values.items(), key=lambda x: x[1], reverse=True):
                print(f"     - '{valor}': {count} archivos")
    
    # Procesar cada archivo
    processed = 0
    valid_count = 0
    error_counts = {}
    
    # Lista para acumular todos los resultados para el Excel
    all_results = []
    
    for i, audio_file in enumerate(filtered_files, 1):
        print(f"\n[{i}/{len(filtered_files)}] Procesando: {audio_file.name}")
        
        try:
            result = processor.process_audio(audio_file, temp_dir)
            processed += 1
            
            # Mostrar información detallada
            print(f"  Duración: {result['duration']:.1f}s | Tamaño: {result['bytes']/1024:.1f} KB")
            
            # Mostrar información según la etapa del filtro
            filter_stage = result.get('filter_stage', 'unknown')
            filter_reason = result.get('filter_reason', '')
            
            if filter_stage == "primer_filtro":
                print(f"  ✗ PRIMER FILTRO falló: {filter_reason}")
                if filter_reason == "peso_insuficiente" or filter_reason == "peso_cero":
                    print(f"     Tamaño: {result['bytes']/1024:.1f} KB (requiere > 45 KB)")
                elif filter_reason == "duracion_insuficiente":
                    print(f"     Duración: {result['duration']:.1f}s (requiere > 5s)")
                    
            elif filter_stage == "segundo_filtro":
                print(f"  ✗ SEGUNDO FILTRO falló: {filter_reason}")
                if filter_reason == "palabras_insuficientes":
                    print(f"     Palabras: {result.get('word_count', 0)} (requiere >= 10)")
                elif filter_reason == "hablantes_insuficientes":
                    print(f"     Hablantes: {result.get('speaker_count', 0)} (requiere >= 2)")
                print(f"  Voz detectada: {result['voiced_ratio']:.1%}")
                
            elif filter_stage == "tercer_filtro":
                print(f"  ✗ TERCER FILTRO falló: {filter_reason}")
                print(f"     Detectado: error o buzón de voz")
                print(f"  Hablantes: {result.get('speaker_count', 0)} | Palabras: {result.get('word_count', 0)}")
                
            elif filter_stage == "evidencias":
                print(f"  ✓ Pasó todos los filtros - EVIDENCIAS")
                print(f"  Hablantes: {result.get('speaker_count', 0)} | Palabras: {result.get('word_count', 0)}")
                if result.get('prefix'):
                    print(f"  Prefijo aplicado: {result.get('prefix')}")
            
            if result.get('transcript'):
                transcript_preview = result['transcript'][:100] + "..." if len(result['transcript']) > 100 else result['transcript']
                print(f"  Transcripción: {transcript_preview}")
            
            # Agregar resultado a la lista para el Excel
            excel_row = {
                "Archivo": result.get("file", ""),
                "Etapa_Filtro": result.get("filter_stage", ""),
                "Razón": result.get("filter_reason", ""),
                "Prefijo": result.get("prefix", ""),
                "Duración_sec": round(result.get("duration", 0), 2),
                "Tamaño_KB": round(result.get("bytes", 0) / 1024, 2),
                "Voz_Detectada_%": round(result.get("voiced_ratio", 0) * 100, 2),
                "Num_Hablantes": result.get("speaker_count", 0),
                "Num_Palabras": result.get("word_count", 0),
                "Transcripción": result.get("transcript", "")[:500],  # Limitar a 500 caracteres
                "Tags": ", ".join(result.get("tags", [])),
                "Notas": ", ".join(result.get("notes", [])),
            }
            
            all_results.append(excel_row)
            
            # COPIAR archivo según resultado (NO elimina el original)
            filter_stage = result.get("filter_stage")
            prefix = result.get("prefix")
            
            if filter_stage == "primer_filtro":
                # PRIMER FILTRO falló
                copy_file_with_prefix(audio_file, primer_filtro_dir, prefix)
                print(f"  ✗ PRIMER FILTRO - Copiado a {config.PRIMER_FILTRO_DIR}/ con prefijo {prefix or 'sin prefijo'}")
                error_counts["primer_filtro"] = error_counts.get("primer_filtro", 0) + 1
                
            elif filter_stage == "segundo_filtro":
                # SEGUNDO FILTRO falló
                copy_file_with_prefix(audio_file, segundo_filtro_dir, prefix)
                print(f"  ✗ SEGUNDO FILTRO - Copiado a {config.SEGUNDO_FILTRO_DIR}/ con prefijo {prefix or 'sin prefijo'}")
                error_counts["segundo_filtro"] = error_counts.get("segundo_filtro", 0) + 1
                
            elif filter_stage == "tercer_filtro":
                # TERCER FILTRO falló (error o buzón)
                copy_file_with_prefix(audio_file, tercer_filtro_dir, None)
                print(f"  ✗ TERCER FILTRO - Copiado a {config.TERCER_FILTRO_DIR}/")
                error_counts["tercer_filtro"] = error_counts.get("tercer_filtro", 0) + 1
                
            elif filter_stage == "evidencias":
                # Pasó todos los filtros - va a EVIDENCIAS
                copy_file_with_prefix(audio_file, evidencias_dir, prefix)
                valid_count += 1
                if prefix:
                    print(f"  ✓✓✓ EVIDENCIAS - Copiado a {config.EVIDENCIAS_DIR}/ con prefijo {prefix}")
                else:
                    print(f"  ✓✓✓ EVIDENCIAS - Copiado a {config.EVIDENCIAS_DIR}/")
                if result.get('tags'):
                    print(f"  Tags: {', '.join(result.get('tags', []))}")
            else:
                # Estado desconocido
                print(f"  ⚠ Estado desconocido: {result.get('status')}")
                error_counts["unknown"] = error_counts.get("unknown", 0) + 1
            
        except Exception as e:
            print(f"  ✗✗✗ ERROR CRÍTICO procesando {audio_file.name}: {e}")
            import traceback
            print(f"  Traceback: {traceback.format_exc()[:200]}")
            error_counts["processing_error"] = error_counts.get("processing_error", 0) + 1
            # COPIAR a error genérico (NO elimina el original)
            try:
                error_dir = base_dir / config.ERROR_DIR
                error_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(audio_file), str(error_dir / audio_file.name))
                print(f"  ⚠ Archivo copiado a carpeta de error (original preservado)")
            except Exception as copy_error:
                print(f"  ⚠ No se pudo copiar archivo: {copy_error}")
    
    # Limpiar carpeta temporal
    try:
        for temp_file in temp_dir.glob("*"):
            temp_file.unlink()
        temp_dir.rmdir()
    except:
        pass
    
    # Crear Excel con todos los resultados
    excel_path = None
    if all_results:
        try:
            df = pd.DataFrame(all_results)
            
            # Ordenar por etapa de filtro (evidencias primero) y luego por archivo
            orden_etapas = {'evidencias': 1, 'tercer_filtro': 2, 'segundo_filtro': 3, 'primer_filtro': 4, 'unknown': 5}
            df['Orden_Etapa'] = df['Etapa_Filtro'].map(orden_etapas).fillna(5)
            df = df.sort_values(['Orden_Etapa', 'Archivo']).drop('Orden_Etapa', axis=1)
            
            # Crear nombre del archivo Excel con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_path = base_dir / f"resultados_procesamiento_{timestamp}.xlsx"
            
            # Crear Excel con formato
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Todos_Resultados', index=False)
                
                # Ajustar ancho de columnas
                from openpyxl.utils import get_column_letter
                worksheet = writer.sheets['Todos_Resultados']
                for idx, col in enumerate(df.columns, 1):
                    max_length = max(
                        df[col].astype(str).map(len).max(),
                        len(str(col))
                    )
                    # Limitar ancho máximo a 50
                    col_letter = get_column_letter(idx)
                    worksheet.column_dimensions[col_letter].width = min(max_length + 2, 50)
            
            print(f"\n📊 Excel creado: {excel_path}")
            print(f"   Total de registros: {len(all_results)}")
            
        except Exception as e:
            print(f"\n⚠ Error creando Excel: {e}")
            print(f"   Los resultados se guardaron en memoria pero no se pudo crear el archivo")
            import traceback
            traceback.print_exc()
    
    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"Total archivos encontrados: {len(audio_files)}")
    print(f"Archivos que pasan filtro de nombre (bloque 4 = 19): {len(filtered_files)}")
    print(f"Total procesados: {processed}")
    print(f"✓ EVIDENCIAS (pasaron todos los filtros): {valid_count}")
    print(f"\nDistribución por filtro:")
    print(f"  - PRIMER_FILTRO: {error_counts.get('primer_filtro', 0)}")
    print(f"  - SEGUNDO_FILTRO: {error_counts.get('segundo_filtro', 0)}")
    print(f"  - TERCER_FILTRO: {error_counts.get('tercer_filtro', 0)}")
    if error_counts.get('unknown', 0) > 0:
        print(f"  - Desconocidos: {error_counts.get('unknown', 0)}")
    print(f"{'='*60}\n")
    
    # Mostrar ubicación de resultados
    print(f"📁 Ubicación de archivos:")
    print(f"  ✓ EVIDENCIAS: {evidencias_dir}")
    print(f"  ✗ PRIMER_FILTRO: {primer_filtro_dir}")
    print(f"  ✗ SEGUNDO_FILTRO: {segundo_filtro_dir}")
    print(f"  ✗ TERCER_FILTRO: {tercer_filtro_dir}")
    if all_results:
        print(f"  📊 Excel con todos los resultados: {excel_path}")
    print()


def main():
    """
    Procesa la carpeta especificada en config.RUTA
    """
    # Obtener ruta de la carpeta a procesar desde config
    ruta_carpeta = config.RUTA
    
    # Convertir a Path y resolver ruta absoluta
    input_dir = Path(ruta_carpeta).resolve()
    
    # El directorio base es el directorio del proyecto (donde están las carpetas de salida)
    base_dir = Path(__file__).parent.resolve()
    
    # Procesar la carpeta especificada
    process_folder(input_dir, base_dir)


if __name__ == "__main__":
    main()

