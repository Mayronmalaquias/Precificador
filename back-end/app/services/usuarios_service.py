from app import SessionLocal
from app.models.usuarios import Usuarios
import time

# Cache simples em memória: { chave: (timestamp, resultado) }
_cache = {}
CACHE_TTL = 30  # segundos


def _cache_get(key):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key, value):
    _cache[key] = (time.time(), value)


def _cache_invalidate(*prefixes):
    for key in list(_cache.keys()):
        if any(key.startswith(p) for p in prefixes):
            del _cache[key]


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


def _deduplicar_por_id_usuarios(rows):
    """
    Remove registros repetidos pelo campo id_usuarios.
    Mantém o primeiro que aparecer.
    Se id_usuarios vier vazio, usa o id interno como fallback.
    """
    unicos = []
    vistos = set()

    for r in rows:
        chave = r.id_usuarios if r.id_usuarios is not None else f"_sem_id_{r.id}"
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(r)

    return unicos


def retornar_lista(id_gerente=None, ativo=None, page=1, per_page=1000):
    """
    Retorna lista paginada de usuários.
    - id_gerente: filtra pelo campo team
    - ativo: filtra pelo campo ativo (bool)
    - page / per_page: paginação
    """
    cache_key = f"lista:{id_gerente}:{ativo}:{page}:{per_page}"
    cached = _cache_get(cache_key)
    #if cached:
    #    return cached

    session = SessionLocal()
    try:
        query = session.query(
            Usuarios.id,
            Usuarios.username,
            Usuarios.team,
            Usuarios.nome,
            Usuarios.email,
            Usuarios.telefone,
            Usuarios.instagram,
            Usuarios.descricao,
            Usuarios.permissao,
            Usuarios.id_usuarios,
            Usuarios.ativo,
        )

        if id_gerente is not None:
            query = query.filter(Usuarios.team == id_gerente)

        if ativo is not None:
            query = query.filter(Usuarios.ativo == ativo)

        # ordena para deixar a deduplicação previsível
        rows = (
            query
            .order_by(Usuarios.id.asc())
            .all()
        )

        rows_unicos = _deduplicar_por_id_usuarios(rows)

        total = len(rows_unicos)

        inicio = (page - 1) * per_page
        fim = inicio + per_page
        rows_paginados = rows_unicos[inicio:fim]

        lista = [
            {
                "id": r.id,
                "username": r.username,
                "team": r.team,
                "nome": r.nome,
                "email": r.email,
                "telefone": r.telefone,
                "instagram": r.instagram,
                "descricao": r.descricao,
                "permissao": r.permissao,
                "id_usuarios": r.id_usuarios,
                "ativo": r.ativo,
            }
            for r in rows_paginados
        ]

        resultado = {
            "lista": lista,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
        _cache_set(cache_key, resultado)
        return resultado

    finally:
        session.close()


def retornar_infos(id_corretor=None, username=None):
    """Retorna um único usuário pelo id_usuarios ou username."""
    cache_key = f"info:{id_corretor}:{username}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    session = SessionLocal()
    try:
        query = session.query(Usuarios)

        if id_corretor is not None:
            query = query.filter(Usuarios.id_usuarios == id_corretor)
        elif username is not None:
            query = query.filter(Usuarios.username == username)
        else:
            return {"error": "Nenhum parâmetro informado"}

        usuario = query.first()
        if not usuario:
            return {"error": "Usuário não encontrado"}

        resultado = _usuario_to_dict(usuario)
        _cache_set(cache_key, resultado)
        return resultado

    finally:
        session.close()


def alterar_ativo(id_corretor, ativo):
    session = SessionLocal()
    try:
        usuario = session.query(Usuarios).filter(
            Usuarios.id_usuarios == id_corretor
        ).first()

        if not usuario:
            return {"error": "Usuário não encontrado"}

        usuario.ativo = ativo
        session.commit()

        _cache_invalidate("lista:", f"info:{id_corretor}:")
        return {"ok": "Ativo alterado com sucesso"}

    except Exception:
        session.rollback()
        return {"error": "Erro ao alterar status ativo"}

    finally:
        session.close()


def retornar_corretor_nome(nome):
    """Busca corretores pelo nome (ilike), limitado a 10 resultados."""
    session = SessionLocal()
    try:
        usuarios = (
            session.query(
                Usuarios.id,
                Usuarios.username,
                Usuarios.nome,
                Usuarios.team,
                Usuarios.permissao,
                Usuarios.id_usuarios,
                Usuarios.ativo,
                Usuarios.email,
                Usuarios.telefone,
                Usuarios.instagram,
                Usuarios.descricao,
            )
            .filter(Usuarios.nome.ilike(f"%{nome}%"))
            .order_by(Usuarios.id.asc())
            .all()
        )

        usuarios_unicos = _deduplicar_por_id_usuarios(usuarios)[:10]

        return [
            {
                "id": u.id,
                "username": u.username,
                "nome": u.nome,
                "team": u.team,
                "permissao": u.permissao,
                "id_usuarios": u.id_usuarios,
                "ativo": u.ativo,
                "email": u.email,
                "telefone": u.telefone,
                "instagram": u.instagram,
                "descricao": u.descricao,
            }
            for u in usuarios_unicos
        ]
    finally:
        session.close()


def alterar_gerente(manager, id_corretor):
    session = SessionLocal()
    try:
        usuarios = (
            session.query(Usuarios)
            .filter(Usuarios.id_usuarios.in_([manager, id_corretor]))
            .all()
        )

        user = next((u for u in usuarios if u.id_usuarios == id_corretor), None)
        man = next((u for u in usuarios if u.id_usuarios == manager), None)

        if not user:
            return {"error": "Corretor inválido"}
        if not man:
            return {"error": "Gerente inválido"}
        if man.permissao == "user":
            return {"error": "O usuário informado não tem permissão de gerente"}

        user.team = manager
        session.commit()

        _cache_invalidate("lista:", f"info:{id_corretor}:")
        return {"ok": "Gerente alterado com sucesso"}

    except Exception:
        session.rollback()
        return {"error": "Algo de errado aconteceu"}

    finally:
        session.close()