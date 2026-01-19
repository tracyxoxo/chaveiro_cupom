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
        }
        
        # Lê histórico atual
        history = self._read_history()
        
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
