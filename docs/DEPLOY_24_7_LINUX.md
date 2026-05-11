# Deploy 24/7 do Zyon no Linux (systemd + tmux + Cloudflare Named Tunnel)

Tutorial pra deixar o agente WhatsApp + Claude Code rodando **24 horas por dia, 7 dias por semana**, em uma máquina Linux (testado em Ubuntu 24.04). O objetivo é:

- O agente sobe sozinho no boot
- Sobrevive a logout/SSH disconnect
- Auto-restart em caso de crash
- URL fixa via subdomínio próprio (sem Quick Tunnel efêmero)
- Logs centralizados e fáceis de acompanhar

---

## O que vamos montar

Três serviços systemd rodando em modo **user** (sem precisar root pra continuar rodando):

| Serviço | Função | Tipo |
|---|---|---|
| `zyon-webhook.service` | webhook_server.py escutando em `:3020` | long-running |
| `zyon-tunnel.service` | Cloudflare Named Tunnel expõe `:3020` num subdomínio fixo | long-running |
| `zyon-monitor.service` | cria sessão tmux `zyon` rodando `claude` em loop | oneshot+remain |

Mais um wrapper bash que mantém o `claude` reiniciando se cair (`scripts/claude_monitor_loop.sh`).

```
WhatsApp → megaAPI → https://meusub.dominio.com → cloudflared → 127.0.0.1:3020
                                                                       ↓
                                                            webhook_server.py
                                                                       ↓
                                                       messages_session1.jsonl
                                                                       ↓
                                                  claude (Monitor tool, em tmux)
                                                                       ↓
                                                            send_message.py
                                                                       ↓
                                                                 megaAPI → WhatsApp
```

---

## Pré-requisitos

1. **Zyon já instalado e funcionando manualmente** (siga o `INSTALL_PROMPT.md` antes). O `python -m whatsapp_agent.doctor` deve estar todo verde.
2. **Domínio com DNS gerenciado pela Cloudflare** (gratuito — só registrar o domínio e apontar nameservers). Sem isso, segue só com Quick Tunnel (URL muda a cada restart).
3. **Usuário Linux com sudo** (precisa pra instalar `tmux` e habilitar lingering).
4. **`cloudflared` instalado** (já feito no INSTALL).

---

## Passo 1 — Instalar tmux e habilitar lingering

`tmux` mantém a sessão Claude Code viva mesmo depois que você fecha o terminal. **Lingering** faz os serviços systemd do seu usuário continuarem rodando mesmo sem você logado.

```bash
sudo apt-get install -y tmux
sudo loginctl enable-linger $USER
loginctl show-user $USER | grep Linger   # deve mostrar Linger=yes
```

---

## Passo 2 — Cloudflare Named Tunnel (URL fixa)

> Pule este passo se quiser continuar usando Quick Tunnel. Mas saiba que toda vez que o cloudflared reiniciar a URL muda — você teria que automatizar a re-registração na megaAPI (o repo já fazia isso, mas com Named Tunnel você elimina o problema na raiz).

### 2.1 Login na Cloudflare

```bash
cloudflared tunnel login
```

Vai imprimir uma URL. Abra no navegador, faça login na Cloudflare, **selecione o domínio** que quer usar, clique em **Authorize**. O `cloudflared` baixa automaticamente o certificado pra `~/.cloudflared/cert.pem`.

### 2.2 Criar o tunnel

```bash
cloudflared tunnel create zyon
```

Salva credenciais em `~/.cloudflared/<UUID>.json`. **Nunca commite esse arquivo.**

Se já existir um tunnel `allos` de outro setup e você não tiver as credenciais:

```bash
cloudflared tunnel delete zyon
cloudflared tunnel create zyon
```

### 2.3 Apontar o subdomínio pro tunnel

Substitua `zyon.seudominio.com` pelo subdomínio que você quer:

```bash
cloudflared tunnel route dns -f zyon zyon.seudominio.com
```

A flag `-f` sobrescreve qualquer registro DNS antigo com o mesmo nome.

### 2.4 Criar o config do cloudflared

