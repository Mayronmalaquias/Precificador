import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Platform, Pressable, StyleSheet, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import DateTimePicker, {
  type DateTimePickerEvent,
} from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { ChipSelect } from '@/components/ui/chip-select';
import { NotaSelector } from '@/components/ui/nota-selector';
import { Screen } from '@/components/ui/screen';
import { SectionCard } from '@/components/ui/section-card';
import { TextField } from '@/components/ui/text-field';
import { useToast } from '@/components/ui/toast';
import { ThemedText } from '@/components/themed-text';
import { useSession } from '@/features/auth/session';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
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

const NOTA_CAMPOS = [
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
type Notas = Record<NotaField, number>;

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
const onlyDigits = (v?: string) => String(v || '').replace(/\D/g, '');
const todayISO = () => new Date().toISOString().split('T')[0];

function moedaFromDigits(digits: string): string {
  if (!digits) return '';
  return (Number(digits) / 100).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function isoToBR(iso: string): string {
  const [y, m, d] = iso.split('-');
  return y && m && d ? `${d}/${m}/${y}` : iso;
}

export function VisitaForm() {
  const { colors } = useAppTheme();
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
    try {
      const idCliente = await criarClienteSeNecessario();
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

      const idVisita = await criarVisita(payload);
      toast.show({ type: 'success', message: `Visita lançada! ID: ${idVisita}` });
      resetForm();
    } catch (err: any) {
      toast.show({ type: 'error', message: err?.message || 'Erro inesperado. Tente novamente.' });
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

  return (
    <Screen scroll keyboardAvoiding edges={['top']}>
      <ThemedText style={[Typography.h1, { color: colors.text }]}>Criar visita</ThemedText>

      {/* Corretor */}
      <SectionCard title="Corretor" icon="person-outline">
        <View style={[styles.readonly, { backgroundColor: colors.surfaceAlt }]}>
          <Ionicons name="id-card-outline" size={18} color={colors.textMuted} />
          <ThemedText style={[Typography.body, { color: colors.text, flex: 1 }]} numberOfLines={1}>
            {corretor.id ? `${corretor.id} — ` : ''}
            {corretor.nome || corretor.username || 'Não identificado'}
          </ThemedText>
        </View>
      </SectionCard>

      {/* Imóvel */}
      <SectionCard title="Imóvel" icon="home-outline">
        <ChipSelect
          label="É captação 61?"
          options={[
            { label: 'Sim', value: 'CAPTACAO_61' },
            { label: 'Não', value: 'IMOVEL_NAO_CAPTADO' },
          ]}
          value={situacaoImovel}
          onChange={(v) => alterarSituacao(v as typeof situacaoImovel)}
        />
        <ChipSelect
          label="Tem parceiro externo na visita?"
          options={[
            { label: 'Não', value: 'NAO' },
            { label: 'Sim', value: 'SIM' },
          ]}
          value={parceiroExterno}
          onChange={(v) => setParceiroExterno(v as typeof parceiroExterno)}
        />

        {!isImovelNaoCaptado ? (
          <View style={{ gap: Spacing.two }}>
            <TextField
              label="Endereço do imóvel"
              icon="search-outline"
              placeholder="Ex: SQS 308, W3, Rua 12..."
              value={enderecoQuery}
              onChangeText={(t) => {
                setEnderecoQuery(t);
                setShowImoveis(true);
              }}
              onFocus={() => setShowImoveis(true)}
              autoCorrect={false}
            />
            {loadingImoveis && (
              <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
                Buscando imóveis...
              </ThemedText>
            )}
            {showImoveis && imoveisSugestoes.length > 0 && (
              <View style={[styles.dropdown, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}>
                {imoveisSugestoes.map((it) => (
                  <Pressable
                    key={`${it.codigo}-${it.finalidade || ''}`}
                    onPress={() => selecionarImovel(it)}
                    style={styles.suggestion}>
                    <ThemedText style={[Typography.label, { color: colors.text }]}>
                      {it.codigo ? `Cod. ${it.codigo}` : 'Sem código'}
                      {it.finalidade ? ` · ${it.finalidade}` : ''}
                    </ThemedText>
                    <ThemedText style={[Typography.caption, { color: colors.textSecondary }]} numberOfLines={1}>
                      {montarTitulo(it)}
                    </ThemedText>
                  </Pressable>
                ))}
              </View>
            )}
            <TextField
              label="Código do imóvel"
              icon="pricetag-outline"
              placeholder="Preenchido ao selecionar acima"
              value={imovelId}
              onChangeText={setImovelId}
              autoCapitalize="characters"
            />
          </View>
        ) : (
          <TextField
            label="Endereço do imóvel"
            icon="location-outline"
            placeholder="Digite o endereço completo"
            value={enderecoExterno}
            onChangeText={setEnderecoExterno}
          />
        )}

        {/* Data */}
        <View style={{ gap: Spacing.two }}>
          <ThemedText style={[Typography.label, { color: colors.textSecondary }]}>
            Data da visita
          </ThemedText>
          <Pressable
            onPress={() => setShowDatePicker(true)}
            style={[styles.dateField, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
            <Ionicons name="calendar-outline" size={20} color={colors.textMuted} />
            <ThemedText style={[Typography.body, { color: colors.text, flex: 1 }]}>
              {isoToBR(dataVisita)}
            </ThemedText>
          </Pressable>
          {showDatePicker && (
            <DateTimePicker
              value={new Date(`${dataVisita}T00:00:00`)}
              mode="date"
              maximumDate={new Date()}
              onChange={onDateChange}
            />
          )}
        </View>
      </SectionCard>

      {/* Cliente */}
      <SectionCard title="Cliente" icon="people-outline">
        <View style={{ gap: Spacing.two }}>
          <TextField
            label="Nome do cliente"
            icon="person-outline"
            placeholder="Nome completo"
            value={clienteNome}
            onChangeText={(t) => {
              setClienteNome(t);
              setShowClientes(true);
              setClienteSelecionado(null);
            }}
            onFocus={() => setShowClientes(true)}
            autoCorrect={false}
          />
          {!!clienteNome && (
            <View
              style={[
                styles.badge,
                { backgroundColor: clienteStatus === 'EXISTENTE' ? colors.successSoft : colors.brandSoft },
              ]}>
              <ThemedText
                style={[
                  Typography.caption,
                  { color: clienteStatus === 'EXISTENTE' ? colors.success : colors.brand },
                ]}>
                {clienteStatus === 'EXISTENTE' ? 'Cliente já cadastrado' : 'Novo cliente'}
              </ThemedText>
            </View>
          )}
          {showClientes && (clientesSugestoes.length > 0 || leadsSugestoes.length > 0) && (
            <View style={[styles.dropdown, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}>
              {clientesSugestoes.map((c) => (
                <Pressable key={`c-${c.id_cliente}`} onPress={() => selecionarCliente(c)} style={styles.suggestion}>
                  <ThemedText style={[Typography.label, { color: colors.text }]}>{c.nome}</ThemedText>
                  <ThemedText style={[Typography.caption, { color: colors.textSecondary }]}>
                    {c.telefone || 'Sem telefone'}
                    {c.email ? ` · ${c.email}` : ''}
                  </ThemedText>
                </Pressable>
              ))}
              {leadsSugestoes.length > 0 && (
                <>
                  <ThemedText style={[Typography.caption, styles.dropdownLabel, { color: colors.textMuted }]}>
                    Leads do seu atendimento
                  </ThemedText>
                  {leadsSugestoes.map((lead, i) => (
                    <Pressable key={`l-${lead.id ?? i}`} onPress={() => selecionarLead(lead)} style={styles.suggestion}>
                      <ThemedText style={[Typography.label, { color: colors.text }]}>
                        {lead.cliente || 'Lead sem nome'}
                      </ThemedText>
                      <ThemedText style={[Typography.caption, { color: colors.textSecondary }]} numberOfLines={1}>
                        {[lead.telefone, lead.codigo_imovel ? `Cod. ${lead.codigo_imovel}` : '', lead.fonte]
                          .filter(Boolean)
                          .join(' · ')}
                      </ThemedText>
                    </Pressable>
                  ))}
                </>
              )}
            </View>
          )}
        </View>

        <TextField
          label="Telefone (opcional)"
          icon="call-outline"
          placeholder="(00) 00000-0000"
          keyboardType="phone-pad"
          value={clienteTelefone}
          onChangeText={setClienteTelefone}
        />
        <TextField
          label="E-mail (opcional)"
          icon="mail-outline"
          placeholder="email@exemplo.com"
          keyboardType="email-address"
          autoCapitalize="none"
          value={clienteEmail}
          onChangeText={setClienteEmail}
        />
      </SectionCard>

      {/* Avaliações */}
      <SectionCard title="Avaliações do imóvel" icon="star-outline">
        <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
          Toque no número para dar a nota. 1 = pior, 10 = melhor.
        </ThemedText>
        {NOTA_CAMPOS.map(({ field, label }) => (
          <NotaSelector
            key={field}
            label={label}
            value={notas[field]}
            onChange={(v) => setNotas((p) => ({ ...p, [field]: v }))}
          />
        ))}
        <TextField
          label="Preço ideal (nota 10) — opcional"
          icon="cash-outline"
          placeholder="Ex: 450.000,00"
          keyboardType="number-pad"
          value={moedaFromDigits(precoNota10)}
          onChangeText={(t) => setPrecoNota10(onlyDigits(t))}
        />
      </SectionCard>

      {/* Proposta */}
      <SectionCard title="Proposta" icon="document-text-outline">
        <ChipSelect
          label="O cliente vai fazer proposta?"
          options={[
            { label: 'Sim', value: 'Sim' },
            { label: 'Não', value: 'Nao' },
            { label: 'Talvez', value: 'Talvez' },
          ]}
          value={proposta}
          onChange={(v) => setProposta(v as typeof proposta)}
        />
      </SectionCard>

      {/* Anexo */}
      <SectionCard title="Foto ou PDF da ficha" icon="camera-outline">
        <Pressable
          onPress={pedirAnexo}
          style={[
            styles.upload,
            {
              backgroundColor: anexo ? colors.successSoft : colors.surfaceAlt,
              borderColor: anexo ? colors.success : colors.border,
            },
          ]}>
          <Ionicons
            name={anexo ? 'checkmark-circle' : 'cloud-upload-outline'}
            size={24}
            color={anexo ? colors.success : colors.brand}
          />
          <ThemedText style={[Typography.body, { color: colors.text, flex: 1 }]} numberOfLines={1}>
            {anexo ? anexo.name : 'Toque para tirar foto ou escolher da galeria'}
          </ThemedText>
        </Pressable>
        {!anexo && (
          <ThemedText style={[Typography.caption, { color: colors.textMuted }]}>
            Obrigatório: anexe a ficha assinada pelo cliente.
          </ThemedText>
        )}
      </SectionCard>

      <Button
        label={loading ? 'Enviando visita...' : 'Lançar visita'}
        icon={loading ? undefined : 'checkmark-done-outline'}
        onPress={handleSubmit}
        loading={loading}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  readonly: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: Radius.md,
  },
  dropdown: {
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
    overflow: 'hidden',
  },
  dropdownLabel: {
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
  },
  suggestion: {
    paddingVertical: Spacing.two + 2,
    paddingHorizontal: Spacing.three,
    gap: 2,
  },
  badge: {
    alignSelf: 'flex-start',
    paddingVertical: 3,
    paddingHorizontal: Spacing.two,
    borderRadius: Radius.pill,
  },
  dateField: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    minHeight: 54,
    paddingHorizontal: Spacing.three,
    borderRadius: Radius.md,
    borderWidth: StyleSheet.hairlineWidth,
  },
  upload: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderStyle: 'dashed',
  },
});
