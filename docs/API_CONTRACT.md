# WhatsApp HTTP API Contract (MBKCHAT / WuzAPI)

Este projeto usa a API **MBKCHAT** (baseada no [WuzAPI](https://github.com/asternic/wuzapi)).
Qualquer backend que implemente o contrato abaixo funciona como drop-in replacement.
Basta apontar `API_HOST` (definido no `setup_config`) para o host e o resto do codigo
permanece inalterado.

Este documento e a fonte da verdade. Se voce mantem um clone, sua
implementacao deve corresponder a cada campo e path aqui.

## Authentication

Toda chamada envia:

```
token: {USER_TOKEN}
```

`USER_TOKEN` e por usuario e fornecido ao wizard durante o setup.
O token e enviado como header HTTP — nao como Bearer token.

## Endpoints

Todos os paths sao relativos a `API_HOST` (ex: `https://mbkchat.com.br`).
Nao ha `{instance}` nos paths — o token no header identifica o usuario.

| Method | Path | Purpose | Caller |
|--------|------|---------|--------|
| POST | `/chat/send/text` | Send a text message | `send_message.py` |
| POST | `/chat/send/image` | Send an image (base64) | `send_message.py --type image` |
| POST | `/webhook` | Register the public webhook URL | `update_webhooks.py` |
| POST | `/chat/downloadimage` | Download media as base64 | `media_handler.py` |
| GET  | `/session/status` | Health check (connection status) | `doctor.py` |

## Outbound payloads

### Send text — `POST /chat/send/text`

```json
{
  "Phone": "5511999999999",
  "Body": "hello world\n\n*Claude Code*"
}
```

- `Phone`: digits-only phone number, country code first, no `+`.
- `Body`: full message body. The `*Claude Code*` signature is appended
  by `send_message.py` automatically — clones must NOT add their own
  signature.

Response:
```json
{"code": 200, "success": true, "data": {"Details": "Sent", "Id": "...", "Timestamp": "..."}}
```

### Send image — `POST /chat/send/image`

```json
{
  "Phone": "5511999999999",
  "Image": "data:image/jpeg;base64,iVBORw0KGgoAAAA...",
  "Caption": "optional caption\n\n*Claude Code*"
}
```

- `Image`: base64 string with `data:{mime};base64,` prefix.
- `Caption`: optional caption text.
- 16 MB cap enforced client-side before encoding.

### Configure webhook — `POST /webhook`

```json
{
  "webhook": "https://random-words.trycloudflare.com/?session=1",
  "events": ["Message"]
}
```

Successful response:
```json
{"code": 200, "success": true, "data": {...}}
```

The client checks `data.success is True` to declare success.

### Download media — `POST /chat/downloadimage`

```json
{
  "messageKeys": {
    "mediaKey": "...",
    "directPath": "/v/t62.7117-24/...",
    "url": "https://mmg.whatsapp.net/...",
    "mimetype": "audio/ogg; codecs=opus",
    "messageType": "audioMessage"
  }
}
```

Response:
```json
{"code": 200, "success": true, "data": {"base64": "data:audio/ogg;base64,..."}}
```

Nota: WuzAPI normalmente envia o base64 diretamente no payload do webhook.
O endpoint `/chat/downloadimage` e fallback para quando o base64 nao esta presente.

### Health check — `GET /session/status`

```json
{"code": 200, "success": true, "data": {"Connected": true, "LoggedIn": true}}
```

## Inbound webhook payload

O backend deve fazer POST de um JSON para a `webhookUrl` registrada para
cada mensagem WhatsApp recebida. O receiver (`webhook_server.py`)
le os seguintes campos:

```
Envelope:
  event                     string  "Message" (ignoramos outros eventos)
  instance                  string  JID da instancia (ignorado)
  data.id                   string  unique message id (usado para dedup)
  data.fromMe               bool    true se foi enviado PELO numero da instancia
  data.chat                 string  JID do chat (ex: "5511999999999@s.whatsapp.net")
  data.sender               string  JID do sender (fallback para chat)
  data.pushName             string  contact display name
  data.message.conversation                 string  plain text (when present)
  data.message.extendedTextMessage.text    string  formatted text (alternate)
  data.message.imageMessage.base64         string  base64-encoded image
  data.message.imageMessage.mimeType       string  e.g. "image/jpeg"
  data.message.imageMessage.caption        string  image caption
  data.message.audioMessage.base64         string  base64-encoded audio
  data.message.audioMessage.mimeType       string  e.g. "audio/ogg; codecs=opus"
  data.message.videoMessage.base64         string  base64-encoded video (rejected)
  data.message.videoMessage.mimeType       string  video mime type
  data.messageTimestamp     int     Unix timestamp (seconds)
```

O receiver detecta o tipo de mensagem examinando as chaves dentro de
`data.message` que correspondem a `audioMessage` / `imageMessage` /
`videoMessage`. Texto puro e detectado por `data.message.conversation`
ou `data.message.extendedTextMessage.text`.

### Exemplo de payload de texto:

```json
{
  "event": "Message",
  "instance": "5511999999999@s.whatsapp.net",
  "data": {
    "id": "MSG123",
    "fromMe": false,
    "chat": "5511999999999@s.whatsapp.net",
    "pushName": "Geo",
    "message": {"conversation": "ola"},
    "messageTimestamp": 1700000000
  }
}
```

### Exemplo de payload de imagem:

```json
{
  "event": "Message",
  "instance": "5511999999999@s.whatsapp.net",
  "data": {
    "id": "IMG456",
    "fromMe": false,
    "chat": "5511999999999@s.whatsapp.net",
    "pushName": "Geo",
    "message": {
      "imageMessage": {
        "base64": "data:image/jpeg;base64,/9j/4AAQ...",
        "mimeType": "image/jpeg",
        "caption": "veja isso"
      }
    },
    "messageTimestamp": 1700000000
  }
}
```

## Whitelist behavior

O receiver aplica uma whitelist de telefone (`config.ALLOWED_PHONE`) ANTES
de escrever na fila JSONL. Mensagens de outros numeros sao descartadas
silenciosamente. O backend nao precisa aplicar isso — e um filtro client-side.

## Phone number format

| Rule | Example |
|------|---------|
| Country code required | `5511999999999` |
| No `+` prefix | `5511999999999` |
| No spaces/dashes | `5511999999999` |
| JID format | `5511999999999@s.whatsapp.net` |
| LID format | `5511999999999@lid` |

## Versioning note

Este contrato reflete WuzAPI/MBKCHAT em 2026-05-11. Field names e paths
sao estaveis na API documentada do WuzAPI. Se um clone divergir, liste
as diferencas no README do clone e atualize este documento.