```bash
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: <UUID-do-tunnel>
credentials-file: /home/SEU_USER/.cloudflared/<UUID-do-tunnel>.json

ingress:
  - hostname: zyon.seudominio.com
    service: http://127.0.0.1:3020
  - service: http_status:404
EOF
```

Substitua `<UUID-do-tunnel>` (saída do `tunnel create`) e `SEU_USER`.

### 2.5 Atualizar `config.py` do Zyon

Edite `config.py` e fixe a URL pública:

```python
PUBLIC_WEBHOOK_URL = "https://zyon.seudominio.com"
```

Depois registre na megaAPI:

```bash
.venv/bin/python -m whatsapp_agent.update_webhooks
```

---

## Passo 3 — Criar os scripts de loop

### 3.1 `scripts/claude_monitor_loop.sh`

Esse script roda dentro do tmux e mantém o `claude` reiniciando automaticamente se cair. Na primeira execução ele recebe o prompt de bootstrap; em todas as próximas usa `--continue` pra retomar a mesma conversa (sem perder estado).

```bash
#!/usr/bin/env bash
set -u
cd /home/SEU_USER/zyon
source /home/SEU_USER/zyon/.venv/bin/activate

PROMPT='Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1'
FIRST_RUN_FLAG=/home/SEU_USER/zyon/.claude_monitor_started

if [ ! -f "$FIRST_RUN_FLAG" ]; then
    echo "[claude_monitor_loop] first run: starting fresh session"
    touch "$FIRST_RUN_FLAG"
    /home/SEU_USER/.local/bin/claude --dangerously-skip-permissions "$PROMPT"
fi

while true; do
    echo "[claude_monitor_loop] resuming session"
    /home/SEU_USER/.local/bin/claude --dangerously-skip-permissions --continue "continue monitorando" || true
    echo "[claude_monitor_loop] claude exited; restarting in 5s..."
    sleep 5
done
```

> **Atenção segurança:** `--dangerously-skip-permissions` permite que o `claude` execute Bash/Edit sem confirmar. Necessário pra rodar headless. A whitelist de telefone na megaAPI garante que só o seu número consegue disparar o agente. Se isso te preocupa, ative `CMD_TOKEN` no `config.py` pra exigir prefixo de senha em cada mensagem.

### 3.2 `scripts/tmux_ensure_zyon.sh`

Cria a sessão tmux só se ela não existir (idempotente — pode rodar muitas vezes sem problema).

```bash
#!/usr/bin/env bash
set -u
SESSION=zyon
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[tmux_ensure_zyon] session '$SESSION' already running"
    exit 0
fi
echo "[tmux_ensure_zyon] creating tmux session '$SESSION'"
tmux new-session -d -s "$SESSION" -c /home/SEU_USER/zyon \
    "/home/SEU_USER/zyon/scripts/claude_monitor_loop.sh"
echo "[tmux_ensure_zyon] attach with: tmux attach -t $SESSION"
```

### 3.3 Permissões

```bash
chmod +x scripts/claude_monitor_loop.sh scripts/tmux_ensure_zyon.sh
```

---

## Passo 4 — Criar os 3 serviços systemd

Coloque em `~/.config/systemd/user/`:

```bash
mkdir -p ~/.config/systemd/user
```

### 4.1 `zyon-webhook.service`

```ini
[Unit]
Description=Zyon WhatsApp webhook server (port 3020)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/SEU_USER/zyon
ExecStart=/home/SEU_USER/zyon/.venv/bin/python -m whatsapp_agent.webhook_server
Restart=on-failure
RestartSec=5
StandardOutput=append:/home/SEU_USER/zyon/webhook.log
StandardError=append:/home/SEU_USER/zyon/webhook.log

[Install]
WantedBy=default.target
```

### 4.2 `zyon-tunnel.service`

```ini
[Unit]
Description=Zyon Cloudflare Named Tunnel
After=network-online.target zyon-webhook.service
Wants=network-online.target
Requires=zyon-webhook.service

[Service]
Type=simple
WorkingDirectory=/home/SEU_USER/zyon
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate --config /home/SEU_USER/.cloudflared/config.yml run zyon
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/SEU_USER/zyon/cloudflared.log
StandardError=append:/home/SEU_USER/zyon/cloudflared.log

[Install]
WantedBy=default.target
```

