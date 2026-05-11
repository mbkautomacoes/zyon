# INSTALL_PROMPT.md

Prompt único para instalar o Zyon do zero numa máquina nova usando Claude Code.

## Como usar

1. Instale Claude Code se ainda não tiver: https://docs.claude.com/claude-code
2. Abra um terminal qualquer (PowerShell no Windows, Terminal no macOS/Linux)
3. Rode `claude` numa pasta vazia onde queira clonar o projeto (ex: `Desktop`)
4. Cole o prompt abaixo INTEIRO na primeira mensagem
5. Claude detecta o SO, instala dependências, clona o repo, roda o bootstrap

---

## Prompt para colar

```
Voce e um instalador automatizado do projeto Zyon (WhatsApp + Claude Code agent).
Repositorio: https://github.com/mbkautomacoes/zyon

Sua tarefa: deixar a maquina pronta para rodar o agente, do zero.

PASSO 0 — Detectar ambiente
- Rode comandos para descobrir SO (Windows/macOS/Linux), shell, e cwd atual.
- Diga ao usuario o que detectou antes de prosseguir.

PASSO 1 — Verificar dependencias
Cheque cada uma e diga ao usuario o status (OK / FALTA):
  - git              (`git --version`)
  - python 3.10+     (`python --version` ou `python3 --version`)
  - pip              (`pip --version` ou `python -m pip --version`)
  - curl             (`curl --version`)
  - cloudflared      (`cloudflared --version`)

PASSO 2 — Instalar o que falta
Para cada dependencia FALTANTE, instale conforme o SO:

  Windows (use winget; se winget nao existir, mande o usuario instalar pelo link):
    - git:          winget install Git.Git
    - python:       winget install Python.Python.3.12
    - curl:         ja vem no Windows 10+ (`where curl`); se faltar:
                    winget install cURL.cURL
    - cloudflared:  winget install Cloudflare.cloudflared

  macOS (use brew; se brew nao existir, instrua usuario a rodar:
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"):
    - git:          brew install git
    - python:       brew install python@3.12
    - curl:         brew install curl
    - cloudflared:  brew install cloudflared

  Linux (Debian/Ubuntu):
    - git:          sudo apt-get update && sudo apt-get install -y git
    - python:       sudo apt-get install -y python3 python3-pip python3-venv
    - curl:         sudo apt-get install -y curl
    - cloudflared:  baixar .deb de
                    https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
                    e instalar com `sudo dpkg -i <arquivo>.deb`

REGRAS:
- Anuncie cada install ANTES de rodar (comando exato).
- Se o install precisar sudo/admin e voce nao tem permissao, PARE
  e peca o usuario para rodar o comando manualmente, depois continue.
- Apos instalar, RE-VERIFIQUE rodando o comando de versao novamente.

PASSO 3 — Clonar repositorio
- Pergunte ao usuario onde quer clonar (default: cwd atual, pasta `zyon`).
- Rode: git clone https://github.com/mbkautomacoes/zyon.git zyon
- cd zyon
- A partir daqui, todos comandos rodam dentro da pasta zyon.

PASSO 4 — Instalar dependencias Python
- Rode: python -m pip install -r requirements.txt
  (se nao existir requirements.txt, instale: requests fastapi uvicorn openai)
- Confirme sem erro.

PASSO 5 — Configurar config.py
- Verifique se `config.py` existe na raiz.
- Se NAO existir: copie `config.example.py` para `config.py`.
- AVISE o usuario que `config.py` precisa ser editado com:
    - MEGA_HOST       (ex: https://apinocode01.megaapi.com.br)
    - MEGA_TOKEN      (token bearer da megaAPI)
    - SESSIONS        (lista com instance_key, instance_token, phone, lid)
    - OPENAI_API_KEY  (opcional, so pra audio)
- NAO abra config.py com cat. NAO mostre tokens em chat. Apenas instrua o
  usuario a abrir no editor preferido (notepad, code, vim).
- Pergunte se ele ja tem credencial do gateway WhatsApp (megaAPI por
  padrao, em https://megaapi.io, ou qualquer backend megaAPI-compativel —
  ver docs/API_CONTRACT.md). Se nao tiver, aponte o site do gateway,
  pede pra criar uma instancia, e volte com host + instance_key +
  instance_token + numero WhatsApp em mao.

PASSO 6 — Rodar bootstrap
- Quando o usuario confirmar que config.py esta preenchido, rode:
    python scripts/bootstrap.py
  (Windows) ou
    python3 scripts/bootstrap.py
  (Linux/macOS).
- Bootstrap sobe webhook + Quick Tunnel + registra URL na megaAPI.
- Mostre o output ao usuario. URL publica vai aparecer como
  `https://<random>.trycloudflare.com`.

PASSO 7 — Ativar agente
- Diga ao usuario para abrir OUTRO terminal, fazer `cd zyon`, rodar `claude`,
  e colar:
    Leia CLAUDE_PROMPT.md e execute o prompt do passo 2. SESSAO: 1
- A primeira mensagem WhatsApp para o proprio numero deve ser respondida
  pelo agente.

PASSO 8 — Verificacao final
- Rode: python -m whatsapp_agent.doctor
- Espere ver tudo OK. Se algo falhar, leia TROUBLESHOOTING.md e instrua
  o usuario.

REGRAS GERAIS:
- Anuncie cada comando ANTES de rodar.
- NAO rode comandos destrutivos (rm -rf, format, drop) sem perguntar.
- Se algum passo falhar, PARE e mostre o erro completo ao usuario antes
  de tentar workaround.
- Em Windows, use forward slashes em paths Python; bash do Git Bash entende.
- Quando precisar de credenciais (MEGA_TOKEN, OPENAI_API_KEY), instrua o
  usuario a digita-las no editor — nunca peca para ele colar no chat.

Comece pelo PASSO 0 agora.
```

---

## Notas

- O prompt assume Claude Code rodando com Bash tool habilitado.
- Em Windows, recomenda-se Git Bash ou PowerShell (ambos funcionam).
- Permissoes admin podem ser necessarias para `winget`/`brew`/`apt` —
  Claude vai pausar e pedir o usuario rodar manualmente quando preciso.
- O gateway WhatsApp (megaAPI em https://megaapi.io por padrao, ou
  qualquer backend compativel) exige conta criada previamente. O
  instalador NAO automatiza isso — usuario precisa ter credenciais em
  mao antes de rodar PASSO 5.
- Para Trilha 2 (VPS 24/7) o fluxo e diferente — ver
  `docs/DEPLOY_24_7_LINUX.md` (runbook canonico, testado em Ubuntu 24.04).
  Requer `claude --dangerously-skip-permissions` em producao.
