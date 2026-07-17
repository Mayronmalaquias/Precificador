import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import "../assets/css/Parcerias.css";

const FILTROS = [
  { id: "todas", label: "Todas" },
  { id: "parceiras", label: "Parceiras" },
  { id: "contrato", label: "Com contrato" },
  { id: "sem", label: "Não faz" },
];

function ehNegativo(p) {
  const alvo = `${p.nome || ""} ${p.observacao || ""}`.toLowerCase();
  return alvo.includes("negativ");
}

function iniciais(nome) {
  const partes = String(nome).trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "?";
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return `${partes[0][0]}${partes[1][0]}`.toUpperCase();
}

function ParceriaCard({ p }) {
  const faz = p.faz_parceria;
  const negativo = ehNegativo(p);
  return (
    <article className={`pc-card ${faz ? "" : "is-sem"} ${negativo ? "is-neg" : ""}`}>
      <div className="pc-avatar" aria-hidden="true">{iniciais(p.nome)}</div>

      <div className="pc-body">
        <h3 className="pc-nome">{p.nome}</h3>

        <div className="pc-tags">
          {faz && p.percentual && <span className="pc-pill pc-pill-split">{p.percentual}</span>}
          {!faz && <span className="pc-pill pc-pill-sem">Não faz parceria</span>}
          {p.tem_contrato && (
            <span className="pc-pill pc-pill-contrato">
              <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                <path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" strokeWidth="2"
                  strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Contrato
            </span>
          )}
          {negativo && <span className="pc-pill pc-pill-neg">Histórico negativo</span>}
        </div>

        {p.observacao && !negativo && <p className="pc-obs">{p.observacao}</p>}
      </div>
    </article>
  );
}

function Parcerias() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState("todas");

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const res = await api.get("/parcerias");
        if (vivo) setItems(res.items || []);
      } catch (e) {
        if (vivo) setErro(e.message);
      } finally {
        if (vivo) setLoading(false);
      }
    })();
    return () => { vivo = false; };
  }, []);

  const stats = useMemo(() => ({
    total: items.length,
    parceiras: items.filter((p) => p.faz_parceria).length,
    contrato: items.filter((p) => p.tem_contrato).length,
  }), [items]);

  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return items.filter((p) => {
      if (filtro === "parceiras" && !p.faz_parceria) return false;
      if (filtro === "contrato" && !p.tem_contrato) return false;
      if (filtro === "sem" && p.faz_parceria) return false;
      if (q && !p.nome.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [items, busca, filtro]);

  return (
    <div className="pc-page">
      <div className="pc-shell">
        <header className="pc-hero">
          <span className="pc-kicker">Imobiliária 61</span>
          <h1>Parcerias</h1>
          <p>Imobiliárias e corretores parceiros da 61 e as regras de divisão de cada um.</p>

          <div className="pc-stats">
            <div className="pc-stat">
              <strong>{stats.total}</strong>
              <span>cadastradas</span>
            </div>
            <div className="pc-stat">
              <strong>{stats.parceiras}</strong>
              <span>fazem parceria</span>
            </div>
            <div className="pc-stat">
              <strong>{stats.contrato}</strong>
              <span>com contrato</span>
            </div>
          </div>
        </header>

        <div className="pc-controls">
          <div className="pc-search">
            <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
              <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M14 14l4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              inputMode="search"
              placeholder="Buscar imobiliária…"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              aria-label="Buscar parceria"
            />
            {busca && (
              <button className="pc-search-clear" onClick={() => setBusca("")} aria-label="Limpar busca">×</button>
            )}
          </div>

          <div className="pc-segment" role="tablist" aria-label="Filtrar parcerias">
            {FILTROS.map((f) => (
              <button
                key={f.id}
                role="tab"
                aria-selected={filtro === f.id}
                className={`pc-seg-btn ${filtro === f.id ? "active" : ""}`}
                onClick={() => setFiltro(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {loading && <div className="pc-info">Carregando parcerias…</div>}
        {erro && <div className="pc-info pc-info-erro">{erro}</div>}

        {!loading && !erro && (
          lista.length === 0 ? (
            <div className="pc-info">Nenhuma parceria encontrada.</div>
          ) : (
            <div className="pc-grid">
              {lista.map((p) => <ParceriaCard key={p.id} p={p} />)}
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default Parcerias;
