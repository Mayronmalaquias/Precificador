import { api } from '@/services/api';

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
  return `id_corretor=${encodeURIComponent(idCorretor)}&q=&limit=200`;
}

export async function listarVisitas(idCorretor: string): Promise<VisitaItem[]> {
  const d = await api.get<ListaResp<VisitaItem>>(`/visitas_busca?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}

export async function listarClientes(idCorretor: string): Promise<ClienteItem[]> {
  const d = await api.get<ListaResp<ClienteItem>>(`/clientes_busca?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}

export async function listarImoveis(idCorretor: string): Promise<ImovelItem[]> {
  const d = await api.get<ListaResp<ImovelItem>>(`/imoveis_busca_corretor?${qs(idCorretor)}`);
  return Array.isArray(d?.lista) ? d.lista : [];
}
