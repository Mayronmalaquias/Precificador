import { Link, useNavigate } from 'react-router-dom';

function Header() {
  const navigate = useNavigate();
  const isLogado = localStorage.getItem('auth') === 'true';

  const handleLogout = () => {
    localStorage.removeItem('auth');
    navigate('/login');
  };

  return (
    <header>
      <h1>Inteligência Imobiliária 61</h1>
      <nav>
        <Link to="/">Início</Link>
        {isLogado ? (
          <>
            {' | '}
            <Link to="/interno">Acessar Página</Link>
            {' | '}
            <button onClick={handleLogout}>Sair</button>
          </>
        ) : (
          <>
            {' | '}
            <Link to="/login">Login</Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;
