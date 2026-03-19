// Header.js
import { NavLink, useNavigate } from 'react-router-dom';
import '../assets/css/Header.css';

function Header() {
  const navigate = useNavigate();

  const isLogado = localStorage.getItem('auth') === 'true';
  const userData = JSON.parse(localStorage.getItem('userData') || '{}');
  const isAdmin = userData.grant === 'admin' || userData.permissao === 'admin';

  const handleLogout = () => {
    localStorage.removeItem('auth');
    localStorage.removeItem('userData');
    navigate('/login');
  };

  const getNavLinkClass = ({ isActive }) =>
    isActive ? 'nav-link active-link' : 'nav-link';

  return (
    <header>
      <h1>Inteligência Imobiliária 61</h1>

      <nav>
        <NavLink to="/" end className={getNavLinkClass}>
          Início
        </NavLink>

        {' | '}

        <NavLink to="/Experts" className={getNavLinkClass}>
          Experts
        </NavLink>

        {' | '}

        <NavLink to="/61Financiamento" className={getNavLinkClass}>
          61Financeiro
        </NavLink>

        {isLogado ? (
          <>
            {' | '}
            <NavLink to="/NovaVisita" className={getNavLinkClass}>
              Criar Visita
            </NavLink>

            {' | '}
            <NavLink to="/AppVisita" className={getNavLinkClass}>
              Relatório de Visita
            </NavLink>

            {isAdmin && (
              <>
                {' | '}
                <NavLink to="/RelatorioGerente" className={getNavLinkClass}>
                  Relatório Gerente
                </NavLink>

                {' | '}
                <NavLink to="/register" className={getNavLinkClass}>
                  Registrar Usuário
                </NavLink>
              </>
            )}

            {' | '}
            <button onClick={handleLogout} className="logout-button">
              Sair
            </button>
          </>
        ) : (
          <>
            {' | '}
            <NavLink to="/login" className={getNavLinkClass}>
              Login
            </NavLink>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;