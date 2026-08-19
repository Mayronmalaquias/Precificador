import { moedaInput, moedaNumero, moedaDeNumero, soDigitos, MAX_DIGITOS_MOEDA } from './moeda';

// Teto da coluna Numeric(14,2) no back.
const TETO_COLUNA = 999999999999.99;

describe('máscara de moeda — convenção', () => {
  test('os dígitos digitados são centavos', () => {
    expect(moedaInput('1')).toBe('0,01');
    expect(moedaInput('12')).toBe('0,12');
    expect(moedaInput('123')).toBe('1,23');
    expect(moedaInput('123456')).toBe('1.234,56');
  });

  test('entrada vazia ou sem dígito não vira zero', () => {
    expect(moedaInput('')).toBe('');
    expect(moedaInput('abc')).toBe('');
    expect(moedaInput(null)).toBe('');
    expect(moedaNumero('')).toBe('');
  });

  test('reaproveita um valor já formatado', () => {
    expect(moedaNumero('R$ 1.234,56')).toBe('1234.56');
  });
});

describe('máscara de moeda — precisão (A-3)', () => {
  // A implementação antiga fazia Number(digitos)/100 e, acima de 2^53, devolvia
  // 123456789012345.69 para esta entrada: dois centavos que ninguém digitou.
  test('nunca inventa centavos', () => {
    for (let n = 1; n <= MAX_DIGITOS_MOEDA; n += 1) {
      const digitos = '1234567890123456789'.slice(0, n);
      const enviado = moedaNumero(digitos);
      const semSeparador = enviado.replace('.', '').replace(/^0+/, '') || '0';
      expect(semSeparador).toBe(digitos.replace(/^0+/, '') || '0');
    }
  });

  test('nenhum valor aceito estoura a coluna do banco', () => {
    for (let n = 1; n <= MAX_DIGITOS_MOEDA; n += 1) {
      expect(Number(moedaNumero('9'.repeat(n)))).toBeLessThanOrEqual(TETO_COLUNA);
    }
  });

  test('trunca no teto em vez de estourar', () => {
    expect(soDigitos('9'.repeat(40))).toHaveLength(MAX_DIGITOS_MOEDA);
    expect(moedaNumero('9'.repeat(40))).toBe('999999999999.99');
  });
});

describe('máscara de moeda — volta da API', () => {
  test('preenche o form na edição sem perder centavos', () => {
    expect(moedaDeNumero(590000)).toBe('590.000,00');
    expect(moedaDeNumero(6555555.55)).toBe('6.555.555,55');
    expect(moedaDeNumero(0.01)).toBe('0,01');
    expect(moedaDeNumero(null)).toBe('');
  });

  test('ida e volta preserva o valor', () => {
    for (const bruto of ['1', '12345', '99999999999999']) {
      expect(moedaNumero(moedaDeNumero(Number(moedaNumero(bruto))))).toBe(moedaNumero(bruto));
    }
  });
});
