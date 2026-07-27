import { api } from '@/services/api';

export const ETAPAS = ['escolha', 'prospeccao', 'interacao', 'apresentacao', 'captacao'] as const;
export type Etapa = (typeof ETAPAS)[number];

export const ETAPA_LABELS: Record<Etapa, string> = {
  escolha: 'Escolha',
  prospeccao: 'Prospecção',
  interacao: 'Interação',
  apresentacao: 'Apresentação',
  captacao: 'Captação',
};

export type StatusCaptacao = 'ativo' | 'exclusividade' | 'fechado';

export type Captacao = {
  id: number;
  id_corretor: string;
  nome_corretor?: string | null;
  team?: string | null;
  endereco: string;
  bairro?: string | null;
  bloco?: string | null;
  numero_imovel?: string | null;
  tem_numero?: boolean | null;
  link_anuncio?: string | null;
  etapa_atual: Etapa;
  status: StatusCaptacao;
  motivo_fechamento?: string | null;
  data_fechamento?: string | null;
  exclusividade_ate?: string | null;
  data_entrada_etapa?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  [key: string]: unknown;
};

export type HistoricoItem = {
  id: number;
  captacao_id: number;
  etapa: string;
  tipo: string;
  descricao: string;
  data_acao?: string | null;
  created_at?: string | null;
};

export function proximaEtapa(e: Etapa): Etapa | null {
  const i = ETAPAS.indexOf(e);
  return i >= 0 && i < ETAPAS.length - 1 ? ETAPAS[i + 1] : null;
}
export function etapaAnterior(e: Etapa): Etapa | null {
  const i = ETAPAS.indexOf(e);
  return i > 0 ? ETAPAS[i - 1] : null;
}

// ── Endpoints ────────────────────────────────────────────────────────────
export async function listarCaptacoes(idCorretor: string): Promise<Captacao[]> {
  const d = await api.get<{ ok?: boolean; captacoes?: Captacao[] }>(
    `/captacoes?id_corretor=${encodeURIComponent(idCorretor)}`,
  );
  return Array.isArray(d?.captacoes) ? d.captacoes : [];
}

export type NovaCaptacao = {
  id_corretor: string;
  nome_corretor?: string;
  team?: string;
  endereco: string;
  bairro?: string;
  bloco?: string;
  numero_imovel?: string;
  tem_numero?: boolean;
  link_anuncio?: string;
  etapa_atual?: Etapa;
};

export async function criarCaptacao(data: NovaCaptacao): Promise<Captacao> {
  const d = await api.post<{ ok?: boolean; captacao?: Captacao; error?: string }>('/captacoes', data);
  if (!d?.ok || !d.captacao) throw new Error(d?.error || 'Erro ao criar captação');
  return d.captacao;
}

export async function atualizarCaptacao(
  id: number,
  data: Record<string, unknown>,
): Promise<Captacao> {
  const d = await api.put<{ ok?: boolean; captacao?: Captacao; error?: string }>(
    `/captacoes/${id}`,
    data,
  );
  if (!d?.ok || !d.captacao) throw new Error(d?.error || 'Erro ao atualizar captação');
  return d.captacao;
}

export async function listarHistorico(id: number): Promise<HistoricoItem[]> {
  const d = await api.get<{ ok?: boolean; historico?: HistoricoItem[] }>(
    `/captacoes/${id}/historico`,
  );
  return Array.isArray(d?.historico) ? d.historico : [];
}

export async function fecharCaptacao(id: number, motivo: string): Promise<Captacao> {
  const d = await api.post<{ ok?: boolean; captacao?: Captacao; error?: string }>(
    `/captacoes/${id}/fechar`,
    { motivo },
  );
  if (!d?.ok || !d.captacao) throw new Error(d?.error || 'Erro ao fechar captação');
  return d.captacao;
}

export async function marcarExclusividade(id: number, dataExclusividade: string): Promise<Captacao> {
  const d = await api.post<{ ok?: boolean; captacao?: Captacao; error?: string }>(
    `/captacoes/${id}/exclusividade`,
    { data_exclusividade: dataExclusividade },
  );
  if (!d?.ok || !d.captacao) throw new Error(d?.error || 'Erro ao marcar exclusividade');
  return d.captacao;
}

export async function excluirCaptacao(id: number): Promise<void> {
  const d = await api.del<{ ok?: boolean; error?: string }>(`/captacoes/${id}/excluir`);
  if (!d?.ok) throw new Error(d?.error || 'Erro ao excluir captação');
}