### 4.3 `zyon-monitor.service`

```ini
[Unit]
Description=Zyon Claude Code monitor (tmux session 'zyon')
After=zyon-tunnel.service
Wants=zyon-tunnel.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/SEU_USER/zyon
ExecStart=/home/SEU_USER/zyon/scripts/tmux_ensure_zyon.sh
ExecStop=/usr/bin/tmux kill-session -t zyon

[Install]
WantedBy=default.target
```

---

## Passo 5 — Ativar e iniciar

```bash
systemctl --user daemon-reload
systemctl --user enable --now zyon-webhook.service zyon-tunnel.service zyon-monitor.service
```

Verifique:

```bash
systemctl --user status zyon-webhook zyon-tunnel zyon-monitor
```

Os 3 devem estar **active**. O monitor aparece como **active (exited)** porque é `Type=oneshot` — quem segura o claude vivo é o tmux, não o systemd.

Teste o tunnel:

```bash
curl -I https://zyon.seudominio.com
# 501 ou 404 está OK — significa que o cloudflared encaminhou pro webhook_server,
# que não responde GET (ele só aceita POST da megaAPI)
```

Mande uma mensagem do seu WhatsApp pra você mesmo. O agente deve responder em alguns segundos com a assinatura `*Claude Code*`.

---

## Comandos de logs e operação

### Logs em tempo real

```bash
# Tudo num só lugar (recomendado pra debug)
journalctl --user -u zyon-webhook -u zyon-tunnel -u zyon-monitor -f

# Por serviço
journalctl --user -u zyon-webhook -f
journalctl --user -u zyon-tunnel -f
journalctl --user -u zyon-monitor -f

# Logs de aplicação
tail -f /home/SEU_USER/zyon/webhook.log         # mensagens chegando
tail -f /home/SEU_USER/zyon/cloudflared.log     # tunnel
tail -f /home/SEU_USER/zyon/raw_debug.jsonl     # payload bruto megaAPI (verboso)
tail -f /home/SEU_USER/zyon/messages_session1.jsonl  # mensagens já filtradas
```

### Histórico

```bash
# Últimas 100 linhas
journalctl --user -u zyon-webhook -n 100 --no-pager

# Desde 1h atrás
journalctl --user -u zyon-tunnel --since "1 hour ago"

# Apenas erros
journalctl --user -u zyon-monitor -p err
```

### Acompanhar o claude ao vivo (interativo)

```bash
tmux attach -t zyon
# Pra sair sem matar a sessão: Ctrl+B depois D
```

### Ciclo de vida

```bash
# Reiniciar tudo
systemctl --user restart zyon-webhook zyon-tunnel zyon-monitor

# Parar tudo
systemctl --user stop zyon-monitor zyon-tunnel zyon-webhook

# Iniciar tudo
systemctl --user start zyon-webhook zyon-tunnel zyon-monitor

# Status agregado
systemctl --user status zyon-webhook zyon-tunnel zyon-monitor

# Diagnóstico do agente
cd ~/zyon && .venv/bin/python -m whatsapp_agent.doctor
```

### Aliases úteis pro `~/.bashrc`

```bash
alias zyon-logs='journalctl --user -u zyon-webhook -u zyon-tunnel -u zyon-monitor -f'
alias zyon-status='systemctl --user status zyon-webhook zyon-tunnel zyon-monitor'
alias zyon-restart='systemctl --user restart zyon-webhook zyon-tunnel zyon-monitor'
alias zyon-stop='systemctl --user stop zyon-monitor zyon-tunnel zyon-webhook'
alias zyon-start='systemctl --user start zyon-webhook zyon-tunnel zyon-monitor'
alias zyon-msgs='tail -f ~/zyon/messages_session1.jsonl'
alias zyon-raw='tail -f ~/zyon/raw_debug.jsonl'
alias zyon-webhook-log='tail -f ~/zyon/webhook.log'
alias zyon-tunnel-log='tail -f ~/zyon/cloudflared.log'
alias zyon-attach='tmux attach -t zyon'
alias zyon-doctor='cd ~/zyon && .venv/bin/python -m whatsapp_agent.doctor'
```

