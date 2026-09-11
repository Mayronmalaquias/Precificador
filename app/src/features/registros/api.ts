import { ApiError, api } from '@/services/api';

export type AvaliacaoItem = {
  id_avaliacao?: string;
  cliente?: string;
  localizacao?: string;
  tamanho?: string;
  planta?: string;
  acabamento?: string;
  conservacao?: string;
  condominio?: string;
  preco?: string;
  notaGeral?: string;
};

export type VisitaClienteItem = {
  id_cliente?: string;
  nome?: string;
  telefone?: string;
  email?: string;
  papel?: string;
};

export type VisitaItem = {
  id_visita: string;
  cliente?: string;
  clientes?: VisitaClienteItem[];
  dataVisita?: string;
  imovelId?: string;
  enderecoExterno?: string;
  proposta?: string;
  tipoCaptacao?: string;
  imovelNaoCaptado?: string;
  anexoFichaVisita?: string;
  linkImagem?: string;
  createdAt?: string;
  avaliacoes?: AvaliacaoItem[];
  parceiros?: { nome?: string; imobiliaria?: string }[];
  label?: string;
};

export type ClienteItem = {
  id_cliente?: string | number;
  nome?: string;
  telefone?: string;
  email?: string;
};

export type ImovelItem = {
  id_imovel?: string;
  qtd_visitas?: number;
  ultima_data?: string;
  clientes?: string[];
  endereco_externo?: string;
  label?: string;
};

type ListaResp<T> = { ok?: boolean; lista?: T[] };

function qs(idCorretor: string) {
  return `id_corretor=${encodeURIComponent(idCorretor)}&q=&limit=100000`;
}

export async function listarVisitas(idCorretor: string): Promise<VisitaItem[]> {
  const d = await api.get<ListaResp<VisitaItem>>(`/visitas_busca?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}

export async function listarClientes(idCorretor: string): Promise<ClienteItem[]> {
  const d = await api.get<ListaResp<ClienteItem>>(`/clientes_busca?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}

// App: imoveis NO NOME do corretor (estoque atual), nao os visitados.
// Endpoint proprio do app; o site segue usando /imoveis_busca_corretor (visitados).
export async function listarImoveis(idCorretor: string): Promise<ImovelItem[]> {
  const d = await api.get<ListaResp<ImovelItem>>(`/imoveis_estoque_corretor?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}

// ── Detalhe da visita (rota nova do back) ────────────────────────────────
// Formato diferente do item de `/visitas_busca`: vem da gestão de visitas e
// traz a resposta do cliente e a pendência de revisão do gerente.

export type VisitaDetalhe = {
  id_visita: string;
  data_visita?: string | null;
  imovel?: string;
  id_imovel?: string;
  id_cliente?: string;
  cliente?: string;
  corretor?: string;
  equipe?: string;
  proposta?: string;
  tem_nota?: boolean;
  tem_anexo?: boolean;
  endereco_externo?: string;
  motivo_sim?: string;
  motivo_talvez?: string;
  link_imagem?: string;
  link_audio?: string;
  anexo_ficha_visita?: string;
  situacao_imovel?: string;
  motivo_ok?: boolean;
  /** 'anexo' | 'notas' | 'motivo' — o que o gerente ainda não revisou. */
  pendencias?: string[];
  revisao_pendente?: boolean;
  visto_em?: string | null;
};

/**
 * GET /visitas/{id}. O escopo sai do cadastro do solicitante — 404 quando a
 * visita existe mas está fora dele.
 *
 * `solicitante_id` vai explícito de propósito: o back prefere o `sub` do JWT,
 * mas o token expira em 12h e a chamada continua passando pela X-API-KEY. Sem o
 * parâmetro, a rota ficaria sem saber quem perguntou depois que o JWT vencesse.
 *
 * Devolve `null` em vez de estourar: é enriquecimento de uma tela que já
 * renderiza sem ele.
 */
export async function obterVisita(
  idVisita: string,
  solicitanteId: string,
): Promise<VisitaDetalhe | null> {
  if (!idVisita || !solicitanteId) return null;
  try {
    const d = await api.get<{ ok?: boolean; visita?: VisitaDetalhe }>(
      `/visitas/${encodeURIComponent(idVisita)}?solicitante_id=${encodeURIComponent(solicitanteId)}`,
    );
    return d?.visita ?? null;
  } catch (err) {
    if (err instanceof ApiError) return null; // fora do escopo / não encontrada
    throw err;
  }
}

// ── Cliente: abrir e editar (rotas novas do back) ────────────────────────

export type ClienteDetalhe = {
  id_cliente: string;
  nome: string;
  telefone: string;
  email: string;
  id_corretor?: string;
};

export async function obterCliente(
  idCliente: string,
  solicitanteId: string,
): Promise<ClienteDetalhe | null> {
  if (!idCliente || !solicitanteId) return null;
  const d = await api.get<{ ok?: boolean; cliente?: ClienteDetalhe }>(
    `/clientes/${encodeURIComponent(idCliente)}?solicitante_id=${encodeURIComponent(solicitanteId)}`,
  );
  return d?.cliente ?? null;
}

/**
 * PUT /clientes/{id}. Manda só o que mudou: chave ausente mantém o valor atual,
 * chave com string vazia apaga. Nome vazio o back recusa.
 */
export async function editarCliente(
  idCliente: string,
  solicitanteId: string,
  campos: Partial<Pick<ClienteDetalhe, 'nome' | 'telefone' | 'email'>>,
): Promise<ClienteDetalhe> {
  const d = await api.put<{ ok?: boolean; cliente?: ClienteDetalhe; error?: string }>(
    `/clientes/${encodeURIComponent(idCliente)}?solicitante_id=${encodeURIComponent(solicitanteId)}`,
    campos,
  );
  if (!d?.ok || !d.cliente) throw new Error(d?.error || 'Erro ao salvar cliente');
  return d.cliente;
}
