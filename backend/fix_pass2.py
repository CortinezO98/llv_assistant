import bcrypt
from app.db.session import SessionLocal
from app.db.models.agent import Agent

password = "Admin2024!"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

db = SessionLocal()
agent = db.query(Agent).filter(Agent.email == 'linhaar@llvclinic.com').first()
if agent:
    agent.password_hash = hashed
    db.commit()
    print('Hash actualizado:', hashed[:30])
else:
    print('Agente no encontrado')
db.close()