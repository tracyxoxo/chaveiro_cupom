from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import textwrap

LOJA_NOME = "CHAVEIRO BROTERO"
CNPJ = "33.198.084/0001-79"
ENDERECO = "Rua Conselheiro Brotero, 946"
TELEFONES = "Tel: (11) 3825-4871  Cel: (11) 99112-3798"
MENSAGEM_RODAPE = "Obrigado pela preferência!"
LARGURA_COLUNAS = 32


@dataclass
class ItemCupom:
    descricao: str
    quantidade: int
    valor_unitario: Decimal


class CupomFormatter:
    def __init__(self, largura: int = LARGURA_COLUNAS):
        self.largura = max(24, int(largura))
        self.sep = "-" * self.largura

    @staticmethod
    def _fmt_money(valor: Decimal) -> str:
        quant = valor.quantize(Decimal("0.01"))
        inteiro, frac = f"{quant:.2f}".split(".")
        inteiro_pt = f"{int(inteiro):,}".replace(",", ".")
        return f"R$ {inteiro_pt},{frac}"

    def _center(self, texto: str) -> str:
        return texto.center(self.largura)

    def _wrap(self, texto: str) -> list[str]:
        return textwrap.wrap(texto, width=self.largura, break_long_words=True)

    def montar(
        self,
        itens: list[ItemCupom],
        samaritano: bool,
        numero_os: str | None = None,
        quando: datetime | None = None,
    ) -> str:
        quando = quando or datetime.now()
        linhas: list[str] = []

        # Cabeçalho
        linhas.append(self.sep)
        linhas.append(self._center(LOJA_NOME))
        linhas.append(f"CNPJ: {CNPJ}")
        linhas.append(ENDERECO)
        linhas.append(TELEFONES)
        if samaritano:
            linhas.append(self._center("SERVICO SAMARITANO"))
        linhas.append(self.sep)

        # Corpo (itens)
        total = Decimal("0.00")
        for item in itens:
            subtotal = item.valor_unitario * item.quantidade
            total += subtotal
            linha_base = f"{item.quantidade}x {item.descricao.strip()} - {self._fmt_money(subtotal)}"
            desc_wrapped = self._wrap(linha_base)
            linhas.extend(desc_wrapped)

        # Número da OS (se Samaritano)
        if samaritano and numero_os:
            linhas.append(self.sep)
            linhas.append(f"OS: {numero_os}")

        # Total e rodapé
        linhas.append(self.sep)
        linhas.append(f"Total: {self._fmt_money(total)}")
        linhas.append(self.sep)
        linhas.append(f"Data: {quando.strftime('%d/%m/%Y %H:%M')}")
        linhas.append(MENSAGEM_RODAPE)
        linhas.append(self.sep)

        return "\n".join(linhas) + "\n"
