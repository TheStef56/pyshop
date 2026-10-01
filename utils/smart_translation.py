import os
import hashlib
import subprocess
import time
import re
from babel.messages.pofile import read_po, write_po
from googletrans import Translator

# Percorso assoluto al file messages.pot
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
MESSAGES_POT_LOCATION = os.path.abspath(os.path.join(BASE_DIR, "../messages.pot"))

def file_is_newer(file1, file2):
    if not os.path.exists(file2):
        return True
    if not os.path.exists(file1):
        return False
    return os.path.getmtime(file1) > os.path.getmtime(file2)

def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def needs_extraction():
    if not os.path.exists(MESSAGES_POT_LOCATION):
        print("📝 messages.pot non esiste, estrazione necessaria")
        return True

    pot_time = os.path.getmtime(MESSAGES_POT_LOCATION)

    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['venv', '.git', '__pycache__', 'node_modules']):
            continue

        for file in files:
            if file.endswith(('.py', '.html')):
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) > pot_time:
                    print(f"📝 {file_path} è più recente di messages.pot")
                    return True

    return False

def needs_translation_update(lang):
    po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
    if not os.path.exists(po_path):
        print(f"📝 {po_path} non esiste, aggiornamento necessario")
        return True
    if not os.path.exists(MESSAGES_POT_LOCATION):
        return False
    if file_is_newer(MESSAGES_POT_LOCATION, po_path):
        print(f"📝 messages.pot è più recente di {po_path}")
        return True
    return False

def needs_compilation(lang):
    po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
    mo_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.mo')

    if not os.path.exists(mo_path):
        print(f"📝 {mo_path} non esiste, compilazione necessaria")
        return True

    if file_is_newer(po_path, mo_path):
        po_hash = file_hash(po_path)
        mo_hash = file_hash(mo_path)
        if po_hash and mo_hash and po_hash != mo_hash:
            print(f"📝 {po_path} è più recente e diverso da {mo_path}")
            return True

    return False

def extract_messages():
    print("🔍 Estraendo messaggi dal codice...")
    try:
        subprocess.run([
            "pybabel", "extract", 
            "--ignore-dirs", "venv*",
            "-F", "babel.cfg",
            "-k", "lazy_gettext", "-k", "_", "-k", "gettext",
            "-o", MESSAGES_POT_LOCATION,
            "."
        ], check=True)
        print("✅ Messaggi estratti in messages.pot")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nell'estrazione: {e}")
        return False
    except FileNotFoundError:
        print("❌ pybabel non trovato. Installa babel: pip install babel")
        return False

def update_translation(lang):
    po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
    if not os.path.exists(po_path):
        print(f"🆕 Inizializzando traduzione per {lang}...")
        try:
            subprocess.run([
                "pybabel", "init",
                "-i", MESSAGES_POT_LOCATION,
                "-d", "translations",
                "-l", lang
            ], check=True)
            print(f"✅ Traduzione inizializzata per {lang}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Errore nell'inizializzazione di {lang}: {e}")
            return False
    else:
        print(f"🔄 Aggiornando traduzione per {lang}...")
        try:
            subprocess.run([
                "pybabel", "update",
                "-i", MESSAGES_POT_LOCATION,
                "-d", "translations",
                "-l", lang
            ], check=True)
            print(f"✅ Traduzione aggiornata per {lang}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Errore nell'aggiornamento di {lang}: {e}")
            return False

def smart_translation_update():
    languages = ['it']
    print("🔍 Controllando cosa deve essere aggiornato...")
    if needs_extraction():
        if not extract_messages():
            return False
    else:
        print("⏭️ Estrazione non necessaria")
    for lang in languages:
        print(f"\n🌍 Controllando lingua: {lang}")
        po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
        if needs_translation_update(lang):
            if not update_translation(lang):
                continue
            clean_fuzzy_flags(po_path)
        else:
            print(f"⏭️ File PO per {lang} è aggiornato")
        if has_empty_translations(po_path):
            print(f"🔄 Trovate traduzioni vuote per {lang}")
            auto_translate_po(po_path, lang)
        else:
            print(f"⏭️ Tutte le traduzioni per {lang} sono complete")
        if needs_compilation(lang):
            compile_translation(lang)
        else:
            print(f"⏭️ Compilazione per {lang} non necessaria")
    print("\n🎉 Aggiornamento traduzioni completato!")
    return True

