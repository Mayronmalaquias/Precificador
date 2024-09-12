function submitOnChange() {
    const formData = new FormData(document.getElementById('formularioAnalise'));
    const formObject = Object.fromEntries(formData.entries());

    fetch('/analisar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: new URLSearchParams(formObject)
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            return response.json().then(err => { throw new Error(err.error || "Erro desconhecido"); });
        }
    })
    .then(data => {
        // Animação para atualização suave dos valores
        animateUpdate('vlrM2Venda', `Valor de M² de Venda: ${data.valorM2Venda}`);
        animateUpdate('vlrVendaNominal', `Valor de Venda Nominal: ${data.valorVendaNominal}`);
        animateUpdate('mtrMediaVenda', `Metragem Média de Venda: ${data.metragemMediaVenda}`);
        animateUpdate('coeficienteVar', `Coeficiente de Variação de Venda: ${data.coeficienteVariacaoVenda}`);
        animateUpdate('tamAmostra', `Tamanho da Amostra de Venda: ${data.tamanhoAmostraVenda}`);
        animateUpdate('vlrM2Loc', `Valor de M² de Locação: ${data.valorM2Locacao}`);
        animateUpdate('vlrLocacaoNominal', `Valor de Locação Nominal: ${data.valorLocacaoNominal}`);
        animateUpdate('mtrMediaLoc', `Metragem Média de Locação: ${data.metragemMediaLocacao}`);
        animateUpdate('coeficienteVarLoc', `Coeficiente de Variação de Locação: ${data.coeficienteVariacaoLocacao}`);
        animateUpdate('tamAmostraLoc', `Tamanho da Amostra de Locação: ${data.tamanhoAmostraLocacao}`);
        animateUpdate('Rentabilidade', `Rentabilidade Média: ${data.rentabilidadeMedia}`);
    })
    .catch(error => {
        console.error('Erro:', error);
        alert("Amostra insuficiente para analise");
    });
}

// Animação suave de atualização
function animateUpdate(elementId, newText) {
    const element = document.getElementById(elementId);
    element.style.opacity = 0;
    setTimeout(() => {
        element.innerText = newText;
        element.style.opacity = 1;
    }, 300);
}

document.addEventListener('DOMContentLoaded', function() {
    submitOnChange();
});