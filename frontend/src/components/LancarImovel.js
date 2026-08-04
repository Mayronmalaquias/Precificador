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

  const set = (k) => (e) => {
    const v = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [k]: v }));
  };

  // Corretores (para o codigousuario = id_imoview do corretor)
  useEffect(() => {
    fetch(`${BASE}/corretor/retornar-lista?ativo=true&per_page=1000`)
      .then((r) => r.json())
      .then((d) => setCorretores((d?.lista || []).filter((c) => (c.nome || c.username))))
      .catch(() => {});
  }, []);

  // Listas do Imoview
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

      // fetch direto (multipart) — o interceptor injeta X-API-KEY sem tocar no Content-Type.
      const resp = await fetch(`${BASE}/assistente/incluir-imovel`, { method: "POST", body: fd });
      const d = await resp.json().catch(() => ({}));
      if (!resp.ok || d.ok === false) throw new Error(d.error || "Erro ao lançar o imóvel.");

      setResultado(d);
      toast(`Imóvel lançado! Código ${d.codigo ?? "—"}.`, "success");
      setForm(VAZIO);
      setFotos([]);
    } catch (err) {
      toast(err.message || "Erro ao lançar o imóvel.", "error");
    } finally {
      setEnviando(false);
    }
  }, [enviando, form, fotos, userData, toast]);

  return (
    <div className="li-page">
      <div className="li-header">
        <h1>Lançar Imóvel</h1>
        <p>Lançamento único: inclui no <strong>Imoview</strong> e cria o cartão no <strong>Trello</strong>.</p>
      </div>

      {resultado && (
        <div className="li-resultado">
          ✅ Imóvel lançado no Imoview — código <strong>{resultado.codigo ?? "—"}</strong>.
          {" "}Planilha: {resultado.sheet?.ok ? "gravada ✓" : `⚠️ ${resultado.sheet?.error || "falhou"}`}.
          {" "}Trello: {resultado.trello?.ok
            ? <a href={resultado.trello.url} target="_blank" rel="noreferrer">cartão criado ✓</a>
            : <>⚠️ {resultado.trello?.error || "falhou"}</>}.
        </div>
      )}

      <form className="li-form" onSubmit={enviar}>
        <fieldset className="li-fs">
          <legend>Identificação</legend>
          <label className="li-field li-col2">
            <span>Corretor *</span>
            <select value={form.codigousuario} onChange={onCorretor} required>
              <option value="">Selecione…</option>
              {corretoresOpts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <Select label="Finalidade *" value={form.finalidade} onChange={set("finalidade")} opts={listas.finalidades} loading={carregandoListas} req />
          <Select label="Destinação *" value={form.destinacao} onChange={set("destinacao")} opts={listas.destinacoes} loading={carregandoListas} req />
          <Select label="Tipo *" value={form.codigotipo} onChange={set("codigotipo")} opts={listas.tipos} loading={carregandoListas} req />
          <Select label="Unidade *" value={form.codigounidade} onChange={set("codigounidade")} opts={listas.unidades} loading={carregandoListas} req />
          <Select label="Local da chave *" value={form.localchave} onChange={set("localchave")} opts={listas.localchaves} loading={carregandoListas} req />
          <label className="li-check"><input type="checkbox" checked={form.exclusivo} onChange={set("exclusivo")} /> Exclusivo</label>
        </fieldset>

        <fieldset className="li-fs">
          <legend>Endereço</legend>
          <Txt label="Rua *" value={form.rua} onChange={set("rua")} cls="li-col2" />
          <Txt label="Número" value={form.numero} onChange={set("numero")} />
          <Txt label="Complemento" value={form.complemento} onChange={set("complemento")} />
          <Txt label="Bloco" value={form.bloco} onChange={set("bloco")} />
          <Txt label="Bairro *" value={form.bairro} onChange={set("bairro")} />
          <Txt label="Cidade" value={form.cidade} onChange={set("cidade")} />
          <Txt label="Estado" value={form.estado} onChange={set("estado")} />
        </fieldset>

        <fieldset className="li-fs">
          <legend>Valores e áreas</legend>
          <Txt label="Valor *" value={form.valor} onChange={set("valor")} type="text" />
          <Txt label="Condomínio" value={form.valorcondominio} onChange={set("valorcondominio")} />
          <Txt label="IPTU (valor)" value={form.valoriptu} onChange={set("valoriptu")} />
          <Txt label="Comissão %" value={form.comissao} onChange={set("comissao")} />
          <Txt label="Área interna *" value={form.areainterna} onChange={set("areainterna")} />
          <Txt label="Área externa" value={form.areaexterna} onChange={set("areaexterna")} />
        </fieldset>

        <fieldset className="li-fs">
          <legend>Características</legend>
          <Txt label="Quartos" value={form.numeroquartos} onChange={set("numeroquartos")} />
          <Txt label="Suítes" value={form.numerosuites} onChange={set("numerosuites")} />
          <Txt label="Banheiros" value={form.numerobanhos} onChange={set("numerobanhos")} />
          <Txt label="Salas" value={form.numerosalas} onChange={set("numerosalas")} />
          <Txt label="Varandas" value={form.numerovarandas} onChange={set("numerovarandas")} />
          <Txt label="Vagas" value={form.numerovagas} onChange={set("numerovagas")} />
        </fieldset>

        <fieldset className="li-fs">
          <legend>Proprietário (obrigatório)</legend>
          <Txt label="Nome *" value={form.prop_nome} onChange={set("prop_nome")} cls="li-col2" />
          <Txt label="CPF/CNPJ *" value={form.prop_cpf} onChange={set("prop_cpf")} />
          <Txt label="Telefone *" value={form.prop_telefone} onChange={set("prop_telefone")} />
          <Txt label="E-mail" value={form.prop_email} onChange={set("prop_email")} />
          <Txt label="% participação" value={form.prop_percentual} onChange={set("prop_percentual")} />
        </fieldset>

        <fieldset className="li-fs">
          <legend>Documentação / Trello</legend>
          <Txt label="Matrícula" value={form.matricula} onChange={set("matricula")} />
          <Txt label="Inscrição IPTU" value={form.inscricao_iptu} onChange={set("inscricao_iptu")} />
          <label className="li-check"><input type="checkbox" checked={form.cessao_direitos} onChange={set("cessao_direitos")} /> Cessão de direitos</label>
        </fieldset>

        <fieldset className="li-fs">
          <legend>Descrição e fotos</legend>
          <label className="li-field li-col-full">
            <span>Descrição *</span>
            <textarea rows={4} value={form.descricao} onChange={set("descricao")} required />
          </label>
          <label className="li-field li-col-full">
            <span>Fotos</span>
            <input type="file" accept="image/*" multiple onChange={(e) => setFotos(Array.from(e.target.files || []))} />
            {fotos.length > 0 && <small>{fotos.length} foto(s) selecionada(s)</small>}
          </label>
        </fieldset>

        <div className="li-acoes">
          <button type="submit" className="li-btn" disabled={enviando || carregandoListas}>
            {enviando ? "Lançando…" : "Lançar imóvel"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Txt({ label, value, onChange, type = "text", cls = "" }) {
  return (
    <label className={`li-field ${cls}`}>
      <span>{label}</span>
      <input type={type} value={value} onChange={onChange} />
    </label>
  );
}

function Select({ label, value, onChange, opts, loading, req }) {
  return (
    <label className="li-field">
      <span>{label}</span>
      <select value={value} onChange={onChange} required={req}>
        <option value="">{loading ? "Carregando…" : "Selecione…"}</option>
        {opts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}
