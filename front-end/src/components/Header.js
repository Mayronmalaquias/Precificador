// Header.js
import { NavLink, useNavigate } from 'react-router-dom'; // Alterado Link para NavLink

function Header() {
  const navigate = useNavigate();
  const isLogado = localStorage.getItem('auth') === 'true';

  const handleLogout = () => {
    localStorage.removeItem('auth');
    navigate('/login');
  };

  // Função para determinar a classe do NavLink
  const getNavLinkClass = ({ isActive }) => {
    return isActive ? 'nav-link active-link' : 'nav-link';
  };

  return (
    <header>
      <h1>Inteligência Imobiliária 61</h1>
      <nav>
        <NavLink to="/" end className={getNavLinkClass}> {/* Adicionado 'end' para correspondência exata */}
          Início
        </NavLink>
        {isLogado ? (
          <>
            {' | '}
            <NavLink to="/interno" className={getNavLinkClass}>
              Acessar Página
            </NavLink>
            {' | '}
            <button onClick={handleLogout} className="logout-button">Sair</button> {/* Adicionada classe para estilização específica se necessário */}
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