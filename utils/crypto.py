from cryptography.fernet import Fernet
import os
import json
from dotenv import load_dotenv

load_dotenv()
# Imposta la tua chiave segreta in un file di configurazione sicuro o variabile d'ambiente
SECRET_KEY = os.environ.get("FERNET_KEY")
fernet = Fernet(SECRET_KEY.encode())

def encrypt_json(data: dict) -> str:
    json_data = json.dumps(data)
    return fernet.encrypt(json_data.encode()).decode()

def decrypt_json(data: str) -> dict:
    decrypted = fernet.decrypt(data.encode()).decode()
    return json.loads(decrypted)

def encrypt_string(text: str) -> str:
    return fernet.encrypt(text.encode()).decode()

def decrypt_string(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
