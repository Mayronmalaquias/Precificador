/**
 * Máscara de moeda compartilhada (Propostas Efetivas e Lançar Imóvel).
 *
 * Convenção da casa: os dígitos digitados são CENTAVOS — "1" vira 0,01 e "123" vira 1,23.
 *
 * A conversão é feita por string, nunca por float. A versão anterior fazia
 * `Number(digitos) / 100`, e acima de 2^53 isso perde precisão e INVENTA centavos:
 * "12345678901234567" virava 123456789012345.69 e gravava um valor que ninguém digitou.
 *
 * O teto de 14 dígitos (12 inteiros + 2 centavos) é o da coluna `Numeric(14,2)`.
 * Sem ele, um valor longo estourava a coluna e virava erro 500 no lançamento.
 */

export const MAX_DIGITOS_MOEDA = 14;

export const soDigitos = (v) =>
  String(v ?? '').replace(/\D/g, '').slice(0, MAX_DIGITOS_MOEDA);

/** Separa os dígitos em parte inteira e centavos, sem passar por Number. */
function partes(valor) {
  const d = soDigitos(valor);
  if (!d) return null;
  const cheio = d.padStart(3, '0');
  return {
    inteiros: cheio.slice(0, -2).replace(/^0+(?=\d)/, ''),
    centavos: cheio.slice(-2),
  };
}

/** O que aparece no input: "1.234,56". */
export function moedaInput(valor) {
  const p = partes(valor);
  if (!p) return '';
  return `${p.inteiros.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${p.centavos}`;
}

/** O que vai para a API: "1234.56" (string, para o back decidir a precisão). */
export function moedaNumero(valor) {
  const p = partes(valor);
  return p ? `${p.inteiros}.${p.centavos}` : '';
}

/** Centavos a partir de um número já vindo da API (para preencher o form na edição). */
export const moedaDeNumero = (n) =>
  n || n === 0 ? moedaInput(String(Math.round(Number(n) * 100))) : '';
