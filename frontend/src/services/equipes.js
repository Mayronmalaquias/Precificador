import { api } from './api';

// Cache de módulo (preenchido pelo EquipesProvider). Permite que código fora de
// componentes React — ex.: helpers/sub-componentes — resolvam o nome da equipe.
let _equipesMap = {};

export function setEquipesCache(map) {
  _equipesMap = map || {};
}

export function nomeEquipe(id) {
  return _equipesMap[String(id)] || String(id || '—');
}

export function equipesOpcoesFromCache() {
  return Object.entries(_equipesMap).map(([value, label]) => ({ value, label }));
}

export async function fetchEquipes(incluirInativas = false) {
  const path = incluirInativas ? '/equipes?incluir_inativas=true' : '/equipes';
  const data = await api.get(path);
  return Array.isArray(data?.equipes) ? data.equipes : [];
}

export function criarEquipe({ id_equipe, nome, email, id_gerente }) {
  return api.post('/equipes', { id_equipe, nome, email, id_gerente });
}

export function atualizarEquipe(id_equipe, patch) {
  return api.put(`/equipes/${encodeURIComponent(id_equipe)}`, patch);
}
