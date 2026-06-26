from app import SessionLocal
from app.models.usuarios import Usuarios
from werkzeug.security import generate_password_hash
from datetime import date, datetime
import time

RH_CAMPOS_OBRIGATORIOS = {
    "status",
    "nome",
    "unidade",
    "gerente_responsavel",
    "data_entrada_61",
    "telefone_corporativo",
    "email_corporativo",
    "data_nascimento",
    "estado_civil",
    "possui_filhos",
    "endereco",
    "contato_emergencia",
    "cpf",
    "contrato_assinado",
    "codigo_conduta_assinado",
    "lgpd_assinada",
    "onboarding_realizado",
}

RH_CAMPOS_EDITAVEIS = {
    "status", "unidade", "gerente_responsavel", "data_entrada_61",
    "creci", "validade_creci", "telefone_pessoal", "telefone_corporativo",
    "email_pessoal", "email_corporativo", "data_nascimento", "estado_civil",
    "possui_filhos", "endereco", "contato_emergencia", "cpf", "rg", "cnpj",
    "razao_social", "banco", "agencia", "conta", "tipo_conta", "chave_pix",
    "contrato_assinado", "codigo_conduta_assinado", "lgpd_assinada",
    "onboarding_realizado", "desligado", "data_desligamento", "observacoes",
}

DATE_FIELDS = {
    "data_entrada_61",
    "validade_creci",
    "data_nascimento",
    "data_desligamento",
}

BOOL_FIELDS = {
    "possui_filhos",
    "contrato_assinado",
    "codigo_conduta_assinado",
    "lgpd_assinada",
    "onboarding_realizado",
    "desligado",
}

CAMPOS_EDITAVEIS = {
    "nome", "email", "telefone", "instagram", "descricao",
    "username", "permissao", "team",
}.union(RH_CAMPOS_EDITAVEIS)

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


