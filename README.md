# org — music Organization with Recursivity and Gratification

Organizador y sanitizador de bibliotecas de audio por metadatos.

## Requisitos

- Python 3.10+
- [mutagen](https://mutagen.readthedocs.io/)

```bash
pip install mutagen
```

## Uso

```bash
./org.py
```

Se muestra un menú interactivo con dos modos:

### 1. Organizar

Toma archivos de audio sueltos dentro de un directorio y los mueve a la estructura `Artista/Album/`, leyendo metadatos vía mutagen. Los archivos se renombran con el formato `{track} - {artist} - {title}.ext`. Los archivos acompañantes (`.lrc`, `.txt`, `.jpg`, etc.) con el mismo nombre base también se trasladan.

```
./org.py
Elije una opción [1/2]: 1
Directorio [Enter = directorio actual]: /ruta/a/música
```

### 2. Sanitizar

Dos operaciones en secuencia:

1. **Fusión de carpetas** — Busca directorios raíz cuyo nombre contenga separadores (`&`, `;`, `,`, `and`) indicando múltiples artistas. Los colapsa en la carpeta del primer artista, fusionando su contenido recursivamente.
2. **Renombrado de archivos** — Recorre toda la estructura y normaliza los nombres de archivo que contengan separadores, quedándose con el primer artista.

```
./org.py
Elije una opción [1/2]: 2
Directorio [Enter = directorio actual]: /ruta/a/música
```

## Extensiones soportadas

`mp3`, `flac`, `ogg`, `m4a`, `opus`, `wav`, `aac`, `wv`, `ape`

## Etiquetas de metadatos leídas

- **Album Artist**: `albumartist`, `album_artist`, `TPE2`, `artist`, `TPE1`
- **Álbum**: `album`, `TALB`
- **Título**: `title`, `TIT2`
- **Número de pista**: `tracknumber`, `TRCK`

## Licencia

MIT
