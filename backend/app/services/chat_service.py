import os
import json
import anthropic
from datetime import date, timedelta
from sqlalchemy import text

from app.database import SessionLocal
from app.models.imovel import Imovel
from app.services.analise_service import consultar_estudo_metricas

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


TOOLS = [
    {
        "name": "buscar_imoveis",
        "description": (
            "Busca imóveis disponíveis no banco de dados com base nas preferências do cliente. "
            "Use quando o cliente quiser ver imóveis, pedir sugestões ou perguntar o que está disponível. "
            "Retorna até 5 imóveis com link direto para o anúncio original."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "oferta": {
                    "type": "string",
                    "enum": ["Venda", "Aluguel", "Temporada"],
                    "description": "Venda, Aluguel ou Temporada"
                },
                "tipo": {
                    "type": "string",
                    "description": "Tipo do imóvel: Apartamento, Casa, etc."
                },
                "bairro": {
                    "type": "string",
                    "description": "Bairro desejado"
                },
                "quartos": {
                    "type": "integer",
                    "description": "Número de quartos"
                },
                "preco_max": {
                    "type": "number",
                    "description": "Preço máximo em reais"
                },
                "preco_min": {
                    "type": "number",
                    "description": "Preço mínimo em reais"
                }
            },
            "required": ["oferta"]
        }
    },
    {
        "name": "precificar_imovel",
        "description": (
            "Avalia o preço de mercado de um imóvel com base nos dados processados da base. "
            "Use quando o cliente quiser saber quanto vale seu imóvel, pedir avaliação de preço, "
            "ou perguntar sobre valores de mercado numa região."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "description": "Tipo do imóvel: Apartamento, Casa, etc."
                },
                "bairro": {
                    "type": "string",
                    "description": "Bairro do imóvel"
                },
                "oferta": {
                    "type": "string",
                    "enum": ["Venda", "Aluguel"],
                    "description": "Venda ou Aluguel"
                },
                "quartos": {
                    "type": "integer",
                    "description": "Número de quartos"
                },
                "metragem": {
                    "type": "number",
                    "description": "Área útil em m²"
                }
            },
            "required": ["tipo", "bairro", "oferta"]
        }
    },
    {
        "name": "dicas_anuncio",
        "description": (
            "Fornece dicas baseadas em dados reais de como anunciar um imóvel para maximizar resultados. "
            "Use quando o cliente quiser saber como anunciar, quais fotos tirar, o que destacar, "
            "ou pedir orientações para colocar o imóvel no mercado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tipo": {
                    "type": "string",
                    "description": "Tipo do imóvel: Apartamento, Casa, etc."
                },
                "oferta": {
                    "type": "string",
                    "enum": ["Venda", "Aluguel"],
                    "description": "Venda ou Aluguel"
                },
                "bairro": {
                    "type": "string",
                    "description": "Bairro do imóvel (opcional)"
                }
            },
            "required": ["tipo", "oferta"]
        }
    }
]

SYSTEM_PROMPT = """Você é a Renata, assistente virtual da 61 Imóveis — imobiliária especializada em Brasília/DF.

Você ajuda clientes a:
• Encontrar imóveis disponíveis (venda ou aluguel) de acordo com suas preferências
• Avaliar o valor de mercado de um imóvel com base em dados reais
• Receber dicas de como anunciar um imóvel para vender ou alugar mais rápido

Seja sempre cordial, objetiva e profissional. Use linguagem acessível.

Ao mostrar imóveis:
- Liste de forma clara com tipo, bairro (e quadra quando disponível), quartos, área e preço
- Sempre inclua o link do anúncio original (campo "link") — é o link direto no portal
- Formate preços como R$ 450.000 ou R$ 2.500/mês
- Se o campo "portal" for "df", o link é do DFImóveis

Ao precificar:
- Explique o valor/m² e o valor estimado total
- Mencione o tamanho da amostra como indicador de confiança

Ao dar dicas de anúncio:
- Seja específico para o tipo e bairro informados
- Baseie as dicas nos dados reais do mercado local

Se não tiver informações suficientes para usar uma ferramenta, pergunte ao cliente antes."""


