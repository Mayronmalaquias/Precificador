import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import type { DateTimePickerEvent } from '@react-native-community/datetimepicker';

import { useToast } from '@/components/ui/toast';
import { useSession } from '@/features/auth/session';
import { mensagemErro } from '@/utils/erro';
import {
  buscarImoveis,
  carregarClientes,
  carregarLeads,
  criarCliente,
  criarVisita,
  uploadAnexo,
  type AnexoFile,
  type ClienteBusca,
  type ImovelBusca,
  type LeadBusca,
} from '@/features/visita/api';

export const NOTA_CAMPOS = [
  { field: 'localizacao', label: 'Localização' },
  { field: 'tamanho', label: 'Tamanho' },
  { field: 'planta', label: 'Planta do imóvel' },
  { field: 'acabamento', label: 'Qualidade do acabamento' },
  { field: 'conservacao', label: 'Estado de conservação' },
  { field: 'condominio', label: 'Condomínio e área comum' },
  { field: 'preco', label: 'Preço' },
  { field: 'notaGeral', label: 'Nota geral' },
] as const;

type NotaField = (typeof NOTA_CAMPOS)[number]['field'];
export type Notas = Record<NotaField, number>;

const NOTAS_INICIAIS: Notas = {
  localizacao: 10,
  tamanho: 10,
  planta: 10,
  acabamento: 10,
  conservacao: 10,
  condominio: 10,
  preco: 10,
  notaGeral: 10,
};

const norm = (v?: string) => String(v || '').trim().toLowerCase();
export const onlyDigits = (v?: string) => String(v || '').replace(/\D/g, '');
const todayISO = () => new Date().toISOString().split('T')[0];

