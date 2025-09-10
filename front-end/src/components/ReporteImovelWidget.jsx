// LinkReporteImovel.jsx
import React, { useMemo, useState } from "react";
import "../assets/css/ReporteImovelWidget.css"; // importe o CSS abaixo

export default function LinkReporteImovel({
  baseUrl = "https://www.inteligencia61imoveis.com.br/api/reporteImovel",
  paramName = "codigo",
  autoFocus = true,
}) {
  const [codigo, setCodigo] = useState("");

  const link = useMemo(() => {
    const c = String(codigo || "").trim();
    if (!c) return "";
    const qs = new URLSearchParams({ [paramName]: c }).toString();
    return `${baseUrl}?${qs}`;
  }, [codigo, baseUrl, paramName]);

  const onSubmit = (e) => {
    e.preventDefault();
    if (link) window.open(link, "_blank", "noopener,noreferrer");
  };

  const onCopy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      const btn = document.getElementById("lr-copy");
      if (btn) {
        const old = btn.textContent;
        btn.textContent = "Link copiado";
        setTimeout(() => (btn.textContent = old), 1200);
      }
    } catch {}
  };

  return (
    <main className="lr-page">
      <section className="lr-card" aria-labelledby="lr-title" aria-live="polite">
        <header className="lr-header">
          <h1 id="lr-title" className="lr-title">Relatório do Imóvel</h1>
          <p className="lr-subtitle">
            Baixe o relatório do seu imóvel e veja o desempenho das avaliações.
          </p>
        </header>

        <form onSubmit={onSubmit} className="lr-form" role="search" aria-label="Gerar link do relatório">
          <label htmlFor="lr-codigo" className="lr-label">Código do imóvel</label>
          <div className="lr-fields">
            <input
              id="lr-codigo"
              className="lr-input"
              placeholder="Ex.: 28"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              autoFocus={autoFocus}
              autoComplete="off"
              inputMode="numeric"
              aria-describedby="lr-help"
            />
            <div className="lr-actions">
              <button type="submit" className="lr-btn primary" disabled={!link}>
                Baixar PDF
              </button>
              <button
                type="button"
                id="lr-copy"
                className="lr-btn ghost"
                onClick={onCopy}
                disabled={!link}
              >
                Copiar link
              </button>
            </div>
          </div>
          <small id="lr-help" className="lr-help">
            gere um pdf atualizado com as avaliações do seu imovel
          </small>
        </form>

        {/* <div className="lr-link-wrap">
          <span className="lr-link-label">Link gerado</span>
          {link ? (
            <a className="lr-link" href={link} target="_blank" rel="noreferrer">
              {link}
            </a>
          ) : (
            <span className="lr-link placeholder">—</span>
          )}
        </div> */}
      </section>
    </main>
  );
}
