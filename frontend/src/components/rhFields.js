// Equipes agora vêm do banco (ver EquipesContext / services/equipes). Nada hardcoded aqui.

export const RH_REQUIRED_FIELDS = [
  "status",
  "nome",
  "unidade",
  "gerente_responsavel",
  "data_entrada_61",
  "telefone_corporativo",
  "email_corporativo",
  "data_nascimento",
  "estado_civil",
  "possui_filhos",
  "endereco",
  "contato_emergencia",
  "cpf",
  "contrato_assinado",
  "codigo_conduta_assinado",
  "lgpd_assinada",
  "onboarding_realizado",
];

export const RH_FIELDS = [
  { name: "status", label: "Status", type: "select", options: ["Ativo", "Inativo", "Desligado"] },
  { name: "nome", label: "Nome completo", base: true },
  { name: "unidade", label: "Unidade" },
  { name: "gerente_responsavel", label: "Gerente responsável" },
  { name: "data_entrada_61", label: "Data de entrada na 61", type: "date" },
  { name: "creci", label: "CRECI" },
  { name: "validade_creci", label: "Validade CRECI", type: "date" },
  { name: "telefone_pessoal", label: "Telefone pessoal" },
  { name: "telefone_corporativo", label: "Telefone corporativo" },
  { name: "email_pessoal", label: "E-mail pessoal", type: "email" },
  { name: "email_corporativo", label: "E-mail corporativo", type: "email" },
  { name: "data_nascimento", label: "Data de nascimento", type: "date" },
  { name: "estado_civil", label: "Estado civil", type: "select", options: ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União estável"] },
  { name: "possui_filhos", label: "Possui filhos", type: "boolean" },
  { name: "endereco", label: "Endereço", type: "textarea" },
  { name: "contato_emergencia", label: "Contato de emergência", type: "textarea" },
  { name: "cpf", label: "CPF" },
  { name: "rg", label: "RG" },
  { name: "cnpj", label: "CNPJ" },
  { name: "razao_social", label: "Razão social" },
  { name: "banco", label: "Banco" },
  { name: "agencia", label: "Agência" },
  { name: "conta", label: "Conta" },
  { name: "tipo_conta", label: "Tipo de conta", type: "select", options: ["Corrente", "Poupança", "Pagamento"] },
  { name: "chave_pix", label: "Chave PIX" },
  { name: "contrato_assinado", label: "Contrato assinado", type: "boolean" },
  { name: "codigo_conduta_assinado", label: "Código de conduta assinado", type: "boolean" },
  { name: "lgpd_assinada", label: "LGPD assinada", type: "boolean" },
  { name: "onboarding_realizado", label: "Onboarding realizado", type: "boolean" },
  { name: "desligado", label: "Desligado?", type: "boolean" },
  { name: "data_desligamento", label: "Data de desligamento", type: "date" },
  { name: "observacoes", label: "Observações", type: "textarea" },
];

export function usuarioCampoVazio(usuario, fieldName) {
  const valor = usuario?.[fieldName];
  return valor === undefined || valor === null || String(valor).trim() === "";
}

export function camposFaltantes(usuario) {
  const faltantes = RH_FIELDS.filter((field) =>
    RH_REQUIRED_FIELDS.includes(field.name) && usuarioCampoVazio(usuario, field.name)
  );
  if ((usuario?.desligado === true || String(usuario?.desligado) === "true") && usuarioCampoVazio(usuario, "data_desligamento")) {
    const dataDesligamento = RH_FIELDS.find((field) => field.name === "data_desligamento");
    if (dataDesligamento) faltantes.push(dataDesligamento);
  }
  return faltantes;
}

export function emptyRhForm() {
  return RH_FIELDS.reduce((acc, field) => {
    acc[field.name] = "";
    return acc;
  }, {});
}
