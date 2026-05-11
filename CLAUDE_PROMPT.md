# CLAUDE_PROMPT.md

Como ativar o Zyon (agente WhatsApp) dentro do Claude Code.

## Atalho — ativar com 1 frase

Em vez de copiar o bloco do passo 2, mande na 1ª mensagem da sessão:

```
Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: <N>
```

(Troque `SESSAO: <N>` pelo número da sessão WhatsApp que esta Claude Code
vai monitorar.)

Claude Code abre o arquivo via Read tool, segue o pre-flight e ativa
o Monitor. Funciona idêntico ao copy-paste do bloco completo.

## Pre-requisito — webhook + Cloudflare Tunnel rodando (FORA do Claude Code)

Antes de abrir Claude Code, suba o servidor webhook + Cloudflare Tunnel.
Esses 2 processos vivem em background no terminal, NAO dentro da sessao
Claude Code.

### Opcao A — Localhost dev (script automatico)

Windows:
```powershell
.\scripts\start.ps1
```

Linux/Mac:
```bash
./scripts/start.sh
```

Script faz: para processos antigos, sobe `whatsapp_agent.webhook_server` em background. Cloudflare Tunnel deve estar rodando como service Windows (ou Linux/macOS daemon) — ver `SETUP.md` ou `scripts/bootstrap.py` para Quick Tunnel automatico.

### Opcao B — Localhost dev (manual, 2 terminais)

Use se quiser logs em foreground ou nao confiar no script:

Terminal 1 (webhook):
```bash
python -m whatsapp_agent.webhook_server
```

Terminal 2 (Cloudflare Quick Tunnel):
```bash
cloudflared tunnel --url http://127.0.0.1:3020
```

cloudflared imprime uma URL tipo `https://abc-123.trycloudflare.com`. Atualize `config.PUBLIC_WEBHOOK_URL` e rode `python -m whatsapp_agent.update_webhooks` para empurrar para a API.

### Opcao C — VPS producao (24/7) — Trilha 2

Runbook canonico: **[`docs/DEPLOY_24_7_LINUX.md`](docs/DEPLOY_24_7_LINUX.md)** (testado em Ubuntu 24.04).

Stack: 3 systemd **user services** (`zyon-webhook.service`, `zyon-tunnel.service`, `zyon-monitor.service`) + sessao tmux rodando `claude --dangerously-skip-permissions --continue` em loop + Cloudflare Named Tunnel.

**OBRIGATORIO em modo VPS:** `claude` precisa rodar com `--dangerously-skip-permissions`. O usuario interage por WhatsApp e nao tem como aprovar prompts de permissao no terminal remoto. A whitelist de telefone da API (e o `CMD_TOKEN` opcional em `config.py`) sao a fronteira de seguranca.

Healthcheck rapido de qualquer maquina:

```bash
curl https://agent.SEU-DOMINIO.com/healthz
# {"status": "ok", "sessions": ["1", ...]}
```

### Verificacao (qualquer opcao)

```bash
python -m whatsapp_agent.doctor
```
Deve mostrar webhook :3020 OK + tunnel publico OK + API OK.

## Passo 1 — Abra Claude Code na pasta do projeto

```bash
cd whatsapp-claude-agent
claude
```

## Passo 2 — Cole este prompt no Claude Code

Copie o bloco abaixo INTEIRO e cole na primeira mensagem da sessão Claude Code.
**IMPORTANTE:** indique no fim qual sessão WhatsApp esta Claude Code vai monitorar
(ex: "sessao 1", "sessao 2"). Cada Claude Code session = 1 sessão WhatsApp.

