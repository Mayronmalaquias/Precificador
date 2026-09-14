import { Pressable, StyleSheet, View } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '@/components/ui/button';
import { ChipSelect } from '@/components/ui/chip-select';
import { NotaSelector } from '@/components/ui/nota-selector';
import { Screen } from '@/components/ui/screen';
import { SectionCard } from '@/components/ui/section-card';
import { TextField } from '@/components/ui/text-field';
import { ThemedText } from '@/components/themed-text';
import { useAppTheme } from '@/hooks/use-app-theme';
import { Radius, Spacing, Typography } from '@/theme';
import {
  NOTA_CAMPOS,
  isoToBR,
  moedaFromDigits,
  onlyDigits,
  useVisitaForm,
} from '@/features/visita/use-visita-form';

export function VisitaForm() {
  const { colors } = useAppTheme();
  const {
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
  } = useVisitaForm();

  return (
    <Screen scroll keyboardAvoiding edges={['top']}>
      <ThemedText style={Typography.h1}>Criar visita</ThemedText>

      {/* Corretor */}
      <SectionCard title="Corretor" icon="person-outline">
        <View style={[styles.readonly, { backgroundColor: colors.surfaceAlt }]}>
          <Ionicons name="id-card-outline" size={18} color={colors.textMuted} />
          <ThemedText style={[Typography.body, { flex: 1 }]} numberOfLines={1}>
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
                    <ThemedText style={Typography.label}>
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
            <ThemedText style={[Typography.body, { flex: 1 }]}>
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
                  <ThemedText style={Typography.label}>{c.nome}</ThemedText>
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
                      <ThemedText style={Typography.label}>
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
          <ThemedText style={[Typography.body, { flex: 1 }]} numberOfLines={1}>
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

