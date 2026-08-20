import React, { useCallback, useEffect, useMemo, useState } from "react";
import { BASE } from "../services/api";
import { soDigitos, moedaInput, moedaNumero } from "../services/moeda";
import { porRotulo } from "../services/ordenar";
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
// As listas do Imoview (unidade, tipo, destinacao, local da chave, bairro) chegam na
// ordem de cadastro deles — alfabetica aqui para dar p/ achar item na lista longa.
const asOpts = (lista) => porRotulo(Array.isArray(lista) ? lista.map(opt).filter(Boolean) : []);
const CAMPOS_MOEDA = new Set(["valor", "valorcondominio", "valoriptu"]);

// Máscara em services/moeda.js — os dígitos representam centavos, e a conversão é feita
// por string: `Number(digitos) / 100` perdia precisão acima de 2^53 e inventava centavos.
const somenteDigitos = soDigitos;
const formatarMoedaInput = moedaInput;
const moedaParaNumero = moedaNumero;

// Rótulo de um código dentro de uma lista já carregada do Imoview.
const rotulo = (opts, value) =>
  String(opts?.find((o) => String(o.value) === String(value))?.label ?? "");

// Formata "880000", "880000.00" ou "880.000,00" → "R$ 880.000,00".
//
// O ponto e ambiguo: em "880.000,00" (digitado) ele separa milhar, em "880000.00" (o que
// `moedaNumero` produz) ele separa os centavos. Tratar tudo como milhar multiplicava o
// valor por 100 no texto do grupo — "R$ 88.000.000,00" para um imovel de 880 mil.
function paraNumeroBR(v) {
  const texto = String(v ?? "").trim();
  if (!texto) return NaN;
  // Decimal canonico: so digitos e, no maximo, um ponto seguido dos centavos.
  if (/^-?\d+(\.\d+)?$/.test(texto)) return Number(texto);
  // Formato brasileiro: ponto e milhar, virgula e decimal.
  return Number(texto.replace(/\./g, "").replace(",", "."));
}

