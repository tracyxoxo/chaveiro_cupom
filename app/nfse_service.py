# app/nfse_service.py
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

# Adiciona o diretório raiz ao path para importar nfse_client
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from nfse_client import NFSeClient
    _HAS_NFSE = True
except ImportError:
    _HAS_NFSE = False
    NFSeClient = object  # type: ignore


class NFSeService:
    """Serviço para emissão de Nota Fiscal de Serviços Eletrônica (NFSe)"""

    def __init__(self):
        if not _HAS_NFSE:
            raise RuntimeError("Biblioteca nfse_client não encontrada. Certifique-se de que nfse_client.py está no diretório raiz.")
        
        # Credenciais estáticas (configurar via variáveis de ambiente)
        # Você pode definir essas variáveis no sistema ou criar um arquivo .env
        self.inscricao = "33.198.084/0001-79"
        self.senha = "Chaveiro24"
        self.servico_id = "0cc05183-d497-4745-bba7-842c283a7ca7"
        
        if not self.inscricao or not self.senha:
            raise RuntimeError(
                "Credenciais NFSe não configuradas. "
                "Defina NFSE_INSCRICAO e NFSE_SENHA nas variáveis de ambiente. "
                "Exemplo: set NFSE_INSCRICAO=seu_numero && set NFSE_SENHA=sua_senha"
            )

    def emitir_nota(
        self,
        cpf_cnpj: str,
        data_competencia: datetime,
        valor: str,
        descricao: str,
    ) -> bytes:
        """
        Emite uma nota fiscal e retorna o PDF da DANFSE
        
        Args:
            cpf_cnpj: CPF ou CNPJ do tomador (apenas números)
            data_competencia: Data de competência da nota
            valor: Valor do serviço (formato: "20.00")
            descricao: Descrição do serviço
            
        Returns:
            bytes: Conteúdo do PDF da DANFSE
        """
        # Remove formatação do CPF/CNPJ
        tomador = cpf_cnpj.replace(".", "").replace("-", "").replace("/", "")
        
        client = NFSeClient()
        
        # Login
        client.login(self.inscricao, self.senha)
        
        # Abre contexto de emissão
        client.abrir_emissao(data_competencia)
        
        # Busca informações do tomador
        client.lookup_tomador(tomador)
        
        # Prepara dados da nota
        dados = {
            "EmitenteEhMEINaDataAtual": "True",
            "IdServicoFavorito": self.servico_id,
            "ValorServico": valor,
            "Descricao": descricao,
            "HaRetencaoISSQNNaFonte": "0"
        }
        
        # Emite a nota
        client.emitir_nota(dados, data_competencia)
        
        # Baixa o PDF (em memória)
        if not client.ultima_nota_id:
            raise Exception("Nota emitida mas ID não foi capturado")
        
        url = (
            "https://www.nfse.gov.br"
            f"/EmissorNacional/Notas/Download/DANFSe/{client.ultima_nota_id}"
        )
        
        response = client.session.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Erro ao baixar DANFSe: {response.status_code}")
        
        # Retorna o conteúdo do PDF
        return response.content
