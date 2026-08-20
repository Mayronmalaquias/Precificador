/**
 * Ordenação alfabética para listas de dropdown.
 *
 * `localeCompare` com "pt-BR" em vez de comparar string crua: o `<` do JavaScript usa
 * ordem de code point, e aí "Ângela" cai depois de "Zuleica" e "Órion" depois de "Xavier".
 * Com o locale, acento entra no lugar certo.
 *
 * `numeric: true` faz "Bloco 2" vir antes de "Bloco 10" (a comparação crua ordena por
 * caractere e coloca o 10 primeiro).
 *
 * Só use em lista de NOMES (corretor, equipe, bairro, tipo). Lista com ordem própria —
 * situação da proposta, etapa do funil, faixa de valor, ano — perde sentido em ordem
 * alfabética e deve ficar como está.
 */
const comparador = (a, b) =>
  String(a ?? "").localeCompare(String(b ?? ""), "pt-BR", { numeric: true, sensitivity: "base" });

/** Ordena por um campo (padrão `label`), sem alterar o array original. */
export function porRotulo(lista, campo = "label") {
  if (!Array.isArray(lista)) return [];
  return [...lista].sort((a, b) => comparador(a?.[campo], b?.[campo]));
}

/** Ordena uma lista de strings. */
export function porTexto(lista) {
  if (!Array.isArray(lista)) return [];
  return [...lista].sort(comparador);
}

export default porRotulo;
