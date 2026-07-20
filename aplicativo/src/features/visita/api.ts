import { api, BASE } from '@/services/api';

// ── Tipos ────────────────────────────────────────────────────────────────
export type ClienteBusca = {
  id_cliente?: string | number;
  nome?: string;
  telefone?: string;
  email?: string;
};

export type LeadBusca = {
  id?: string | number;
  cliente?: string;
  telefone?: string;
  codigo_imovel?: string;
  fonte?: string;
  contato?: string;
  data?: string;
};

export type ImovelBusca = {
  codigo?: string | number;
  titulo?: string;
  endereco?: string;
  numero?: string;
  bairro?: string;
  cidade?: string;
  uf?: string;
  finalidade?: string;
};

export type Avaliacoes = {
  localizacao: number;
  tamanho: number;
  planta: number;
  acabamento: number;
  conservacao: number;
  condominio: number;
  preco: number;
  notaGeral: number;
};

export type VisitaPayload = Record<string, unknown>;

type ListaResp<T> = { ok?: boolean; lista?: T[] };

// ── Buscas (o back-end filtra por corretor) ──────────────────────────────
export async function carregarClientes(idCorretor: string): Promise<ClienteBusca[]> {
  const d = await api.get<ListaResp<ClienteBusca>>(
    `/clientes_busca?id_corretor=${encodeURIComponent(idCorretor)}&q=&limit=500`,
  );
  return Array.isArray(d?.lista) ? d.lista : [];
}

export async function carregarLeads(idCorretor: string): Promise<LeadBusca[]> {
  const d = await api.get<ListaResp<LeadBusca>>(
    `/leads_busca?id_corretor=${encodeURIComponent(idCorretor)}&q=&limit=80`,
  );
  return Array.isArray(d?.lista) ? d.lista : [];
}

export async function buscarImoveis(endereco: string): Promise<ImovelBusca[]> {
  const q = endereco.trim();
  if (q.length < 3) return [];
  const d = await api.get<ListaResp<ImovelBusca>>(
    `/imoveis_busca?endereco=${encodeURIComponent(q)}`,
  );
  return Array.isArray(d?.lista) ? d.lista : [];
}

// ── Criar cliente ────────────────────────────────────────────────────────
export async function criarCliente(input: {
  nome: string;
  telefone: string;
  email: string;
  id_corretor: string;
  corretor_email: string;
}): Promise<string | number | null> {
  const d = await api.post<{ ok?: boolean; id_cliente?: string | number; error?: string }>(
    '/clientes',
    input,
  );
  if (!d?.ok) throw new Error(d?.error || 'Erro ao criar cliente');
  return d.id_cliente ?? null;
}

// ── Upload de anexo (multipart — não passa pelo JSON client) ─────────────
export type AnexoFile = { uri: string; name: string; type: string };

export async function uploadAnexo(params: {
  file: AnexoFile;
  idCorretor: string;
  imovelId: string;
  dataVisita: string;
}): Promise<{ drivePath: string; driveLink: string }> {
  const fd = new FormData();
  // No RN, arquivos vão como { uri, name, type }.
  fd.append('file', params.file as unknown as Blob);
  fd.append('idCorretor', params.idCorretor);
  fd.append('imovelId', params.imovelId);
  fd.append('dataVisita', params.dataVisita);

  const res = await fetch(`${BASE}/upload_pdf`, { method: 'POST', body: fd });
  const d = await res.json().catch(() => ({}));
  if (!res.ok || !d?.ok) throw new Error(d?.error || 'Erro ao enviar arquivo');
  return { drivePath: d.drivePath || '', driveLink: d.driveLink || '' };
}

// ── Criar visita ─────────────────────────────────────────────────────────
export async function criarVisita(payload: VisitaPayload): Promise<string> {
  const d = await api.post<{ ok?: boolean; id_visita?: string; error?: string }>(
    '/visitas',
    payload,
  );
  if (!d?.ok) throw new Error(d?.error || 'Erro ao registrar visita');
  return String(d.id_visita ?? '');
}
