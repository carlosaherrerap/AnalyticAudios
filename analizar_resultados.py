"""
Script para analizar los resultados del procesamiento
Muestra estadísticas detalladas de por qué los audios fueron rechazados
"""
import json
from pathlib import Path
from collections import Counter

def analizar_resultados(carpeta_json="audios_filtrados"):
    """Analiza los JSONs generados para entender los resultados"""
    
    carpeta = Path(carpeta_json)
    if not carpeta.exists():
        print(f"❌ Carpeta {carpeta} no existe")
        return
    
    json_files = list(carpeta.glob("*.json"))
    
    if not json_files:
        print(f"❌ No se encontraron archivos JSON en {carpeta}")
        return
    
    print(f"\n{'='*60}")
    print(f"ANÁLISIS DE RESULTADOS")
    print(f"{'='*60}")
    print(f"Total de JSONs encontrados: {len(json_files)}\n")
    
    # Contadores
    status_counts = Counter()
    error_type_counts = Counter()
    speaker_counts = Counter()
    tags_counts = Counter()
    valid_files = []
    error_files = []
    
    # Analizar cada JSON
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            status = data.get('status', 'unknown')
            status_counts[status] += 1
            
            if status == 'valid':
                valid_files.append(data)
            else:
                error_files.append(data)
                error_type = data.get('error_type', 'unknown')
                error_type_counts[error_type] += 1
            
            # Contar hablantes
            speaker_count = data.get('speaker_count', 0)
            speaker_counts[speaker_count] += 1
            
            # Contar tags
            for tag in data.get('tags', []):
                tags_counts[tag] += 1
                
        except Exception as e:
            print(f"Error leyendo {json_file}: {e}")
    
    # Mostrar estadísticas
    print("📊 ESTADÍSTICAS GENERALES")
    print("-" * 60)
    print(f"Válidos: {status_counts['valid']}")
    print(f"Errores: {status_counts['error']}")
    print(f"Desconocidos: {status_counts['unknown']}")
    
    if error_type_counts:
        print(f"\n📋 TIPOS DE ERROR:")
        for error_type, count in error_type_counts.most_common():
            print(f"  - {error_type}: {count}")
    
    print(f"\n👥 DISTRIBUCIÓN DE HABLANTES:")
    for speakers, count in sorted(speaker_counts.items()):
        print(f"  - {speakers} hablante(s): {count} archivos")
    
    print(f"\n🏷️  TAGS MÁS COMUNES:")
    for tag, count in tags_counts.most_common(10):
        print(f"  - {tag}: {count}")
    
    # Mostrar ejemplos de válidos
    if valid_files:
        print(f"\n✓ EJEMPLOS DE AUDIOS VÁLIDOS:")
        for i, data in enumerate(valid_files[:5], 1):
            print(f"\n  {i}. {data.get('file', 'N/A')}")
            print(f"     Hablantes: {data.get('speaker_count', 0)}")
            print(f"     Tags: {', '.join(data.get('tags', []))}")
            transcript = data.get('transcript', '')[:80]
            if transcript:
                print(f"     Transcripción: {transcript}...")
    
    # Mostrar ejemplos de errores más comunes
    if error_files:
        print(f"\n❌ EJEMPLOS DE ERRORES (primeros 5):")
        for i, data in enumerate(error_files[:5], 1):
            print(f"\n  {i}. {data.get('file', 'N/A')}")
            print(f"     Error: {data.get('error_type', 'unknown')}")
            print(f"     Hablantes: {data.get('speaker_count', 0)}")
            print(f"     Voz detectada: {data.get('voiced_ratio', 0):.1%}")
            print(f"     Tags: {', '.join(data.get('tags', []))}")
            if data.get('notes'):
                print(f"     Notas: {', '.join(data.get('notes', []))}")
            transcript = data.get('transcript', '')[:80]
            if transcript:
                print(f"     Transcripción: {transcript}...")
    
    print(f"\n{'='*60}\n")
    
    # Recomendaciones
    if status_counts['valid'] == 0 and status_counts['error'] > 0:
        print("💡 RECOMENDACIONES:")
        print("-" * 60)
        
        if error_type_counts.get('no_evidence', 0) > 0:
            print("⚠ Muchos archivos rechazados por 'no_evidence':")
            print("  - Verifica que las keywords en config.py sean apropiadas")
            print("  - Considera agregar más palabras clave válidas")
            print("  - Revisa si la diarización está detectando correctamente 2 hablantes")
        
        if error_type_counts.get('no_voice', 0) > 0:
            print("⚠ Archivos rechazados por 'no_voice':")
            print("  - Considera reducir min_voiced_ratio en config.py")
        
        if error_type_counts.get('transcription_failed', 0) > 0:
            print("⚠ Archivos con error en transcripción:")
            print("  - Verifica que Whisper esté funcionando correctamente")
            print("  - Revisa la calidad del audio")
        
        print()

if __name__ == "__main__":
    import sys
    carpeta = sys.argv[1] if len(sys.argv) > 1 else "audios_filtrados"
    analizar_resultados(carpeta)

