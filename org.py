#!/usr/bin/env python3
"""
music_organizer.py — Organiza y sanitiza carpetas de audio por metadatos.

Modos:
  1. Organizar  — mueve archivos de audio sueltos a {artista}/{album}/
  2. Sanitizar  — colapsa carpetas de nivel raíz con nombre "artista1; artista2"
                  hacia la carpeta del primer artista
"""

import re
import sys
import shutil
from pathlib import Path

try:
    from mutagen import File as MutagenFile
except ImportError:
    print("Falta mutagen. Instálalo con:  pip install mutagen")
    sys.exit(1)

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav", ".aac", ".wv", ".ape"}

# Detecta si un nombre contiene separadores de artistas múltiples
HAS_SEPARATOR_RE = re.compile(r"\s*(?:&|;|,|\band\b)\s*", re.IGNORECASE)

# Parte por cualquier separador para obtener el primer artista
ARTIST_SPLIT_RE = re.compile(r"\s*(?:&|;|,|\band\b|\n)\s*", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------

def sanitize_name(name: str) -> str:
    """Reemplaza caracteres inválidos en nombres de archivo/directorio."""
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    return name


def first_artist(raw: str) -> str:
    """Devuelve el primer artista de una cadena con múltiples artistas."""
    parts = ARTIST_SPLIT_RE.split(raw.strip())
    return parts[0].strip() if parts else raw.strip()


def get_tag(tags, *keys):
    """Primer valor no vacío entre varias claves de etiquetas."""
    for key in keys:
        val = tags.get(key)
        if val:
            if isinstance(val, list):
                val = val[0]
            val = str(val).strip()
            if val:
                return val
    return None


def read_metadata(filepath: Path):
    """Lee metadatos de un archivo de audio. Devuelve dict o None."""
    audio = MutagenFile(filepath, easy=True)
    if audio is None or audio.tags is None:
        return None

    tags = audio.tags

    album_artist_raw = (
        get_tag(tags, "albumartist", "album_artist", "TPE2")
        or get_tag(tags, "artist", "TPE1")
        or "Unknown Artist"
    )
    album     = sanitize_name(get_tag(tags, "album", "TALB") or "Unknown Album")
    title     = sanitize_name(get_tag(tags, "title", "TIT2") or filepath.stem)
    track_raw = get_tag(tags, "tracknumber", "TRCK") or "0"
    track_num = re.split(r"[/\-]", track_raw)[0].strip().zfill(2)

    artist_clean = sanitize_name(first_artist(album_artist_raw))

    return {
        "album_artist_dir":  artist_clean,
        "album_artist_file": artist_clean,
        "album":             album,
        "title":             title,
        "track":             track_num,
    }


# ---------------------------------------------------------------------------
# Modo 1 — Organizar
# ---------------------------------------------------------------------------

def organize(directory: Path):
    audio_files = [f for f in directory.iterdir()
                   if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]

    if not audio_files:
        print("No se encontraron archivos de audio con extensiones conocidas.")
        return

    moved = skipped = 0

    for audio_path in sorted(audio_files):
        meta = read_metadata(audio_path)
        if not meta:
            print(f"  [SIN METADATOS]  {audio_path.name}")
            skipped += 1
            continue

        dest_dir = directory / meta["album_artist_dir"] / meta["album"]
        dest_dir.mkdir(parents=True, exist_ok=True)

        new_stem       = f"{meta['track']} - {meta['album_artist_file']} - {meta['title']}"
        new_audio_name = new_stem + audio_path.suffix.lower()
        dest_audio     = dest_dir / new_audio_name

        if dest_audio.resolve() == audio_path.resolve():
            print(f"  [YA EN SU LUGAR] {audio_path.name}")
        else:
            shutil.move(str(audio_path), str(dest_audio))
            print(f"  [MOVIDO]  {audio_path.name}")
            print(f"         → {dest_audio.relative_to(directory)}")
            moved += 1

        # Archivos compañeros con el mismo stem (lrc, txt, jpg, etc.)
        for companion in directory.iterdir():
            if not companion.is_file():
                continue
            if companion.suffix.lower() in AUDIO_EXTENSIONS:
                continue
            if companion.stem != audio_path.stem:
                continue
            dest_companion = dest_dir / (new_stem + companion.suffix.lower())
            if dest_companion.resolve() != companion.resolve():
                shutil.move(str(companion), str(dest_companion))
                print(f"  [COMPAÑERO]  {companion.name} → {dest_companion.relative_to(directory)}")

    print(f"\nListo. {moved} movido(s), {skipped} sin metadatos.")


# ---------------------------------------------------------------------------
# Modo 2 — Sanitizar
# ---------------------------------------------------------------------------

def merge_dirs(src: Path, dst: Path):
    """
    Mueve recursivamente el contenido de src hacia dst.
    Si un subdirectorio existe en ambos, entra en él y repite.
    Si un archivo ya existe en dst, lo omite y avisa.
    Después borra src si quedó vacío.
    """
    for item in list(src.iterdir()):
        target = dst / item.name
        if item.is_dir():
            target.mkdir(exist_ok=True)
            merge_dirs(item, target)
        else:
            if target.exists():
                print(f"    [OMITIDO, ya existe] {item.name}")
            else:
                shutil.move(str(item), str(target))
                print(f"    [MOVIDO] {item.name}")

    # Elimina src si quedó vacío
    try:
        src.rmdir()
        print(f"  [ELIMINADA] '{src.name}'")
    except OSError:
        print(f"  [ADVERTENCIA] No se pudo eliminar '{src.name}' (¿no vacía?)")


def sanitize_files(directory: Path):
    """
    Recorre recursivamente directory buscando archivos de audio (y .lrc) cuyo
    nombre siga el patrón  {track} - {artist} - {title}.ext  y donde la parte
    del artista contenga separadores. Renombra usando solo el primer artista.
    """
    renamed = 0

    for filepath in sorted(directory.rglob("*")):
        if not filepath.is_file():
            continue

        stem  = filepath.stem   # nombre sin extensión
        parts = stem.split(" - ", 2)   # máximo 3 partes: track, artist, title

        # Solo procesamos si tiene exactamente 3 partes (track - artist - title)
        if len(parts) != 3:
            continue

        track_raw_stem, artist_raw, title = parts
        track        = re.split(r"[/\\-]", track_raw_stem)[0].strip().zfill(2)
        artist_clean = sanitize_name(first_artist(artist_raw))
        new_stem     = f"{track} - {artist_clean} - {title}"

        # Si el nombre ya es el esperado, no hay nada que hacer
        if filepath.stem == new_stem:
            continue

        new_path = filepath.with_name(new_stem + filepath.suffix.lower())

        if new_path.exists():
            print(f"  [OMITIDO, ya existe] {new_path.name}")
        else:
            filepath.rename(new_path)
            print(f"  [RENOMBRADO] {filepath.name}")
            print(f"            → {new_path.name}")
            renamed += 1

    return renamed


def sanitize_dirs(directory: Path):
    """
    Busca carpetas de primer nivel cuyo nombre contenga separadores de artistas,
    las colapsa hacia la carpeta del primer artista, y luego sanitiza los nombres
    de archivos dentro de toda la estructura.
    """
    # De más profundo a más superficial para no romper rutas al renombrar padres antes que hijos
    all_dirs = sorted([d for d in directory.rglob("*") if d.is_dir()], key=lambda p: -len(p.parts))
    dirty    = [d for d in all_dirs if HAS_SEPARATOR_RE.search(d.name)]

    dirs_merged = dirs_renamed = 0

    if not dirty:
        print("No se encontraron carpetas con separadores de artistas.")
    else:
        for dirty_dir in dirty:
            raw_name   = dirty_dir.name
            clean_name = sanitize_name(first_artist(raw_name))
            clean_dir  = dirty_dir.parent / clean_name

            print(f"\n  [DETECTADA] '{raw_name}'  →  '{clean_name}'")

            if not HAS_SEPARATOR_RE.search(raw_name):
                print(f"    Regex no confirmó separador, se omite.")
                continue

            if clean_dir.exists():
                print(f"  [FUSIONANDO] '{raw_name}' → '{clean_name}'")
                merge_dirs(dirty_dir, clean_dir)
                dirs_merged += 1
            else:
                dirty_dir.rename(clean_dir)
                print(f"  [RENOMBRADA] '{raw_name}' → '{clean_name}'")
                dirs_renamed += 1

        print(f"\nCarpetas: {dirs_renamed} renombrada(s), {dirs_merged} fusionada(s).")

    # Sanitizar nombres de archivos en toda la estructura
    print(f"\nSanitizando nombres de archivos en '{directory.resolve()}'...\n")
    files_renamed = sanitize_files(directory)
    print(f"\nArchivos: {files_renamed} renombrado(s).")


# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------

def ask_directory() -> Path:
    raw = input("Directorio [Enter = directorio actual]: ").strip()
    directory = Path(raw) if raw else Path.cwd()
    if not directory.exists() or not directory.is_dir():
        print(f"Error: '{directory}' no es un directorio válido.")
        sys.exit(1)
    return directory


def main():
    print("=" * 40)
    print("  Music Organizer")
    print("=" * 40)
    print("  1. Organizar")
    print("  2. Sanitizar")
    print("=" * 40)

    choice = input("Elige una opción [1/2]: ").strip()

    match choice:
        case "1":
            directory = ask_directory()
            print(f"\nOrganizando: {directory.resolve()}\n")
            organize(directory)

        case "2":
            directory = ask_directory()
            print(f"\nSanitizando: {directory.resolve()}\n")
            sanitize_dirs(directory)

        case _:
            print("Opción inválida. Usa 1 o 2.")
            sys.exit(1)


if __name__ == "__main__":
    main()