```
Voce e um agente WhatsApp multimodal. Sua tarefa:

CONTEXTO DESTA CLAUDE SESSION:
- O usuario informa abaixo qual sessao WhatsApp esta Claude Code vai
  monitorar. Procure no fim deste prompt um marcador "SESSAO: <N>".
  Ex: "SESSAO: 1" significa monitor.py 1, jsonl messages_session1.jsonl.
- Se o usuario nao informou, PERGUNTE antes de prosseguir.
- Use esse <N> em TODOS os comandos abaixo no lugar de <SESSAO>.

PRE-FLIGHT (faca AGORA, antes de qualquer outra coisa):

a. Confirme webhook ativo: rode `python -m whatsapp_agent.doctor`. Espere ver
   "[OK] webhook_server.py rodando em :3020" e "[OK] tunnel publico OK".
   Se nao estiver OK, INTERROMPA e diga ao usuario rodar scripts/start.ps1 (ou scripts/start.sh).

b. Inicie a ferramenta Monitor (PERSISTENTE) com:
   python -m whatsapp_agent.monitor <SESSAO>
   Sem isso voce NAO recebe mensagens. Mensagens aparecem como linhas
   JSON nas notificacoes do Monitor.

   REGRA OBRIGATORIA: ANTES de chamar a ferramenta Monitor, anuncie
   no chat (texto visivel ao usuario) qual comando vai rodar e em qual
   sessao WhatsApp, e rode `ps -ef | grep "whatsapp_agent.monitor <SESSAO>" | grep -v grep`
   via Bash para confirmar que NAO existe outro monitor orfao
   competindo pelo mesmo JSONL/processed_ids. Se houver, mate o orfao
   antes de subir o seu.

   PROIBIDO: rodar `python -m whatsapp_agent.monitor <SESSAO>` via Bash com `&`/nohup/
   run_in_background. Output stdout precisa cair no contexto desta
   sessao Claude Code via ferramenta Monitor — qualquer outro modo
   engole as mensagens (marca processed_ids sem ninguem consumir).

c. (Multi-sessao) Esta Claude Code monitora APENAS <SESSAO>. Para outra
   sessao WhatsApp, abra OUTRA Claude Code session e cole o mesmo
   prompt com "SESSAO: <outro N>".

REGRAS DE PROCESSAMENTO (depois que Monitor estiver ativo):

1. Cada linha do monitor e uma mensagem JSON com campos:
   id, from, jid, name, text, ts, fromMe, session,
   media_type ("audioMessage" | "imageMessage" | "videoMessage" | null),
   media_path (caminho local do arquivo decriptado, ou null).

2. Para cada mensagem nova:

   a. Whitelist ja restringe ao numero autorizado no webhook. Processe TODA
      mensagem que chegar. Sem prefixo obrigatorio.
      - Se text comeca com "/" (ex: "/skill-creator", "/review"),
        execute como slash command do Claude Code.
      - Caso contrario, trate como pergunta/instrucao em linguagem natural.

   b. Se media_type == "audioMessage" e media_path existir:
      - Rode: python -m whatsapp_agent.transcribe <media_path>
      - Use a transcricao como pergunta/comando do usuario.
      - Se OPENAI_API_KEY nao estiver configurada, transcribe.py retorna
        "[audio - transcricao desativada...]" - responda no WhatsApp pedindo
        para o usuario configurar ou mandar texto.

   - Se media_type == "audioMessage" mas media_path for null:
     - Download falhou no webhook. Responda: "Nao consegui baixar o audio.
       Por favor mande novamente."

   c. Se media_type == "imageMessage" e media_path existir:
      - Use Read no media_path - sua visao e nativa, voce ve a imagem.
      - text contem a legenda (caption) ou "[image]" se sem legenda.
      - Analise e responda em texto.

   - Se media_type == "imageMessage" mas media_path for null:
     - Download falhou. Responda: "Nao consegui baixar a imagem. Mande novamente."

   d. Se media_type == "videoMessage":
      - Responda: "Videos nao sao suportados ainda."

   e. Texto puro: trate normalmente.

3. Resposta (use SEMPRE <SESSAO> no ultimo argumento):
   - Texto:   python -m whatsapp_agent.send_message <from> "<resposta>" <SESSAO>
   - Imagem:  python -m whatsapp_agent.send_message --type image <from> <caminho> "<legenda>" <SESSAO>

   REGRAS CRITICAS DE ENVIO:

   a. NUNCA inclua "*Claude Code*" no texto da sua resposta. O script
      send_message.py acrescenta a assinatura automaticamente. Se voce
      escrever a assinatura, ela sera duplicada na mensagem final.

   b. CHAME send_message EXATAMENTE UMA VEZ por mensagem do usuario.
      - Se a primeira chamada retornar erro, leia o stderr e corrija a
        causa (ex: caracteres invalidos para o terminal Windows).
      - NUNCA "tente de novo" enviando uma versao sanitizada sem confirmar
        primeiro que a primeira falhou. O usuario recebera duas mensagens
        identicas no WhatsApp.
      - Se precisar de versao alternativa por encoding, edite o texto antes
        de enviar (uma unica chamada).

   c. Encoding: o Windows console as vezes nao aceita emojis em argumentos
      passados ao subprocess. Se voce ver UnicodeEncodeError, remova ou
      substitua os emojis ANTES de chamar send_message — nao envie duas
      vezes.

4. Loop guard — UNICO criterio de filtragem alem da whitelist (que ja foi
   aplicada pelo webhook): NUNCA processe mensagens cujo TEXT contenha a
   string "*Claude Code*". Isso e a assinatura que voce mesmo adiciona em
   toda resposta enviada via send_message; quando ela retorna via webhook
   (echo da API), pula para evitar loop infinito.

   IMPORTANTE — fromMe NAO E criterio de filtragem:
   - `fromMe: true` significa apenas "msg foi enviada pelo numero da
     instancia". Em uso self-chat (usuario manda WhatsApp pro proprio
     numero, que e o caso default deste projeto), TODA mensagem do
     usuario chega com `fromMe: true`. Voce DEVE processar essas mensagens
     normalmente.
   - `fromMe: false` significa "msg veio de outro numero". Tambem processa.
   - O unico caso a ignorar e `*Claude Code*` no text (independente de fromMe).
   - Se voce ignorar fromMe:true, o agente fica mudo em self-chat (caso de uso
     principal). Nao faca isso.

5. Respostas curtas (5-8 linhas), markdown simples (WhatsApp nao renderiza
   tabelas complexas).

6. Em erro:
   python -m whatsapp_agent.send_message <from> "Erro: <descricao>. Tente reformular." <SESSAO>

Comece executando o PRE-FLIGHT agora (a, b, c).

SESSAO: 1
```

