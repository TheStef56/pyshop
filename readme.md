# pyshop

Gestione utenti, ruoli e permessi con Flask, SQLAlchemy e Flask-Session.

## Requisiti

- Python 3.10+
- MySQL server
- pip

## Installazione

1. Crea e attiva un ambiente virtuale:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. Installa le dipendenze:
    ```bash
    pip install -r requirements.txt
    ```

3. Configura il database MySQL:
    - Crea il database `pyshop` e un utente con permessi.

4. Inizializza le migrazioni e il database:
    ```bash
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```

5. Esegui il seed per dati di esempio:
    ```bash
    python manage.py seed
    ```

## Avvio del progetto

```bash
python app.py
```

## Struttura del progetto

- `app.py` - entrypoint Flask/app factory
- `manage.py` - CLI per seed e comandi custom
- `models/` - modelli SQLAlchemy (`User`, `UserRoles`, `RolePermission`)
- `blueprints/` - blueprint Flask (es. admin)
- `migrations/` - gestione migrazioni Alembic