Depois `source ~/.bashrc`.

---

## Trocando o modelo e effort do Claude

Por padrão o `claude` usa Opus (mais caro, mais capaz). Pra produção 24/7 normalmente vale rodar com **Sonnet** (mais barato, ainda muito bom) e ajustar o **effort** (quanto mais alto, mais raciocínio = mais lento e mais caro).

Modelos atuais (referência rápida):

| Alias | Nome completo | Quando usar |
|---|---|---|
| `opus` | `claude-opus-4-7` | Tarefas complexas; mais caro |
| `sonnet` | `claude-sonnet-4-6` | Default recomendado pra agente WhatsApp |
| `haiku` | `claude-haiku-4-5` | Respostas curtas, máxima velocidade |

Effort: `low` < `medium` < `high` < `xhigh` < `max`. Pra um agente WhatsApp que responde mensagens, `medium` costuma ser o sweet spot.

### Opção 1 — Permanente (no loop script)

Edite `scripts/claude_monitor_loop.sh` e adicione `--model` e `--effort` em **ambas** as chamadas do `claude`:

```bash
/home/SEU_USER/.local/bin/claude \
    --dangerously-skip-permissions \
    --model claude-sonnet-4-6 \
    --effort medium \
    "$PROMPT"
```

E na linha do loop:

```bash
/home/SEU_USER/.local/bin/claude \
    --dangerously-skip-permissions \
    --model claude-sonnet-4-6 \
    --effort medium \
    --continue "continue monitorando" || true
```

Aplica reiniciando o serviço:

```bash
systemctl --user restart zyon-monitor
```

Confira que pegou:

```bash
ps -ef | grep 'claude --dang' | grep -v grep
# deve mostrar: ... --model claude-sonnet-4-6 --effort medium ...
```

### Opção 2 — Ad-hoc (slash command no tmux)

Pra trocar pontualmente sem mexer no script:

```bash
tmux attach -t zyon
```

Dentro do claude rodando:

- `/model` — abre seletor interativo
- `/model sonnet` — troca direto pra Sonnet 4.6
- `/effort medium` — troca o effort

Sair sem matar: `Ctrl+B` depois `D`.

> **Atenção:** essa mudança é só pra sessão atual. Quando o `claude` reiniciar (crash ou reboot), volta pra configuração do script. Se gostou da nova combinação, edite o script.

### Opção 3 — Defaults via `settings.json`

Cria/edita `~/.claude/settings.json` (global) ou `zyon/.claude/settings.json` (por projeto):

```json
{
  "model": "claude-sonnet-4-6",
  "effort": "medium"
}
```

A precedência é: `--flag` na CLI > `settings.json` do projeto > `settings.json` global.

### Como saber qual modelo está sendo usado

Anexa no tmux (`tmux attach -t zyon`) e olha o canto inferior direito da interface — mostra o modelo ativo. Ou no claude rodando:

```
/status
```

---

## Troubleshooting

### Service não inicia: "Failed to connect to bus: No medium found"

