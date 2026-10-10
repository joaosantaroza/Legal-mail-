---
name: legalmail
description: >
  Skill de operação completa da integração LegalMail (app.legalmail.com.br) do
  escritório João Santaroza. Acionar SEMPRE que João mencionar: "LegalMail",
  "peticionar", "protocolar", "protocola essa peça", "sobe no LegalMail",
  "intimação", "intimações pendentes", "radar de intimações", "roda o radar",
  "prazo aberto", "importar processo", "importa esse processo", "puxa os autos",
  "atualiza os autos", "dossiê do processo", "meus processos", "lista os processos",
  "consulta o processo", "movimentações", "baixa o documento", "campos
  personalizados", "etiqueta o processo", "certificado digital", "relatório do
  mês", "entrada de cliente novo", "onboarding", ou enviar peça + anexos pedindo
  para subir no tribunal. Também acionar para qualquer consulta, gestão ou
  peticionamento envolvendo o acervo do escritório na plataforma. Cobre: consulta
  e gestão de processos, radar de intimações, importação (avulsa e lote), esteira
  de protocolo (inicial e intermediária) com parada obrigatória antes do envio,
  dossiê, partes, usuários, certificados e relatório gerencial.
version: 1.1.0
---

# LegalMail · Operação da Integração
## Skill oficial do escritório João Santaroza · validada em produção em 09/06/2026

---

## REGRAS INEGOCIÁVEIS (ler antes de qualquer operação)

1. **NUNCA protocolar sem confirmação expressa do João.** O endpoint de envio
   (`intermediate/send`, `complaint/send`) só é chamado depois que o João disser
   explicitamente "protocola", "envia", "pode mandar". Montar tudo e PARAR é o
   comportamento padrão. Não existe protocolo automático ou silencioso.
2. **NUNCA fazer polling.** Nenhum status é consultado em loop. O LegalMail pune
   3 erros 429 em 10 minutos com bloqueio progressivo: 10 min → dobra a cada
   reincidência → até 7 dias. Se vier 429: parar, informar o `Retry-After`, esperar.
3. **Operações destrutivas só com confirmação individual.** Excluir processo,
   deletar petição, remover parte/usuário: descrever a ação, avisar que é
   irreversível, esperar o OK. Cada exclusão tem sua própria confirmação.
4. **Varreduras sempre espaçadas.** Limite: 60 req/min. Em varreduras de acervo,
   usar `sleep` de ~1.3s entre chamadas (70 processos ≈ 2 min).
5. **Chave de API:** vive SOMENTE no segredo do ambiente, na variável
   `LEGALMAIL_API_KEY`. Nunca pedir a chave na conversa, nunca escrevê-la em
   arquivo, commit, documento, artifact ou resposta, e nunca imprimi-la
   (`echo`, `env`, `printenv`, log de URL). Só ler a variável quando o João
   pedir uma operação do LegalMail. Usar sempre o cliente `legalmail.py`, que
   lê a variável e mascara a chave nas mensagens de erro. Se a variável não
   existir: avisar o João para cadastrá-la nas configurações do ambiente e
   abrir uma sessão nova — não prosseguir de outro jeito. Se a chave for
   regenerada no menu Integrações, basta trocar o segredo; a skill não muda.
6. **Verificar a quem pertence o processo** antes de montar qualquer peça. Se a
   petição/documentos enviados forem de outro advogado (OAB diferente da do João,
   OAB/PR 81.381), alertar antes de prosseguir.
---

## DADOS FIXOS DO WORKSPACE

| Item | Valor |
|---|---|
| Base URL | `https://app.legalmail.com.br` |
| Chave de API (KEY) | **Não fica aqui.** Segredo do ambiente `LEGALMAIL_API_KEY` (lido por `legalmail.py`). |
| Autenticação | `api_key` como query param em TODA requisição |
| Certificado do escritório | ID `3207` · vence **05/11/2026** (alertar a partir de set/2026) |
| Usuário | João (admin, único) |
| Acervo (09/06/2026) | 70 processos · 15 tribunais · 39 protocolos no histórico |
| Limite | 60 req/min · anti-polling com bloqueio progressivo |

