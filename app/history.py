# app/history.py
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

from .cupom_core import ItemCupom

BASE_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = BASE_DIR / "historico_cupons.json"


class HistoryService:
    """Serviço para gerenciar histórico de cupons emitidos"""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file

    def _ensure_history_file(self) -> None:
        """Garante que o arquivo de histórico existe"""
        if not self.history_file.exists():
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _read_history(self) -> List[Dict[str, Any]]:
        """Lê o histórico completo do arquivo JSON"""
        self._ensure_history_file()
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_history(self, history: List[Dict[str, Any]]) -> None:
        """Escreve o histórico completo no arquivo JSON"""
        self._ensure_history_file()
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def add_cupom(
        self,
        itens: List[ItemCupom],
        texto_cupom: str,
        samaritano: bool,
        numero_os: str | None = None,
        data_emissao: datetime | None = None,
    ) -> Dict[str, Any]:
        """
        Adiciona um cupom ao histórico
        
        Returns:
            Dict com os dados do cupom salvo incluindo ID único
        """
        data_emissao = data_emissao or datetime.now()
        
        # Calcula total
        total = sum(item.valor_unitario * item.quantidade for item in itens)
        
        # Serializa itens para JSON (Decimal -> str)
        itens_data = [
            {
                "descricao": item.descricao,
                "quantidade": item.quantidade,
                "valor_unitario": str(item.valor_unitario),
            }
            for item in itens
        ]
        
        # Cria entrada do cupom
        cupom_entry = {
            "id": data_emissao.strftime("%Y%m%d_%H%M%S_%f"),
            "data_emissao": data_emissao.isoformat(),
            "data_emissao_formatada": data_emissao.strftime("%d/%m/%Y %H:%M"),
            "samaritano": samaritano,
            "numero_os": numero_os,
            "itens": itens_data,
            "total": str(total),
            "texto_cupom": texto_cupom,
            "status": "ATIVO",  # Novo cupom sempre começa como ATIVO
        }
        
        # Lê histórico atual
        history = self._read_history()
        
        # Migra cupons antigos sem status para ATIVO
        for cupom in history:
            if "status" not in cupom:
                cupom["status"] = "ATIVO"
        
        # Adiciona novo cupom no início (mais recente primeiro)
        history.insert(0, cupom_entry)
        
        # Salva histórico
        self._write_history(history)
        
        return cupom_entry

    def get_history(self, limit: int | None = None) -> List[Dict[str, Any]]:
        """
        Retorna o histórico de cupons
        
        Args:
            limit: Número máximo de cupons a retornar (None = todos)
            
        Returns:
            Lista de cupons ordenados do mais recente para o mais antigo
        """
        history = self._read_history()
        
        # Migra cupons antigos sem status para ATIVO
        needs_save = False
        for cupom in history:
            if "status" not in cupom:
                cupom["status"] = "ATIVO"
                needs_save = True
        
        if needs_save:
            self._write_history(history)
        
        if limit is not None:
            return history[:limit]
        return history

    def get_cupom_by_id(self, cupom_id: str) -> Dict[str, Any] | None:
        """Retorna um cupom específico pelo ID"""
        history = self._read_history()
        for cupom in history:
            if cupom.get("id") == cupom_id:
                return cupom
        return None

    def cancelar_cupom(self, cupom_id: str) -> bool:
        """
        Cancela um cupom (muda status para CANCELADO)
        
        Returns:
            True se o cupom foi cancelado, False se não foi encontrado
        """
        history = self._read_history()
        for cupom in history:
            if cupom.get("id") == cupom_id:
                cupom["status"] = "CANCELADO"
                self._write_history(history)
                return True
        return False

    def get_relatorio_periodo(
        self,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
        status: str | None = None,
    ) -> Dict[str, Any]:
        """
        Gera relatório de cupons por período
        
        Args:
            data_inicio: Data inicial do período (None = sem limite)
            data_fim: Data final do período (None = sem limite)
            status: Filtrar por status ("ATIVO", "CANCELADO", None = todos)
            
        Returns:
            Dict com lista de cupons e totais
        """
        history = self._read_history()
        cupons_filtrados = []
        total_ativos = Decimal("0.00")
        total_cancelados = Decimal("0.00")
        
        for cupom in history:
            # Migra cupons antigos sem status
            if "status" not in cupom:
                cupom["status"] = "ATIVO"
            
            # Filtro por status
            if status and cupom.get("status") != status:
                continue
            
            # Filtro por data
            data_emissao = datetime.fromisoformat(cupom["data_emissao"])
            if data_inicio and data_emissao < data_inicio:
                continue
            if data_fim and data_emissao > data_fim:
                continue
            
            cupons_filtrados.append(cupom)
            
            # Soma totais
            total_cupom = Decimal(cupom["total"])
            if cupom.get("status") == "CANCELADO":
                total_cancelados += total_cupom
            else:
                total_ativos += total_cupom
        
        return {
            "cupons": cupons_filtrados,
            "total_ativos": str(total_ativos),
            "total_cancelados": str(total_cancelados),
            "total_geral": str(total_ativos + total_cancelados),
            "quantidade": len(cupons_filtrados),
        }

    def fechar_caixa_dia(self, data: datetime | None = None) -> Dict[str, Any]:
        """
        Gera relatório de fechamento de caixa do dia
        
        Args:
            data: Data do fechamento (None = hoje)
            
        Returns:
            Dict com relatório completo do dia
        """
        if data is None:
            data = datetime.now()
        
        # Início e fim do dia
        inicio_dia = data.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_dia = data.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_relatorio_periodo(data_inicio=inicio_dia, data_fim=fim_dia)