Ocorre quando você tenta `systemctl --user` em uma sessão onde `XDG_RUNTIME_DIR` não está setado (ex: SSH não-login shell). Workaround:

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
```

Adicione ao `~/.bashrc` se acontecer sempre.

### Tunnel sobe mas requisições retornam 404

Provavelmente tem um `~/.cloudflared/config.yml` global interferindo, ou o ingress está apontando pra porta errada. Cheque:

```bash
cat ~/.cloudflared/config.yml
ss -tlnp | grep 3020   # webhook deve estar escutando
```

### `claude` no tmux não responde mensagens

Anexe e veja o que está acontecendo:

```bash
tmux attach -t zyon
```

Causas comuns:
- Tela mostrando aprovação pendente: signfica que `--dangerously-skip-permissions` não foi passado (verifique `claude_monitor_loop.sh`)
- Tela mostrando erro de auth: rode `claude` manualmente uma vez pra fazer login da Anthropic
- Monitor tool não foi iniciado: o prompt inicial pode não ter sido executado corretamente — delete o flag e reinicie:

  ```bash
  rm -f ~/zyon/.claude_monitor_started
  systemctl --user restart zyon-monitor
  ```

### Webhook recebe mas mensagem é ignorada

Confira `phone` e `lid` no `config.py` — devem bater com os do `raw_debug.jsonl` no campo `phone_connected` ou no `key.remoteJid`/`participant`. O whitelist é o filtro: se não bate, a linha não chega no `messages_sessionN.jsonl`.

### Agente respondeu duas vezes a mesma mensagem

Significa que tem **dois monitors** ativos (ex: você não fechou o terminal antigo antes de ativar o systemd). Garanta que só existe um:

```bash
ps -ef | grep monitor.py | grep -v grep
# Deve aparecer só 1
```

### URL `zyon.seudominio.com` não resolve

Espere 1-2 minutos pelo DNS. Confira no painel da Cloudflare se o registro CNAME foi criado apontando pro tunnel. Force re-criação:

```bash
cloudflared tunnel route dns -f zyon zyon.seudominio.com
```

---

## Arquitetura: por que cada peça?

- **systemd user services** ao invés de root: roda com permissões mínimas, sob a mesma conta que tem acesso aos arquivos do projeto e ao Python venv
- **lingering**: sem isso, todos os user services morrem quando você desloga
- **tmux pro claude**: o claude é interativo (TUI) — não dá pra rodar headless puro. O tmux dá um terminal virtual onde ele opera; sobrevive a logout
- **`Type=oneshot RemainAfterExit=yes` no monitor**: o systemd só precisa criar o tmux uma vez; quem mantém o claude vivo é o loop bash dentro do tmux
- **Loop bash (`while true; do claude --continue ...; done`)**: se o claude crashar, reinicia em 5s. `--continue` retoma a mesma conversa sem reiniciar do zero
- **Named Tunnel ao invés de Quick Tunnel**: URL fixa = nunca precisa atualizar o webhook na megaAPI = zero downtime no restart
- **`Requires=zyon-webhook.service` no tunnel**: garante que tunnel só sobe se webhook estiver vivo (sem isso, você teria janela onde o domínio responde 502)

---

## Checklist de produção

- [ ] `python -m whatsapp_agent.doctor` retorna tudo OK
- [ ] `curl https://zyon.seudominio.com` retorna algo (não DNS error)
- [ ] `systemctl --user status` mostra os 3 serviços ativos
- [ ] `tmux attach -t zyon` mostra `claude` rodando com Monitor tool ativo
- [ ] Mandar msg de teste no WhatsApp e receber resposta com `*Claude Code*` no final
- [ ] `sudo reboot` e validar que tudo subiu sozinho 1 minuto depois
- [ ] **Rotacionar OPENAI_API_KEY e MEGA_TOKEN** se foram colados em chat/PR durante setup

---

## Limitações conhecidas

- **`--dangerously-skip-permissions`**: o claude tem acesso irrestrito ao shell. Mitigue com `CMD_TOKEN` se quiser camada extra de auth por mensagem
- **Crash da própria autenticação Claude**: se a sessão Claude expira, o loop não consegue se re-autenticar sozinho. Você precisa anexar no tmux e refazer login manualmente
- **Tunnel quota**: Cloudflare Tunnel grátis é generoso, mas tem limites de bandwidth. Dificilmente um agente WhatsApp atinge isso, mas vale saber
- **Memória**: cada `claude` em background consome ~200MB. Em VPS de 1GB, vigie

---

## Créditos e referências

- Repositório: https://github.com/mbkautomacoes/zyon
- Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- systemd user services: https://wiki.archlinux.org/title/Systemd/User
- Claude Code: https://docs.claude.com/claude-code

---

**Tutorial escrito durante o setup real em maio/2026. Testado em Ubuntu 24.04 LTS.**
