from __future__ import annotations
from pathlib import Path

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .cupom_core import CupomFormatter, ItemCupom
from .printer import PrinterService
from .history import HistoryService

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="Chaveiro Brotero - Cupom")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

formatter = CupomFormatter()
printer_service = PrinterService()
history_service = HistoryService()


def _format_money_br(valor_str: str) -> str:
    """Formata valor em string para formato brasileiro (R$ x.xxx,xx)"""
    try:
        valor = Decimal(valor_str)
        inteiro = int(valor)
        centavos = int((valor - Decimal(inteiro)) * 100)
        inteiro_str = f"{inteiro:,}".replace(",", ".")
        return f"{inteiro_str},{centavos:02d}"
    except Exception:
        return valor_str.replace(".", ",")


def _format_history_for_template(historico: List[dict]) -> List[dict]:
    """Formata o histórico para exibição no template"""
    historico_formatado = []
    for cupom in historico:
        cupom_formatted = cupom.copy()
        # Formata total
        cupom_formatted["total_formatado"] = _format_money_br(cupom["total"])
        # Formata valores dos itens
        for item in cupom_formatted["itens"]:
            item["valor_unitario_formatado"] = _format_money_br(item["valor_unitario"])
        historico_formatado.append(cupom_formatted)
    return historico_formatado



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Carrega histórico para exibir na página
    historico = history_service.get_history(limit=10)
    historico_formatado = _format_history_for_template(historico)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "itens": [],
            "preview_text": None,
            "msg": None,
            "error": None,
            "samaritano": False,
            "numero_os": "",
            "historico": historico_formatado,
        },
    )


def _parse_itens(
    descricoes: List[str],
    quantidades: List[str],
    valores: List[str],
):
    itens: list[ItemCupom] = []
    for desc, qtd_txt, val_txt in zip(descricoes, quantidades, valores):
        desc = (desc or "").strip()
        qtd_txt = (qtd_txt or "").strip()
        val_txt = (val_txt or "").strip().replace("R$", "").replace(" ", "").replace(",", ".")

        if not desc:
            continue
        if not qtd_txt and not val_txt:
            continue

        try:
            qtd = int(qtd_txt)
            valor = Decimal(val_txt)
            if qtd <= 0 or valor <= 0:
                raise InvalidOperation
        except Exception:
            raise ValueError(f"Item inválido: desc={desc}, qtd={qtd_txt}, valor={val_txt}")

        itens.append(ItemCupom(descricao=desc, quantidade=qtd, valor_unitario=valor))

    if not itens:
        raise ValueError("É necessário pelo menos um item válido.")
    return itens


@app.post("/preview", response_class=HTMLResponse)
async def preview(
    request: Request,
    descricao: List[str] = Form(default=[]),
    quantidade: List[str] = Form(default=[]),
    valor: List[str] = Form(default=[]),
    samaritano: Optional[str] = Form(default=None),
    numero_os: str = Form(default=""),
):
    samaritano_flag = samaritano is not None

    try:
        itens = _parse_itens(descricao, quantidade, valor)
        if samaritano_flag and not numero_os.strip():
            raise ValueError("Número da OS é obrigatório para serviços do Samaritano.")
        texto = formatter.montar(
            itens=itens,
            samaritano=samaritano_flag,
            numero_os=numero_os.strip() or None,
        )
        error = None
    except ValueError as e:
        itens = []
        texto = None
        error = str(e)

    # Carrega histórico para exibir na página
    historico = history_service.get_history(limit=10)
    historico_formatado = _format_history_for_template(historico)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "itens": list(zip(descricao, quantidade, valor)),
            "preview_text": texto,
            "msg": None,
            "error": error,
            "samaritano": samaritano_flag,
            "numero_os": numero_os,
            "historico": historico_formatado,
        },
    )


@app.post("/emitir", response_class=HTMLResponse)
async def emitir(
    request: Request,
    descricao: List[str] = Form(default=[]),
    quantidade: List[str] = Form(default=[]),
    valor: List[str] = Form(default=[]),
    samaritano: Optional[str] = Form(default=None),
    numero_os: str = Form(default=""),
):
    samaritano_flag = samaritano is not None

    try:
        itens = _parse_itens(descricao, quantidade, valor)
        if samaritano_flag and not numero_os.strip():
            raise ValueError("Número da OS é obrigatório para serviços do Samaritano.")

        texto = formatter.montar(
            itens=itens,
            samaritano=samaritano_flag,
            numero_os=numero_os.strip() or None,
        )

        # 🔽 agora passa pelo serviço de impressão
        printer_service.emitir(texto, samaritano_flag)

        # 🔽 salva no histórico
        history_service.add_cupom(
            itens=itens,
            texto_cupom=texto,
            samaritano=samaritano_flag,
            numero_os=numero_os.strip() or None,
        )

        msg = f"Cupom emitido com sucesso ({'Samaritano' if samaritano_flag else 'Padrão'})!"
        error = None
        preview_text = texto
    except ValueError as e:
        msg = None
        error = str(e)
        preview_text = None
    except RuntimeError as e:
        # Erro na impressão ESC/POS mas .txt salvo
        msg = None
        error = str(e)
        preview_text = texto if "texto" in locals() else None

    # Carrega histórico para exibir na página
    historico = history_service.get_history(limit=10)
    historico_formatado = _format_history_for_template(historico)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "itens": list(zip(descricao, quantidade, valor)),
            "preview_text": preview_text,
            "msg": msg,
            "error": error,
            "samaritano": samaritano_flag,
            "numero_os": numero_os,
            "historico": historico_formatado,
        },
    )


@app.get("/api/historico")
async def get_historico(limit: Optional[int] = None):
    """API endpoint para retornar o histórico de cupons"""
    historico = history_service.get_history(limit=limit)
    return JSONResponse(content=historico)

