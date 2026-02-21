# 🔑 Chaveiro Brotero - Sistema de Cupons

> 📖 **English:** [Read in English](README.en.md)

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg) ![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Sistema completo para emissão de cupons fiscais com integração a impressora ESC/POS, emissão de NFSe e armazenamento em nuvem**

[Funcionalidades](#-funcionalidades) • [Instalação](#-instalação) • [Configuração](#-configuração) • [Uso](#-como-usar) • [Documentação](#-documentação)

</div>

---

## Screenshots

![Tela Inicial]()

<!-- 
Exemplo de como adicionar screenshots:
![Tela Principal](docs/screenshots/main-screen.png)
![Histórico](docs/screenshots/history.png)
![Emissão NFSe](docs/screenshots/nfse.png)
-->

##  Funcionalidades

### 🧾 Emissão de Cupons
-  Interface web moderna e responsiva
-  Suporte a múltiplos itens por cupom
-  Cálculo automático de totais
-  Pré-visualização antes de emitir
-  Impressão direta em impressoras ESC/POS
-  Salvamento automático em arquivo .txt

### 🏥 Cupons Customizáveis
-  Modo especial para serviços customizáveis
-  Campo obrigatório para número da OS
-  Formatação diferenciada no cupom
-  Relatórios específicos por período

### 📄 Nota Fiscal de Serviços Eletrônica (NFSe)
-  Emissão automática de NFSe via portal NFSe.gov.br
-  Busca automática de razão social do tomador
-  Geração de PDF da DANFSE
-  Upload automático para Google Drive
-  Link público para compartilhamento
-  Integração com WhatsApp para envio ao cliente
-  Nome do arquivo: `DANFSE_RAZAOSOCIAL_data.pdf`

### 📊 Histórico e Relatórios
-  Histórico completo de todos os cupons emitidos
-  Visualização paginada do histórico
-  Cancelamento de cupons
-  Relatórios por período
-  Fechamento de caixa diário
-  Relatórios específicos para nota customizada
-  Exportação em HTML para impressão/PDF

### 🎨 Interface
-  Design moderno e intuitivo
-  Modo escuro/claro
-  Responsivo (funciona em tablets e celulares)
-  Feedback visual em todas as ações
-  Histórico com badges visuais (Padrão/Customizado/NFSe)

## 🚀 Instalação

### Pré-requisitos

- Python 3.10 ou superior
- Impressora ESC/POS (opcional, para impressão física)
- Conta no portal NFSe.gov.br (opcional, para emissão de notas fiscais)
- Conta Google com Google Drive (opcional, para armazenamento de PDFs)

### Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/chaveiro_cupom.git
   cd chaveiro_cupom
   ```

2. **Crie um ambiente virtual**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r app/requirements.txt
   ```

4. **Configure as variáveis de ambiente**
   
   Copie o arquivo `.env.example` e configure conforme suas necessidades:
   ```bash
   # Windows
   copy .env.example .env

   # Linux/Mac
   cp .env.example .env
   ```

   Edite o arquivo `.env` ou configure as variáveis de ambiente diretamente.

## ⚙️ Configuração

### 1. Histórico de Cupons (Opcional)

Configure o diretório onde o histórico será salvo. Recomenda-se usar uma pasta sincronizada na nuvem (OneDrive, Dropbox, etc.):

```bash
# Windows
set HISTORICO_CUPONS_DIR=C:\Users\SeuUsuario\OneDrive\Chaveiro

# Linux/Mac
export HISTORICO_CUPONS_DIR=/home/usuario/Dropbox/Chaveiro
```

**Arquivo**: `app/history.py` (linha 16)

### 2. Google Drive (Opcional - para upload de NFSe)

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative a API do Google Drive
4. Vá em **APIs & Services > Credentials**
5. Crie uma **OAuth 2.0 Client ID** do tipo **Desktop app**
6. Baixe o arquivo JSON e salve como `app/client_secrets.json`
7. Configure a pasta do Drive em `app/drive_upload.py` (linha 60)

**Nota**: Na primeira execução, o sistema abrirá o navegador para autorização. Um arquivo `token.json` será criado automaticamente.

### 3. NFSe - Nota Fiscal de Serviços Eletrônica (Opcional)

Configure suas credenciais do portal NFSe.gov.br:

```bash
# Windows
set NFSE_INSCRICAO=seu_numero_de_inscricao
set NFSE_SENHA=sua_senha
set NFSE_SERVICO_ID=id_do_servico_favorito

# Linux/Mac
export NFSE_INSCRICAO=seu_numero_de_inscricao
export NFSE_SENHA=sua_senha
export NFSE_SERVICO_ID=id_do_servico_favorito
```

**Arquivo**: `app/nfse_service.py` (linhas 31-33)

**Importante**: Você precisa ter um serviço favorito cadastrado no portal NFSe.gov.br. O ID do serviço pode ser encontrado após cadastrá-lo.

📖 **Guia completo**: Veja [NFSE_SETUP.md](NFSE_SETUP.md) para mais detalhes.

### 4. Impressora ESC/POS (Opcional)

O sistema detecta automaticamente impressoras USB compatíveis. Se necessário, configure manualmente:

```bash
set USB_VENDOR_ID=0x04e8
set USB_PRODUCT_ID=0x0202
set PRINTER_BACKEND=usb
```

##  Como Usar

### Iniciar o Servidor

**Windows:**
```bash
start_chaveiro.bat
```

**Linux/Mac:**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O sistema abrirá automaticamente em `http://127.0.0.1:8000`

### Emitir um Cupom

1. Acesse a interface web
2. Preencha os itens do cupom:
   - Descrição do serviço
   - Quantidade
   - Valor unitário
3. (Opcional) Marque "Serviço customizado" e informe o número da OS
4. (Opcional) Marque "Emitir Nota Fiscal (NFSe)" e informe o CPF/CNPJ do tomador
5. Clique em "Pré-visualizar" para ver como ficará o cupom
6. Clique em "Emitir cupom" para imprimir e salvar

### Emitir NFSe

1. Marque a opção "Emitir Nota Fiscal (NFSe)"
2. Preencha o CPF ou CNPJ do tomador (com ou sem formatação)
3. (Opcional) Marque "Imprimir nota fiscal na impressora" se desejar impressão física
4. Clique em "Emitir cupom"
5. Após a emissão, você terá:
   - PDF da DANFSE disponível para download
   - Link do Google Drive (se configurado)
   - Botão para enviar por WhatsApp

### Visualizar Histórico

- O histórico aparece automaticamente na página principal
- Use "Carregar mais" para ver cupons antigos
- Clique em "Detalhes" para ver informações completas
- Use "Cancelar" para cancelar um cupom (muda status para CANCELADO)

### Relatórios

1. Clique em "Relatórios" no menu lateral
2. Escolha o tipo de relatório:
   - **Por Período**: Filtre por data inicial/final e status
   - **Fechamento de Caixa**: Relatório do dia atual
   - **Fechamento Customizado**: Relatório específico para serviços com ordem de serviço
3. Visualize os resultados e exporte em HTML/PDF usando Ctrl+P

## 📁 Estrutura do Projeto

```
chaveiro_cupom/
├── app/
│   ├── static/
│   │   └── style.css          # Estilos CSS
│   ├── templates/
│   │   ├── index.html         # Interface principal
│   │   └── relatorios.html    # Página de relatórios
│   ├── cupom_core.py          # Lógica de formatação de cupons
│   ├── drive_upload.py        # Integração com Google Drive
│   ├── history.py             # Gerenciamento de histórico
│   ├── main.py                # API FastAPI principal
│   ├── nfse_client.py         # Cliente HTTP para NFSe.gov.br
│   ├── nfse_service.py        # Serviço de emissão de NFSe
│   ├── printer.py             # Integração com impressora ESC/POS
│   ├── requirements.txt       # Dependências Python
│   └── client_secrets.json    # Credenciais Google OAuth (não versionado)
├── _cupons/                   # Cupons padrão salvos (.txt)
├── _nfse/                     # PDFs de NFSe temporários
├── arquitetura.md             # Documentação de arquitetura
├── NFSE_SETUP.md             # Guia de configuração NFSe
├── .env.example              # Exemplo de variáveis de ambiente
├── start_chaveiro.bat        # Script de inicialização (Windows)
└── README.md                  # Este arquivo
```

##  Tecnologias

- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno e rápido
- **[Uvicorn](https://www.uvicorn.org/)** - Servidor ASGI
- **[Jinja2](https://jinja.palletsprojects.com/)** - Engine de templates
- **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** - Parsing HTML (NFSe)
- **[Requests](https://requests.readthedocs.io/)** - Cliente HTTP
- **[Google API Python Client](https://github.com/googleapis/google-api-python-client)** - Integração Google Drive
- **[Python ESC/POS](https://github.com/python-escpos/python-escpos)** - Comunicação com impressoras

##  Documentação

- **[Arquitetura do Sistema](arquitetura.md)** - Documentação técnica completa
- **[Configuração NFSe](NFSE_SETUP.md)** - Guia passo a passo para configurar NFSe

##  Segurança

- Credenciais sensíveis não devem ser commitadas no repositório
- Use variáveis de ambiente para configurações sensíveis
- O arquivo `token.json` (Google OAuth) é gerado automaticamente e não deve ser compartilhado
- O arquivo `client_secrets.json` contém credenciais OAuth e não deve ser versionado

##  Troubleshooting

### Impressora não imprime
- Verifique se a impressora está conectada e ligada
- Tente desconectar e reconectar o cabo USB
- O sistema salvará o cupom em arquivo .txt mesmo se a impressora falhar

### NFSe não emite
- Verifique se as credenciais estão corretas
- Confirme que o serviço favorito está cadastrado no portal
- Verifique os logs no console para mensagens de erro específicas
- O cupom será emitido normalmente mesmo se a NFSe falhar

### Google Drive não faz upload
- Verifique se o arquivo `client_secrets.json` está presente
- Confirme que a API do Google Drive está ativada
- Verifique se a pasta do Drive está configurada corretamente
- Na primeira execução, autorize o acesso quando o navegador abrir

### Histórico não aparece
- Verifique se o diretório configurado existe e tem permissões de escrita
- Confirme que o arquivo `historico_cupons.json` pode ser criado/escrito

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abrir um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👤 Autor

**Matheus Silvestre**

---

<div align="center">

**⭐ Se este projeto foi útil para você, considere dar uma estrela! ⭐**

Feito com ❤️ para facilitar a gestão de cupons fiscais

</div>
