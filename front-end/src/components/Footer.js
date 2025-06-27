// Footer.jsx
import logo61 from '../assets/img/LOGO 61 PNG (3).png';

function Footer() {
  // Links para facilitar a manutenção
  const socialLinks = {
    whatsapp: 'https://api.whatsapp.com/send?phone=5561998786161',
    instagram: 'https://www.instagram.com/61imoveis/',
    youtube: 'https://www.youtube.com/@61imoveis',
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="footer-container">
        {/* --- ÁREA PRINCIPAL DO RODAPÉ --- */}
        <div className="footer-main">
          {/* Coluna 1: Marca e Redes Sociais */}
          <div className="footer-column footer-brand">
            <p className="footer-tagline">Compra, Venda e Aluguel de Apartamentos e Casas em Brasília e Águas Claras.</p>
          </div>

          {/* Coluna 2: A 61 Imóveis */}
          <div className="footer-column">
            <h5>A 61 Imóveis</h5>
            <ul className="footer-links">
              <li><a href="https://www.61imoveis.com/sobre">Quem Somos</a></li>
              <li><a href="https://www.61imoveis.com/contato">Fale Conosco</a></li>
              <li><a href="https://www.61imoveis.com/nossa-equipe">Nossa Equipe</a></li>
              <li><a href="https://www.61imoveis.com/politica-privacidade">Política de Privacidade</a></li>
               <li><a href="https://www.61imoveis.com/politica-privacidade#codigoEticaConduta">Código de Ética</a></li>
              <li><a href="https://forms.gle/R3petwJNKZLtM2cc7" target="_blank" rel="noreferrer">Canal de Denúncia</a></li>
              <li>CRECI: 21418</li>
            </ul>
          </div>

          {/* Coluna 3: Nossos Serviços */}
          <div className="footer-column">
            <h5>Nossos Serviços</h5>
            <ul className="footer-links">
              <li><a href="https://www.61imoveis.com/aluguel">Imóveis para Alugar</a></li>
              <li><a href="https://www.61imoveis.com/venda">Imóveis para Comprar</a></li>
              <li><a href="https://www.61imoveis.com/condominios">Condomínios no DF</a></li>
              <li><a href="https://61imoveis.61imoveis.com/anuncie-conosco-2/">Anuncie seu Imóvel</a></li>
              {/* <li><a href="https://lp.61imoveis.com/guia-61-de-venda-de-imoveis" target="_blank" rel="noreferrer">Guia de Venda</a></li>
              <li><a href="https://lp.61imoveis.com/guia-61-de-aluguel-de-imoveis" target="_blank" rel="noreferrer">Guia de Locação</a></li>
              <li><a href="https://lp.61imoveis.com/guia-61-do-comprador-de-imoveis" target="_blank" rel="noreferrer">Guia do Comprador de Imoveis</a></li>
              <li><a href="https://lp.61imoveis.com/lp-guia-61-do-inventario-de-imoveis" target="_blank" rel="noreferrer">Guia do inventario de imoveis</a></li> */}

            </ul>
          </div>
          
          {/* Coluna 4: Atendimento */}
          <div className="footer-column">
              <h5>Atendimento</h5>
              <ul className="footer-links">
                  <li><a href="mailto:61@61imoveis.com">61@61imoveis.com</a></li>
                  <li><a href="tel:6136862430">(61) 3686-2430</a></li>
                  <li className="footer-address">
                      <strong>Asa Sul:</strong> SEPS Q 707/907 Ed. San Marino, Sala 118
                  </li>
                   <li className="footer-address">
                      <strong>Águas Claras:</strong> E-business, R. Pau Brasil, Lt. 6, Sala 702
                  </li>
              </ul>
          <img src={logo61} alt="Logo 61 Imóveis" className="footer-logo" />
          </div>
        </div>

        {/* --- BARRA INFERIOR --- */}
        <div className="footer-bottom-bar">
            <div className="social-icons">
              <a href={socialLinks.whatsapp} target="_blank" rel="noreferrer" aria-label="WhatsApp">
                {/* Ícone SVG do WhatsApp */}
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.75 13.96c.27.13.42.25.5.38.13.19.13.44.08.64s-.16.38-.5.61c-.32.24-.72.38-1.04.38h-.02c-.39 0-1.03-.13-1.88-.59-.97-.54-1.83-1.35-2.56-2.22-.84-.97-1.42-2.1-1.63-2.61-.22-.52-.13-1.03.22-1.39.29-.29.64-.44.92-.44.25 0 .47.08.64.25.22.22.33.54.38.72.05.19.05.44-.03.69-.08.24-.16.42-.27.56-.1.13-.22.25-.32.35-.1.1-.19.19-.16.35.03.15.22.61.69 1.14.72.78 1.44 1.13 1.63 1.22.19.08.39.08.54-.03zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>
              </a>
              <a href={socialLinks.instagram} target="_blank" rel="noreferrer" aria-label="Instagram">
                {/* Ícone SVG do Instagram */}
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c2.72 0 3.05.01 4.12.06 1.06.05 1.79.22 2.42.47.65.25 1.17.59 1.73 1.14.55.56.89 1.08 1.14 1.73.25.63.42 1.36.47 2.42.05 1.07.06 1.4.06 4.12s-.01 3.05-.06 4.12c-.05 1.06-.22 1.79-.47 2.42-.25.65-.59 1.17-1.14 1.73-.56.55-1.08.89-1.73 1.14-.63.25-1.36.42-2.42.47-1.07.05-1.4.06-4.12.06s-3.05-.01-4.12-.06c-1.06-.05-1.79-.22-2.42-.47-.65-.25-1.17-.59-1.73-1.14-.55-.56-.89-1.08-1.14-1.73-.25-.63-.42-1.36-.47-2.42-.05-1.07-.06-1.4-.06-4.12s.01-3.05.06-4.12c.05-1.06.22-1.79.47-2.42.25-.65.59-1.17 1.14-1.73.56-.55 1.08-.89 1.73-1.14.63-.25 1.36-.42 2.42-.47C8.95 2.01 9.28 2 12 2zm0 1.8c-2.69 0-3.02.01-4.07.06-1.03.05-1.63.21-2.12.42-.56.22-.96.5-1.34 1.01-.54.54-.82 1.04-1.01 1.5-.22.56-.42 1.16-.47 2.12-.05 1.05-.06 1.38-.06 4.07s.01 3.02.06 4.07c.05 1.03.21 1.63.42 2.12.19.48.47.88 1.01 1.34.46.46.96.74 1.5.94.56.22 1.16.42 2.12.47 1.05.05 1.38.06 4.07.06s3.02-.01 4.07-.06c1.03-.05 1.63-.21 2.12-.42.56-.22.96-.5 1.34-1.01.54-.54.82-1.04 1.01-1.5.22-.56.42-1.16.47-2.12.05-1.05.06-1.38.06-4.07s-.01-3.02-.06-4.07c-.05-1.03-.21-1.63-.42-2.12-.19-.48-.47-.88-1.01-1.34-.46-.46-.96-.74-1.5-.94-.56-.22-1.16-.42-2.12-.47-1.05-.05-1.38-.06-4.07-.06zM12 7.27c-2.61 0-4.73 2.12-4.73 4.73s2.12 4.73 4.73 4.73 4.73-2.12 4.73-4.73-2.12-4.73-4.73-4.73zm0 7.67c-1.62 0-2.93-1.31-2.93-2.93s1.31-2.93 2.93-2.93 2.93 1.31 2.93 2.93-1.31 2.93-2.93 2.93zm4.61-7.81c0 .5-.41.91-.91.91s-.91-.41-.91-.91.41-.91.91-.91.91.41.91.91z"/></svg>
              </a>
              <a href={socialLinks.youtube} target="_blank" rel="noreferrer" aria-label="YouTube">
                {/* Ícone SVG do YouTube */}
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M21.58 7.19c-.23-.86-.9-1.52-1.76-1.75C18.25 5 12 5 12 5s-6.25 0-7.82.44c-.86.23-1.52.89-1.75 1.75C2 8.76 2 12 2 12s0 3.24.43 4.81c.23.86.9 1.52 1.75 1.75C5.75 19 12 19 12 19s6.25 0 7.82-.44c.86-.23 1.52-.89 1.76-1.75C22 15.24 22 12 22 12s0-3.24-.42-4.81zM9.75 15.2V8.8l5.22 3.2-5.22 3.2z"/></svg>
              </a>
            </div>
          <p>© {currentYear} 61 Imóveis. Todos os direitos reservados.</p>
          <p>Desenvolvido pela <a href="https://www.61imoveis.com/" target="_blank" rel="noreferrer">61 Imóveis</a></p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;