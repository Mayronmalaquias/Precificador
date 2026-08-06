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
const CAMPOS_MOEDA = new Set(["valor", "valorcondominio", "valoriptu"]);

const somenteDigitos = (valor) => String(valor ?? "").replace(/\D/g, "");

// Mesmo comportamento do Criar Visita: os dígitos representam centavos.
function formatarMoedaInput(valor) {
  const digitos = somenteDigitos(valor);
  if (!digitos) return "";
  return (Number(digitos) / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const moedaParaNumero = (valor) => somenteDigitos(valor)
  ? String(Number(somenteDigitos(valor)) / 100)
  : "";

// Rótulo de um código dentro de uma lista já carregada do Imoview.
const rotulo = (opts, value) =>
  String(opts?.find((o) => String(o.value) === String(value))?.label ?? "");

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

const propVazio = () => ({ nome: "", cpfoucnpj: "", telefone: "", email: "", percentual: "100" });

const VAZIO = {
  // Principal = o que vai pro Imoview (codigousuario) e pra planilha. O 2º corretor só
  // existe do nosso lado (fato_captacao) — o Imoview ignora captador secundário.
  codigousuario: "", corretor_nome: "",
  codigousuario2: "", corretor2_nome: "",
  finalidade: "", destinacao: "", codigotipo: "", codigounidade: "", localchave: "",
  rua: "", numero: "", complemento: "", bloco: "", edificio: "", bairro: "", cidade: "Brasília", estado: "DF",
  valor: "", valorcondominio: "", valoriptu: "", comissao: "",
  areainterna: "", areaexterna: "",
  numeroquartos: "", numerosalas: "", numerobanhos: "", numerosuites: "", numerovarandas: "", numerovagas: "",
  descricao: "",
  proprietarios: [propVazio()],
  matricula: "", inscricao_iptu: "", exclusivo: false, cessao_direitos: false,
};

export default function LancarImovel() {
  const toast = useToast();
  const { userData } = useAuth();
  const [form, setForm] = useState(VAZIO);
  const [corretores, setCorretores] = useState([]);
  const [listas, setListas] = useState({ unidades: [], finalidades: [], destinacoes: [], tipos: [], localchaves: [], bairros: [] });
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

  const setMoeda = (k) => (e) => {
    const v = somenteDigitos(e.target.value);
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
            bairros: asOpts(d.bairros),
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

  // `campo`/`nomeCampo`: "codigousuario"/"corretor_nome" (principal) ou os do 2º corretor.
  const onCorretor = (campo, nomeCampo) => (e) => {
    const codigo = e.target.value;
    const c = corretores.find((x) => String(x.id_imoview) === String(codigo));
    setForm((f) => ({ ...f, [campo]: codigo, [nomeCampo]: c ? (c.nome || c.username) : "" }));
  };

  const corretoresOpts = useMemo(
    () => corretores
      .filter((c) => c.id_imoview)
      .map((c) => ({ value: c.id_imoview, label: c.nome || c.username }))
      .sort((a, b) => String(a.label).localeCompare(String(b.label), "pt-BR")),
    [corretores]
  );

  /* ── Proprietários (lista) ──────────────────────────────────────────── */
  const setProp = (i, campo) => (e) => {
    const valor = e.target.value;
    setForm((f) => ({
      ...f,
      proprietarios: f.proprietarios.map((p, idx) => (idx === i ? { ...p, [campo]: valor } : p)),
    }));
  };

  const addProp = () =>
    setForm((f) => ({ ...f, proprietarios: [...f.proprietarios, propVazio()] }));

  const removeProp = (i) =>
    setForm((f) => ({
      ...f,
      proprietarios: f.proprietarios.length > 1
        ? f.proprietarios.filter((_, idx) => idx !== i)
        : f.proprietarios,
    }));

  const somaPercentual = useMemo(
    () => form.proprietarios.reduce((acc, p) => acc + (Number(String(p.percentual).replace(",", ".")) || 0), 0),
    [form.proprietarios]
  );

  const enviar = useCallback(async (e) => {
    e.preventDefault();
    if (enviando) return;
    if (!form.codigousuario) { toast("Selecione o corretor principal.", "error"); return; }
    if (form.codigousuario2 && form.codigousuario2 === form.codigousuario) {
      toast("O 2º corretor precisa ser diferente do principal.", "error"); return;
    }
    if (!form.rua) { toast("Informe a rua.", "error"); return; }
    if (!form.descricao) { toast("Informe a descrição.", "error"); return; }

    const props = form.proprietarios.filter((p) => String(p.nome).trim());
    if (!props.length) { toast("Informe ao menos um proprietário.", "error"); return; }
    const incompleto = props.find((p) => !String(p.cpfoucnpj).trim() || !String(p.telefone).trim());
    if (incompleto) {
      toast(`Proprietário "${incompleto.nome}": preencha CPF/CNPJ e telefone.`, "error"); return;
    }

    setEnviando(true);
    setResultado(null);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (Array.isArray(v) || v === "" || v == null) return;
        const valorEnvio = CAMPOS_MOEDA.has(k) ? moedaParaNumero(v) : v;
        fd.append(k, typeof valorEnvio === "boolean" ? String(valorEnvio) : valorEnvio);
      });
      // Array não passa em multipart — vai como JSON e o back desserializa.
      fd.append("proprietarios", JSON.stringify(props));
      fd.append("assistente_nome", userData?.nome || userData?.username || "");
      fd.append("assistente_id", userData?.id_usuarios || "");
      // Rótulos p/ o snapshot da captação (fato_captacao) — evita o back ter que
      // consultar as listas do Imoview de novo só p/ resolver código → nome.
      fd.append("tipo_nome", rotulo(listas.tipos, form.codigotipo));
      fd.append("finalidade_nome", rotulo(listas.finalidades, form.finalidade));
      fotos.forEach((foto) => fd.append("fotos", foto));

      const resp = await fetch(`${BASE}/assistente/incluir-imovel`, { method: "POST", body: fd });
      const d = await resp.json().catch(() => ({}));
      if (!resp.ok || d.ok === false) throw new Error(d.error || "Erro ao lançar o imóvel.");

      setResultado(d);
      // snapshot p/ o aviso do grupo (antes de limpar o form)
      setAviso({
        codigo: d.codigo,
        endereco: [form.rua, form.numero, form.bloco, form.complemento].filter(Boolean).join(" - "),
        valor: moedaParaNumero(form.valor),
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
  }, [enviando, form, fotos, userData, toast, listas.tipos, listas.finalidades]);

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
          <Field label="Corretor principal" req span={2}>
            <select value={form.codigousuario} onChange={onCorretor("codigousuario", "corretor_nome")} required>
              <option value="">Selecione o corretor…</option>
              {corretoresOpts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <small className="li-hint">Vai pro Imoview e pra planilha de estoque.</small>
          </Field>

          <Field label="2º corretor" span={2}>
            <select value={form.codigousuario2} onChange={onCorretor("codigousuario2", "corretor2_nome")}>
              <option value="">Sem 2º corretor</option>
              {corretoresOpts
                .filter((o) => String(o.value) !== String(form.codigousuario))
                .map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <small className="li-hint">
              Conta captação cheia no ranking. Não vai pro Imoview — o CRM só aceita um captador.
            </small>
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
          <TextField label="Edifício" value={form.edificio} onChange={set("edificio")} span={2} />
          <SelectField label="Bairro" value={form.bairro} onChange={set("bairro")} opts={listas.bairros} loading={carregandoListas} req />
          <TextField label="Cidade" value={form.cidade} onChange={set("cidade")} />
          <TextField label="Estado" value={form.estado} onChange={set("estado")} />
        </Section>

        <Section n={3} icon="💰" title="Valores e áreas" desc="Preço, encargos e metragem.">
          <TextField label="Valor" value={formatarMoedaInput(form.valor)} onChange={setMoeda("valor")} req prefix="R$" inputMode="numeric" />
          <TextField label="Condomínio" value={formatarMoedaInput(form.valorcondominio)} onChange={setMoeda("valorcondominio")} prefix="R$" inputMode="numeric" />
          <TextField label="IPTU (valor)" value={formatarMoedaInput(form.valoriptu)} onChange={setMoeda("valoriptu")} prefix="R$" inputMode="numeric" />
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

        <Section n={5} icon="🧾" title="Proprietários" desc="Obrigatório — o Imoview não cadastra sem. Pode ter mais de um." required>
          {form.proprietarios.map((p, i) => (
            <div key={i} className="li-prop">
              <div className="li-prop-head">
                <strong>Proprietário {i + 1}</strong>
                {form.proprietarios.length > 1 && (
                  <button type="button" className="li-prop-remove" onClick={() => removeProp(i)}>
                    Remover
                  </button>
                )}
              </div>
              <div className="li-grid">
                <TextField label="Nome" value={p.nome} onChange={setProp(i, "nome")} req span={2} />
                <TextField label="CPF / CNPJ" value={p.cpfoucnpj} onChange={setProp(i, "cpfoucnpj")} req />
                <TextField label="Telefone" value={p.telefone} onChange={setProp(i, "telefone")} req />
                <TextField label="E-mail" value={p.email} onChange={setProp(i, "email")} />
                <TextField label="% participação" value={p.percentual} onChange={setProp(i, "percentual")} suffix="%" />
              </div>
            </div>
          ))}

          <div className="li-prop-footer">
            <button type="button" className="li-prop-add" onClick={addProp}>
              + Adicionar proprietário
            </button>
            {form.proprietarios.length > 1 && somaPercentual !== 100 && (
              <span className="li-prop-aviso">
                Participações somam {somaPercentual}% — confira (o normal é 100%).
              </span>
            )}
          </div>
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

function TextField({ label, value, onChange, req, span, prefix, suffix, type = "text", inputMode }) {
  return (
    <Field label={label} req={req} span={span}>
      <div className={`li-input-wrap ${prefix ? "has-prefix" : ""} ${suffix ? "has-suffix" : ""}`}>
        {prefix && <span className="li-affix li-prefix">{prefix}</span>}
        <input type={type} inputMode={inputMode} value={value} onChange={onChange} required={req} />
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
