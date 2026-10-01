import re
import os
import unicodedata
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename : str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def filename_to_json_key(filename : str) -> str:
    # Rimuove il path se presente
    filename = filename.split('/')[-1].split('\\')[-1]
    name = filename.rsplit('.', 1)[0]
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]+', '-', name)
    name = name.strip('-')
    return name

def convert_to_webp(image_path, quality=85, lossless=False):
    try:
        if image_path.lower().endswith('.webp'):
            return image_path

        with Image.open(image_path) as img:
            # Se ha canale alpha, mantienilo
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')

            webp_path = os.path.splitext(image_path)[0] + '.webp'
            img.save(
                webp_path,
                'WEBP',
                quality=quality,
                lossless=lossless,   # se vuoi output senza perdita
                save_all=True
            )

        if os.path.exists(image_path):
            os.remove(image_path)

        return webp_path
    except Exception as e:
        print(f"Errore nella conversione WebP: {e}")
        return image_path