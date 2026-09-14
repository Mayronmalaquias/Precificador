/**
 * Leitura segura de erro capturado.
 *
 * `catch (err: any)` seguido de `err?.message` estava repetido em 12 lugares. `any`
 * desliga a checagem inteira do bloco — qualquer acesso passa a compilar, inclusive os
 * errados. Estas funcoes tratam o valor como `unknown`, que e o que ele de fato e: um
 * `throw` pode carregar qualquer coisa, nao so `Error`.
 */

/** Mensagem do erro quando houver; senao o padrao da chamada. */
export function mensagemErro(err: unknown, padrao: string): string {
  if (err instanceof Error && err.message) return err.message;
  // Nem todo runtime lanca instancias de `Error` (a API pode rejeitar com objeto cru).
  if (typeof err === 'object' && err !== null) {
    const m = (err as { message?: unknown }).message;
    if (typeof m === 'string' && m) return m;
  }
  return padrao;
}

/** Aborto por timeout do `AbortController` — checado pelo nome, sem supor a classe. */
export function ehAbort(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    (err as { name?: unknown }).name === 'AbortError'
  );
}
