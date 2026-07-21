import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchEquipes, setEquipesCache } from '../services/equipes';

const EquipesContext = createContext(null);

function mapToOpcoes(map) {
  return Object.entries(map).map(([value, label]) => ({ value, label }));
}

export function EquipesProvider({ children }) {
  const [equipes, setEquipes] = useState([]);
  const [carregado, setCarregado] = useState(false);

  const reload = useCallback(async () => {
    try {
      setEquipes(await fetchEquipes());
    } catch {
      // sem equipes se a API falhar (nada de lista pré-determinada)
    } finally {
      setCarregado(true);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // Fonte da verdade: banco. Sem fallback hardcoded.
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

  const equipesOpcoes = useMemo(() => mapToOpcoes(equipesMap), [equipesMap]);

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