**Limite conhecido da API:** etiquetas nativas da plataforma são INVISÍVEIS
(nenhum endpoint existe). Para classificação legível por API, usar **campos
personalizados** (seção própria abaixo). Audiências também não têm endpoint —
extrair dos títulos das movimentações ("audiência", "designação", "pauta").

---

## COMO CHAMAR A API (sempre pelo cliente)

O `KEY` dos exemplos abaixo é só ilustrativo: o cliente injeta a chave sozinho.
Escreva o caminho SEM `api_key`.

```bash
python3 legalmail.py GET  /api/v1/lawsuit/summary
python3 legalmail.py GET  /api/v1/lawsuit/detail numero_processo=0000000-00.0000.0.00.0000
python3 legalmail.py POST /api/v1/lawsuit/custom_fields/upsert --json '{"fk_processo": 1, ...}'
python3 legalmail.py POST /api/v1/complaintsandpleadings/file idpeticoes=P idprocessos=ID --file peca.pdf
python3 legalmail.py POST /api/v1/complaintsandpleadings/attachments idpeticoes=P fk_documentos_tipos=T \
    --file anexo.pdf --form descricao_outros="Texto"
python3 legalmail.py check   # só confirma que a variável existe, sem mostrar a chave
```

Os endpoints de envio (`intermediate/send`, `complaint/send`) exigem `--confirmo-protocolo`,
que só se passa depois do OK expresso do João (Regra 1). Em 429 o cliente para e
mostra o `Retry-After` — não repetir a chamada.

---

## FLUXO 1 · CONSULTAR PROCESSOS

```
GET /api/v1/lawsuit/all?api_key=KEY&offset=0&limit=50      # acervo paginado (máx 50)
GET /api/v1/lawsuit/detail?api_key=KEY&numero_processo=X   # ou &idprocesso=ID
GET /api/v1/lawsuit/summary?api_key=KEY                    # resumo agregado
GET /api/v1/lawsuit/case-files?api_key=KEY&idprocesso=ID   # autos/movimentações
GET /api/v1/lawsuit/docket-entry/url?api_key=KEY&idmovimentacoes=ID  # URL do doc
```

- O acervo completo: paginar de 50 em 50 até página vazia, com sleep 1.5s.
- `case-files` devolve as movimentações com `idmovimentacoes`, título, data, tipo.
- A URL do documento permite **baixar e ler** o PDF (decisão, ofício, laudo) —
  usar para dossiês e para extrair prazos do texto.
- Atualizar autos (robôs revisitam o tribunal): `POST /api/v1/lawsuit/update`.
- Download completo dos autos: job assíncrono — solicitar, consultar resultado
  UMA vez quando o João pedir, nunca em loop.

## FLUXO 2 · RADAR DE INTIMAÇÕES (rotina semanal)

```
GET /api/v1/pleading/notices-to-comply?api_key=KEY&idprocessos=ID
```

Devolve `intimacoes_prazo_aberto[]` e `intimacoes_prazo_fechado[]`, cada uma com
data, tipo, fonte (sistema do tribunal), destinatário e **texto integral**.

Procedimento: paginar o acervo → consultar cada processo com sleep 1.3s →
consolidar painel em 3 blocos:
- **AGIR** — prazo aberto, ordenado da publicação mais antiga para a mais nova
- **MONITORAR** — fechadas recentes (vencidas sem manifestação, cumpridas sem vínculo)
- **LIMPO** — sem pendências
Para cada item de AGIR: ler o texto da intimação, identificar o que é exigido e
o prazo, propor o próximo passo (pode emendar no Fluxo 4). Saída: resumo na
conversa ou PDF com identidade visual da Atena (skill `atena-identidade-visual`).

Variações: "radar só dos trabalhistas", "radar do bloco Selzlein", "o que venceu
desde a última varredura?".

## FLUXO 3 · IMPORTAR PROCESSO (avulso ou lote)

