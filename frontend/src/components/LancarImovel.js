import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import "../assets/css/LancarImovel.css";

// Mapeia um item de lista do Imoview para {value,label} de forma tolerante ao shape.
function opt(item) {
  if (item == null) return null;
  if (typeof item === "string" || typeof item === "number") return { value: item, label: String(item) };
  const value = item.codigo ?? item.id ?? item.codigounidade ?? item.value;
  const label = item.descricao ?? item.nome ?? item.titulo ?? item.label ?? String(value);
  return value == null ? null : { value, label };
}
const asOpts = (lista) => (Array.isArray(lista) ? lista.map(opt).filter(Boolean) : []);

// Formata "880000" / "880.000,00" → "R$ 880.000,00"
function fmtValorBR(v) {
  const n = Number(String(v ?? "").replace(/\./g, "").replace(",", "."));
  return isFinite(n) && n ? n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : String(v ?? "");
}

// Texto do grupo de captação (mesmo padrão do WhatsApp).
function textoAviso(a, foco) {
  return [
    foco ? "FOCO" : "NÃO FOCO",
    a.codigo ?? "",
    String(a.endereco || "").toUpperCase(),
    fmtValorBR(a.valor),
    a.comissao ? `${a.comissao}%` : "",
    String(a.corretor || "").toUpperCase(),
  ].filter((x) => String(x).trim() !== "").join("\n");
}

const VAZIO = {
  codigousuario: "", corretor_nome: "",
  finalidade: "", destinacao: "", codigotipo: "", codigounidade: "", localchave: "",
  rua: "", numero: "", complemento: "", bloco: "", bairro: "", cidade: "Brasília", estado: "DF",
  valor: "", valorcondominio: "", valoriptu: "", comissao: "",
  areainterna: "", areaexterna: "",
  numeroquartos: "", numerosalas: "", numerobanhos: "", numerosuites: "", numerovarandas: "", numerovagas: "",
  descricao: "",
  prop_nome: "", prop_cpf: "", prop_telefone: "", prop_email: "", prop_percentual: "100",
  matricula: "", inscricao_iptu: "", exclusivo: false, cessao_direitos: false,
};