def _buscar_imoveis(oferta, tipo=None, bairro=None, quartos=None, preco_max=None, preco_min=None):
    session = SessionLocal()
    try:
        hoje = date.today()
        um_ano_atras = hoje - timedelta(days=365)

        # "Interessados" no portal dfimoveis agrupa Venda e Aluguel sem distinção;
        # buscamos tanto pelo valor exato quanto por "Interessados" para cobrir todos os casos.
        ofertas_busca = [oferta, "Interessados"]

        q = session.query(Imovel).filter(
            Imovel.oferta.in_(ofertas_busca),
            Imovel.data_coleta >= um_ano_atras,
            Imovel.link.isnot(None),
        )
        if tipo:
            q = q.filter(Imovel.tipo.ilike(f"%{tipo}%"))
        if bairro:
            q = q.filter(Imovel.bairro.ilike(f"%{bairro}%"))
        if quartos:
            q = q.filter(Imovel.quartos == quartos)
        if preco_max:
            q = q.filter(Imovel.preco <= preco_max)
        if preco_min:
            q = q.filter(Imovel.preco >= preco_min)

        imoveis = q.order_by(Imovel.data_coleta.desc()).limit(5).all()

        if not imoveis:
            return {
                "encontrados": 0,
                "imoveis": [],
                "mensagem": "Nenhum imóvel encontrado com esses critérios. Tente ampliar os filtros."
            }

        resultado = []
        for i in imoveis:
            resultado.append({
                "codigo": i.codigo,
                "tipo": i.tipo,
                "bairro": i.bairro,
                "quadra": i.quadra,
                "cidade": i.cidade,
                "quartos": int(i.quartos) if i.quartos else None,
                "vagas": int(i.vagas) if i.vagas else None,
                "area_util": float(i.area_util) if i.area_util else None,
                "preco": float(i.preco) if i.preco else None,
                "anunciante": i.anunciante,
                "portal": i.portal,
                "link": i.link,
            })

        return {"encontrados": len(resultado), "imoveis": resultado}
    finally:
        session.close()


def _precificar_imovel(tipo, bairro, oferta, quartos=None, metragem=None):
    resultado = consultar_estudo_metricas(
        tipo_imovel=tipo,
        bairro=bairro,
        quartos=quartos,
        nr_cluster=None,
        oferta=oferta,
        vagas=None,
        metragem=metragem
    )
    if not resultado:
        return {
            "encontrado": False,
            "mensagem": f"Não encontrei dados suficientes para {tipo} em {bairro}. Tente um bairro mais amplo ou sem filtro de quartos."
        }
    return {"encontrado": True, "dados": resultado}


def _dicas_anuncio(tipo, oferta, bairro=None):
    session = SessionLocal()
    try:
        hoje = date.today()
        um_ano_atras = hoje - timedelta(days=365)

        # Inclui "Interessados" pois o portal dfimoveis usa esse valor para anúncios ativos
        q = session.query(Imovel).filter(
            Imovel.tipo.ilike(f"%{tipo}%"),
            Imovel.oferta.in_([oferta, "Interessados"]),
            Imovel.data_coleta >= um_ano_atras
        )
        if bairro:
            q = q.filter(Imovel.bairro.ilike(f"%{bairro}%"))

        imoveis = q.limit(200).all()

        if not imoveis:
            return {"mensagem": "Não encontrei dados suficientes para gerar dicas nesse segmento."}

        precos = [float(i.preco) for i in imoveis if i.preco and i.preco > 0]
        areas = [float(i.area_util) for i in imoveis if i.area_util and i.area_util > 0]
        quartos_list = [int(i.quartos) for i in imoveis if i.quartos]
        vagas_list = [int(i.vagas) for i in imoveis if i.vagas]

        stats = {"tipo": tipo, "oferta": oferta, "bairro": bairro, "amostra": len(imoveis)}

        if precos:
            stats["preco_medio"] = round(sum(precos) / len(precos))
            stats["preco_minimo"] = round(min(precos))
            stats["preco_maximo"] = round(max(precos))

        if areas:
            stats["area_media"] = round(sum(areas) / len(areas), 1)
            stats["area_minima"] = round(min(areas), 1)
            stats["area_maxima"] = round(max(areas), 1)

        if quartos_list:
            quartos_freq = {}
            for q_num in quartos_list:
                quartos_freq[q_num] = quartos_freq.get(q_num, 0) + 1
            stats["quartos_mais_anunciado"] = max(quartos_freq, key=quartos_freq.get)
            stats["distribuicao_quartos"] = {
                f"{k} quartos": f"{round(v/len(quartos_list)*100)}%"
                for k, v in sorted(quartos_freq.items())
            }

        if vagas_list:
            com_vaga = sum(1 for v in vagas_list if v > 0)
            stats["percentual_com_vaga"] = f"{round(com_vaga/len(vagas_list)*100)}%"

        return stats
    finally:
        session.close()


def _process_tool(name, inputs):
    if name == "buscar_imoveis":
        return _buscar_imoveis(**inputs)
    if name == "precificar_imovel":
        return _precificar_imovel(**inputs)
    if name == "dicas_anuncio":
        return _dicas_anuncio(**inputs)
    return {"erro": "Ferramenta desconhecida"}


# In-memory session store: session_id -> list of messages
_sessions: dict = {}
_MAX_HISTORY = 20


def chat(session_id: str, user_message: str) -> str:
    client = _get_client()
    history = _sessions.setdefault(session_id, [])
    history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=history,
    )

    # Agentic loop: processa tool_use até obter stop_reason == "end_turn"
    while response.stop_reason == "tool_use":
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        history.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            result = _process_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result, ensure_ascii=False, default=str)
            })

        history.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

    final_text = "".join(b.text for b in response.content if hasattr(b, "text"))
    history.append({"role": "assistant", "content": final_text})

    # Limita histórico para controlar custo
    if len(history) > _MAX_HISTORY:
        _sessions[session_id] = history[-_MAX_HISTORY:]

    return final_text
