// Header.js
import { NavLink, useNavigate } from 'react-router-dom';
import '../assets/css/Header.css';

function Header() {
  const navigate = useNavigate();
  
  // 1. Verificações de estado vindas do localStorage
  const isLogado = localStorage.getItem('auth') === 'true';
  
  // 2. Recuperar os dados do usuário para checar a permissão
  const userData = JSON.parse(localStorage.getItem('userData') || '{}');
  const isAdmin = userData.grant === 'admin' || userData.permissao === 'admin';

  const handleLogout = () => {
    localStorage.removeItem('auth');
    localStorage.removeItem('userData'); // Limpa os dados do usuário também
    navigate('/login');
  };

  const getNavLinkClass = ({ isActive }) => {
    return isActive ? 'nav-link active-link' : 'nav-link';
  };

  return (
    <header>
      <h1>Inteligência Imobiliária 61</h1>
      <nav>
        <NavLink to="/" end className={getNavLinkClass}>
          Início
        </NavLink>
        
        {isLogado ? (
          <>
            {' | '}
            <NavLink to="/interno" className={getNavLinkClass}>
              Acessar Página
            </NavLink>
            <NavLink to="/NovaVisita" className={getNavLinkClass}>
              Criar Visita
            </NavLink>
            <NavLink to="/AppVisita" className={getNavLinkClass}>
              Relatorio de Visita
            </NavLink>

            {/* 3. Condicional para mostrar o Registro apenas para Admins */}
            {isAdmin && (
              <>
                {' | '}
                <NavLink to="/register" className={getNavLinkClass}>
                  Registrar Usuário
                </NavLink>
              </>
            )}

            {' | '}
            <button onClick={handleLogout} className="logout-button">Sair</button>
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