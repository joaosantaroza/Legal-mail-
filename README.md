# legalmail

Integração com a API do LegalMail (app.legalmail.com.br) do escritório
João Santaroza Assessoria Jurídica.

## A chave de API não fica neste repositório

A chave é lida da variável de ambiente `LEGALMAIL_API_KEY`, guardada como
segredo do ambiente de nuvem do Claude Code. Ela só é usada quando há um
pedido de operação no LegalMail.

### Configurar (uma vez)

1. No Claude Code, abra o menu do **ambiente de nuvem** na barra de título
   da sessão e clique em **Edit**.
2. Em **Network secrets** (ou **API credentials**; se não houver, em
   variáveis de ambiente), crie `LEGALMAIL_API_KEY` com a chave gerada no
   menu Integrações do LegalMail.
3. Abra uma sessão nova com este repositório.
4. Confira: `python3 legalmail.py check`.

Nunca cole a chave no chat, em arquivo ou em commit. Se ela vazar,
regenere no LegalMail e troque só o segredo.

## Conteúdo

- `SKILL.md` — skill de operação (fluxos, regras, erros conhecidos).
- `legalmail.py` — cliente sem dependências externas: injeta a chave,
  mascara a chave em erros, para em HTTP 429 e bloqueia os endpoints de
  protocolo sem `--confirmo-protocolo`.

## Exemplos

```bash
python3 legalmail.py GET /api/v1/lawsuit/summary
python3 legalmail.py GET /api/v1/lawsuit/all offset=0 limit=50
```
