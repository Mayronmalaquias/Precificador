// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Tabs from './components/Tabs';
import Login from './components/Login';
import Register from './components/Register';
import ReporteImovel from './components/ReporteImovelWidget';
import PrivateRoute from './auth/PrivateRoute';
import AdminRoute from './auth/AdminRoute';
import PaginaPublica from './components/FormularioPublico';
import FormVisita from './components/FormVisita';
import AppVisita from './components/FormVisitaApp';
import NovaVisita from './components/NovaVisita';
import Experts from './components/Experts';
import Ranking from './components/Ranking';
import FormComissao from './components/FormComissao';
import Financiamento from './components/CalculoFinanciamento';
import RelatorioGerente from './components/RelatorioGerente';

import './assets/css/styles.css';
import './assets/css/report.css';
import './assets/css/map.css';
import './assets/css/footer.css';
import './assets/css/chat.css';
import './assets/css/FormVisita.css';

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

            <Route path="/" element={<PaginaPublica />} />
            <Route path="/login" element={<Login />} />
            <Route path="/Experts" element={<Experts />} />
            <Route path="/61Financiamento" element={<Financiamento />} />

            <Route path="/verificarImovel" element={<ReporteImovel />} />
            <Route path="/enviarVisita" element={<FormVisita />} />
            <Route path="/Ranking" element={<Ranking />} />
            <Route path="/FormComissao" element={<FormComissao />} />

            <Route
              path="/AppVisita"
              element={
                <PrivateRoute>
                  <AppVisita />
                </PrivateRoute>
              }
            />

            <Route
              path="/NovaVisita"
              element={
                <PrivateRoute>
                  <NovaVisita />
                </PrivateRoute>
              }
            />

            <Route
              path="/register"
              element={
                <AdminRoute>
                  <Register />
                </AdminRoute>
              }
            />

            <Route
              path="/RelatorioGerente"
              element={
                <AdminRoute>
                  <RelatorioGerente />
                </AdminRoute>
              }
            />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;