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
        // animateUpdate('mtrMediaVenda', `Metragem Média de Venda: ${data.metragemMediaVenda}`);
        // animateUpdate('coeficienteVar', `Coeficiente de Variação de Venda: ${data.coeficienteVariacaoVenda}`);
        // animateUpdate('tamAmostra', `Tamanho da Amostra de Venda: ${data.tamanhoAmostraVenda}`);
        animateUpdate('vlrM2Loc', `Valor de M² de Locação: ${data.valorM2Locacao}`);
        animateUpdate('vlrLocacaoNominal', `Valor de Locação Nominal: ${data.valorLocacaoNominal}`);
        // animateUpdate('mtrMediaLoc', `Metragem Média de Locação: ${data.metragemMediaLocacao}`);
        // animateUpdate('coeficienteVarLoc', `Coeficiente de Variação de Locação: ${data.coeficienteVariacaoLocacao}`);
        // animateUpdate('tamAmostraLoc', `Tamanho da Amostra de Locação: ${data.tamanhoAmostraLocacao}`);
        animateUpdate('Rentabilidade', `Rentabilidade Média: ${data.rentabilidadeMedia}`);
        
        // Atualiza o mapa chamando a função de carregamento do mapa
        console.log("MIRON HEHE");
        console.log(document.getElementById('outCluster').value);
        // carregarMapa(document.getElementById('map-selector').value,document.getElementById('outCluster').value, document.getElementById('mapOption').value);
    })
    .catch(error => {
        console.error('Erro:', error);
        alert("Amostra insuficiente para análise");
    });
}

// Função para carregar o mapa via AJAX
// Função para carregar o mapa via AJAX com o tipo de mapa selecionado
function carregarMapa(tipoMapa, cluster, tamanho_mapa) {
    // Exibir o spinner antes de carregar o mapa
    const clusterTemp = cluster ?? 5;
    const clusterElement = document.getElementById('nrCluster'); // Assumindo que o elemento tem o ID 'cluster'
    const clusterOutput = document.getElementById('outCluster');

    if (clusterElement) {
        clusterElement.value = clusterTemp;
        clusterOutput.value = clusterTemp // Atualiza o valor exibido para o cluster selecionado
    }
    document.getElementById('loading').style.display = 'flex'; 
    document.getElementById('map').style.display = 'none'; 

    fetch(`/carregar_mapa?tipo=${tipoMapa}&cluster=${clusterTemp}&tamanho=${tamanho_mapa}`)
        .then(response => response.text())
        .then(data => {
            // Inserir o mapa no contêiner e esconder o spinner de carregamento
            document.getElementById('map').innerHTML = data;
            document.getElementById('loading').style.display = 'none';  // Esconder o spinner
            document.getElementById('map').style.display = 'block';     // Mostrar o mapa
        })
        .catch(error => {
            console.error('Erro ao carregar o mapa:', error);
            alert("Erro ao carregar o mapa.");
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
    carregarMapa(); // Carregar o mapa inicialmente ao carregar a página
});

document.getElementById('map-selector').addEventListener('change', function() {
    carregarMapa(document.getElementById('map-selector').value,document.getElementById('outCluster').value, document.getElementById('mapOption').value);
});

document.getElementById('mapOption').addEventListener('change', function() {
    carregarMapa(document.getElementById('map-selector').value,document.getElementById('outCluster').value, document.getElementById('mapOption').value);
});

function alterarCluster(valor) {
    console.log("chegou aqui");

    // Atualiza o valor do cluster
    document.getElementById('nrCluster').value = parseInt(valor); // Atualiza o valor do campo de entrada
    document.getElementById('outCluster').value = parseInt(valor); // Atualiza o valor do output
    submitOnChange()
    // Submete o formulário
    // document.getElementById('formularioAnalise').submit(); 
}
