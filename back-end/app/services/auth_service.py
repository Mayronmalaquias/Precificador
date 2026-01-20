from werkzeug.security import generate_password_hash, check_password_hash
from app import SessionLocal
from app.models.usuarios import Usuarios

def cadastrar_usuario(username, password, team,
                      nome=None, email=None, telefone=None,
                      instagram=None, descricao=None, 
                      id_usuarios=None, permissao=None): # Corrigido aqui: id_usuarios
    session = SessionLocal()
    hashed_pw = generate_password_hash(password)

    usuario = Usuarios(
        username=username,
        password=hashed_pw,
        team=team,
        nome=nome,
        email=email,
        telefone=telefone,
        instagram=instagram,
        descricao=descricao,
        id_usuarios = id_usuarios, # Corrigido aqui: id_usuarios
        permissao = permissao
    )

    session.add(usuario)
    session.commit()
    session.close()


def login(username, password):
    """
    Em vez de retornar só True/False,
    retorna o objeto Usuarios ou None.
    """
    session = SessionLocal()
    usuario = session.query(Usuarios).filter_by(username=username).first()
    session.close()

    if usuario and check_password_hash(usuario.password, password):
        return usuario
    return None
