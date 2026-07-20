// Declarações para imports de CSS (web) usados pelo scaffold Expo.
declare module '*.css';
declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}
