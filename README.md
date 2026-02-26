# Lexia WhatsApp Agent

Agente de IA integrado com WhatsApp Business API, construído com o Google Agent Development Kit (ADK) e implantado no Google Cloud Run.

## Características

- **ADK Integration**: Utiliza o framework Google ADK para criar agentes de IA sofisticados
- **WhatsApp Business API**: Integração completa com Meta WhatsApp Business API
- **Cloud Run Deployment**: Implantação serverless no Google Cloud Run
- **Webhook Support**: Suporte para webhooks de entrada e saída
- **Async Processing**: Processamento assíncrono de mensagens

## Requisitos

- Python 3.10+
- Google Cloud Project com credenciais de serviço
- Meta WhatsApp Business Account com credenciais de API
- Docker (para implantação em contêiner)

## Instalação Local

### 1. Clonar o repositório

```bash
git clone <seu-repositorio-github>
cd lexia-whatsapp-agent/whatsapp_agent
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas credenciais
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Executar localmente

```bash
python main.py
```

O agente estará disponível em `http://localhost:8080`

## Configuração

### Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `PHONE_NUMBER_ID` | ID do número de telefone WhatsApp | `551528574703551` |
| `VERIFY_TOKEN` | Token de verificação do webhook | `lexia-aoc-2602` |
| `WABA_ID` | ID da conta WhatsApp Business | `535733579621373` |
| `WHATSAPP_ACCESS_TOKEN` | Token de acesso da Meta API | `EAASODqDoBJU...` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Caminho para arquivo de credenciais GCP | `/path/to/key.json` |

### Variáveis de Ambiente Opcionais

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `PORT` | Porta para o servidor | `8080` |
| `ENVIRONMENT` | Ambiente de execução | `production` |
| `LOG_LEVEL` | Nível de logging | `INFO` |
| `ADK_MODEL` | Modelo Gemini a utilizar | `gemini-2.5-flash` |

## Endpoints da API

### GET `/health`

Verifica a saúde do serviço.

**Resposta:**
```json
{
  "status": "healthy",
  "service": "Lexia WhatsApp Agent",
  "version": "1.0.0"
}
```

### GET `/webhook`

Verifica o webhook com Meta (GET verification).

**Parâmetros:**
- `hub.verify_token`: Token de verificação
- `hub.challenge`: Desafio da Meta

### POST `/webhook`

Recebe mensagens do WhatsApp Business API.

**Payload esperado:**
```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "changes": [
        {
          "value": {
            "messages": [
              {
                "from": "551199999999",
                "id": "wamid.xxx",
                "type": "text",
                "text": {
                  "body": "Olá!"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

### GET `/`

Retorna informações do serviço.

## Implantação no Google Cloud Run

### 1. Configurar o Google Cloud

```bash
gcloud auth activate-service-account --key-file=path/to/service-account-key.json
gcloud config set project lexia-platform-488308
gcloud auth configure-docker southamerica-east1-docker.pkg.dev
```

### 2. Criar repositório no Artifact Registry

```bash
gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker \
  --location=southamerica-east1 \
  --description="Cloud Run Docker repository"
```

### 3. Construir e enviar imagem Docker

```bash
docker build -t southamerica-east1-docker.pkg.dev/lexia-platform-488308/cloud-run-source-deploy/lexia-whatsapp-agent:latest .
docker push southamerica-east1-docker.pkg.dev/lexia-platform-488308/cloud-run-source-deploy/lexia-whatsapp-agent:latest
```

### 4. Implantar no Cloud Run

```bash
gcloud run deploy lexia-whatsapp-agent \
  --image=southamerica-east1-docker.pkg.dev/lexia-platform-488308/cloud-run-source-deploy/lexia-whatsapp-agent:latest \
  --region=southamerica-east1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars=PHONE_NUMBER_ID=551528574703551,VERIFY_TOKEN=lexia-aoc-2602,WABA_ID=535733579621373,WHATSAPP_ACCESS_TOKEN=seu_token_aqui \
  --memory=1Gi \
  --cpu=1 \
  --timeout=3600
```

## Configuração do Webhook no Meta Business Suite

### 1. Acessar Meta Business Suite

1. Acesse https://business.facebook.com
2. Navegue para seu aplicativo Meta
3. Vá para "Configurações" → "Webhooks"

### 2. Configurar Webhook

1. Clique em "Editar Webhook"
2. Insira a URL do Cloud Run: `https://seu-cloud-run-url/webhook`
3. Insira o token de verificação: `lexia-aoc-2602`
4. Selecione os campos: `messages`, `message_status`, `message_template_status_update`
5. Clique em "Verificar e Salvar"

### 3. Inscrever Conta WhatsApp Business

1. Vá para "Configurações" → "Aplicativos"
2. Selecione seu aplicativo Meta
3. Clique em "Inscrever" para sua conta WhatsApp Business

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Business API                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                    Webhook POST
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Google Cloud Run (Lexia Agent)                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  FastAPI Application                                   │ │
│  │  ├─ /webhook (POST) - Recebe mensagens                │ │
│  │  ├─ /webhook (GET) - Verifica webhook                 │ │
│  │  ├─ /health - Health check                            │ │
│  │  └─ / - Info endpoint                                 │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Google ADK Agent                                      │ │
│  │  ├─ Model: Gemini 2.5 Flash                           │ │
│  │  ├─ Tools & Skills                                    │ │
│  │  └─ Session Management                                │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Meta API Client                                       │ │
│  │  └─ Envia respostas para WhatsApp                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                         │
                  HTTP POST Response
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp User                            │
└─────────────────────────────────────────────────────────────┘
```

## Fluxo de Mensagens

1. **Recebimento**: Usuário envia mensagem no WhatsApp
2. **Webhook**: Meta envia POST para `/webhook` do Cloud Run
3. **Processamento**: ADK Agent processa a mensagem
4. **Resposta**: Agente gera resposta via Gemini API
5. **Envio**: Resposta é enviada de volta via Meta API
6. **Confirmação**: Mensagem é marcada como lida

## Troubleshooting

### Webhook não está recebendo mensagens

1. Verifique se a URL do webhook está correta no Meta Business Suite
2. Confirme se o token de verificação está correto
3. Verifique os logs do Cloud Run: `gcloud run logs read lexia-whatsapp-agent --region=southamerica-east1`

### Mensagens não estão sendo enviadas

1. Verifique se o `WHATSAPP_ACCESS_TOKEN` é válido
2. Confirme se o `PHONE_NUMBER_ID` está correto
3. Verifique se a conta WhatsApp Business está ativa
4. Consulte os logs para mensagens de erro

### Erros de autenticação no Google Cloud

1. Verifique se as credenciais de serviço são válidas
2. Confirme se o projeto GCP está ativo
3. Verifique as permissões da conta de serviço

## Logs e Monitoramento

### Ver logs do Cloud Run

```bash
gcloud run logs read lexia-whatsapp-agent --region=southamerica-east1 --limit=100
```

### Monitorar em tempo real

```bash
gcloud run logs read lexia-whatsapp-agent --region=southamerica-east1 --follow
```

## Contribuindo

Para contribuir com melhorias, abra uma issue ou pull request no repositório GitHub.

## Licença

Este projeto é licenciado sob a Apache License 2.0 - veja o arquivo LICENSE para detalhes.

## Suporte

Para suporte, entre em contato através do GitHub Issues ou envie um email para support@lexia.com.br