/** Centavos digitados -> "1.234,56". Usada pelo campo de preço na tela. */
export function moedaFromDigits(digits: string): string {
  if (!digits) return '';
  return (Number(digits) / 100).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** "2026-09-14" -> "14/09/2026". */
export function isoToBR(iso: string): string {
  const [y, m, d] = iso.split('-');
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

/**
 * Estado e regras do formulário de visita.
 *
 * Separado da tela porque o componente tinha 747 linhas — 13% de todo o `src/` — e
 * misturava ~350 linhas de estado/validação/submit com ~270 de JSX. Aqui mora o que o
 * formulário FAZ; em `visita-form.tsx`, como ele APARECE.
 */
export function useVisitaForm() {
  const toast = useToast();
  const { user, nomeUsuario } = useSession();

  const corretor = useMemo(
    () => ({
      id: String(user?.id_usuarios || user?.id_corretor || ''),
      nome: nomeUsuario,
      username: String(user?.username || ''),
      telefone: String(user?.telefone || ''),
      instagram: String(user?.instagram || ''),
      descricao: String(user?.descricao || ''),
      email: String(user?.email || ''),
    }),
    [user, nomeUsuario],
  );

  // Imóvel
  const [situacaoImovel, setSituacaoImovel] = useState<'CAPTACAO_61' | 'IMOVEL_NAO_CAPTADO'>(
    'CAPTACAO_61',
  );
  const [parceiroExterno, setParceiroExterno] = useState<'NAO' | 'SIM'>('NAO');
  const [imovelId, setImovelId] = useState('');
  const [enderecoExterno, setEnderecoExterno] = useState('');
  const [enderecoQuery, setEnderecoQuery] = useState('');
  const [imoveisSugestoes, setImoveisSugestoes] = useState<ImovelBusca[]>([]);
  const [loadingImoveis, setLoadingImoveis] = useState(false);
  const [showImoveis, setShowImoveis] = useState(false);
  const [dataVisita, setDataVisita] = useState(todayISO());
  const [showDatePicker, setShowDatePicker] = useState(false);

  const isImovelNaoCaptado = situacaoImovel === 'IMOVEL_NAO_CAPTADO';

  // Cliente
  const [clienteNome, setClienteNome] = useState('');
  const [clienteTelefone, setClienteTelefone] = useState('');
  const [clienteEmail, setClienteEmail] = useState('');
  const [clientes, setClientes] = useState<ClienteBusca[]>([]);
  const [leads, setLeads] = useState<LeadBusca[]>([]);
  const [clienteSelecionado, setClienteSelecionado] = useState<ClienteBusca | null>(null);
  const [showClientes, setShowClientes] = useState(false);

  // Avaliações + proposta + anexo
  const [notas, setNotas] = useState<Notas>(NOTAS_INICIAIS);
  const [precoNota10, setPrecoNota10] = useState('');
  const [proposta, setProposta] = useState<'Sim' | 'Nao' | 'Talvez'>('Talvez');
  const [anexo, setAnexo] = useState<AnexoFile | null>(null);

  const [loading, setLoading] = useState(false);

  // Carrega clientes e leads do corretor no mount.
  useEffect(() => {
    if (!corretor.id) return;
    let active = true;
    (async () => {
      try {
        const [cs, ls] = await Promise.all([
          carregarClientes(corretor.id),
          carregarLeads(corretor.id),
        ]);
        if (active) {
          setClientes(cs);
          setLeads(ls);
        }
      } catch {
        // silencioso — buscas são auxiliares
      }
    })();
    return () => {
      active = false;
    };
  }, [corretor.id]);

  // Alterna captação; "não captado" fixa o código em "0000" (lógica no handler,
  // não em efeito, para não disparar setState síncrono durante render).
  function alterarSituacao(val: 'CAPTACAO_61' | 'IMOVEL_NAO_CAPTADO') {
    setSituacaoImovel(val);
    if (val === 'IMOVEL_NAO_CAPTADO') {
      setImovelId('0000');
      setEnderecoQuery('');
      setImoveisSugestoes([]);
      setShowImoveis(false);
    } else {
      setImovelId((prev) => (prev === '0000' ? '' : prev));
    }
  }

  // Busca de imóveis com debounce.
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (isImovelNaoCaptado || !showImoveis) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoadingImoveis(true);
      try {
        setImoveisSugestoes(await buscarImoveis(enderecoQuery));
      } catch {
        setImoveisSugestoes([]);
      } finally {
        setLoadingImoveis(false);
      }
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [enderecoQuery, showImoveis, isImovelNaoCaptado]);

  // Sugestões de cliente (filtro local) + status novo/existente.
  const clientesSugestoes = useMemo(() => {
    const termo = norm(clienteNome);
    if (!termo) return [];
    return clientes.filter((c) => norm(c.nome).includes(termo)).slice(0, 6);
  }, [clienteNome, clientes]);

  const leadsSugestoes = useMemo(() => {
    const termo = norm(clienteNome);
    const base = termo
      ? leads.filter((l) =>
          [l.cliente, l.telefone, l.codigo_imovel, l.fonte, l.contato].map(norm).join(' ').includes(termo),
        )
      : leads;
    return base.slice(0, 6);
  }, [clienteNome, leads]);

  // Status derivado (sem efeito): existente se há seleção ou match exato.
  const clienteStatus: 'NOVO' | 'EXISTENTE' = useMemo(() => {
    if (clienteSelecionado?.id_cliente) return 'EXISTENTE';
    const termo = norm(clienteNome);
    const tel = onlyDigits(clienteTelefone);
    if (!termo) return 'NOVO';
    const exato = clientes.find(
      (c) => norm(c.nome) === termo || (tel && onlyDigits(c.telefone) === tel),
    );
    return exato ? 'EXISTENTE' : 'NOVO';
  }, [clienteSelecionado, clienteNome, clienteTelefone, clientes]);

  function montarEndereco(item: ImovelBusca): string {
    return [item.endereco, item.numero, item.bairro, item.cidade ? `${item.cidade}${item.uf ? `/${item.uf}` : ''}` : '']
      .filter(Boolean)
      .join(', ');
  }
  function montarTitulo(item: ImovelBusca): string {
    return String(item.titulo || '').trim() || montarEndereco(item) || 'Imóvel encontrado';
  }

  function selecionarImovel(item: ImovelBusca) {
    const endereco = montarEndereco(item);
    const codigo = String(item.codigo || '');
    setImovelId(codigo);
    setEnderecoExterno(endereco || montarTitulo(item));
    setEnderecoQuery([codigo ? `Cod. ${codigo}` : '', montarTitulo(item)].filter(Boolean).join(' - '));
    setShowImoveis(false);
    setImoveisSugestoes([]);
  }

  function selecionarCliente(c: ClienteBusca) {
    setClienteSelecionado(c);
    setClienteNome(c.nome || '');
    setClienteTelefone(c.telefone || '');
    setClienteEmail(c.email || '');
    setShowClientes(false);
  }

  function selecionarLead(lead: LeadBusca) {
    const tel = onlyDigits(lead.telefone);
    const existente = clientes.find(
      (c) => norm(c.nome) === norm(lead.cliente) || (tel && onlyDigits(c.telefone) === tel),
    );
    const codigo = String(lead.codigo_imovel || '').trim();
    setClienteSelecionado(existente?.id_cliente ? existente : null);
    setClienteNome(existente?.nome || lead.cliente || '');
    setClienteTelefone(existente?.telefone || lead.telefone || '');
    setClienteEmail(existente?.email || clienteEmail);
    if (!isImovelNaoCaptado && codigo) {
      setImovelId(codigo);
      setEnderecoQuery(['Cod. ' + codigo, lead.fonte].filter(Boolean).join(' - '));
    }
    setShowClientes(false);
  }

  function onDateChange(event: DateTimePickerEvent, date?: Date) {
    if (Platform.OS === 'android') setShowDatePicker(false);
    if (event.type === 'set' && date) setDataVisita(date.toISOString().split('T')[0]);
  }

  async function escolherAnexo(origem: 'camera' | 'galeria') {
    try {
      const perm =
        origem === 'camera'
          ? await ImagePicker.requestCameraPermissionsAsync()
          : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        toast.show({ type: 'error', message: 'Permissão negada para acessar a mídia.' });
        return;
      }
      const result =
        origem === 'camera'
          ? await ImagePicker.launchCameraAsync({ quality: 0.6 })
          : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.6 });

      if (result.canceled || !result.assets?.[0]) return;
      const a = result.assets[0];
      const type = a.mimeType || 'image/jpeg';
      const name = a.fileName || `ficha_${Date.now()}.${type.includes('png') ? 'png' : 'jpg'}`;
      setAnexo({ uri: a.uri, name, type });
    } catch {
      toast.show({ type: 'error', message: 'Não foi possível abrir a câmera/galeria.' });
    }
  }

  function pedirAnexo() {
    Alert.alert('Anexar ficha', 'Escolha a origem da imagem', [
      { text: 'Câmera', onPress: () => escolherAnexo('camera') },
      { text: 'Galeria', onPress: () => escolherAnexo('galeria') },
      { text: 'Cancelar', style: 'cancel' },
    ]);
  }

  function resetForm() {
    setSituacaoImovel('CAPTACAO_61');
    setParceiroExterno('NAO');
    setImovelId('');
    setEnderecoExterno('');
    setEnderecoQuery('');
    setImoveisSugestoes([]);
    setShowImoveis(false);
    setDataVisita(todayISO());
    setClienteNome('');
    setClienteTelefone('');
    setClienteEmail('');
    setClienteSelecionado(null);
    setShowClientes(false);
    setNotas(NOTAS_INICIAIS);
    setPrecoNota10('');
    setProposta('Talvez');
    setAnexo(null);
  }

  async function criarClienteSeNecessario(): Promise<string> {
    const nome = clienteNome.trim();
    if (clienteStatus === 'EXISTENTE' && clienteSelecionado?.id_cliente) {
      return String(clienteSelecionado.id_cliente);
    }
    const id = await criarCliente({
      nome,
      telefone: clienteTelefone.trim(),
      email: clienteEmail.trim(),
      id_corretor: corretor.id,
      corretor_email: corretor.email,
    });
    return id ? String(id) : '';
  }

  const handleSubmit = useCallback(async () => {
    if (loading) return;

    // Validação (espelha o web).
    if (!isImovelNaoCaptado && !enderecoQuery.trim()) {
      toast.show({ type: 'error', message: 'Digite um endereço de imóvel.' });
      return;
    }
    if (isImovelNaoCaptado && !enderecoExterno.trim()) {
      toast.show({ type: 'error', message: 'Informe o endereço do imóvel.' });
      return;
    }
    if (!corretor.id) {
      toast.show({ type: 'error', message: 'Sessão inválida. Entre novamente.' });
      return;
    }
    if (!anexo) {
      toast.show({ type: 'error', message: 'Anexe uma foto ou PDF da ficha.' });
      return;
    }
    if (!clienteNome.trim()) {
      toast.show({ type: 'error', message: 'Informe o nome do cliente.' });
      return;
    }

    setLoading(true);
    let etapa = 'Cadastrar cliente';
    try {
      const idCliente = await criarClienteSeNecessario();
      etapa = 'Enviar ficha da visita';
      const { drivePath, driveLink } = await uploadAnexo({
        file: anexo,
        idCorretor: corretor.id,
        imovelId,
        dataVisita,
      });

      const payload = {
        imovelId: isImovelNaoCaptado ? '0000' : imovelId,
        dataVisita,
        parceiroExterno,
        situacaoImovel,
        clienteNome: clienteNome.trim(),
        clienteTelefone: clienteTelefone.trim(),
        clienteEmail: clienteEmail.trim(),
        proposta,
        papelVisita: 'Interessado',
        enderecoExterno: enderecoExterno || enderecoQuery,
        parceiroNome: '',
        parceiroImobiliaria: '',
        clienteAssinanteNome: '',
        clienteAssinanteTelefone: '',
        clienteAssinanteEmail: '',
        assinatura: '',
        audioDescricaoClienteVisita: '',
        linkAudio: '',
        ...notas,
        precoNota10: precoNota10 ? Number(precoNota10) / 100 : '',
        idCorretor: corretor.id,
        idCliente,
        anexoFichaVisita: drivePath,
        linkImagem: driveLink,
        corretor: corretor.nome || corretor.username,
        corretorEmail: corretor.email,
        telefoneCorretor: corretor.telefone,
        instagramCorretor: corretor.instagram,
        descricaoCorretor: corretor.descricao,
        avaliacoes: { ...notas },
      };

      etapa = 'Salvar visita';
      const idVisita = await criarVisita(payload);
      toast.show({ type: 'success', message: `Visita lançada! ID: ${idVisita}` });
      resetForm();
    } catch (err) {
      toast.show({ type: 'error', message: `${etapa}: ${mensagemErro(err, 'Não foi possível concluir a operação.')}` });
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    loading,
    isImovelNaoCaptado,
    enderecoQuery,
    enderecoExterno,
    corretor,
    anexo,
    clienteNome,
    clienteTelefone,
    clienteEmail,
    imovelId,
    dataVisita,
    parceiroExterno,
    situacaoImovel,
    proposta,
    notas,
    precoNota10,
    clienteStatus,
    clienteSelecionado,
  ]);


  return {
    alterarSituacao,
    anexo,
    clienteEmail,
    clienteNome,
    clienteStatus,
    clienteTelefone,
    clientesSugestoes,
    corretor,
    dataVisita,
    enderecoExterno,
    enderecoQuery,
    handleSubmit,
    imoveisSugestoes,
    imovelId,
    isImovelNaoCaptado,
    leadsSugestoes,
    loading,
    loadingImoveis,
    montarTitulo,
    notas,
    onDateChange,
    parceiroExterno,
    pedirAnexo,
    precoNota10,
    proposta,
    selecionarCliente,
    selecionarImovel,
    selecionarLead,
    setClienteEmail,
    setClienteNome,
    setClienteSelecionado,
    setClienteTelefone,
    setEnderecoExterno,
    setEnderecoQuery,
    setImovelId,
    setNotas,
    setParceiroExterno,
    setPrecoNota10,
    setProposta,
    setShowClientes,
    setShowDatePicker,
    setShowImoveis,
    showClientes,
    showDatePicker,
    showImoveis,
    situacaoImovel,
  };
}
