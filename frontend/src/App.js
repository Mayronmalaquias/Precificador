// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { EquipesProvider } from './context/EquipesContext';
import './assets/css/design-system.css';
import './assets/css/Toast.css';
import Header from './components/Header';
import Footer from './components/Footer';
import Tabs from './components/Tabs';
import Login from './components/Login';
import Register from './components/Register';
import ReporteImovel from './components/ReporteImovelWidget';
import PrivateRoute from './auth/PrivateRoute';
import AdminRoute from './auth/AdminRoute';
import AdministradorRoute from './auth/AdministradorRoute';
import AssistenteRoute from './auth/AssistenteRoute';
import DiretorRoute from './auth/DiretorRoute';
import PropostasRoute from './auth/PropostasRoute';
import GerenteOperacionalRoute from './auth/GerenteOperacionalRoute';
import VendasRoute from './auth/VendasRoute';
import PaginaPublica from './components/FormularioPublico';
import FormVisita from './components/FormVisita';
import AppVisita from './components/FormVisitaApp';
import NovaVisita from './components/NovaVisita';
import Experts from './components/Experts';
import Parcerias from './components/Parcerias';
import Ranking from './components/Ranking';
import FormComissao from './components/FormComissao';
import Financiamento from './components/CalculoFinanciamento';
import RelatorioGerente from './components/RelatorioGerente';
import RecuperarSenha from './components/RecuperarSenha';
import TrocarSenha from './components/TrocarSenha'
import ControleCorretor from './components/ControleCorretor'
import JornadaCaptacao from './components/JornadaCaptacao'
import GestaoClientesVisitas from './components/GestaoClientesVisitas'
import RHUsuarios from './components/RHUsuarios'
import GerenciarEquipes from './components/GerenciarEquipes'
import AdminBases from './components/AdminBases'
import Vendas from './components/Vendas'
import GerenteRHCorretores from './components/GerenteRHCorretores'
import LancarImovel from './components/LancarImovel'
import VisaoDiretor from './components/VisaoDiretor'
import PropostasEfetivas from './components/PropostasEfetivas'
import GestaoLeads from './components/GestaoLeads'
import GestaoVisitas from './components/GestaoVisitas'
import Tarefas from './components/Tarefas'
import ConsultaImoveis from './components/ConsultaImoveis'

import './assets/css/styles.css';
import './assets/css/report.css';
import './assets/css/map.css';
// footer.css (rodapé rosa centralizado) foi substituído pelo `.site-footer` de
// footerPaginaUnica.css. Ficava no bundle pintando de rosa qualquer <footer> sem classe —
// o rodapé do modal de Propostas Efetivas, por exemplo.
import './assets/css/chat.css';
import './assets/css/FormVisita.css';

function App() {
  return (
    <AuthProvider>
      <EquipesProvider>
      <ToastProvider>
        <Router>
          <div className="page">
            <Header />
            <main>
              <Routes>
                <Route
                  path="/interno"
                  element={<PrivateRoute><Tabs /></PrivateRoute>}
                />
                <Route
                  path="/TrocarSenha"
                  element={<PrivateRoute><TrocarSenha /></PrivateRoute>}
                />

                <Route path="/" element={<PaginaPublica />} />
                <Route path="/login" element={<Login />} />
                <Route path="/RecuperarSenha" element={<RecuperarSenha />} />
                <Route path="/Experts" element={<Experts />} />
                <Route
                  path="/Parcerias"
                  element={<PrivateRoute><Parcerias /></PrivateRoute>}
                />
                <Route path="/61Financiamento" element={<Financiamento />} />
                <Route path="/verificarImovel" element={<ReporteImovel />} />
                <Route path="/enviarVisita" element={<FormVisita />} />
                <Route path="/FormComissao" element={<FormComissao />} />
                <Route
                  path="/Ranking"
                  element={<PrivateRoute><Ranking /></PrivateRoute>}
                />
                <Route
                  path="/AppVisita"
                  element={<PrivateRoute><AppVisita /></PrivateRoute>}
                />
                <Route
                  path="/NovaVisita"
                  element={<PrivateRoute><NovaVisita /></PrivateRoute>}
                />
                <Route
                  path="/register"
                  element={<AssistenteRoute><Register /></AssistenteRoute>}
                />
                <Route
                  path="/RelatorioGerente"
                  element={<AdminRoute><RelatorioGerente /></AdminRoute>}
                />
                <Route
                  path="/VisaoDiretor"
                  element={<DiretorRoute><VisaoDiretor /></DiretorRoute>}
                />
                <Route
                  path="/ConsultaImoveis"
                  element={<PropostasRoute><ConsultaImoveis /></PropostasRoute>}
                />
                <Route
                  path="/PropostasEfetivas"
                  element={<PropostasRoute><PropostasEfetivas /></PropostasRoute>}
                />
                {/* Módulos de gestão. Leads e Visitas usam o mesmo recorte do Relatório
                    do Gerente (AdminRoute); o hub de Tarefas vale para quem tem equipe
                    ou enxerga tudo, e o próprio serviço corta o escopo. */}
                <Route
                  path="/GestaoLeads"
                  element={<AdminRoute><GestaoLeads /></AdminRoute>}
                />
                <Route
                  path="/GestaoVisitas"
                  element={<AdminRoute><GestaoVisitas /></AdminRoute>}
                />
                <Route
                  path="/Tarefas"
                  element={<PrivateRoute><Tarefas /></PrivateRoute>}
                />
                <Route
                  path="/ControleCorretor"
                  element={<AdministradorRoute><ControleCorretor /></AdministradorRoute>}
                />
                <Route
                  path="/RHUsuarios"
                  element={<AdministradorRoute><RHUsuarios /></AdministradorRoute>}
                />
                <Route
                  path="/GerenciarEquipes"
                  element={<AdministradorRoute><GerenciarEquipes /></AdministradorRoute>}
                />
                <Route
                  path="/LancarImovel"
                  element={<AssistenteRoute><LancarImovel /></AssistenteRoute>}
                />
                <Route
                  path="/GerenteRH"
                  element={<GerenteOperacionalRoute><GerenteRHCorretores /></GerenteOperacionalRoute>}
                />
                <Route
                  path="/AdminBases"
                  element={<AdministradorRoute><AdminBases /></AdministradorRoute>}
                />
                <Route
                  path="/Vendas"
                  element={<VendasRoute><Vendas /></VendasRoute>}
                />
                <Route
                  path="/JornadaCaptacao"
                  element={<PrivateRoute><JornadaCaptacao /></PrivateRoute>}
                />
                <Route
                  path="/GestaoClientes"
                  element={<PrivateRoute><GestaoClientesVisitas /></PrivateRoute>}
                />
              </Routes>
            </main>
            <Footer />
          </div>
        </Router>
      </ToastProvider>
      </EquipesProvider>
    </AuthProvider>
  );
}

export default App;
