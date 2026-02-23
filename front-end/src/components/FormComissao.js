import React, { useState, useEffect } from 'react';
import '../assets/css/formComissao.css';

function DivisaoComissao() {
  const API_BASE = '/api';
  // const API_BASE = 'http://localhost:5000';

  const emptyLine = { nome_corretor: '', id_corretor: '', percentual: '', observacao: '' };

  const [formData, setFormData] = useState({
    id_contrato: '',
    venda: [{ ...emptyLine }],
    captacao: [{ ...emptyLine }],
  });

  const [loading, setLoading] = useState(false);

  // contratos 2026
  const [contratos, setContratos] = useState([]);
  const [loadingContratos, setLoadingContratos] = useState(false);

  // corretores
  const [corretores, setCorretores] = useState([]);
  const [loadingCorretores, setLoadingCorretores] = useState(false);

  useEffect(() => {
    fetchContratos2026();
    fetchCorretores();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchContratos2026 = async () => {
    try {
      setLoadingContratos(true);

      // ✅ SEM /divisao (como você pediu)
      const response = await fetch(`${API_BASE}/contratos-2026`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();

      if (response.ok) {
        setContratos(Array.isArray(data.contratos) ? data.contratos : []);
      } else {
        alert(data.error || 'Erro ao carregar contratos de 2026.');
      }
    } catch (error) {
      console.error('Erro ao buscar contratos:', error);
      alert('Erro de conexão ao carregar contratos.');
    } finally {
      setLoadingContratos(false);
    }
  };

  const fetchCorretores = async () => {
    try {
      setLoadingCorretores(true);

      // ✅ SEM /divisao (como você pediu)
      const response = await fetch(`${API_BASE}/corretores`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await response.json();

      if (response.ok) {
        setCorretores(Array.isArray(data.corretores) ? data.corretores : []);
      } else {
        alert(data.error || 'Erro ao carregar corretores.');
      }
    } catch (error) {
      console.error('Erro ao buscar corretores:', error);
      alert('Erro de conexão ao carregar corretores.');
    } finally {
      setLoadingCorretores(false);
    }
  };

  const setContrato = (e) => {
    setFormData((prev) => ({ ...prev, id_contrato: e.target.value }));
  };

  const handleLineChange = (tipo, index, field, value) => {
    setFormData((prev) => {
      const arr = [...prev[tipo]];
      arr[index] = { ...arr[index], [field]: value };
      return { ...prev, [tipo]: arr };
    });
  };

  // ✅ fallback: id_corretor OU IdCorretor | nome_corretor OU Nome
  const getCorretorId = (c) => String(c?.id_corretor ?? c?.IdCorretor ?? '').trim();
  const getCorretorNome = (c) => String(c?.nome_corretor ?? c?.Nome ?? '').trim();

  const handleSelectCorretor = (tipo, index, selectedId) => {
    const sel = String(selectedId || '').trim();

    const selected = corretores.find((c) => getCorretorId(c) === sel);

    const nome = selected ? getCorretorNome(selected) : '';
    const id = selected ? getCorretorId(selected) : '';

    setFormData((prev) => {
      const arr = [...prev[tipo]];
      arr[index] = { ...arr[index], id_corretor: id, nome_corretor: nome };
      return { ...prev, [tipo]: arr };
    });
  };

  const addLine = (tipo) => {
    setFormData((prev) => ({
      ...prev,
      [tipo]: [...prev[tipo], { ...emptyLine }],
    }));
  };

  const removeLine = (tipo, index) => {
    setFormData((prev) => {
      const arr = prev[tipo].filter((_, i) => i !== index);
      return { ...prev, [tipo]: arr.length ? arr : [{ ...emptyLine }] };
    });
  };

  const sumPercent = (tipo) => {
    return formData[tipo].reduce((acc, l) => {
      const v = Number(String(l.percentual).replace(',', '.'));
      return acc + (Number.isNaN(v) ? 0 : v);
    }, 0);
  };

  const validate = () => {
    if (!formData.id_contrato.trim()) {
      alert('Selecione um contrato.');
      return false;
    }

    const vendaValid = formData.venda.filter((l) => String(l.nome_corretor).trim() && String(l.percentual).trim());
    const captValid = formData.captacao.filter((l) => String(l.nome_corretor).trim() && String(l.percentual).trim());

    if (vendaValid.length === 0 && captValid.length === 0) {
      alert('Adicione pelo menos 1 linha em VENDA ou CAPTAÇÃO.');
      return false;
    }

    const somaVenda = sumPercent('venda');
    const somaCapt = sumPercent('captacao');

    if (vendaValid.length > 0 && Math.abs(somaVenda - 100) > 0.0001) {
      alert(`A soma dos percentuais de VENDA deve ser 100. Atual: ${somaVenda.toFixed(2)}`);
      return false;
    }

    if (captValid.length > 0 && Math.abs(somaCapt - 100) > 0.0001) {
      alert(`A soma dos percentuais de CAPTAÇÃO deve ser 100. Atual: ${somaCapt.toFixed(2)}`);
      return false;
    }

    const checkLines = (tipo, label) => {
      for (let i = 0; i < formData[tipo].length; i++) {
        const l = formData[tipo][i];
        const nome = String(l.nome_corretor).trim();
        const perc = Number(String(l.percentual).replace(',', '.'));

        if (!nome && !String(l.percentual).trim()) continue;

        if (!nome) {
          alert(`${label} linha ${i + 1}: Nome do corretor é obrigatório.`);
          return false;
        }
        if (Number.isNaN(perc) || perc <= 0 || perc > 100) {
          alert(`${label} linha ${i + 1}: Percentual inválido (0-100).`);
          return false;
        }
      }
      return true;
    };

    if (!checkLines('venda', 'VENDA')) return false;
    if (!checkLines('captacao', 'CAPTAÇÃO')) return false;

    return true;
  };

  const buildPayload = () => {
    const linhas = [];

    formData.venda.forEach((l) => {
      const nome = String(l.nome_corretor).trim();
      const percStr = String(l.percentual).trim();
      if (!nome || !percStr) return;

      linhas.push({
        papel: 'VENDA',
        id_corretor: String(l.id_corretor || '').trim(),
        nome_corretor: nome,
        percentual: Number(percStr.replace(',', '.')),
        observacao: String(l.observacao || '').trim(),
      });
    });

    formData.captacao.forEach((l) => {
      const nome = String(l.nome_corretor).trim();
      const percStr = String(l.percentual).trim();
      if (!nome || !percStr) return;

      linhas.push({
        papel: 'CAPTACAO',
        id_corretor: String(l.id_corretor || '').trim(),
        nome_corretor: nome,
        percentual: Number(percStr.replace(',', '.')),
        observacao: String(l.observacao || '').trim(),
      });
    });

    return { id_contrato: String(formData.id_contrato).trim(), linhas };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    const payload = buildPayload();

    try {
      setLoading(true);

      // POST mantém seu endpoint atual
      const response = await fetch(`${API_BASE}/divisao-comissao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Divisão salva! Linhas inseridas: ${data.linhas_inseridas}`);
      } else {
        alert(data.error || 'Erro ao salvar divisão.');
      }
    } catch (error) {
      console.error('Erro na requisição:', error);
      alert('Erro de conexão com o servidor.');
    } finally {
      setLoading(false);
    }
  };

  const somaVenda = sumPercent('venda');
  const somaCapt = sumPercent('captacao');

  const renderLinha = (tipo, idx, l) => {
    const selectedId = String(l.id_corretor || '').trim();

    return (
      <div key={`${tipo}-${idx}`} className="dc__line">
        <select
          className="dc__control dc__control--select"
          value={selectedId}
          onChange={(e) => handleSelectCorretor(tipo, idx, e.target.value)}
        >
          <option value="">
            {loadingCorretores ? 'Carregando corretores...' : 'Selecione o corretor'}
          </option>

          {corretores.map((c) => {
            const id = getCorretorId(c);
            const nome = getCorretorNome(c);
            if (!id || !nome) return null;

            return (
              <option key={id} value={id}>
                {nome} ({id})
              </option>
            );
          })}
        </select>

        <input
          className="dc__control"
          type="text"
          placeholder="Id"
          value={l.id_corretor}
          onChange={(e) => handleLineChange(tipo, idx, 'id_corretor', e.target.value)}
          title="Você pode digitar manualmente, mas o ideal é selecionar no dropdown"
        />

        <input
          className="dc__control dc__control--perc"
          type="text"
          placeholder="%"
          value={l.percentual}
          onChange={(e) => handleLineChange(tipo, idx, 'percentual', e.target.value)}
        />

        <input
          className="dc__control"
          type="text"
          placeholder="Observação (opcional)"
          value={l.observacao}
          onChange={(e) => handleLineChange(tipo, idx, 'observacao', e.target.value)}
        />

        <button
          className="dc__btn dc__btn--danger"
          type="button"
          onClick={() => removeLine(tipo, idx)}
          title="Remover"
        >
          –
        </button>

        <input type="hidden" value={l.nome_corretor} readOnly />
      </div>
    );
  };

  return (
    <div className="divLogin dc" style={{ maxWidth: 980 }}>
      <h2>Divisão de Comissão (VGC)</h2>

      <form className="dc__form" onSubmit={handleSubmit}>
        <select className="dc__select" name="id_contrato" value={formData.id_contrato} onChange={setContrato} required>
          <option value="">
            {loadingContratos ? 'Carregando contratos de 2026...' : 'Selecione o contrato (2026)'}
          </option>

          {contratos.map((c) => {
            const id = String(c?.Id_Contrato ?? c?.id_contrato ?? '').trim();
            const display = String(c?.display ?? c?.Display ?? id).trim();
            if (!id) return null;

            return (
              <option key={id} value={id}>
                {display}
              </option>
            );
          })}
        </select>

        {/* VENDA */}
        <div className="dc__section">
          <div className="dc__sectionHead">
            <h3 className="dc__sectionTitle">VENDA</h3>
            <div className={`dc__sum ${Math.abs(somaVenda - 100) < 0.0001 ? 'is-ok' : 'is-warn'}`}>
              Soma %: <strong>{somaVenda.toFixed(2)}</strong>
            </div>
          </div>

          <div className="dc__gridHead">
            <span>Corretor</span>
            <span>ID</span>
            <span>%</span>
            <span>Observação</span>
            <span></span>
          </div>

          {formData.venda.map((l, idx) => renderLinha('venda', idx, l))}

          <button className="dc__btn dc__btn--ghost" type="button" onClick={() => addLine('venda')}>
            + Adicionar linha (VENDA)
          </button>
        </div>

        {/* CAPTAÇÃO */}
        <div className="dc__section">
          <div className="dc__sectionHead">
            <h3 className="dc__sectionTitle">CAPTAÇÃO</h3>
            <div className={`dc__sum ${Math.abs(somaCapt - 100) < 0.0001 ? 'is-ok' : 'is-warn'}`}>
              Soma %: <strong>{somaCapt.toFixed(2)}</strong>
            </div>
          </div>

          <div className="dc__gridHead">
            <span>Corretor</span>
            <span>ID</span>
            <span>%</span>
            <span>Observação</span>
            <span></span>
          </div>

          {formData.captacao.map((l, idx) => renderLinha('captacao', idx, l))}

          <button className="dc__btn dc__btn--ghost" type="button" onClick={() => addLine('captacao')}>
            + Adicionar linha (CAPTAÇÃO)
          </button>
        </div>

        <button className="dc__btn dc__btn--primary" type="submit" disabled={loading}>
          {loading ? 'Salvando...' : 'Salvar Divisão'}
        </button>
      </form>
    </div>
  );
}

export default DivisaoComissao;