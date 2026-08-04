import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import '../assets/css/Header.css';

function Header() {
  const navigate = useNavigate();
  const { isLogado, isAdmin, isAdministrador, isAssistente, permissao, nomeUsuario, idCorretor, logout } = useAuth();
  const isAdminOuDiretor = ['administrador', 'diretor'].includes(permissao);
  const profileRef = useRef(null);
  const servicosRef = useRef(null);
  const gestaoRef = useRef(null);

  const [menuAberto, setMenuAberto] = useState(false);
  const [servicosAberto, setServicosAberto] = useState(false);
  const [gestaoAberto, setGestaoAberto] = useState(false);

  const iniciais = useMemo(() => {
    const partes = String(nomeUsuario).trim().split(' ').filter(Boolean);
    if (partes.length === 0) return 'U';
    if (partes.length === 1) return partes[0].slice(0, 1).toUpperCase();
    return `${partes[0][0]}${partes[1][0]}`.toUpperCase();
  }, [nomeUsuario]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleTrocarSenha = () => {
    setMenuAberto(false);
    navigate('/TrocarSenha');
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setMenuAberto(false);
      }

      if (servicosRef.current && !servicosRef.current.contains(event.target)) {
        setServicosAberto(false);
      }

      if (gestaoRef.current && !gestaoRef.current.contains(event.target)) {
        setGestaoAberto(false);
      }
    };

    const handleEsc = (event) => {
      if (event.key === 'Escape') {
        setMenuAberto(false);
        setServicosAberto(false);
        setGestaoAberto(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEsc);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEsc);
    };
  }, []);

  const getNavLinkClass = ({ isActive }) =>
    isActive ? 'nav-link active-link' : 'nav-link';

  const atalhos = [
    { to: '/Parcerias', label: 'Parcerias', end: false, show: isLogado },
    {
      href: 'https://sites.google.com/view/portal-do-corretor-61-imoveis/seja-bem-vindo',
      label: 'Portal do Corretor',
      external: true,
      show: isLogado,
    },
    { to: '/61Financiamento', label: '61Financeiro', end: false, show: true },
    { to: '/Experts', label: 'Experts', end: false, show: true },
  ].filter((item) => item.show);

  const servicos = [
    { to: '/', label: 'Início', end: true, show: true },
    { to: '/NovaVisita', label: 'Criar Visita', show: isLogado },
    { to: '/JornadaCaptacao?novo=1', label: 'Novo Imóvel', subtitle: 'captação', show: isLogado },
    { to: '/AppVisita', label: 'Relatório de Visita', show: isLogado },
    { to: '/GestaoClientes', label: 'Gestao de Clientes', show: isLogado },
    { to: '/RelatorioGerente', label: 'Relatório Gerente', show: isLogado && isAdmin },
    { to: '/ranking', label: 'Ranking', show: isLogado && isAdmin },
    { to: '/AdminBases', label: 'Gestão de Bases', show: isLogado && isAdminOuDiretor },
    { to: '/Vendas', label: 'Vendas', show: isLogado && isAdminOuDiretor },
    { to: '/JornadaCaptacao', label: 'Jornada Captação', show: isLogado },
    { to: '/LancarImovel', label: 'Lançar Imóvel', subtitle: 'Imoview + Trello', show: isLogado && (isAssistente || isAdministrador) },
  ].filter((item) => item.show);

  const gestao = [
    { to: '/GerenteRH', label: 'Controle Equipe', show: isLogado && isAdmin },
    { to: '/GerenciarEquipes', label: 'Equipes', show: isLogado && isAdministrador },
    { to: '/RHUsuarios', label: 'RH Usuarios', show: isLogado && isAdministrador },
    { to: '/ControleCorretor', label: 'Controle usuarios', show: isLogado && isAdministrador },
    { to: '/register', label: 'Registrar Usuario', show: isLogado && isAdministrador },
  ].filter((item) => item.show);

  return (
    <header className="app-header">
      
      <div className="brand-area" onClick={() => navigate('/')}>
        <div className="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" className="brand-icon-svg">
            <path
              d="M3 10.5L12 3l9 7.5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M5.5 9.5V20h13V9.5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M9 20v-5h6v5"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <div className="brand-text">
          <span className="brand-kicker">Inteligência</span>
          <h1>Imobiliária 61</h1>
        </div>
      </div>

      {atalhos.length > 0 && (
        <nav className="atalhos-bar" aria-label="Atalhos">
          {atalhos.map((item) =>
            item.external ? (
              <a
                key={item.href}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                className="nav-link nav-atalho"
              >
                {item.label}
              </a>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  isActive ? 'nav-link nav-atalho active-link' : 'nav-link nav-atalho'
                }
              >
                {item.label}
              </NavLink>
            )
          )}
        </nav>
      )}

      <div className="header-right">
        <nav className="main-nav">
          <div
            className={`services-dropdown ${servicosAberto ? 'open' : ''}`}
            ref={servicosRef}
          >
            <button
              type="button"
              className="services-button"
              onClick={() => setServicosAberto((prev) => !prev)}
              aria-expanded={servicosAberto}
              aria-label="Abrir menu de serviços"
            >
              Serviços
              <span className={`services-chevron ${servicosAberto ? 'open' : ''}`}>
                ▾
              </span>
            </button>

            {servicosAberto && (
              <div className="services-menu">
                {servicos.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={getNavLinkClass}
                    onClick={() => setServicosAberto(false)}
                  >
                    {item.label}
                    {item.subtitle && (
                      <span className="services-menu-subtitle">{item.subtitle}</span>
                    )}
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          {gestao.length > 0 && (
            <div
              className={`services-dropdown ${gestaoAberto ? 'open' : ''}`}
              ref={gestaoRef}
            >
              <button
                type="button"
                className="services-button"
                onClick={() => setGestaoAberto((prev) => !prev)}
                aria-expanded={gestaoAberto}
                aria-label="Abrir menu de gestão"
              >
                Gestão
                <span className={`services-chevron ${gestaoAberto ? 'open' : ''}`}>
                  ▾
                </span>
              </button>

              {gestaoAberto && (
                <div className="services-menu">
                  {gestao.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      className={getNavLinkClass}
                      onClick={() => setGestaoAberto(false)}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          )}

          {!isLogado && (
            <NavLink to="/login" className={getNavLinkClass}>
              Login
            </NavLink>
          )}

          {!isLogado && (
            <NavLink to="/register" className={getNavLinkClass}>
              Criar conta
            </NavLink>
          )}
        </nav>

        {isLogado && (
          <div className="profile-wrapper" ref={profileRef}>
            <button
              type="button"
              className={`profile-button ${menuAberto ? 'open' : ''}`}
              onClick={() => setMenuAberto((prev) => !prev)}
              aria-label="Abrir menu do usuário"
              aria-expanded={menuAberto}
            >
              <span className="profile-avatar">{iniciais}</span>
            </button>

            {menuAberto && (
              <div className="profile-dropdown">
                <div className="profile-dropdown-header">
                  <div className="profile-dropdown-avatar">{iniciais}</div>
                  <div className="profile-dropdown-user">
                    <strong>{nomeUsuario}</strong>
                    <span>ID: {idCorretor}</span>
                  </div>
                </div>

                <button onClick={handleLogout} className="logout-button">
                  Sair
                </button>
                <button onClick={handleTrocarSenha} className="profile-menu-button">
                  Trocar senha
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
