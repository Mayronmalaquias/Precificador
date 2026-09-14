import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

/**
 * No web o app é renderizado estaticamente (`web.output: "static"`), então o primeiro
 * render acontece sem acesso ao tema do sistema. Só depois de hidratar o valor é confiável.
 */
const naoMuda = () => () => {};

/** `false` no render estático, `true` depois de hidratar. */
function useHidratou() {
  // `useSyncExternalStore` dá o mesmo resultado que um `useState` + `useEffect`, mas sem
  // disparar um segundo render em cascata — era o que o eslint apontava aqui.
  return useSyncExternalStore(
    naoMuda,
    () => true,
    () => false,
  );
}

export function useColorScheme() {
  const hidratou = useHidratou();
  const scheme = useRNColorScheme();

  return hidratou ? scheme : 'light';
}
