# Configuração de Emissão de NFSe

## Requisitos

1. Ter credenciais de acesso ao portal NFSe.gov.br
2. Ter um serviço favorito cadastrado no portal
3. Configurar as variáveis de ambiente

## Configuração

### Windows (CMD)
```cmd
set NFSE_INSCRICAO=xxxxx
set NFSE_SENHA=xxx
set NFSE_SERVICO_ID=0cc05183-d497-4745-bba7-842c283a7ca7
```

### Windows (PowerShell)
```powershell
$env:NFSE_INSCRICAO="xxx"
$env:NFSE_SENHA="xxxx"
$env:NFSE_SERVICO_ID="0cc05183-d497-4745-bba7-842c283a7ca7"
```

### Linux/Mac
```bash
export NFSE_INSCRICAO=seu_numero_de_inscricao
export NFSE_SENHA=sua_senha
export NFSE_SERVICO_ID=0cc05183-d497-4745-bba7-842c283a7ca7
```

## Como Usar

1. Preencha os itens do cupom normalmente
2. Marque a opção "Emitir Nota Fiscal (NFSe)"
3. Preencha o CPF ou CNPJ do tomador (com ou sem formatação)
4. Clique em "Emitir cupom"
5. Se a emissão for bem-sucedida, aparecerá um botão para baixar o PDF da DANFSE

## Observações

- O CPF/CNPJ é validado automaticamente (deve ter 11 ou 14 dígitos)
- A descrição da nota será gerada automaticamente com base nos itens do cupom
- O valor será calculado automaticamente como a soma dos itens
- A data de competência será a data atual
- Se houver erro na emissão da NFSe, o cupom ainda será emitido normalmente
