"""
Script de EMERGENCIA para recuperar archivos que fueron movidos
Este script busca archivos en las carpetas de destino y los devuelve a la carpeta original
"""
import shutil
from pathlib import Path
import config

def recuperar_archivos(carpeta_origen: str, carpeta_proyecto: str = "."):
    """
    Recupera archivos que fueron movidos a carpetas de error/válidos
    y los devuelve a la carpeta original
    """
    origen = Path(carpeta_origen)
    proyecto = Path(carpeta_proyecto).resolve()
    
    if not origen.exists():
        print(f"❌ La carpeta de origen no existe: {origen}")
        return
    
    print(f"Recuperando archivos desde: {origen}")
    print(f"Directorio del proyecto: {proyecto}\n")
    
    # Carpetas donde pueden estar los archivos
    carpetas_destino = [
        proyecto / config.OUTPUT_DIR,  # audios_filtrados
        proyecto / config.ERROR_DIR,   # errores
    ]
    
    # Agregar subcarpetas de error
    for subdir in config.ERROR_SUBDIRS.values():
        carpetas_destino.append(proyecto / subdir)
    
    archivos_recuperados = 0
    archivos_no_encontrados = []
    
    # Buscar todos los archivos de audio en la carpeta de origen
    audio_extensions = {'.mp3', '.wav', '.gsm', '.m4a', '.flac', '.ogg'}
    archivos_originales = [
        f for f in origen.iterdir() 
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    
    print(f"Buscando {len(archivos_originales)} archivos originales...\n")
    
    # Para cada archivo original, buscar si está en alguna carpeta de destino
    for archivo_original in archivos_originales:
        nombre_archivo = archivo_original.name
        encontrado = False
        
        # Buscar en todas las carpetas de destino
        for carpeta_dest in carpetas_destino:
            if not carpeta_dest.exists():
                continue
            
            # Buscar el archivo (puede tener timestamp agregado)
            archivos_en_destino = list(carpeta_dest.glob(f"{archivo_original.stem}*{archivo_original.suffix}"))
            
            for archivo_destino in archivos_en_destino:
                # Verificar que el archivo original no existe (fue movido)
                if not archivo_original.exists():
                    try:
                        # COPIAR de vuelta (por si acaso)
                        shutil.copy2(str(archivo_destino), str(archivo_original))
                        print(f"✓ Recuperado: {nombre_archivo} desde {carpeta_dest.name}/")
                        archivos_recuperados += 1
                        encontrado = True
                        break
                    except Exception as e:
                        print(f"⚠ Error recuperando {nombre_archivo}: {e}")
                
        if not encontrado and not archivo_original.exists():
            archivos_no_encontrados.append(nombre_archivo)
    
    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN DE RECUPERACIÓN")
    print(f"{'='*60}")
    print(f"Archivos recuperados: {archivos_recuperados}")
    print(f"Archivos no encontrados: {len(archivos_no_encontrados)}")
    
    if archivos_no_encontrados:
        print(f"\n⚠ Archivos que no se encontraron en carpetas de destino:")
        for archivo in archivos_no_encontrados[:20]:  # Mostrar primeros 20
            print(f"  - {archivo}")
        if len(archivos_no_encontrados) > 20:
            print(f"  ... y {len(archivos_no_encontrados) - 20} más")
    
    print(f"\n💡 IMPORTANTE:")
    print(f"   - Los archivos fueron COPIADOS de vuelta a la carpeta original")
    print(f"   - Los archivos en carpetas de destino NO fueron eliminados")
    print(f"   - Revisa manualmente las carpetas:")
    for carpeta in carpetas_destino:
        if carpeta.exists():
            count = len(list(carpeta.glob("*.*")))
            print(f"     - {carpeta}: {count} archivos")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python recuperar_archivos.py <carpeta_origen> [carpeta_proyecto]")
        print("\nEjemplo:")
        print("  python recuperar_archivos.py E:/ProcesoAudios/2025/11/11")
        print("  python recuperar_archivos.py E:/ProcesoAudios/2025/11/11 E:/ProcesoAudios/2025/sandIA")
        sys.exit(1)
    
    carpeta_origen = sys.argv[1]
    carpeta_proyecto = sys.argv[2] if len(sys.argv) > 2 else "."
    
    print("="*60)
    print("SCRIPT DE RECUPERACIÓN DE ARCHIVOS")
    print("="*60)
    print("\n⚠ ADVERTENCIA: Este script intentará recuperar archivos")
    print("   que fueron movidos a carpetas de destino.\n")
    
    respuesta = input("¿Continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("Cancelado.")
        sys.exit(0)
    
    recuperar_archivos(carpeta_origen, carpeta_proyecto)

