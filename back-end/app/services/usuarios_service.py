from app import SessionLocal
from app.models.usuarios import Usuarios


def _usuario_to_dict(usuario):
    return {
        "id": usuario.id,
        "username": usuario.username,
        "team": usuario.team,
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "instagram": usuario.instagram,
        "descricao": usuario.descricao,
        "permissao": usuario.permissao,
        "id_usuarios": usuario.id_usuarios,
        "ativo": getattr(usuario, "ativo", None),
    }


def retornar_lista(id_gerente=None, ativo=None):
    session = SessionLocal()
    try:
        query = session.query(Usuarios)

        if id_gerente is not None:
            query = query.filter_by(team=id_gerente)

        if ativo is not None:
            query = query.filter_by(ativo=ativo)

        usuarios = query.all()
        return [_usuario_to_dict(usuario) for usuario in usuarios]

    finally:
        session.close()


def retornar_infos(id_corretor=None, username=None):
    session = SessionLocal()
    try:
        query = session.query(Usuarios)

        if id_corretor is not None:
            query = query.filter_by(id_usuarios=id_corretor)

        if username is not None:
            query = query.filter_by(username=username)

        usuario = query.first()

        if not usuario:
            return {"error": "Usuário não encontrado"}

        return _usuario_to_dict(usuario)

    finally:
        session.close()


def alterar_ativo(id_corretor, ativo):
    session = SessionLocal()
    try:
        usuario = session.query(Usuarios).filter_by(id_usuarios=id_corretor).first()

        if not usuario:
            return {"error": "Usuário não encontrado"}

        usuario.ativo = ativo
        session.commit()

        return {"ok": "Ativo alterado com sucesso"}

    except Exception:
        session.rollback()
        return {"error": "Erro ao alterar status ativo"}

    finally:
        session.close()