def _date_to_iso(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return value


def _parse_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _parse_bool(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in {"true", "1", "sim", "s", "yes"}:
        return True
    if value in {"false", "0", "nao", "não", "n", "no"}:
        return False
    return None


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
        "id_imoview": getattr(usuario, "id_imoview", None),
        "status": getattr(usuario, "status", None),
        "unidade": getattr(usuario, "unidade", None),
        "gerente_responsavel": getattr(usuario, "gerente_responsavel", None),
        "data_entrada_61": _date_to_iso(getattr(usuario, "data_entrada_61", None)),
        "creci": getattr(usuario, "creci", None),
        "validade_creci": _date_to_iso(getattr(usuario, "validade_creci", None)),
        "telefone_pessoal": getattr(usuario, "telefone_pessoal", None),
        "telefone_corporativo": getattr(usuario, "telefone_corporativo", None),
        "email_pessoal": getattr(usuario, "email_pessoal", None),
        "email_corporativo": getattr(usuario, "email_corporativo", None),
        "data_nascimento": _date_to_iso(getattr(usuario, "data_nascimento", None)),
        "estado_civil": getattr(usuario, "estado_civil", None),
        "possui_filhos": getattr(usuario, "possui_filhos", None),
        "endereco": getattr(usuario, "endereco", None),
        "contato_emergencia": getattr(usuario, "contato_emergencia", None),
        "cpf": getattr(usuario, "cpf", None),
        "rg": getattr(usuario, "rg", None),
        "cnpj": getattr(usuario, "cnpj", None),
        "razao_social": getattr(usuario, "razao_social", None),
        "banco": getattr(usuario, "banco", None),
        "agencia": getattr(usuario, "agencia", None),
        "conta": getattr(usuario, "conta", None),
        "tipo_conta": getattr(usuario, "tipo_conta", None),
        "chave_pix": getattr(usuario, "chave_pix", None),
        "contrato_assinado": getattr(usuario, "contrato_assinado", None),
        "codigo_conduta_assinado": getattr(usuario, "codigo_conduta_assinado", None),
        "lgpd_assinada": getattr(usuario, "lgpd_assinada", None),
        "onboarding_realizado": getattr(usuario, "onboarding_realizado", None),
        "desligado": getattr(usuario, "desligado", None),
        "data_desligamento": _date_to_iso(getattr(usuario, "data_desligamento", None)),
        "observacoes": getattr(usuario, "observacoes", None),
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
        query = session.query(Usuarios)

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

        lista = [_usuario_to_dict(r) for r in rows_paginados]

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
        if ativo:
            usuario.status = "Ativo"
        elif not usuario.desligado:
            usuario.status = "Inativo"
        session.commit()

        _cache_invalidate("lista:", f"info:{id_corretor}:")
        return {"ok": "Ativo alterado com sucesso", "status": usuario.status}

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
        if man.permissao not in ("gerente", "administrador", "diretor"):
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


def editar_usuario(solicitante_id, id_corretor, dados=None, nova_senha=None):
    """
    Edita os dados (e opcionalmente a senha) de um usuário.
    Só é permitido se o solicitante (validado no banco, não no payload) for diretor.
    """
    session = SessionLocal()
    try:
        solicitante = session.query(Usuarios).filter(
            Usuarios.id_usuarios == solicitante_id
        ).first()

        solicitante_admin = (
            solicitante
            and (
                solicitante.permissao in {"diretor", "administrador", "administrativo"}
                or str(solicitante.team or "").lower() == "administrativo"
            )
        )
        if not solicitante_admin:
            return {"error": "Apenas diretores, administradores ou RH podem editar usuários."}

        usuario = session.query(Usuarios).filter(
            Usuarios.id_usuarios == id_corretor
        ).first()

        if not usuario:
            return {"error": "Usuário não encontrado"}

        for campo, valor in (dados or {}).items():
            if campo in CAMPOS_EDITAVEIS:
                if campo in DATE_FIELDS:
                    valor = _parse_date(valor)
                elif campo in BOOL_FIELDS:
                    valor = _parse_bool(valor)
                setattr(usuario, campo, valor)

        if usuario.desligado:
            usuario.status = "Desligado"
            usuario.ativo = False
        elif usuario.status == "Desligado":
            usuario.status = "Ativo" if usuario.ativo else "Inativo"

        if nova_senha:
            usuario.password = generate_password_hash(nova_senha)

        session.commit()

        _cache_invalidate("lista:", f"info:{id_corretor}:")
        return {"ok": "Usuário atualizado com sucesso", "usuario": _usuario_to_dict(usuario)}

    except Exception:
        session.rollback()
        return {"error": "Erro ao atualizar usuário"}

    finally:
        session.close()


def editar_rh_corretor_gerente(solicitante_id, id_corretor, dados=None):
    """
    Permite que um gerente preencha dados de RH dos corretores ativos da propria equipe.
    Administradores, diretores e administrativo podem usar o mesmo fluxo sem restricao de equipe.
    """
    session = SessionLocal()
    try:
        solicitante = session.query(Usuarios).filter(
            Usuarios.id_usuarios == solicitante_id
        ).first()

        if not solicitante:
            return {"error": "Solicitante nao encontrado"}

        permissao = str(solicitante.permissao or "").lower()
        solicitante_admin = (
            permissao in {"diretor", "administrador", "administrativo"}
            or str(solicitante.team or "").lower() == "administrativo"
        )
        if permissao != "gerente" and not solicitante_admin:
            return {"error": "Apenas gerentes, administradores, diretores ou RH podem preencher dados de RH."}

        usuario = session.query(Usuarios).filter(
            Usuarios.id_usuarios == id_corretor
        ).first()

        if not usuario:
            return {"error": "Corretor nao encontrado"}

        if str(usuario.permissao or "").lower() != "corretor":
            return {"error": "Este fluxo permite editar apenas corretores."}

        if usuario.ativo is not True:
            return {"error": "Este fluxo permite editar apenas corretores ativos."}

        if not solicitante_admin and str(usuario.team or "") != str(solicitante.id_usuarios or ""):
            return {"error": "O corretor nao pertence a equipe deste gerente."}

        campos_gerente = set(RH_CAMPOS_EDITAVEIS).union({"nome"}) - {"desligado", "data_desligamento"}

        for campo, valor in (dados or {}).items():
            if campo not in campos_gerente:
                continue
            if campo in DATE_FIELDS:
                valor = _parse_date(valor)
            elif campo in BOOL_FIELDS:
                valor = _parse_bool(valor)
            setattr(usuario, campo, valor)

        if usuario.desligado:
            usuario.status = "Desligado"
            usuario.ativo = False
        elif usuario.status == "Desligado":
            usuario.status = "Ativo" if usuario.ativo else "Inativo"

        session.commit()

        _cache_invalidate("lista:", f"info:{id_corretor}:")
        return {"ok": "Dados de RH atualizados com sucesso", "usuario": _usuario_to_dict(usuario)}

    except Exception:
        session.rollback()
        return {"error": "Erro ao atualizar dados de RH"}

    finally:
        session.close()
