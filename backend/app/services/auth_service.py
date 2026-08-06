from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from app import SessionLocal
from app.models.usuarios import Usuarios
from app.services.usuarios_service import DATE_FIELDS, BOOL_FIELDS, _parse_bool, _parse_date, _usuario_to_dict


def _gerar_proximo_id_usuario(session):
    maior_numero = 61000
    ids = session.query(Usuarios.id_usuarios).filter(Usuarios.id_usuarios.isnot(None)).all()

    for (id_usuario,) in ids:
        valor = str(id_usuario or "").strip().upper()
        if not valor.startswith("C61"):
            continue
        sufixo = valor[1:]
        if sufixo.isdigit():
            maior_numero = max(maior_numero, int(sufixo))

    return f"C{maior_numero + 1}"


def cadastrar_usuario(username, password, team,
                      nome=None, email=None, telefone=None,
                      instagram=None, descricao=None,
                      id_usuarios=None, permissao=None, dados_extras=None):

    session = SessionLocal()
    try:
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        id_usuarios = (id_usuarios or "").strip() or _gerar_proximo_id_usuario(session)

        campos_extras = {}
        for campo, valor in (dados_extras or {}).items():
            if campo in DATE_FIELDS:
                valor = _parse_date(valor)
            elif campo in BOOL_FIELDS:
                valor = _parse_bool(valor)
            campos_extras[campo] = valor

        # Espelha o alterar_ativo(True) do RH, pra nao nascer com status vazio.
        if not campos_extras.get("status"):
            campos_extras["status"] = "Ativo"
        if campos_extras.get("desligado") is None:
            campos_extras["desligado"] = False

        # Codigo Imoview: unico, senao o Lancar Imovel atribui o imovel ao corretor errado.
        cod_imoview = str(campos_extras.get("id_imoview") or "").strip()
        campos_extras["id_imoview"] = cod_imoview or None
        if cod_imoview:
            em_uso = session.query(Usuarios.nome).filter(
                Usuarios.id_imoview == cod_imoview
            ).first()
            if em_uso:
                raise ValueError(
                    f"Código Imoview {cod_imoview} já está em uso por {em_uso[0] or 'outro usuário'}."
                )

        usuario = Usuarios(
            username=username,
            password=hashed_pw,
            team=team,
            # Nasce liberado: o cadastro so e feito por quem ja esta logado
            # (administrador/assistente), entao nao passa mais pela fila do RH.
            ativo=True,
            nome=nome,
            email=email,
            telefone=telefone,
            instagram=instagram,
            descricao=descricao,
            id_usuarios=id_usuarios,
            permissao=permissao,
            **campos_extras,
        )

        session.add(usuario)
        session.commit()
        session.refresh(usuario)

        # Ao registrar um gerente, garante a equipe dele. Equipe = `team` (corretores
        # compartilham o team do gerente); se team vazio, cai no id do gerente. So cria se
        # faltar — nunca renomeia uma equipe ja cadastrada.
        if str(permissao or "").lower() == "gerente":
            try:
                id_equipe_gerente = str(team or "").strip() or id_usuarios
                from app.models.equipe import Equipe
                ja_existe = session.query(Equipe.id_equipe).filter_by(id_equipe=id_equipe_gerente).first()
                if id_equipe_gerente and not ja_existe:
                    from app.services.equipes_service import criar_equipe
                    criar_equipe(id_equipe=id_equipe_gerente, nome=nome or username)
            except Exception:
                # não bloqueia o cadastro do gerente se a criação da equipe falhar
                pass

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
            if usuario.ativo is False:
                return {"inactive": True}
            user_data = _usuario_to_dict(usuario)
            return user_data

        return None

    finally:
        session.close()


def registrar_nova_senha(username, newpass):
    session = SessionLocal()
    try:
        usuario = session.query(Usuarios).filter_by(username=username).first()
        if not usuario:
            return {"error": "Usuario invalido!"}
        
        usuario.password = generate_password_hash(newpass, method="pbkdf2:sha256")
        session.commit()
        return {"ok": "Senha alterada!"}

    except Exception:
        session.rollback()
        return {"error": "Ocorreu um erro ao acessar o banco de dados"}
    finally:
        session.close()
