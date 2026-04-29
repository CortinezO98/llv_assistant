"""
scripts/create_tables.py

Crea todas las tablas en la base de datos.
Ejecutar: python scripts/create_tables.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import Base, engine
import app.db.models  # noqa: importa todos los modelos

print("Creando tablas en la base de datos...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas exitosamente.")
print("\nTablas disponibles:")
for table in Base.metadata.sorted_tables:
    print(f"  - {table.name}")
