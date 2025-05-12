from werkzeug.security import generate_password_hash, check_password_hash
from app import SessionLocal
from app.models.usuarios import Usuarios

def cadastrar_usuario(username, password, team):
    session = SessionLocal()
    hashed_pw = generate_password_hash(password)
    usuario = Usuarios(username=username, password=hashed_pw, team=team)
    session.add(usuario)
    session.commit()
    session.close()

def login(username, password):
    session = SessionLocal()
    usuario = session.query(Usuarios).filter_by(username=username).first()
    session.close()

    if usuario and check_password_hash(usuario.password, password):
        return True
    return False
