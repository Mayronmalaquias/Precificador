"""Regra de acesso ao relatorio do imovel pelo corretor.

**So imovel captado por ele.** O relatorio e material de apresentacao; distribuir o de
imovel alheio nao e decisao do corretor.

Fonte da verdade: a **API do Imoview**, filtrando por `codigocaptador` = `usuarios.id_imoview`
(o codigo do corretor no CRM). E o proprio CRM dizendo quem captou o que.

Duas fontes foram descartadas no caminho:

- `visitas.tipo_captacao` — rotulo digitado por visita, nao registro de captacao. Medido em
  13/08/2026: das 274 visitas marcadas "Captacao Propria" com captacao correspondente, so
  **146 (53%)** tinham o corretor como captador; e **768 visitas** eram de imovel realmente
  captado por ele *sem* estar marcadas assim.
- `fato_captacao` — base interna alimentada por lancamento e planilha: fica atras do CRM e
  grava `codigo_imovel` formatado ("10.258") em parte das linhas.

O PDF em si e o MESMO que o gerente baixa (`/imoveis/pdf/download`): um relatorio por imovel
com visitas, clientes e avaliacoes. Aqui mora so a permissao.
"""
from typing import Any, Dict, List

import requests

from app.database import SessionLocal
from app.extensions import cache
from app.models.usuarios import Usuarios

# Teto de paginas da varredura por captador (20 por pagina = 2.000 imoveis). O maior
# captador da base tem 378.
MAX_PAGINAS_CAPTADOR = 100


class ImovelPdfErro(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _codigo_limpo(valor: Any) -> str:
    """"10.258" -> "10258". Parte das bases grava o codigo formatado como numero."""
    texto = _texto(valor)
    if not texto:
        return ""
    return "".join(ch for ch in texto.split(",")[0] if ch.isdigit())


def _codigo_imoview_do_corretor(id_corretor: str) -> str:
    """`usuarios.id_imoview` — o codigo do corretor no CRM (120 usuarios tem)."""
    session = SessionLocal()
    try:
        user = session.query(Usuarios).filter(
            Usuarios.id_usuarios == _texto(id_corretor)
        ).first()
        return _texto(user.id_imoview) if user else ""
    finally:
        session.close()


@cache.memoize(timeout=1800)
def _captados_no_imoview(codigo_captador: str) -> List[str]:
    """Codigos que o captador tem no CRM, direto da API. Cache de 30 min.

    `codigocaptador` e o unico parametro que a API respeita para isso — testados sem efeito
    nenhum (devolvem o catalogo inteiro, 11.430): `codigosusuarios`, `codigousuario`,
    `captadores`, `usuariocaptador`, `codigoscaptadores`. Filtrar pelo retorno tambem nao
    serve: o campo `captadores` do payload volta vazio.
    """
    from app.services.imoview_service import IMOVIEW_BASE, _headers

    codigos, pagina = [], 1
    while pagina <= MAX_PAGINAS_CAPTADOR:
        resposta = requests.post(
            f"{IMOVIEW_BASE}/Imovel/RetornarImoveis",
            headers=_headers(),
            json={
                "numeropagina": pagina, "numeroregistros": 20,
                "naoconsiderarmeusite": True, "codigocaptador": codigo_captador,
            },
            timeout=45,
        )
        if resposta.status_code >= 400:
            raise ImovelPdfErro(
                f"Imoview HTTP {resposta.status_code} ao consultar as captações", 502
            )
        lista = (resposta.json() or {}).get("lista") or []
        if not lista:
            break
        codigos.extend(_codigo_limpo(item.get("codigo")) for item in lista)
        if len(lista) < 20:
            break
        pagina += 1
    return sorted({c for c in codigos if c})


def listar_codigos_captados(id_corretor: str) -> List[str]:
    """Codigos captados pelo corretor. A tela usa para o selo e para exibir o botao."""
    codigo_captador = _codigo_imoview_do_corretor(id_corretor)
    if not codigo_captador:
        # Sem codigo no CRM nao da p/ perguntar ao Imoview. Lista vazia (nenhum botao) e
        # melhor que liberar tudo.
        return []
    try:
        return _captados_no_imoview(codigo_captador)
    except ImovelPdfErro:
        raise
    except Exception:
        return []


def checar_direito(codigo: str, id_corretor: str) -> Dict[str, Any]:
    codigo = _texto(codigo)
    id_corretor = _texto(id_corretor)
    if not codigo or not id_corretor:
        raise ImovelPdfErro("Informe o código do imóvel e o corretor")

    codigo_captador = _codigo_imoview_do_corretor(id_corretor)
    if not codigo_captador:
        raise ImovelPdfErro("Seu usuário não tem código do Imoview cadastrado", 403)

    alvo = _codigo_limpo(codigo) or codigo
    if alvo not in set(_captados_no_imoview(codigo_captador)):
        raise ImovelPdfErro("O relatório do imóvel só sai para imóvel captado por você", 403)
    return {"codigo": alvo}
