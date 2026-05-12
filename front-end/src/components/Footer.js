// Footer.jsx
import logo61 from '../assets/img/LOGO 61 PNG (2) (1).png';

function Footer() {
  const socialLinks = {
    whatsapp: 'https://api.whatsapp.com/send?phone=5561998786161',
    instagram: 'https://www.instagram.com/61imoveis/',
    youtube: 'https://www.youtube.com/@61imoveis',
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="footer-container">
        <div className="footer-main">
          <div className="footer-column footer-brand">
            <p className="footer-tagline">
              Compra, Venda e Aluguel de Apartamentos e Casas em Brasília e Águas Claras.
            </p>
          </div>

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

          <div className="footer-column">
            <h5>Nossos Serviços</h5>
            <ul className="footer-links">
              <li><a href="https://www.61imoveis.com/aluguel">Imóveis para Alugar</a></li>
              <li><a href="https://www.61imoveis.com/venda">Imóveis para Comprar</a></li>
              <li><a href="https://www.61imoveis.com/condominios">Condomínios no DF</a></li>
              <li><a href="https://61imoveis.61imoveis.com/anuncie-conosco-2/">Anuncie seu Imóvel</a></li>
            </ul>
          </div>

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

        <div className="footer-bottom-bar">
          <div className="social-icons">
            <a
              href={socialLinks.whatsapp}
              target="_blank"
              rel="noreferrer"
              aria-label="WhatsApp"
              className="social-icon-link social-icon-link--whatsapp"
              title="WhatsApp"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12.04 2C6.54 2 2.07 6.39 2.07 11.79c0 1.86.53 3.61 1.46 5.09L2 22l5.28-1.38a10.13 10.13 0 0 0 4.76 1.19c5.5 0 9.97-4.39 9.97-9.79S17.54 2 12.04 2Zm0 17.98c-1.5 0-2.95-.4-4.23-1.15l-.3-.18-3.13.82.84-3.02-.2-.31a8.01 8.01 0 0 1-1.22-4.35c0-4.39 3.7-7.97 8.24-7.97s8.24 3.58 8.24 7.97-3.7 8.19-8.24 8.19Zm4.52-5.99c-.25-.12-1.47-.71-1.7-.79-.23-.09-.39-.12-.56.12-.16.25-.64.79-.78.95-.14.16-.29.18-.54.06-.25-.12-1.05-.38-2-1.2-.74-.65-1.24-1.45-1.38-1.69-.14-.25-.02-.38.11-.5.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.16.04-.31-.02-.43-.06-.12-.56-1.33-.76-1.82-.2-.47-.4-.41-.56-.42h-.48c-.16 0-.43.06-.66.31-.23.25-.87.84-.87 2.04s.89 2.37 1.02 2.53c.12.16 1.75 2.62 4.24 3.67.59.25 1.05.4 1.41.51.59.19 1.13.16 1.56.1.48-.07 1.47-.59 1.68-1.16.21-.57.21-1.06.14-1.16-.06-.1-.23-.16-.48-.29Z" />
              </svg>
            </a>

            <a
              href={socialLinks.instagram}
              target="_blank"
              rel="noreferrer"
              aria-label="Instagram"
              className="social-icon-link social-icon-link--instagram"
              title="Instagram"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7.75 2h8.5A5.76 5.76 0 0 1 22 7.75v8.5A5.76 5.76 0 0 1 16.25 22h-8.5A5.76 5.76 0 0 1 2 16.25v-8.5A5.76 5.76 0 0 1 7.75 2Zm0 2A3.76 3.76 0 0 0 4 7.75v8.5A3.76 3.76 0 0 0 7.75 20h8.5A3.76 3.76 0 0 0 20 16.25v-8.5A3.76 3.76 0 0 0 16.25 4h-8.5ZM12 7.25A4.75 4.75 0 1 1 12 16.75 4.75 4.75 0 0 1 12 7.25Zm0 2A2.75 2.75 0 1 0 12 14.75 2.75 2.75 0 0 0 12 9.25Zm5-2.55a1.15 1.15 0 1 1 0 2.3 1.15 1.15 0 0 1 0-2.3Z" />
              </svg>
            </a>

            <a
              href={socialLinks.youtube}
              target="_blank"
              rel="noreferrer"
              aria-label="YouTube"
              className="social-icon-link social-icon-link--youtube"
              title="YouTube"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M21.58 7.19a3 3 0 0 0-2.11-2.12C17.61 4.57 12 4.57 12 4.57s-5.61 0-7.47.5a3 3 0 0 0-2.11 2.12A31.18 31.18 0 0 0 1.92 12c0 1.64.16 3.27.5 4.81a3 3 0 0 0 2.11 2.12c1.86.5 7.47.5 7.47.5s5.61 0 7.47-.5a3 3 0 0 0 2.11-2.12c.34-1.54.5-3.17.5-4.81 0-1.64-.16-3.27-.5-4.81ZM9.98 15.43V8.57L15.9 12l-5.92 3.43Z" />
              </svg>
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
