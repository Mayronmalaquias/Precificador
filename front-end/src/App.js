// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Tabs from './components/Tabs';
import Login from './components/Login';
import ReporteImovel from './components/ReporteImovelWidget'
import PrivateRoute from './auth/PrivateRoute';
import PaginaPublica from './components/FormularioPublico';
// em App.js ou Tabs.js
import './assets/css/styles.css';
import './assets/css/report.css';
import './assets/css/map.css';
import './assets/css/footer.css';
import './assets/css/chat.css';

function App() {
  return (
    <Router>
      <div className="page">
        <Header />
        <main>
          <Routes>
            <Route
              path="/interno"
              element={
                <PrivateRoute>
                  <Tabs />
                </PrivateRoute>
              }
            />
            <Route path="/" element={
                <PaginaPublica />
              }
            />
            <Route path="/login" element={<Login />} />
            <Route path="/verificarImovel" element={<ReporteImovel />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
