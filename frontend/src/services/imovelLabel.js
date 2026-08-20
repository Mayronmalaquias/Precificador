/**
 * Descrição legível de um imóvel vindo da busca do Imoview.
 *
 * O motivo de existir: em Águas Claras (e em qualquer bairro de torres) o logradouro não
 * identifica nada. Um imóvel real da base:
 *
 *     endereco    "Rua das Paineiras"
 *     numero      "S/N"
 *     bloco       ""
 *     complemento "Lote 2 - Apartamento 2503"
 *     edificio    "Residencial Palácio do Sol"
 *     bairro      "Norte (Águas Claras)"
 *
 * Só com endereço e número saía "Rua das Paineiras, S/N" — o corretor não conseguia
 * dizer qual imóvel era. O nome do edifício é o que distingue, então vem primeiro.
 *
 * O `edificio` é enviado pelo Imoview em toda busca; onde não houver prédio ele volta
 * vazio e some da linha, então isso vale para a base inteira, não só Águas Claras.
 */

const texto = (v) => String(v ?? "").trim();

// O Imoview usa "S/N" e "n/a" como preenchimento quando o prédio não tem número na rua.
// Mostrar isso só ocupa espaço — a mesma regra já existia no Lançar Imóvel.
const NUMERO_VAZIO = /^(s\/?n|n\/?a|0)$/i;
const numeroUtil = (v) => (texto(v) && !NUMERO_VAZIO.test(texto(v)) ? texto(v) : "");

/** Nome do prédio, quando houver. */
export const edificioDe = (item) => texto(item?.edificio);

/**
 * Linha única para listas e seletores.
 * Ex.: "Residencial Palácio do Sol · Rua das Paineiras · Lote 2 - Apartamento 2503 · Norte (Águas Claras)"
 */
export function descricaoImovel(item, { comBairro = true, separador = " · " } = {}) {
  const rua = [texto(item?.endereco), numeroUtil(item?.numero)].filter(Boolean).join(", ");
  return [
    edificioDe(item),
    rua,
    texto(item?.bloco) ? `Bloco ${texto(item.bloco)}` : "",
    texto(item?.complemento),
    comBairro ? texto(item?.bairro) : "",
  ].filter(Boolean).join(separador);
}

/**
 * Endereço completo para gravar/exibir por extenso (inclui cidade/UF).
 * Mantém a vírgula como separador, que é o formato que as telas de visita já usavam.
 */
export function enderecoCompleto(item) {
  const cidade = texto(item?.cidade)
    ? `${texto(item.cidade)}${texto(item?.uf) ? `/${texto(item.uf)}` : ""}`
    : "";
  return [
    edificioDe(item),
    texto(item?.endereco),
    numeroUtil(item?.numero),
    texto(item?.bloco) ? `Bloco ${texto(item.bloco)}` : "",
    texto(item?.complemento),
    texto(item?.bairro),
    cidade,
  ].filter(Boolean).join(", ");
}

export default descricaoImovel;
