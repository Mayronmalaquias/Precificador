import React, { useCallback, useEffect, useState } from "react";
import { BASE as API_BASE, api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import "../assets/css/AdminBases.css";

// useToast() devolve a funcao addToast(msg, tipo); este wrapper expoe success/error
function useNotify() {
  const toast = useToast();
  return {
    success: (m) => toast(m, "success"),
    error: (m) => toast(m, "error"),
  };
}

// upload multipart: NAO setar Content-Type (o browser monta o boundary)
async function apiUpload(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || data.message || "Erro no processamento");
  }
  return data;
}

const ABAS = [
  { id: "importar", label: "Importar" },
  { id: "consultar", label: "Consultar" },
  { id: "cadastros", label: "Tipos / Bairros" },
  { id: "venda", label: "Venda" },
  { id: "destaque", label: "Destaque" },
];

function AdminBases() {
  const [aba, setAba] = useState("importar");

  return (
    <div className="ds-page">
      <div className="ds-container-lg ab-wrap">
        <header className="ab-header">
          <h1>Gestão de Bases</h1>
          <p>Captação, saída, estoque, venda e destaque — importação de arquivo ou lançamento manual.</p>
        </header>

        <nav className="ab-tabs">
          {ABAS.map((t) => (
            <button
              key={t.id}
              className={`ab-tab ${aba === t.id ? "active" : ""}`}
              onClick={() => setAba(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="ab-content">
          {aba === "importar" && <AbaImportar />}
          {aba === "consultar" && <AbaConsultar />}
          {aba === "cadastros" && <AbaCadastros />}
          {aba === "venda" && <AbaVenda />}
          {aba === "destaque" && <AbaDestaque />}
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   IMPORTAR
   ============================================================ */
function AbaImportar() {
  return (
    <div className="ab-grid-cards">
      <ImportCard
        titulo="Captação"
        descricao="Export do Imoview (CSV/XLSX). Cria/atualiza imóvel, foco PP/AC e cria bairro novo."
        endpoint="/admin/bases/importar/captacao"
        extras={[{ name: "finalidade", label: "Finalidade", default: "Venda" }]}
        ManualForm={ManualCaptacao}
      />
      <ImportCard
        titulo="Saída"
        descricao="Tudo que não estiver Vago/Disponível vira saída. Captadores herdados da última captação."
        endpoint="/admin/bases/importar/saida"
        extras={[{ name: "finalidade", label: "Finalidade", default: "Venda" }]}
        ManualForm={ManualSaida}
      />
      <ImportCard
        titulo="Estoque"
        descricao="Snapshot atual (XLS do Imoview/XLSX/CSV). Data padrão = hoje."
        endpoint="/admin/bases/importar/estoque"
        extras={[{ name: "data_estoque", label: "Data do estoque", type: "date" }]}
        ManualForm={ManualEstoque}
      />
    </div>
  );
}

function ImportCard({ titulo, descricao, endpoint, extras = [], ManualForm }) {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const [arquivo, setArquivo] = useState(null);
  const [extraVals, setExtraVals] = useState(
    () => Object.fromEntries(extras.map((e) => [e.name, e.default || ""]))
  );
  const [loading, setLoading] = useState(false);
  const [resumo, setResumo] = useState(null);
  const [manual, setManual] = useState(false);

  const processar = async () => {
    if (!arquivo) {
      toast.error("Selecione um arquivo");
      return;
    }
    setLoading(true);
    setResumo(null);
    try {
      const fd = new FormData();
      fd.append("arquivo", arquivo);
      fd.append("criado_por", idCorretor || "");
      extras.forEach((e) => extraVals[e.name] && fd.append(e.name, extraVals[e.name]));
      const data = await apiUpload(endpoint, fd);
      setResumo(data);
      toast.success(`${data.inseridos} inserido(s)`);
    } catch (e) {
      toast.error(e.message);
      setResumo({ erro: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ds-card ab-import-card">
      <h3>{titulo}</h3>
      <p className="ab-muted">{descricao}</p>

      <input
        type="file"
        accept=".csv,.xls,.xlsx"
        className="ab-file"
        onChange={(e) => setArquivo(e.target.files?.[0] || null)}
      />

      {extras.map((e) => (
        <div className="ds-form-group" key={e.name}>
          <label className="ds-label">{e.label}</label>
          <input
            type={e.type || "text"}
            className="ds-input"
            value={extraVals[e.name]}
            onChange={(ev) => setExtraVals((p) => ({ ...p, [e.name]: ev.target.value }))}
          />
        </div>
      ))}

      <button className="ds-btn ds-btn-primary ds-btn-full" onClick={processar} disabled={loading}>
        {loading ? "Processando..." : "Processar arquivo"}
      </button>

      {resumo && !resumo.erro && (
        <div className="ab-resumo">
          <span className="ab-chip ok">Inseridos: {resumo.inseridos}</span>
          <span className="ab-chip warn">Duplicados: {resumo.ignorados_duplicados}</span>
          {"bairros_criados" in resumo && (
            <span className="ab-chip info">Bairros criados: {resumo.bairros_criados}</span>
          )}
          {resumo.erros?.length > 0 && (
            <details className="ab-erros">
              <summary>{resumo.erros.length} erro(s)</summary>
              <ul>{resumo.erros.slice(0, 20).map((er, i) => <li key={i}>{er}</li>)}</ul>
            </details>
          )}
        </div>
      )}
      {resumo?.erro && <div className="ds-alert ds-alert-error">{resumo.erro}</div>}

      <button className="ab-link" onClick={() => setManual((m) => !m)}>
        {manual ? "▾ Ocultar lançamento manual" : "▸ Lançamento manual avulso"}
      </button>
      {manual && <ManualForm />}
    </div>
  );
}

function useManualSubmit(endpoint) {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const [loading, setLoading] = useState(false);
  const enviar = async (payload, reset) => {
    setLoading(true);
    try {
      await api.post(endpoint, { ...payload, criado_por: idCorretor || "" });
      toast.success("Registro salvo");
      reset?.();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };
  return { enviar, loading };
}

function ManualCaptacao() {
  const { enviar, loading } = useManualSubmit("/admin/bases/captacao");
  const vazio = { codigo: "", captadores: "", bairro: "", valor: "", tipo: "", comissao: "", data_entrada: "", finalidade: "Venda" };
  const [f, setF] = useState(vazio);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  return (
    <div className="ab-manual">
      <div className="ds-form-row">
        <Campo label="Código*" value={f.codigo} onChange={set("codigo")} />
        <Campo label="Captadores (nome | nome)" value={f.captadores} onChange={set("captadores")} />
        <Campo label="Bairro" value={f.bairro} onChange={set("bairro")} />
        <Campo label="Valor" value={f.valor} onChange={set("valor")} />
        <Campo label="Tipo" value={f.tipo} onChange={set("tipo")} />
        <Campo label="Comissão %" value={f.comissao} onChange={set("comissao")} />
        <Campo label="Data entrada" type="date" value={f.data_entrada} onChange={set("data_entrada")} />
        <Campo label="Finalidade" value={f.finalidade} onChange={set("finalidade")} />
      </div>
      <button className="ds-btn ds-btn-primary ds-btn-sm" disabled={loading || !f.codigo}
        onClick={() => enviar(f, () => setF(vazio))}>Salvar captação</button>
    </div>
  );
}

function ManualSaida() {
  const { enviar, loading } = useManualSubmit("/admin/bases/saida");
  const vazio = { codigo: "", data_saida: "", motivo: "", captadores: "" };
  const [f, setF] = useState(vazio);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  return (
    <div className="ab-manual">
      <div className="ds-form-row">
        <Campo label="Código*" value={f.codigo} onChange={set("codigo")} />
        <Campo label="Data saída" type="date" value={f.data_saida} onChange={set("data_saida")} />
        <Campo label="Motivo" value={f.motivo} onChange={set("motivo")} />
        <Campo label="Captadores (nome | nome)" value={f.captadores} onChange={set("captadores")} />
      </div>
      <button className="ds-btn ds-btn-primary ds-btn-sm" disabled={loading || !f.codigo}
        onClick={() => enviar(f, () => setF(vazio))}>Salvar saída</button>
    </div>
  );
}

function ManualEstoque() {
  const { enviar, loading } = useManualSubmit("/admin/bases/estoque");
  const vazio = { codigo: "", captadores: "", data_estoque: "", publicacao_na_internet: "", exclusivo: "" };
  const [f, setF] = useState(vazio);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  return (
    <div className="ab-manual">
      <div className="ds-form-row">
        <Campo label="Código*" value={f.codigo} onChange={set("codigo")} />
        <Campo label="Captadores (nome | nome)" value={f.captadores} onChange={set("captadores")} />
        <Campo label="Data estoque" type="date" value={f.data_estoque} onChange={set("data_estoque")} />
        <Campo label="Publicado na internet" value={f.publicacao_na_internet} onChange={set("publicacao_na_internet")} />
        <Campo label="Exclusivo" value={f.exclusivo} onChange={set("exclusivo")} />
      </div>
      <button className="ds-btn ds-btn-primary ds-btn-sm" disabled={loading || !f.codigo}
        onClick={() => enviar(f, () => setF(vazio))}>Salvar estoque</button>
    </div>
  );
}

/* ============================================================
   CONSULTAR
   ============================================================ */
const CONSULTAS = {
  captacoes: {
    endpoint: "/admin/bases/captacao",
    cols: [
      ["codigo_imovel", "Código"], ["data_entrada", "Entrada"], ["bairro_nome", "Bairro"],
      ["tipo_nome", "Tipo"], ["valor", "Valor"], ["captador1", "Captador"],
      ["id_gerente", "Gerente"], ["foco_pp", "PP"], ["foco_ac", "AC"], ["origem", "Origem"],
    ],
    bairro: true,
  },
  saidas: {
    endpoint: "/admin/bases/saida",
    cols: [
      ["codigo_imovel", "Código"], ["data_saida", "Saída"], ["motivo", "Motivo"],
      ["captador1", "Captador"], ["id_gerente", "Gerente"], ["origem", "Origem"],
    ],
  },
  estoque: {
    endpoint: "/admin/bases/estoque",
    cols: [
      ["codigo_imovel", "Código"], ["data_estoque", "Data"], ["captador1", "Captador"],
      ["id_gerente", "Gerente"], ["publicacao_na_internet", "Publicado"], ["exclusivo", "Exclusivo"], ["origem", "Origem"],
    ],
  },
};

function AbaConsultar() {
  const [sub, setSub] = useState("captacoes");
  return (
    <div>
      <nav className="ab-subtabs">
        {Object.keys(CONSULTAS).map((k) => (
          <button key={k} className={`ab-subtab ${sub === k ? "active" : ""}`} onClick={() => setSub(k)}>
            {k}
          </button>
        ))}
      </nav>
      <ConsultaTabela key={sub} config={CONSULTAS[sub]} />
    </div>
  );
}

function ConsultaTabela({ config }) {
  const toast = useNotify();
  const [filtros, setFiltros] = useState({ codigo: "", captador: "", bairro: "", data_de: "", data_ate: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, per_page: 50 });
  const [loading, setLoading] = useState(false);

  const buscar = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page: p, per_page: 50 });
      Object.entries(filtros).forEach(([k, v]) => v && qs.append(k, v));
      const res = await api.get(`${config.endpoint}?${qs.toString()}`);
      setData(res);
      setPage(p);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [config.endpoint, filtros, page, toast]);

  useEffect(() => {
    buscar(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.endpoint]);

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / (data.per_page || 50)));
  const fmt = (v) => (v === true ? "Sim" : v === false ? "" : v ?? "");

  return (
    <div className="ds-card">
      <div className="ab-filtros">
        <input className="ds-input" placeholder="Código" value={filtros.codigo}
          onChange={(e) => setFiltros((p) => ({ ...p, codigo: e.target.value }))} />
        <input className="ds-input" placeholder="Captador" value={filtros.captador}
          onChange={(e) => setFiltros((p) => ({ ...p, captador: e.target.value }))} />
        {config.bairro && (
          <input className="ds-input" placeholder="Bairro" value={filtros.bairro}
            onChange={(e) => setFiltros((p) => ({ ...p, bairro: e.target.value }))} />
        )}
        <input className="ds-input" type="date" value={filtros.data_de}
          onChange={(e) => setFiltros((p) => ({ ...p, data_de: e.target.value }))} />
        <input className="ds-input" type="date" value={filtros.data_ate}
          onChange={(e) => setFiltros((p) => ({ ...p, data_ate: e.target.value }))} />
        <button className="ds-btn ds-btn-primary ds-btn-sm" onClick={() => buscar(1)} disabled={loading}>Filtrar</button>
      </div>

      <div className="ab-table-wrap">
        <table className="ab-table">
          <thead><tr>{config.cols.map(([k, l]) => <th key={k}>{l}</th>)}</tr></thead>
          <tbody>
            {data.items.length === 0 && (
              <tr><td colSpan={config.cols.length} className="ab-empty">{loading ? "Carregando..." : "Nenhum registro"}</td></tr>
            )}
            {data.items.map((row, i) => (
              <tr key={row.id || i}>{config.cols.map(([k]) => <td key={k}>{fmt(row[k])}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="ab-pag">
        <span>{data.total} registro(s)</span>
        <div>
          <button className="ds-btn ds-btn-secondary ds-btn-sm" disabled={page <= 1 || loading} onClick={() => buscar(page - 1)}>Anterior</button>
          <span className="ab-pag-num">{page} / {totalPages}</span>
          <button className="ds-btn ds-btn-secondary ds-btn-sm" disabled={page >= totalPages || loading} onClick={() => buscar(page + 1)}>Próxima</button>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   CADASTROS (Tipo / Bairro)
   ============================================================ */
function AbaCadastros() {
  return (
    <div className="ab-grid-2">
      <DimCrud titulo="Tipos de imóvel" endpoint="/admin/bases/tipos" campoId="id_tipo" />
      <DimCrud titulo="Bairros" endpoint="/admin/bases/bairros" campoId="id_bairro" />
    </div>
  );
}

function DimCrud({ titulo, endpoint, campoId }) {
  const toast = useNotify();
  const [items, setItems] = useState([]);
  const [novo, setNovo] = useState("");
  const [loading, setLoading] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const res = await api.get(endpoint);
      setItems(res.items || []);
    } catch (e) {
      toast.error(e.message);
    }
  }, [endpoint, toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const adicionar = async () => {
    if (!novo.trim()) return;
    setLoading(true);
    try {
      await api.post(endpoint, { nome: novo.trim() });
      setNovo("");
      toast.success("Adicionado");
      carregar();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const editar = async (it) => {
    const nome = window.prompt("Novo nome:", it.nome);
    if (nome == null) return;
    try {
      await api.put(`${endpoint}/${it.id}`, { nome });
      carregar();
    } catch (e) { toast.error(e.message); }
  };

  const excluir = async (it) => {
    if (!window.confirm(`Excluir "${it.nome}"?`)) return;
    try {
      await api.delete(`${endpoint}/${it.id}`);
      carregar();
    } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="ds-card">
      <h3>{titulo}</h3>
      <div className="ab-add">
        <input className="ds-input" placeholder="Nome" value={novo} onChange={(e) => setNovo(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && adicionar()} />
        <button className="ds-btn ds-btn-primary ds-btn-sm" onClick={adicionar} disabled={loading}>Adicionar</button>
      </div>
      <div className="ab-table-wrap ab-dim-list">
        <table className="ab-table">
          <thead><tr><th>ID</th><th>Nome</th><th></th></tr></thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td>{it[campoId]}</td>
                <td>{it.nome}</td>
                <td className="ab-acoes">
                  <button className="ab-link" onClick={() => editar(it)}>editar</button>
                  <button className="ab-link danger" onClick={() => excluir(it)}>excluir</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={3} className="ab-empty">Nenhum registro</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================================
   VENDA (contrato + divisão de comissão com validação)
   Regras (base = Valor Total 61 / VT61), de Form_Venda.html:
   - Gerência soma = 10% do VT61
   - Venda/comprador soma = 22% (44% se parceria) do VT61
   - Captação ∈ {20%, 22%, 24%} do VT61 (sem captação se parceria)
   - Empresa 61 (VT61 − atribuído) ∈ {42, 44, 46, 48%}
   ============================================================ */
const TOL = 0.05;
const numBR = (v) => {
  const n = parseFloat(String(v ?? "").replace(/\s/g, "").replace(",", "."));
  return isNaN(n) ? 0 : n;
};
const fBRL = (v) =>
  `R$ ${(v || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pctStr = (r) => `${(r * 100).toFixed(2).replace(".", ",")}%`;
const allowedPct = (val, vt, pcts) => pcts.some((p) => Math.abs(val - vt * p) <= TOL);

function LinhaComissao({ label, nomeKey, valorKey, ok, vt, f, set }) {
  const v = numBR(f[valorKey]);
  const r = vt > 0 ? v / vt : 0;
  const bw = Math.min(Math.max((r * 100 * 100) / 50, 0), 100);
  const ativo = !!f[nomeKey] || v > 0;
  return (
    <div className="ab-comrow">
      <input className="ds-input" placeholder={label} value={f[nomeKey]} onChange={set(nomeKey)} />
      <input className="ds-input" type="number" step="0.01" placeholder="R$ valor"
        value={f[valorKey]} onChange={set(valorKey)} />
      <div className="ab-bar"><div className={`ab-bar-fill ${ok ? "ok" : "warn"}`} style={{ width: bw + "%" }} /></div>
      <span className={`ab-comnum ${ok ? "ok" : "warn"}`}>{pctStr(r)}</span>
      {ativo && <span className={`ab-badge ${ok ? "ok" : "warn"}`}>{ok ? "OK" : "!"}</span>}
    </div>
  );
}

function SyncContratosPanel() {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);
  const sync = async () => {
    setLoading(true); setRes(null);
    try {
      const r = await api.post("/admin/bases/sync-contratos", { criado_por: idCorretor || "" });
      setRes(r);
      toast.success(`Sync: ${r.inseridos} novos, ${r.atualizados} atualizados`);
    } catch (e) { toast.error(e.message); setRes({ erro: e.message }); }
    finally { setLoading(false); }
  };
  return (
    <div className="ds-card ab-import-card">
      <h3>Sincronizar contratos com a planilha</h3>
      <p className="ab-muted">
        Puxa a aba <strong>Vendas</strong> do Google Sheets para a tabela <strong>contratos</strong>
        (upsert por Id_Contrato). A planilha é a fonte da verdade.
      </p>
      <button className="ds-btn ds-btn-primary" onClick={sync} disabled={loading}>
        {loading ? "Sincronizando..." : "Sincronizar agora"}
      </button>
      {res && !res.erro && (
        <div className="ab-resumo">
          <span className="ab-chip ok">Novos: {res.inseridos}</span>
          <span className="ab-chip info">Atualizados: {res.atualizados}</span>
          {res.qtd_removidos_na_planilha > 0 && (
            <span className="ab-chip warn">Sumiram da planilha: {res.qtd_removidos_na_planilha}</span>
          )}
        </div>
      )}
      {res?.erro && <div className="ds-alert ds-alert-error">{res.erro}</div>}
    </div>
  );
}

function AbaVenda() {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const vazio = {
    id_contrato: "", contrato: "", data_contrato: "", codigo_imovel: "", bairro: "", tipo: "",
    origem_lead: "", data_assinatura: "", parceria: false,
    valor_negocio: "", valor_comissao: "", valor_total_61: "",
    gerente_venda_nome: "", valor_gerente_venda: "",
    gerente_captacao_nome: "", valor_gerente_captacao: "",
    diretor_nome: "", valor_diretor: "",
    corretor_venda_1_nome: "", valor_corretor_venda_1: "",
    corretor_venda_2_nome: "", valor_corretor_venda_2: "",
    corretor_captador_1_nome: "", valor_corretor_captador_1: "",
    corretor_captador_2_nome: "", valor_corretor_captador_2: "",
  };
  const [f, setF] = useState(vazio);
  const [loading, setLoading] = useState(false);
  const [dup, setDup] = useState(null);
  const set = (k) => (e) =>
    setF((p) => ({ ...p, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  // ── cálculo / validação ──
  const vt = numBR(f.valor_total_61);
  const vc = numBR(f.valor_comissao);
  const parceria = f.parceria;
  const gv = numBR(f.valor_gerente_venda), gc = numBR(f.valor_gerente_captacao), dir = numBR(f.valor_diretor);
  const cv1 = numBR(f.valor_corretor_venda_1), cv2 = numBR(f.valor_corretor_venda_2);
  const cc1 = numBR(f.valor_corretor_captador_1), cc2 = numBR(f.valor_corretor_captador_2);
  const numG = (f.gerente_venda_nome ? 1 : 0) + (f.gerente_captacao_nome ? 1 : 0);
  const numCV = (f.corretor_venda_1_nome ? 1 : 0) + (f.corretor_venda_2_nome ? 1 : 0);
  const numCC = (f.corretor_captador_1_nome ? 1 : 0) + (f.corretor_captador_2_nome ? 1 : 0);
  const pctV = parceria ? 0.44 : 0.22;
  const somaGer = gv + gc, somaCV = cv1 + cv2, somaCC = cc1 + cc2;
  const totalAtr = somaGer + somaCV + somaCC + dir;
  const empresa = vt - totalAtr, pctEmp = vt > 0 ? empresa / vt : 0;
  const gerOk = numG > 0 && Math.abs(somaGer - vt * 0.1) <= TOL;
  const vendaOk = numCV > 0 && Math.abs(somaCV - vt * pctV) <= TOL;
  const captOk = parceria ? (Math.abs(somaCC) <= TOL && numCC === 0) : (numCC > 0 && allowedPct(somaCC, vt, [0.2, 0.22, 0.24]));
  const empOk = vt > 0 && allowedPct(empresa, vt, [0.42, 0.44, 0.46, 0.48]);

  const errors = [];
  if (vt <= 0) errors.push("Preencha o Valor Total 61 (base da divisão).");
  if (vc > 0 && vt > vc + TOL) errors.push("VT61 não pode ser maior que a comissão total.");
  if (vt > 0 && (numG === 0 || !gerOk)) errors.push("Gerência deve somar 10% = " + fBRL(vt * 0.1));
  if (vt > 0 && (numCV === 0 || !vendaOk)) errors.push(`Venda deve somar ${pctV * 100}% = ` + fBRL(vt * pctV));
  if (vt > 0 && parceria && (numCC > 0 || Math.abs(somaCC) > TOL)) errors.push("Parceria: não lançar captador interno.");
  if (vt > 0 && !parceria && !captOk) errors.push("Captação deve ser 20%, 22% ou 24% do VT61.");
  if (vt > 0 && (!empOk || empresa < -TOL)) errors.push("Empresa 61 deve ser 42, 44, 46 ou 48%. Atual: " + pctStr(pctEmp));

  const valido = f.id_contrato && vt > 0 && errors.length === 0;

  const checarDup = async () => {
    const cod = (f.codigo_imovel || "").trim();
    if (!cod) { setDup(null); return; }
    try {
      const res = await api.get(`/admin/bases/venda?codigo=${encodeURIComponent(cod)}&per_page=1`);
      setDup(res.total > 0 ? `Já existe ${res.total} contrato(s) com o código ${cod}.` : null);
    } catch { /* silencioso */ }
  };

  const salvar = async () => {
    if (!valido) { toast.error("Corrija as validações antes de salvar"); return; }
    setLoading(true);
    try {
      const pct = (v) => (vt > 0 ? +((v / vt) * 100).toFixed(4) : null);
      await api.post("/admin/bases/venda", {
        ...f, criado_por: idCorretor || "",
        percentual_gerente_venda: pct(gv), percentual_gerente_captacao: pct(gc), percentual_diretor: pct(dir),
        percentual_corretor_venda_1: pct(cv1), percentual_corretor_venda_2: pct(cv2),
        percentual_corretor_captacao_1: pct(cc1), percentual_corretor_captacao_2: pct(cc2),
      });
      toast.success("Venda registrada");
      setF(vazio); setDup(null);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="ab-stack">
      <SyncContratosPanel />
      <div className="ds-card">
        <h3>Dados do contrato</h3>
        <div className="ds-form-row">
          <Campo label="ID Contrato*" value={f.id_contrato} onChange={set("id_contrato")} />
          <Campo label="Contrato" value={f.contrato} onChange={set("contrato")} />
          <Campo label="Data contrato" type="date" value={f.data_contrato} onChange={set("data_contrato")} />
          <div className="ds-form-group">
            <label className="ds-label">Código imóvel</label>
            <input className="ds-input" value={f.codigo_imovel} onChange={set("codigo_imovel")} onBlur={checarDup} />
          </div>
          <Campo label="Bairro" value={f.bairro} onChange={set("bairro")} />
          <Campo label="Tipo" value={f.tipo} onChange={set("tipo")} />
          <Campo label="Valor do negócio" type="number" value={f.valor_negocio} onChange={set("valor_negocio")} />
          <Campo label="Origem do lead" value={f.origem_lead} onChange={set("origem_lead")} />
          <Campo label="Data assinatura" type="date" value={f.data_assinatura} onChange={set("data_assinatura")} />
        </div>
        {dup && <div className="ds-alert ds-alert-warning">{dup}</div>}
      </div>

      <div className="ds-card">
        <h3>Divisão de comissão</h3>
        <div className="ds-form-row">
          <Campo label="Comissão total (informativo)" type="number" value={f.valor_comissao} onChange={set("valor_comissao")} />
          <Campo label="Valor Total 61 (base)*" type="number" value={f.valor_total_61} onChange={set("valor_total_61")} />
        </div>
        <label className="ab-check">
          <input type="checkbox" checked={f.parceria} onChange={set("parceria")} /> Parceria (venda 44%, sem captação interna)
        </label>

        <div className="ab-comgroup">
          <div className="ab-comhead"><span>Gerência</span><span>soma = 10% do VT61</span></div>
          <LinhaComissao label="Gerente venda" nomeKey="gerente_venda_nome" valorKey="valor_gerente_venda" ok={gerOk} vt={vt} f={f} set={set} />
          <LinhaComissao label="Gerente captação" nomeKey="gerente_captacao_nome" valorKey="valor_gerente_captacao" ok={gerOk} vt={vt} f={f} set={set} />
        </div>

        <div className="ab-comgroup">
          <div className="ab-comhead"><span>Corretores de venda</span><span>soma = {pctV * 100}% do VT61</span></div>
          <LinhaComissao label="Corretor venda 1" nomeKey="corretor_venda_1_nome" valorKey="valor_corretor_venda_1" ok={vendaOk} vt={vt} f={f} set={set} />
          <LinhaComissao label="Corretor venda 2" nomeKey="corretor_venda_2_nome" valorKey="valor_corretor_venda_2" ok={vendaOk} vt={vt} f={f} set={set} />
        </div>

        <div className="ab-comgroup">
          <div className="ab-comhead"><span>Corretores de captação</span><span>soma = 20/22/24% do VT61</span></div>
          <LinhaComissao label="Corretor captação 1" nomeKey="corretor_captador_1_nome" valorKey="valor_corretor_captador_1" ok={captOk} vt={vt} f={f} set={set} />
          <LinhaComissao label="Corretor captação 2" nomeKey="corretor_captador_2_nome" valorKey="valor_corretor_captador_2" ok={captOk} vt={vt} f={f} set={set} />
        </div>

        <div className="ab-comgroup">
          <div className="ab-comhead"><span>Diretor (opcional)</span><span>fecha empresa</span></div>
          <LinhaComissao label="Diretor" nomeKey="diretor_nome" valorKey="valor_diretor" ok={empOk} vt={vt} f={f} set={set} />
        </div>

        <div className={`ab-empresa ${empOk && empresa >= -TOL ? "ok" : "warn"}`}>
          <span>Empresa 61 <small>(42/44/46/48%)</small></span>
          <strong>{pctStr(pctEmp)} · {fBRL(empresa)}</strong>
        </div>

        <div className={`ds-alert ${errors.length === 0 && vt > 0 ? "ds-alert-success" : "ds-alert-error"}`}>
          {errors.length === 0 && vt > 0
            ? "✓ Todos os percentuais conferem com as regras da empresa."
            : <span>Verificar: {errors.join(" · ")}</span>}
        </div>

        <button className="ds-btn ds-btn-primary" onClick={salvar} disabled={loading || !valido}>
          {loading ? "Salvando..." : "Registrar venda"}
        </button>
      </div>
    </div>
  );
}

/* ============================================================
   DESTAQUE
   ============================================================ */
function DestaqueImport() {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const [files, setFiles] = useState({ imoveis: null, seguros: null, assinados: null });
  const [loading, setLoading] = useState(false);
  const [resumo, setResumo] = useState(null);
  const setFile = (k) => (e) => setFiles((p) => ({ ...p, [k]: e.target.files?.[0] || null }));

  const processar = async () => {
    if (!files.imoveis || !files.seguros || !files.assinados) {
      toast.error("Envie os 3 arquivos (imóveis, seguros e assinados)");
      return;
    }
    setLoading(true);
    setResumo(null);
    try {
      const fd = new FormData();
      fd.append("imoveis", files.imoveis);
      fd.append("seguros", files.seguros);
      fd.append("assinados", files.assinados);
      fd.append("criado_por", idCorretor || "");
      const data = await apiUpload("/admin/bases/importar/destaque", fd);
      setResumo(data);
      toast.success(`${data.inseridos} destaque(s) inserido(s)`);
    } catch (e) {
      toast.error(e.message);
      setResumo({ erro: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ds-card ab-import-card">
      <h3>Importar destaques (3 arquivos)</h3>
      <p className="ab-muted">
        Substitui <strong>todos</strong> os destaques atuais (full replace), igual ao processo antigo.
        Envie os 3 XLSX do Imoview.
      </p>
      <div className="ab-3files">
        <label className="ab-filelabel">Imóveis
          <input type="file" accept=".csv,.xls,.xlsx" className="ab-file" onChange={setFile("imoveis")} />
        </label>
        <label className="ab-filelabel">Seguros
          <input type="file" accept=".csv,.xls,.xlsx" className="ab-file" onChange={setFile("seguros")} />
        </label>
        <label className="ab-filelabel">Assinados
          <input type="file" accept=".csv,.xls,.xlsx" className="ab-file" onChange={setFile("assinados")} />
        </label>
      </div>
      <button className="ds-btn ds-btn-primary ds-btn-full" onClick={processar} disabled={loading}>
        {loading ? "Processando..." : "Processar destaques"}
      </button>
      {resumo && !resumo.erro && (
        <div className="ab-resumo">
          <span className="ab-chip ok">Inseridos: {resumo.inseridos}</span>
          {"removidos" in resumo && <span className="ab-chip warn">Substituídos: {resumo.removidos}</span>}
          {resumo.erros?.length > 0 && (
            <details className="ab-erros">
              <summary>{resumo.erros.length} erro(s)</summary>
              <ul>{resumo.erros.slice(0, 20).map((er, i) => <li key={i}>{er}</li>)}</ul>
            </details>
          )}
        </div>
      )}
      {resumo?.erro && <div className="ds-alert ds-alert-error">{resumo.erro}</div>}
    </div>
  );
}

function AbaDestaque() {
  const { idCorretor } = useAuth();
  const toast = useNotify();
  const vazio = {
    codigo: "", captadores: "", endereco: "", bairro: "", valor: "",
    data_destaque: "", publicacao_web: "", categoria_df: "", categoria_wi: "", categoria_df_seguro: "",
  };
  const [f, setF] = useState(vazio);
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));

  const salvar = async () => {
    if (!f.codigo) { toast.error("Código obrigatório"); return; }
    setLoading(true);
    try {
      await api.post("/admin/bases/destaque", { ...f, criado_por: idCorretor || "" });
      toast.success("Destaque registrado");
      setF(vazio);
    } catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  };

  return (
   <div className="ab-stack">
    <DestaqueImport />
    <div className="ds-card">
      <h3>Registrar destaque avulso</h3>
      <p className="ab-muted">Lançamento manual de 1 imóvel (não substitui os demais).</p>
      <div className="ds-form-row">
        <Campo label="Código*" value={f.codigo} onChange={set("codigo")} />
        <Campo label="Captadores (nome | nome)" value={f.captadores} onChange={set("captadores")} />
        <Campo label="Endereço" value={f.endereco} onChange={set("endereco")} />
        <Campo label="Bairro" value={f.bairro} onChange={set("bairro")} />
        <Campo label="Valor" value={f.valor} onChange={set("valor")} />
        <Campo label="Data destaque" type="date" value={f.data_destaque} onChange={set("data_destaque")} />
        <Campo label="Publicação web" value={f.publicacao_web} onChange={set("publicacao_web")} />
        <Campo label="Categoria DF" value={f.categoria_df} onChange={set("categoria_df")} />
        <Campo label="Categoria WI" value={f.categoria_wi} onChange={set("categoria_wi")} />
        <Campo label="Categoria DF Seguro" value={f.categoria_df_seguro} onChange={set("categoria_df_seguro")} />
      </div>
      <button className="ds-btn ds-btn-primary" onClick={salvar} disabled={loading || !f.codigo}>
        {loading ? "Salvando..." : "Registrar destaque"}
      </button>
    </div>
   </div>
  );
}

/* ============================================================
   Campo reutilizável
   ============================================================ */
function Campo({ label, value, onChange, type = "text" }) {
  return (
    <div className="ds-form-group">
      <label className="ds-label">{label}</label>
      <input className="ds-input" type={type} value={value} onChange={onChange} />
    </div>
  );
}

export default AdminBases;