export default function LancarImovel() {
  const toast = useToast();
  const { userData } = useAuth();
  const [form, setForm] = useState(VAZIO);
  const [corretores, setCorretores] = useState([]);
  const [listas, setListas] = useState({ unidades: [], finalidades: [], destinacoes: [], tipos: [], localchaves: [] });
  const [fotos, setFotos] = useState([]);
  const [carregandoListas, setCarregandoListas] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [aviso, setAviso] = useState(null);   // snapshot p/ o texto do grupo
  const [foco, setFoco] = useState(true);
  const [copiado, setCopiado] = useState(false);

  const set = (k) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: v }));
  };

  useEffect(() => {
    fetch(`${BASE}/corretor/retornar-lista?ativo=true&per_page=1000`)
      .then((r) => r.json())
      .then((d) => setCorretores((d?.lista || []).filter((c) => (c.nome || c.username))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setCarregandoListas(true);
    fetch(`${BASE}/assistente/imoview/listas`)
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (ok && d.ok) {
          setListas({
            unidades: asOpts(d.unidades), finalidades: asOpts(d.finalidades),
            destinacoes: asOpts(d.destinacoes), tipos: asOpts(d.tipos), localchaves: asOpts(d.localchaves),
          });
        } else {
          toast(d?.error || "Erro ao carregar listas do Imoview.", "error");
        }
      })
      .catch(() => toast("Erro ao carregar listas do Imoview.", "error"))
      .finally(() => setCarregandoListas(false));
  }, [toast]);

  const copiarAviso = () => {
    if (!aviso) return;
    navigator.clipboard.writeText(textoAviso(aviso, foco))
      .then(() => { setCopiado(true); toast("Texto copiado!", "success"); })
      .catch(() => toast("Não consegui copiar — selecione e copie manual.", "error"));
  };

  const onCorretor = (e) => {
    const codigousuario = e.target.value;
    const c = corretores.find((x) => String(x.id_imoview) === String(codigousuario));
    setForm((f) => ({ ...f, codigousuario, corretor_nome: c ? (c.nome || c.username) : "" }));
  };

  const corretoresOpts = useMemo(
    () => corretores
      .filter((c) => c.id_imoview)
      .map((c) => ({ value: c.id_imoview, label: c.nome || c.username }))
      .sort((a, b) => String(a.label).localeCompare(String(b.label), "pt-BR")),
    [corretores]
  );

  const enviar = useCallback(async (e) => {
    e.preventDefault();
    if (enviando) return;
    if (!form.codigousuario) { toast("Selecione o corretor.", "error"); return; }
    if (!form.rua) { toast("Informe a rua.", "error"); return; }
    if (!form.descricao) { toast("Informe a descrição.", "error"); return; }
    if (!form.prop_nome || !form.prop_cpf || !form.prop_telefone) {
      toast("Preencha o proprietário (nome, CPF e telefone).", "error"); return;
    }

    setEnviando(true);
    setResultado(null);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (v !== "" && v != null) fd.append(k, typeof v === "boolean" ? String(v) : v);
      });
      fd.append("assistente_nome", userData?.nome || userData?.username || "");
      fotos.forEach((foto) => fd.append("fotos", foto));

      const resp = await fetch(`${BASE}/assistente/incluir-imovel`, { method: "POST", body: fd });
      const d = await resp.json().catch(() => ({}));
      if (!resp.ok || d.ok === false) throw new Error(d.error || "Erro ao lançar o imóvel.");

      setResultado(d);
      // snapshot p/ o aviso do grupo (antes de limpar o form)
      setAviso({
        codigo: d.codigo,
        endereco: [form.rua, form.numero, form.bloco, form.complemento].filter(Boolean).join(" - "),
        valor: form.valor,
        comissao: form.comissao,
        corretor: form.corretor_nome,
      });
      setFoco(true);
      setCopiado(false);
      toast(`Imóvel lançado! Código ${d.codigo ?? "—"}.`, "success");
      window.scrollTo({ top: 0, behavior: "smooth" });
      setForm(VAZIO);
      setFotos([]);
    } catch (err) {
      toast(err.message || "Erro ao lançar o imóvel.", "error");
    } finally {
      setEnviando(false);
    }
  }, [enviando, form, fotos, userData, toast]);

  return (
    <div className="li-shell">
      <header className="li-hero">
        <div className="li-hero-main">
          <span className="li-eyebrow">Captação · Assistentes</span>
          <h1 className="li-title">Lançar imóvel</h1>
          <p className="li-subtitle">
            Um único lançamento publica no <strong>Imoview</strong>, registra no <strong>estoque</strong> e
            cria o <strong>cartão no Trello</strong> — chega de digitar duas vezes.
          </p>
        </div>
        <div className="li-hero-chips" aria-hidden="true">
          <span className="li-chip"><i>🏢</i> Imoview</span>
          <span className="li-chip"><i>📊</i> Estoque</span>
          <span className="li-chip"><i>🗂️</i> Trello</span>
        </div>
      </header>

      {resultado && (
        <div className="li-success" role="status">
          <div className="li-success-badge">✓</div>
          <div className="li-success-body">
            <strong>Imóvel lançado no Imoview — código {resultado.codigo ?? "—"}.</strong>
            <div className="li-success-tags">
              {resultado.foco?.classificacao && <Tag ok label={`Foco: ${resultado.foco.classificacao}`} />}
              <Tag ok={resultado.sheet?.ok} label={resultado.sheet?.ok ? "Estoque gravado" : `Estoque: ${resultado.sheet?.error || "falhou"}`} />
              {resultado.trello?.ok
                ? <a className="li-tag li-tag--ok" href={resultado.trello.url} target="_blank" rel="noreferrer">Cartão Trello ↗</a>
                : <Tag ok={false} label={`Trello: ${resultado.trello?.error || "falhou"}`} />}
            </div>
            {resultado.sheet?.ok && resultado.sheet?.corretor_na_planilha === false && (
              <div className="li-success-nota">
                Corretor não está na aba "Corretores" da planilha — gravei como
                {" "}<strong>{resultado.sheet.corretor}</strong> (nome do cadastro). Adicione ele na aba
                com o código Imoview p/ as fórmulas baterem.
              </div>
            )}
          </div>
        </div>
      )}

      {aviso && (
        <div className="li-aviso">
          <div className="li-aviso-head">
            <span className="li-aviso-titulo">📣 Aviso pro grupo de captação</span>
            <div className="li-foco-seg">
              <button type="button" className={foco ? "is-on" : ""} onClick={() => { setFoco(true); setCopiado(false); }}>FOCO</button>
              <button type="button" className={!foco ? "is-on is-off" : ""} onClick={() => { setFoco(false); setCopiado(false); }}>NÃO FOCO</button>
            </div>
          </div>
          <pre className="li-aviso-texto">{textoAviso(aviso, foco)}</pre>
          <button type="button" className="li-copiar" onClick={copiarAviso}>
            {copiado ? "✓ Copiado" : "Copiar texto"}
          </button>
        </div>
      )}

      <form className="li-form" onSubmit={enviar}>
        <Section n={1} icon="👤" title="Identificação" desc="Corretor responsável e classificação do imóvel no Imoview.">
          <Field label="Corretor" req span={2}>
            <select value={form.codigousuario} onChange={onCorretor} required>
              <option value="">Selecione o corretor…</option>
              {corretoresOpts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
          <SelectField label="Finalidade" value={form.finalidade} onChange={set("finalidade")} opts={listas.finalidades} loading={carregandoListas} req />
          <SelectField label="Destinação" value={form.destinacao} onChange={set("destinacao")} opts={listas.destinacoes} loading={carregandoListas} req />
          <SelectField label="Tipo" value={form.codigotipo} onChange={set("codigotipo")} opts={listas.tipos} loading={carregandoListas} req />
          <SelectField label="Unidade" value={form.codigounidade} onChange={set("codigounidade")} opts={listas.unidades} loading={carregandoListas} req />
          <SelectField label="Local da chave" value={form.localchave} onChange={set("localchave")} opts={listas.localchaves} loading={carregandoListas} req />
          <Toggle label="Imóvel exclusivo" checked={form.exclusivo} onChange={set("exclusivo")} />
        </Section>

        <Section n={2} icon="📍" title="Endereço" desc="Onde o imóvel fica.">
          <TextField label="Rua" value={form.rua} onChange={set("rua")} req span={2} />
          <TextField label="Número" value={form.numero} onChange={set("numero")} />
          <TextField label="Complemento" value={form.complemento} onChange={set("complemento")} />
          <TextField label="Bloco" value={form.bloco} onChange={set("bloco")} />
          <TextField label="Bairro" value={form.bairro} onChange={set("bairro")} req />
          <TextField label="Cidade" value={form.cidade} onChange={set("cidade")} />
          <TextField label="Estado" value={form.estado} onChange={set("estado")} />
        </Section>

        <Section n={3} icon="💰" title="Valores e áreas" desc="Preço, encargos e metragem.">
          <TextField label="Valor" value={form.valor} onChange={set("valor")} req prefix="R$" />
          <TextField label="Condomínio" value={form.valorcondominio} onChange={set("valorcondominio")} prefix="R$" />
          <TextField label="IPTU (valor)" value={form.valoriptu} onChange={set("valoriptu")} prefix="R$" />
          <TextField label="Comissão" value={form.comissao} onChange={set("comissao")} suffix="%" />
          <TextField label="Área interna" value={form.areainterna} onChange={set("areainterna")} req suffix="m²" />
          <TextField label="Área externa" value={form.areaexterna} onChange={set("areaexterna")} suffix="m²" />
        </Section>

        <Section n={4} icon="🛏️" title="Características" desc="Cômodos e vagas (opcional).">
          <TextField label="Quartos" value={form.numeroquartos} onChange={set("numeroquartos")} />
          <TextField label="Suítes" value={form.numerosuites} onChange={set("numerosuites")} />
          <TextField label="Banheiros" value={form.numerobanhos} onChange={set("numerobanhos")} />
          <TextField label="Salas" value={form.numerosalas} onChange={set("numerosalas")} />
          <TextField label="Varandas" value={form.numerovarandas} onChange={set("numerovarandas")} />
          <TextField label="Vagas" value={form.numerovagas} onChange={set("numerovagas")} />
        </Section>

        <Section n={5} icon="🧾" title="Proprietário" desc="Obrigatório — o Imoview não cadastra sem." required>
          <TextField label="Nome" value={form.prop_nome} onChange={set("prop_nome")} req span={2} />
          <TextField label="CPF / CNPJ" value={form.prop_cpf} onChange={set("prop_cpf")} req />
          <TextField label="Telefone" value={form.prop_telefone} onChange={set("prop_telefone")} req />
          <TextField label="E-mail" value={form.prop_email} onChange={set("prop_email")} />
          <TextField label="% participação" value={form.prop_percentual} onChange={set("prop_percentual")} suffix="%" />
        </Section>

        <Section n={6} icon="📄" title="Documentação" desc="Dados que vão pro cartão do Trello.">
          <TextField label="Matrícula" value={form.matricula} onChange={set("matricula")} />
          <TextField label="Inscrição IPTU" value={form.inscricao_iptu} onChange={set("inscricao_iptu")} />
          <Toggle label="Cessão de direitos" checked={form.cessao_direitos} onChange={set("cessao_direitos")} />
        </Section>

        <Section n={7} icon="📝" title="Descrição e fotos" desc="Texto do anúncio e imagens do imóvel.">
          <Field label="Descrição" req span={3}>
            <textarea rows={4} value={form.descricao} onChange={set("descricao")} placeholder="Descreva as características e diferenciais do imóvel…" required />
          </Field>
          <Field label="Fotos" span={3}>
            <label className="li-drop">
              <input type="file" accept="image/*" multiple onChange={(e) => setFotos(Array.from(e.target.files || []))} />
              <span className="li-drop-icon">📷</span>
              <span className="li-drop-text">
                {fotos.length > 0 ? <b>{fotos.length} foto(s) selecionada(s)</b> : <>Clique para selecionar as fotos</>}
              </span>
            </label>
          </Field>
        </Section>
      </form>

      <div className="li-actionbar">
        <div className="li-actionbar-inner">
          <span className="li-actionbar-hint">Campos com <b>*</b> são obrigatórios.</span>
          <button type="button" className="li-cta" onClick={enviar} disabled={enviando || carregandoListas}>
            {enviando ? <><span className="li-spinner" /> Lançando…</> : "Lançar imóvel"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Subcomponentes de UI ─────────────────────────────────────────────── */

function Section({ n, icon, title, desc, required, children }) {
  return (
    <section className="li-card">
      <div className="li-card-head">
        <span className="li-step">{n}</span>
        <div className="li-card-title">
          <h2><span className="li-card-icon" aria-hidden="true">{icon}</span> {title}
            {required && <span className="li-req-pill">obrigatório</span>}</h2>
          {desc && <p>{desc}</p>}
        </div>
      </div>
      <div className="li-grid">{children}</div>
    </section>
  );
}

function Field({ label, req, span, children }) {
  return (
    <label className={`li-field ${span === 2 ? "li-span2" : span === 3 ? "li-span3" : ""}`}>
      <span className="li-label">{label}{req && <i className="li-star">*</i>}</span>
      {children}
    </label>
  );
}

function TextField({ label, value, onChange, req, span, prefix, suffix, type = "text" }) {
  return (
    <Field label={label} req={req} span={span}>
      <div className={`li-input-wrap ${prefix ? "has-prefix" : ""} ${suffix ? "has-suffix" : ""}`}>
        {prefix && <span className="li-affix li-prefix">{prefix}</span>}
        <input type={type} value={value} onChange={onChange} />
        {suffix && <span className="li-affix li-suffix">{suffix}</span>}
      </div>
    </Field>
  );
}

function SelectField({ label, value, onChange, opts, loading, req }) {
  return (
    <Field label={label} req={req}>
      <select value={value} onChange={onChange} required={req}>
        <option value="">{loading ? "Carregando…" : "Selecione…"}</option>
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </Field>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <label className="li-toggle">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="li-toggle-track"><span className="li-toggle-thumb" /></span>
      <span className="li-toggle-label">{label}</span>
    </label>
  );
}

function Tag({ ok, label }) {
  return <span className={`li-tag ${ok ? "li-tag--ok" : "li-tag--warn"}`}>{label}</span>;
}
