from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from app import SessionLocal
from app.models.usuarios import Usuarios


def cadastrar_usuario(username, password, team,
                      nome=None, email=None, telefone=None,
                      instagram=None, descricao=None,
                      id_usuarios=None, permissao=None):

    session = SessionLocal()
    try:
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
            id_usuarios=id_usuarios,
            permissao=permissao
        )

        session.add(usuario)
        session.commit()
        session.refresh(usuario)

        return usuario

    except IntegrityError as e:
        session.rollback()
        raise ValueError(f"Erro de integridade no banco: {str(e.orig)}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def login(username, password):
    session = SessionLocal()
    try:
        usuario = session.query(Usuarios).filter_by(username=username).first()

        if usuario and check_password_hash(usuario.password, password):
            # retorna os dados antes de fechar a sessão
            user_data = {
                "id": usuario.id,
                "username": usuario.username,
                "team": usuario.team,
                "nome": usuario.nome,
                "email": usuario.email,
                "telefone": usuario.telefone,
                "instagram": usuario.instagram,
                "descricao": usuario.descricao,
                "permissao": usuario.permissao,
                "id_usuarios": usuario.id_usuarios
            }
            return user_data

        return None

    finally:
        session.close()