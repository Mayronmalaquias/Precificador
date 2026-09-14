import { api, postForm } from '@/services/api';
import { File } from 'expo-file-system';
import { Platform } from 'react-native';

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
  // O fetch do Expo 57 exige Blob/bytes; o descritor { uri, name, type }
  // do fetch antigo falha antes de enviar a requisição.
  let arquivo: Blob;
  if (Platform.OS === 'web') {
    const response = await fetch(params.file.uri);
    if (!response.ok) throw new Error('Não foi possível ler a ficha. Selecione o anexo novamente.');
    arquivo = await response.blob();
  } else {
    const file = new File(params.file.uri);
    arquivo = file;
  }
  fd.append('file', arquivo, params.file.name);
  fd.append('idCorretor', params.idCorretor);
  fd.append('imovelId', params.imovelId);
  fd.append('dataVisita', params.dataVisita);

  // `postForm` injeta X-API-KEY/Bearer. Com `fetch` cru a chamada saía sem
  // credencial e a API respondia 401 desde que deixou de ser pública.
  const d = await postForm<{ ok?: boolean; drivePath?: string; driveLink?: string; error?: string }>(
    '/upload_pdf',
    fd,
  );
  if (!d?.ok) throw new Error(d?.error || 'Erro ao enviar arquivo');
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