function fmtValorBR(v) {
  const n = paraNumeroBR(v);
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

// `tem_documento` e `tem_telefone` só existem no formulário — o back não os recebe.
// Documento vazio vira o marcador 00000000000 (o Imoview não aceita proprietário sem
// documento). Telefone vazio simplesmente não é enviado: número falso no CRM é pior que
// campo em branco, porque alguém liga para ele.
const propVazio = () => ({
  nome: "", cpfoucnpj: "", telefone: "", email: "", percentual: "100",
  tem_documento: true, tem_telefone: true,
});

const VAZIO = {
  // Principal = o que vai pro Imoview (codigousuario) e pra planilha. O 2º corretor só
  // existe do nosso lado (fato_captacao) — o Imoview ignora captador secundário.
  codigousuario: "", corretor_nome: "",
  codigousuario2: "", corretor2_nome: "",
  finalidade: "", destinacao: "", codigotipo: "", codigounidade: "", localchave: "",
  cep: "", rua: "", numero: "", complemento: "", bloco: "", edificio: "", bairro: "", cidade: "Brasília", estado: "DF",
  urlvideo: "",
  valor: "", valorcondominio: "", valoriptu: "", comissao: "",
  areainterna: "", areaexterna: "",
  numeroquartos: "", numerosalas: "", numerobanhos: "", numerosuites: "", numerovarandas: "", numerovagas: "",
  descricao: "",
  proprietarios: [propVazio()],
  matricula: "", inscricao_iptu: "", exclusivo: false, cessao_direitos: false,
  foco: "",
};

// Mesma régra do back (admin_bases_service.classificar_foco) — aqui só p/ sugerir.
const BAIRROS_PP = ["PLANO PILOTO", "ASA SUL", "ASA NORTE", "NOROESTE", "SUDOESTE", "JARDIM BOTANICO", "LAGO NORTE", "LAGO SUL", "SETOR SUDOESTE"];
const BAIRROS_AC = ["AGUAS CLARAS"];
const semAcento = (v) => String(v || "").normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toUpperCase();

function sugerirFoco({ bairro, valor, comissao, destinacao }) {
  const b = semAcento(bairro);
  const v = Number(String(valor).replace(/\./g, "").replace(",", ".")) || 0;
  const c = Number(String(comissao).replace(",", ".")) || 0;
  const residencial = ["1", "3"].includes(String(destinacao || "").trim());
  if (!b || !v || !c || !residencial) return "";
  const pp = BAIRROS_PP.some((x) => b === x) && v >= 1000000 && c >= 3.5;
  const ac = BAIRROS_AC.some((x) => b.includes(x)) && v >= 600000 && c >= 3.5;
  if (pp && ac) return "pp_ac";
  if (pp) return "pp";
  if (ac) return "ac";
  return "nao_foco";
}

const FOCO_OPCOES = [
  { value: "nao_foco", label: "Não foco" },
  { value: "pp", label: "Foco PP (Plano Piloto)" },
  { value: "ac", label: "Foco AC (Águas Claras)" },
  { value: "pp_ac", label: "Foco PP + AC" },
];

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
  const [buscandoCep, setBuscandoCep] = useState(false);

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

  // ViaCEP é público e não pede chave; preenche rua/bairro/cidade/UF e deixa o resto
  // editável (o CEP pode ser de logradouro genérico).
  const buscarCep = useCallback(async (valor) => {
    const cep = somenteDigitos(valor);
    if (cep.length !== 8) return;
    setBuscandoCep(true);
    try {
      const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const d = await r.json();
      if (d.erro) { toast("CEP não encontrado.", "error"); return; }
      setForm((f) => ({
        ...f,
        rua: d.logradouro || f.rua,
        bairro: d.bairro || f.bairro,
        cidade: d.localidade || f.cidade,
        estado: d.uf || f.estado,
        complemento: f.complemento || d.complemento || "",
      }));
      toast("Endereço preenchido pelo CEP.", "success");
    } catch {
      toast("Não consegui consultar o CEP — preencha o endereço manualmente.", "error");
    } finally {
      setBuscandoCep(false);
    }
  }, [toast]);

  const onCep = (e) => {
    const valor = e.target.value;
    setForm((f) => ({ ...f, cep: valor }));
    if (somenteDigitos(valor).length === 8) buscarCep(valor);
  };

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

  // Sugestão da regra oficial — o estagiário decide, mas vê o que a regra diria.
  const focoSugerido = useMemo(
    () => sugerirFoco({ bairro: form.bairro, valor: form.valor, comissao: form.comissao, destinacao: form.destinacao }),
    [form.bairro, form.valor, form.comissao, form.destinacao]
  );

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
    if (!String(form.urlvideo).trim()) { toast("Informe o link do vídeo.", "error"); return; }
    if (!form.foco) { toast("Selecione se o imóvel é foco.", "error"); return; }

    const props = form.proprietarios
      .filter((p) => String(p.nome).trim())
      // Quem marcou "sem documento" vai com o campo vazio: o back aplica o
      // 00000000000, que é o marcador único de proprietário sem CPF/CNPJ.
      .map(({ tem_documento, tem_telefone, ...p }) => ({
        ...p,
        cpfoucnpj: tem_documento ? p.cpfoucnpj : "",
        telefone: tem_telefone ? p.telefone : "",
      }));
    if (!props.length) { toast("Informe ao menos um proprietário.", "error"); return; }
    // Marcou que tem telefone? Entao tem que preencher. Quem desmarcou vai sem o campo.
    const semTelefone = form.proprietarios.find(
      (p) => String(p.nome).trim() && p.tem_telefone && !String(p.telefone).trim());
    if (semTelefone) {
      toast(`Proprietário "${semTelefone.nome}": informe o telefone ou desmarque "Tem telefone".`, "error"); return;
    }
    // Marcou que tem documento? Então tem que preencher.
    const semDoc = form.proprietarios.find((p) => String(p.nome).trim() && p.tem_documento && !String(p.cpfoucnpj).trim());
    if (semDoc) {
      toast(`Proprietário "${semDoc.nome}": informe o CPF/CNPJ ou desmarque "Tem CPF / CNPJ".`, "error"); return;
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
      // O texto do grupo já sai com o foco que foi lançado (o botão segue editável).
      setFoco(form.foco !== "nao_foco");
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

        <Section n={2} icon="📍" title="Endereço" desc="Digite o CEP que o resto vem preenchido.">
          <Field label="CEP">
            <div className="li-cep">
              <input value={form.cep} onChange={onCep} inputMode="numeric" placeholder="70000-000" maxLength={9} />
              <button type="button" onClick={() => buscarCep(form.cep)} disabled={buscandoCep}>
                {buscandoCep ? "Buscando…" : "Buscar"}
              </button>
            </div>
          </Field>
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
          <Field label="Foco" req>
            <select value={form.foco} onChange={set("foco")} required>
              <option value="">Selecione…</option>
              {FOCO_OPCOES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {focoSugerido && form.foco !== focoSugerido && (
              <button type="button" className="li-foco-sugestao" onClick={() => setForm((f) => ({ ...f, foco: focoSugerido }))}>
                Regra sugere: <b>{FOCO_OPCOES.find((o) => o.value === focoSugerido)?.label}</b> — usar
              </button>
            )}
          </Field>
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
                <Field label="Documento">
                  <Toggle
                    label={p.tem_documento ? "Tem CPF / CNPJ" : "Sem CPF / CNPJ — vai 00000000000"}
                    checked={p.tem_documento}
                    onChange={(e) => {
                      const marcado = e.target.checked;
                      setForm((f) => ({
                        ...f,
                        proprietarios: f.proprietarios.map((item, idx) => idx === i
                          ? { ...item, tem_documento: marcado, cpfoucnpj: marcado ? item.cpfoucnpj : "" }
                          : item),
                      }));
                    }}
                  />
                </Field>
                {p.tem_documento
                  ? <TextField label="CPF / CNPJ" value={p.cpfoucnpj} onChange={setProp(i, "cpfoucnpj")} req placeholder="Só números ou com pontuação" />
                  : (
                    <Field label="CPF / CNPJ">
                      {/* `disabled`, nao `readOnly`: readOnly ainda recebe foco e da a
                          impressao de que da p/ digitar. Aqui o campo e so o marcador. */}
                      <input
                        value="00000000000"
                        disabled
                        className="li-doc-placeholder"
                        title="Proprietário sem documento — o marcador é enviado automaticamente"
                      />
                    </Field>
                  )}
                <Field label="Telefone do proprietário">
                  <Toggle
                    label={p.tem_telefone ? "Tem telefone" : "Não informou telefone"}
                    checked={p.tem_telefone}
                    onChange={(e) => {
                      const marcado = e.target.checked;
                      setForm((f) => ({
                        ...f,
                        proprietarios: f.proprietarios.map((item, idx) => idx === i
                          ? { ...item, tem_telefone: marcado, telefone: marcado ? item.telefone : "" }
                          : item),
                      }));
                    }}
                  />
                </Field>
                {p.tem_telefone
                  ? <TextField label="Telefone" value={p.telefone} onChange={setProp(i, "telefone")} req />
                  : (
                    <Field label="Telefone">
                      {/* Diferente do CPF, aqui NAO vai marcador: telefone falso no CRM e
                          pior que campo vazio, porque alguem liga. O campo simplesmente
                          nao e enviado — ver `normalizar_proprietarios`. */}
                      <input
                        value="Não informado"
                        disabled
                        className="li-doc-placeholder"
                        title="Proprietário sem telefone — o campo não é enviado ao Imoview"
                      />
                    </Field>
                  )}
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

        <Section n={7} icon="📝" title="Descrição, vídeo e fotos" desc="Texto do anúncio, tour em vídeo e imagens do imóvel.">
          <Field label="Descrição" req span={3}>
            <textarea rows={4} value={form.descricao} onChange={set("descricao")} placeholder="Descreva as características e diferenciais do imóvel…" required />
          </Field>
          <TextField label="Link do vídeo" value={form.urlvideo} onChange={set("urlvideo")} req span={3}
            placeholder="https://youtube.com/… — vai pro Imoview e pro cartão do Trello" />
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

function TextField({ label, value, onChange, req, span, prefix, suffix, type = "text", inputMode, placeholder }) {
  return (
    <Field label={label} req={req} span={span}>
      <div className={`li-input-wrap ${prefix ? "has-prefix" : ""} ${suffix ? "has-suffix" : ""}`}>
        {prefix && <span className="li-affix li-prefix">{prefix}</span>}
        <input type={type} inputMode={inputMode} value={value} onChange={onChange} required={req} placeholder={placeholder} />
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
