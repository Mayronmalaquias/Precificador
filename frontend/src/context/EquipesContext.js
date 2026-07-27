import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchEquipes, setEquipesCache } from '../services/equipes';

const EquipesContext = createContext(null);

export function EquipesProvider({ children }) {
  const [equipes, setEquipes] = useState([]);
  const [carregado, setCarregado] = useState(false);

  const reload = useCallback(async () => {
    try {
      // inclui inativas: nomes históricos (ex.: gráficos) precisam resolver o rótulo
      setEquipes(await fetchEquipes(true));
    } catch {
      // sem equipes se a API falhar (nada de lista pré-determinada)
    } finally {
      setCarregado(true);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // Mapa com TODAS as equipes (ativas + inativas) → resolução de nome/rótulo.
  const equipesMap = useMemo(
    () =>
      equipes.reduce((acc, e) => {
        acc[String(e.id_equipe)] = e.nome || String(e.id_equipe);
        return acc;
      }, {}),
    [equipes],
  );

  // Mantém o cache de módulo sincronizado (usado por helpers fora de componentes).
  useEffect(() => {
    setEquipesCache(equipesMap);
  }, [equipesMap]);

  // Opções para os selects de atribuição: SÓ ativas (não deixa escolher equipe desativada).
  const equipesOpcoes = useMemo(
    () =>
      equipes
        .filter((e) => e.ativo)
        .map((e) => ({ value: String(e.id_equipe), label: e.nome || String(e.id_equipe) })),
    [equipes],
  );

  const getNomeEquipe = useCallback(
    (id) => equipesMap[String(id)] || String(id || '-'),
    [equipesMap],
  );

  const value = useMemo(
    () => ({ equipes, equipesMap, equipesOpcoes, getNomeEquipe, carregado, reload }),
    [equipes, equipesMap, equipesOpcoes, getNomeEquipe, carregado, reload],
  );

  return <EquipesContext.Provider value={value}>{children}</EquipesContext.Provider>;
}

export function useEquipes() {
  const ctx = useContext(EquipesContext);
  if (ctx) return ctx;
  return {
    equipes: [],
    equipesMap: {},
    equipesOpcoes: [],
    getNomeEquipe: (id) => String(id || '-'),
    carregado: false,
    reload: () => {},
  };
}