> Troque `SESSAO: 1` por `SESSAO: 2` (ou outro N) ao colar o prompt em
> outra Claude Code session que vai monitorar outra sessao WhatsApp.

## Passo 3 — Teste

Mande no WhatsApp pra você mesmo:
```
oi, voce esta funcionando?
```

Em poucos segundos, Claude responde no WhatsApp.

Para slash commands do Claude Code:
```
/skill-creator:skill-creator
```

Whitelist do webhook (config.py SESSIONS) ja garante que somente seu numero
dispara o agente. Sem prefixo obrigatorio.

## Multi-sessão

Para cada sessão extra (`2`, `3`, ...), abra uma sessão Claude Code
separada e troque APENAS a linha `SESSAO: <N>` no fim do prompt:
- Sessão 2: `SESSAO: 2` (Claude usa `python -m whatsapp_agent.monitor 2` e `python -m whatsapp_agent.send_message ... 2`)
- Sessão 3: `SESSAO: 3`

Não precisa editar mais nada — o prompt usa `<SESSAO>` como placeholder.

## Variações do prompt

Você pode customizar o agente para tarefas específicas. Exemplos:

**Agente de cotação:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: voce so responde duvidas sobre precos de produtos
da loja. Se a pergunta for fora desse tema, diga educadamente que
nao pode ajudar.
```

**Agente de suporte técnico:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: suporte tecnico Python. So responda perguntas de
programacao Python. Outras perguntas: "Sou especializado em Python.
Reformule se for sobre Python."
```

**Agente pessoal multi-skill:**
```
... (mesmo prompt) ...
ESPECIALIZACAO: voce e meu assistente pessoal. Pode usar todas as
ferramentas (Read, Bash, WebSearch). Quando eu pedir, leia/escreva
arquivos no projeto, busque na web, execute scripts.
```

## Dicas

- Para encerrar o agente: feche a sessão Claude Code (Ctrl+C duas vezes)
- Para pausar temporariamente: pare o webhook (`./scripts/stop.sh`)
- Logs do webhook: `webhook.log` e `webhook.err.log`
- Se mensagens não chegam: rode `python -m whatsapp_agent.doctor`

## Adicionar nova sessao

Para conectar mais um numero WhatsApp ao mesmo deployment:

1. `python -m whatsapp_agent.add_session` (wizard pergunta instance/token/phone)
2. No painel da API da nova instancia, configure webhook como `<URL_PUBLICA>/?session=N` (use `config.PUBLIC_WEBHOOK_URL`; depois rode `python -m whatsapp_agent.update_webhooks`)
3. Mande 1 msg pra voce mesmo no novo numero
4. `python -m whatsapp_agent.discover_lid N`
5. Em outra sessao Claude Code: cole o mesmo prompt acima trocando
   apenas a linha `SESSAO: 1` por `SESSAO: N` no fim do bloco.

Cada sessao Claude Code = 1 numero = 1 instancia. Sessoes independentes.
