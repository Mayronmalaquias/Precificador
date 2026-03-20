import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useRef, useState } from 'react';
import '../assets/css/Header.css';

function Header() {
  const navigate = useNavigate();
  const profileRef = useRef(null);
  const servicosRef = useRef(null);

  const [menuAberto, setMenuAberto] = useState(false);
  const [servicosAberto, setServicosAberto] = useState(false);

  const isLogado = localStorage.getItem('auth') === 'true';
  const userData = JSON.parse(localStorage.getItem('userData') || '{}');
  const isAdmin = userData.grant === 'admin' || userData.permissao === 'admin';

  const nomeUsuario =
    userData.nome ||
    userData.name ||
    userData.nomeCorretor ||
    userData.usuario ||
    'Usuário';

  const idCorretor =
    userData.idCorretor ||
    userData.id_corretor ||
    userData.id ||
    'Não informado';

  const iniciais = useMemo(() => {
    const partes = String(nomeUsuario).trim().split(' ').filter(Boolean);
    if (partes.length === 0) return 'U';
    if (partes.length === 1) return partes[0].slice(0, 1).toUpperCase();
    return `${partes[0][0]}${partes[1][0]}`.toUpperCase();
  }, [nomeUsuario]);

  const handleLogout = () => {
    localStorage.removeItem('auth');
    localStorage.removeItem('userData');
    navigate('/login');
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setMenuAberto(false);
      }

      if (servicosRef.current && !servicosRef.current.contains(event.target)) {
        setServicosAberto(false);
      }
    };

    const handleEsc = (event) => {
      if (event.key === 'Escape') {
        setMenuAberto(false);
        setServicosAberto(false);
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

  const servicos = [
    { to: '/', label: 'Início', end: true, show: true },
    { to: '/Experts', label: 'Experts', show: true },
    { to: '/61Financiamento', label: '61Financeiro', show: true },
    { to: '/NovaVisita', label: 'Criar Visita', show: isLogado },
    { to: '/AppVisita', label: 'Relatório de Visita', show: isLogado },
    { to: '/RelatorioGerente', label: 'Relatório Gerente', show: isLogado && isAdmin },
    { to: '/ranking', label: 'Ranking', show: isLogado && isAdmin },
    { to: '/register', label: 'Registrar Usuário', show: isLogado && isAdmin },
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
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          {!isLogado && (
            <NavLink to="/login" className={getNavLinkClass}>
              Login
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
                    <span>ID Corretor: {idCorretor}</span>
                  </div>
                </div>

                <button onClick={handleLogout} className="logout-button">
                  Sair
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