```
1. GET  /api/v1/uploads/classes?api_key=KEY&term=BUSCA        # → classe_id
2. GET  /api/v1/uploads/allowed-systems?api_key=KEY&numero=CNJ # → sistemas (pje/projudi/esaj/eproc)
3. POST /api/v1/uploads/request?api_key=KEY                    # body: {pedidos:[{numero,tribunal,sistema,classe_id,certificado_id}]}
4. GET  /api/v1/uploads/status?api_key=KEY&hash=H              # pontual, NUNCA loop
   POST /api/v1/uploads/cancel                                  # desfazer pendente
```

- `pedidos` aceita LISTA → importação em lote (carteiras Rhilo inteiras de uma vez).
- Se o sistema vier ambíguo (ex.: TJPR → Projudi/eProc/SEEU), perguntar ao João
  qual usar — não chutar.
- Certificado: usar 3207 salvo instrução contrária.

## FLUXO 4 · PROTOCOLAR — ESTEIRA COMPLETA (testado em produção)

**Intermediária (processo que já corre):**

```
0. (opcional) GET /api/v1/pleading/notices-to-comply           # guardar idintimacoes a cumprir
1. POST /api/v1/complaintsandpleadings/intermediate?api_key=KEY
   body: {"fk_processo": ID, "fk_certificado": 3207, "tutela_antecipada": 0, "custas_recolhidas": 1}
   → devolve {hash_peticao, idpeticoes}
2. POST /api/v1/complaintsandpleadings/file?api_key=KEY&idpeticoes=P&idprocessos=ID
   multipart: file=@peca.pdf            # idpeticoes/idprocessos vão na QUERY, não no form!
3. GET  /api/v1/complaintsandpleadings/attachment/types?api_key=KEY&idpeticoes=P
   → ~93 tipos (10687=Fotografia, 10680=Documento Diverso, 10679=Doc. Identificação...)
   POST /api/v1/complaintsandpleadings/attachments?api_key=KEY&idpeticoes=P&fk_documentos_tipos=T
   multipart: file=@anexo.pdf [+ descricao_outros se tipo "Outros" — máx 100 chars eProc/200 demais]
4. ⛔ PARAR. Apresentar: "petição montada com peça + N anexos. Protocolo agora ou revisa antes?"
   Só com OK expresso: POST /api/v1/complaintsandpleadings/intermediate/send
   body: {fk_peca, ...} + opcional "intimacoes": [ids] para vincular o cumprimento
```

**Inicial (distribuição):** mesmo padrão, com parametrização prévia consultando
as tabelas do tribunal: `complaintsandpleadings/courts`, justiças, áreas,
especialidades, ritos, classes, assuntos, prioridades, motivos de não
recolhimento. Propor valores com base na peça; João confirma. Envio:
`complaint/send` (imediato ou **agendado** para data/hora — útil para último dia
de prazo). Status possíveis: Em fila, Protocolando, Protocolado, Agendado,
Cancelado, Com pendências (ler a mensagem de pendência quando travar).

**Conversão obrigatória de anexos:** a API só aceita PDF (peça E anexos).
Qualquer JPG/PNG/HEIC recebido → converter automaticamente, sem perguntar:

```python
from PIL import Image
Image.open("anexo.jpg").convert("RGB").save("anexo.pdf", "PDF")
```

**Rascunho não aparece em /filings antes do envio** — comportamento normal,
não é erro.

## FLUXO 5 · CAMPOS PERSONALIZADOS (classificação legível por API)

```
POST /api/v1/lawsuit/custom_fields/upsert?api_key=KEY
  body: {"fk_processo": ID, "campos_personalizados": [{"nome":"Temática","tipo":"texto","valor":"V"}]}
GET  /api/v1/lawsuit/custom_fields/get?api_key=KEY&fk_processo=ID
GET  /api/v1/lawsuit/custom_fields/all?api_key=KEY             # definições do workspace
```

⚠️ O campo do body é `campos_personalizados` (não `campos`) e cada item exige
`tipo` (texto|numero|data|email|booleano). A definição nasce no primeiro uso.

