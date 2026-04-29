"""
scripts/create_tables.py
Crea todas las tablas en la base de datos (incluye llv_analytics_events).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import Base, engine
import app.db.models  # importa todos los modelos

print("Creando tablas...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas:")
for t in Base.metadata.sorted_tables:
    print(f"  - {t.name}")