def auto_translate_po(po_path, lang_code):
    translator = Translator()
    print(f"🔄 Traducendo: {po_path} per lingua: {lang_code}")
    with open(po_path, 'r', encoding='utf-8') as f:
        catalog = read_po(f)
    translated_count = 0
    total_count = 0
    for message in catalog:
        if message.id:
            if isinstance(message.id, tuple):
                message_text = message.id[0] if message.id[0] else None
            else:
                message_text = message.id
            if not message_text or not message_text.strip():
                continue
            total_count += 1
            has_translation = False
            if isinstance(message.string, tuple):
                has_translation = any(s and s.strip() for s in message.string)
            else:
                has_translation = message.string and message.string.strip()
            if not has_translation:
                try:
                    display_text = message_text[:50] + "..." if len(message_text) > 50 else message_text
                    print(f"  🔄 Traducendo: '{display_text}'")
                    result = translator.translate(message_text, dest=lang_code)
                    if result and result.text:
                        if isinstance(message.string, tuple):
                            message.string = (result.text,) + message.string[1:]
                        else:
                            message.string = result.text
                        translated_count += 1
                        display_result = result.text[:50] + "..." if len(result.text) > 50 else result.text
                        print(f"  ✅ -> '{display_result}'")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"  ❌ Errore traducendo '{display_text}': {e}")
    if translated_count > 0:
        print(f"📊 Tradotti {translated_count}/{total_count} messaggi per {lang_code}")
        with open(po_path, 'wb') as f:
            write_po(f, catalog)
        return True
    else:
        print(f"📊 Nessuna nuova traduzione necessaria per {lang_code}")
        return False

def clean_fuzzy_flags(po_path):
    if not os.path.exists(po_path):
        return False
    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            catalog = read_po(f)
        for message in catalog:
            if getattr(message, 'fuzzy', False):
                message.fuzzy = False
        with open(po_path, 'wb') as f:
            write_po(f, catalog)
        return True
    except Exception as e:
        print(f"❌ Errore nella pulizia flag fuzzy: {e}")
        return False

def has_empty_translations(po_path):
    if not os.path.exists(po_path):
        return False
    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            catalog = read_po(f)
        for message in catalog:
            if message.id:
                if isinstance(message.id, tuple):
                    message_text = message.id[0] if message.id[0] else None
                else:
                    message_text = message.id
                if not message_text or not message_text.strip():
                    continue
                has_translation = False
                if isinstance(message.string, tuple):
                    has_translation = any(s and s.strip() for s in message.string)
                else:
                    has_translation = message.string and message.string.strip()
                if not has_translation:
                    return True
        return False
    except Exception as e:
        print(f"❌ Errore nel controllo traduzioni vuote: {e}")
        return False

def validate_placeholders(po_path):
    """Controlla che i placeholder nelle traduzioni coincidano con quelli originali."""
    if not os.path.exists(po_path):
        return True
    try:
        with open(po_path, 'r', encoding='utf-8') as f:
            catalog = read_po(f)
        placeholder_pattern = re.compile(r'%\(([^)]+)\)[sd]')
        for message in catalog:
            if message.id and message.string:
                if isinstance(message.id, tuple):
                    source = message.id[0]
                else:
                    source = message.id
                if isinstance(message.string, tuple):
                    translated = message.string[0]
                else:
                    translated = message.string
                src_ph = set(placeholder_pattern.findall(source))
                dst_ph = set(placeholder_pattern.findall(translated))
                if src_ph != dst_ph:
                    print(f"⚠️ Placeholder mismatch in msgid: '{source}'")
                    return False
        return True
    except Exception as e:
        print(f"❌ Errore nella validazione dei placeholder: {e}")
        return False

def compile_translation(lang):
    po_path = os.path.join('translations', lang, 'LC_MESSAGES', 'messages.po')
    if not validate_placeholders(po_path):
        print(f"❌ Compilazione bloccata: mismatch nei placeholder per {lang}")
        return False
    try:
        subprocess.run([
            "pybabel", "compile", 
            "-d", "translations",
            "-l", lang
        ], check=True)
        print(f"✅ Traduzione compilata per {lang}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nella compilazione di {lang}: {e}")
        return False