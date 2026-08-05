"""Cria os usuários assistentes (permissao=assistente, senha 61Imoveis).

Idempotente: pula quem já existe (por username). Username = nome_sobrenome (sem acento,
minúsculo, espaço→underscore) — MESMO formato que `normalizar_user` produz do nome digitado
no login (ex.: "Lucas Oliveira" → "lucas_oliveira"). Nome simples → primeiro nome.
id_usuarios gerado no padrão C61xxx.

Rodar (raiz do backend): PYTHONPATH=. python seed_assistentes.py
"""
import unicodedata

from werkzeug.security import generate_password_hash

from app.database import SessionLocal
from app.models.usuarios import Usuarios
from app.services.auth_service import _gerar_proximo_id_usuario

SENHA = "61Imoveis"
ASSISTENTES = [
    "Douglas", "João Matheus", "Lucas Oliveira", "Mayron", "Victor Hugo",
    "Rodrigo", "Rafael", "Ana Clara", "Victória", "Natanael", "Thiago Vital",
    "Keyce", "Isadora", "Valentina", "Marcela Vianna",
]


def _slug(nome: str) -> str:
    # Mesmo formato do normalizar_user (login): sem acento, minúsculo, espaço→underscore.
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower().strip()
    partes = s.split()
    if len(partes) >= 2:
        return f"{partes[0]}_{partes[1]}"
    return partes[0] if partes else ""


def main() -> None:
    session = SessionLocal()
    criados, pulados = [], []
    try:
        for nome in ASSISTENTES:
            username = _slug(nome)
            if not username:
                continue
            existe = session.query(Usuarios.id).filter(Usuarios.username == username).first()
            if existe:
                pulados.append(username)
                continue
            u = Usuarios(
                username=username,
                password=generate_password_hash(SENHA),
                nome=nome,
                permissao="assistente",
                ativo=True,
                status="Ativo",
                id_usuarios=_gerar_proximo_id_usuario(session),
            )
            session.add(u)
            session.flush()  # garante o próximo id distinto na iteração seguinte
            criados.append(f"{username} ({u.id_usuarios})")
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Criados ({len(criados)}):", ", ".join(criados) or "—")
    print(f"Já existiam ({len(pulados)}):", ", ".join(pulados) or "—")


if __name__ == "__main__":
    main()
