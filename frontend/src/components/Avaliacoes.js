import React from "react";
import "../assets/css/Avaliacoes.css";

/** Notas que o cliente deu ao imóvel na visita.
 *
 * Uma visita pode ter mais de uma avaliação — uma por cliente que assinou. Por isso é
 * lista e cada bloco é identificado pelo nome: com um formulário só, editar a nota de um
 * cliente sobrescreveria a do outro.
 *
 * As chaves são as que `editar_visita` espera no payload (`planta`, `acabamento`…), não
 * as colunas do banco (`planta_imovel`, `qualidade_acabamento`…) — a tradução acontece no
 * servidor, ao montar a resposta.
 */

export const CAMPOS_NOTA = [
  ["localizacao", "Localização"],
  ["tamanho", "Tamanho"],
  ["planta", "Planta"],
  ["acabamento", "Acabamento"],
  ["conservacao", "Conservação"],
  ["condominio", "Condomínio"],
  ["preco", "Preço"],
  ["notaGeral", "Nota geral"],
];

export default function Avaliacoes({ avaliacoes = [], onChange }) {
  if (!avaliacoes.length) {
    return (
      <p className="av-vazio">
        Esta visita não tem avaliação registrada. As notas são preenchidas na criação da
        visita — aqui dá para corrigir as que já existem.
      </p>
    );
  }

  const mudar = (indice, chave, valor) => {
    const copia = avaliacoes.map((a, i) => (i === indice ? { ...a, [chave]: valor } : a));
    onChange(copia);
  };

  return (
    <div className="av-lista">
      {avaliacoes.map((a, i) => (
        <div className="av-bloco" key={a.id_avaliacao || i}>
          <span className="av-dono">{a.cliente || "Cliente sem nome"}</span>
          <div className="av-notas">
            {CAMPOS_NOTA.map(([chave, rotulo]) => (
              <label key={chave}>
                {rotulo}
                <input
                  type="number" min="0" max="10" step="0.5"
                  value={a[chave] ?? ""}
                  onChange={(e) => mudar(i, chave, e.target.value)}
                />
              </label>
            ))}
            <label className="av-largo">
              Preço para nota 10
              <input
                type="text" inputMode="numeric" placeholder="Ex.: 2500000"
                value={a.precoNota10 ?? ""}
                onChange={(e) => mudar(i, "precoNota10", e.target.value)}
              />
            </label>
          </div>
        </div>
      ))}
    </div>
  );
}