Taxonomia padrão do escritório (João pode ajustar): **Temática** (Previdenciário,
Trabalhista, Execução Fiscal, Execução de Título, Cível, Juizado), **Parceria**
(Rhilo, Captação Própria, Indicação), **Fase** (Conhecimento, Recursal,
Execução/Cumprimento). Lote: deduzir dos dados (INSS no polo passivo →
Previdenciário; TRT → Trabalhista; classe contém "Execução Fiscal" → Fiscal);
o que não resolver vira lista curta para o João bater o martelo.

## FLUXO 6 · PROTOCOLOS, PARTES, USUÁRIOS, CERTIFICADOS

```
GET /api/v1/filings?api_key=KEY&limit=50        # filtros: tipo (avulsa|Intermediária), status,
                                                 # processo (busca livre), enviado_por, certificado_de,
                                                 # enviado_em_inicio/fim, protocolado_em_inicio/fim
GET /api/v1/party/search?api_key=KEY&nome=&documento=&polo=&offset=&limit=
GET /api/v1/users?api_key=KEY                   # → idusuarios
GET /api/v1/workspace/certificates?api_key=KEY  # → idcertificados + vencimentos
```

Partes têm CRUD completo + tabelas de apoio (profissões, órgãos expedidores).
Gerador de docs da plataforma: existe mas é redundante — usar as skills do
escritório (identidade visual própria).

## FLUXO 7 · ROTINAS COMPOSTAS

**Onboarding de cliente novo** (uma conversa): kit de documentos pela skill
`kit-cliente-joao-santaroza` → Fluxo 3 (importar processo) → Fluxo 5
(classificar) → Fluxo 2 no processo novo (verificar pendências herdadas).

**Dossiê de processo**: detail + case-files + baixar docs-chave (decisões,
laudos, ofícios) + cruzar com radar → linha do tempo narrada, situação atual,
riscos, próximos passos. Saída: conversa, PDF Atena, ou apresentação
(skill `gamma-apresentacao-juridica` / `design-apresentacao-juridica`).
Combinações: execução parada → skill `prescricao-intercorrente`; condenação →
skill `calculadora-judicial-jf`; previdenciário → skill `rhilo-auxilio-acidente`.

**Relatório mensal** (PDF Atena): filings do período + processos novos vs.
arquivados + distribuição por Temática + pendências do radar + alerta do
certificado (abre o relatório a partir de setembro/2026).

**Audiências** (sem endpoint próprio): varrer case-files dos últimos 30 dias
filtrando títulos com "audiência|designação|pauta|sessão", extrair datas do
texto, cruzar com Google Calendar (conector ativo) e listar o que falta agendar.

---

## ERROS CONHECIDOS E SOLUÇÕES (descobertos nos testes)

| Sintoma | Causa | Solução |
|---|---|---|
| `Missing field: idpeticoes` no upload | Params no form-data | `idpeticoes`/`idprocessos` vão na **query string** |
| `Missing field: campos_personalizados` | Body com `campos` | Renomear para `campos_personalizados` + incluir `tipo` |
| Anexo rejeitado | JPG/PNG enviado | Converter para PDF antes (Pillow) — automático |
| `Method not allowed` em /status | Endpoint errado p/ rascunho | Rascunho não tem status; só após envio aparece em /filings |
| HTTP 429 | Limite/polling | Parar, ler Retry-After, esperar; NUNCA re-tentar em sequência |
| Petição sumiu de /filings | Rascunho não enviado | Normal — rascunhos não listam antes do send |

## CHECKLIST ANTES DE QUALQUER PROTOCOLO

1. O processo pertence ao João? (conferir advogado/OAB nos documentos)
2. A peça está em PDF? Anexos convertidos e tipados?
3. Há intimação pendente a vincular? (Fluxo 2 no processo)
4. Custas: recolhidas/gratuidade definida? Guias informadas se houver?
5. João revisou e deu o OK expresso? → só então `send`
6. Após protocolo: informar status e, se "Com pendências", ler a mensagem
---

*Skill v1.1.0 · 10/10/2026 · chave movida para o segredo do ambiente.*
*v1.0.0 · 09/06/2026 · Validada em produção: acervo varrido (70),
radar piloto (3 pendências), campo personalizado criado, peça + anexo
convertido subidos (petição 707017, apagada após o teste).*
