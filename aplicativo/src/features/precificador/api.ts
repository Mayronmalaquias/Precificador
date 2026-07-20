import { api, ApiError } from '@/services/api';

/** Parâmetros do estudo de métricas (contrato de analise_routes.py). */
export type PrecificadorParams = {
  tipoImovel: string;
  bairro: string;
  quartos: number; // 0 = todos
  vagas: number; // 10 = todos
  metragem: number; // 0 = usa média da amostra
  nrCluster: number; // condição/cluster do imóvel
};

export type MetricasVenda = {
  valorM2Venda: number;
  valorVendaNominal: number;
  metragemMediaVenda: number;
  coeficienteVariacaoVenda: number; // fração (0..1)
  tamanhoAmostraVenda: number;
};

export type MetricasAluguel = {
  valorM2Aluguel: number;
  valorAluguelNominal: number;
  metragemMediaAluguel: number;
  coeficienteVariacaoAluguel: number; // fração (0..1)
  tamanhoAmostraAluguel: number;
};

function buildQuery(p: PrecificadorParams): string {
  const q = new URLSearchParams({
    tipoImovel: p.tipoImovel,
    bairro: p.bairro,
    quartos: String(p.quartos),
    vagas: String(p.vagas),
    metragem: String(p.metragem),
    nrCluster: String(p.nrCluster),
  });
  return q.toString();
}

/**
 * Busca métricas de venda e aluguel em paralelo.
 * Cada lado pode falhar de forma independente (ex.: 404 sem amostra) — devolvemos
 * `null` naquele lado em vez de derrubar a tela inteira.
 */
export async function fetchPrecificacao(params: PrecificadorParams): Promise<{
  venda: MetricasVenda | null;
  aluguel: MetricasAluguel | null;
  erroVenda: string | null;
  erroAluguel: string | null;
}> {
  const qs = buildQuery(params);

  const [vendaRes, aluguelRes] = await Promise.allSettled([
    api.get<MetricasVenda>(`/imovel/venda?${qs}`),
    api.get<MetricasAluguel>(`/imovel/aluguel?${qs}`),
  ]);

  return {
    venda: vendaRes.status === 'fulfilled' ? vendaRes.value : null,
    aluguel: aluguelRes.status === 'fulfilled' ? aluguelRes.value : null,
    erroVenda: vendaRes.status === 'rejected' ? messageFrom(vendaRes.reason) : null,
    erroAluguel: aluguelRes.status === 'rejected' ? messageFrom(aluguelRes.reason) : null,
  };
}

function messageFrom(reason: unknown): string {
  if (reason instanceof ApiError) {
    return reason.status === 404
      ? 'Sem amostra para estes filtros.'
      : reason.message;
  }
  return 'Falha ao consultar. Tente novamente.';
}
