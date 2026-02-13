from __future__ import annotations
from pathlib import Path

import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Form, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .cupom_core import CupomFormatter, ItemCupom
from .printer import PrinterService
from .history import HistoryService
from .nfse_service import NFSeService

BASE_DIR = Path(__file__).resolve().parent.parent
app = FastAPI(title="Chaveiro Brotero - Cupom")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

formatter = CupomFormatter()
printer_service = PrinterService()
history_service = HistoryService()

# Inicializa serviço de NFSe (pode falhar se credenciais não estiverem configuradas)
try:
    nfse_service = NFSeService()
    _NFSE_AVAILABLE = True
except Exception as e:
    _NFSE_AVAILABLE = False
    print(f"Aviso: Serviço de NFSe não disponível: {e}")


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
            "emitir_nfse": False,
            "cpf_cnpj": "",
            "imprimir_nfse": False,
            "historico": historico_formatado,
        },
    )


@app.get("/relatorios", response_class=HTMLResponse)
async def relatorios(request: Request):
    """Página de relatórios"""
    return templates.TemplateResponse(
        "relatorios.html",
        {"request": request},
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
    emitir_nfse: Optional[str] = Form(default=None),
    cpf_cnpj: str = Form(default=""),
    imprimir_nfse: Optional[str] = Form(default=None),
):
    samaritano_flag = samaritano is not None
    emitir_nfse_flag = emitir_nfse is not None
    imprimir_nfse_flag = imprimir_nfse is not None

    try:
        itens = _parse_itens(descricao, quantidade, valor)
        if samaritano_flag and not numero_os.strip():
            raise ValueError("Número da OS é obrigatório para serviços do Samaritano.")
        if emitir_nfse_flag and not cpf_cnpj.strip():
            raise ValueError("CPF/CNPJ é obrigatório para emissão de Nota Fiscal.")
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
            "emitir_nfse": emitir_nfse_flag,
            "cpf_cnpj": cpf_cnpj,
            "imprimir_nfse": imprimir_nfse_flag,
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
    emitir_nfse: Optional[str] = Form(default=None),
    cpf_cnpj: str = Form(default=""),
    imprimir_nfse: Optional[str] = Form(default=None),
):
    samaritano_flag = samaritano is not None
    emitir_nfse_flag = emitir_nfse is not None
    imprimir_nfse_flag = imprimir_nfse is not None
    nfse_pdf_id = None

    try:
        itens = _parse_itens(descricao, quantidade, valor)
        if samaritano_flag and not numero_os.strip():
            raise ValueError("Número da OS é obrigatório para serviços do Samaritano.")
        if emitir_nfse_flag and not cpf_cnpj.strip():
            raise ValueError("CPF/CNPJ é obrigatório para emissão de Nota Fiscal.")

        texto = formatter.montar(
            itens=itens,
            samaritano=samaritano_flag,
            numero_os=numero_os.strip() or None,
        )


        printer_service.emitir(texto, samaritano_flag, save_only=emitir_nfse_flag)

        # 🔽 Emite NFSe se solicitado
        if emitir_nfse_flag and _NFSE_AVAILABLE:
            try:
                # Remove formatação do CPF/CNPJ
                cpf_cnpj_limpo = cpf_cnpj.replace(".", "").replace("-", "").replace("/", "").strip()
                
                # Valida CPF/CNPJ (deve ter 11 ou 14 dígitos)
                if len(cpf_cnpj_limpo) not in [11, 14]:
                    raise ValueError("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos.")
                
                # Calcula total e prepara descrição
                total = sum(item.valor_unitario * item.quantidade for item in itens)
                descricao_nfse = "; ".join([
                    f"{item.quantidade}x {item.descricao}"
                    for item in itens
                ])
                
                # Emite a nota
                pdf_content = nfse_service.emitir_nota(
                    cpf_cnpj=cpf_cnpj_limpo,
                    data_competencia=datetime.now(),
                    valor=str(total),
                    descricao=descricao_nfse,
                )
                
                # Salva PDF temporariamente e gera ID
                nfse_pdf_id = str(uuid.uuid4())
                pdf_path = BASE_DIR / "_nfse" / f"{nfse_pdf_id}.pdf"
                pdf_path.parent.mkdir(exist_ok=True)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_content)
                
                # Imprime a nota fiscal na impressora apenas se o usuário optou
                if imprimir_nfse_flag:
                    try:
                        printer_service.imprimir_pdf(pdf_path)
                    except Exception as e:
                        print(f"Aviso: não foi possível imprimir a NFSe: {e}")
                
            except ValueError as nfse_error:
                # Erro de validação - impede a emissão
                raise nfse_error
            except Exception as nfse_error:
                # Outros erros na NFSe não impedem a emissão do cupom
                print(f"Erro ao emitir NFSe: {nfse_error}")
                # Continua com a emissão do cupom mesmo se NFSe falhar

        # 🔽 salva no histórico (com id do PDF da NFSe quando existir)
        history_service.add_cupom(
            itens=itens,
            texto_cupom=texto,
            samaritano=samaritano_flag,
            numero_os=numero_os.strip() or None,
            nfse_pdf_id=nfse_pdf_id,
        )

        msg_parts = [f"Cupom emitido com sucesso ({'Samaritano' if samaritano_flag else 'Padrão'})!"]
        if emitir_nfse_flag:
            if nfse_pdf_id:
                msg_parts.append("Nota Fiscal emitida com sucesso!")
            elif not _NFSE_AVAILABLE:
                msg_parts.append("Aviso: Serviço de NFSe não disponível.")
            else:
                msg_parts.append("Aviso: Erro ao emitir Nota Fiscal (verifique os logs).")
        
        msg = " ".join(msg_parts)
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
            "emitir_nfse": emitir_nfse_flag,
            "cpf_cnpj": cpf_cnpj,
            "imprimir_nfse": imprimir_nfse_flag,
            "nfse_pdf_id": nfse_pdf_id,
            "historico": historico_formatado,
        },
    )


@app.get("/api/historico")
async def get_historico(
    limit: Optional[int] = None,
    offset: Optional[int] = Query(0, ge=0),
):
    """API endpoint para retornar o histórico de cupons (formatado para o template)."""
    historico = history_service.get_history(limit=limit, offset=offset)
    historico_formatado = _format_history_for_template(historico)
    return JSONResponse(content=historico_formatado)


@app.post("/api/cupom/{cupom_id}/cancelar")
async def cancelar_cupom(cupom_id: str):
    """Cancela um cupom (muda status para CANCELADO)"""
    sucesso = history_service.cancelar_cupom(cupom_id)
    if sucesso:
        return JSONResponse(content={"success": True, "message": "Cupom cancelado com sucesso"})
    else:
        return JSONResponse(
            content={"success": False, "message": "Cupom não encontrado"},
            status_code=404
        )


@app.get("/api/relatorio/periodo")
async def relatorio_periodo(
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filtrar por status (ATIVO, CANCELADO)"),
):
    """Gera relatório de cupons por período"""
    try:
        data_inicio_dt = None
        data_fim_dt = None
        
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        relatorio = history_service.get_relatorio_periodo(
            data_inicio=data_inicio_dt,
            data_fim=data_fim_dt,
            status=status,
        )
        
        # Formata valores para exibição
        relatorio["total_ativos_formatado"] = _format_money_br(relatorio["total_ativos"])
        relatorio["total_cancelados_formatado"] = _format_money_br(relatorio["total_cancelados"])
        relatorio["total_geral_formatado"] = _format_money_br(relatorio["total_geral"])
        
        # Formata cupons para exibição
        for cupom in relatorio["cupons"]:
            cupom["total_formatado"] = _format_money_br(cupom["total"])
            for item in cupom["itens"]:
                item["valor_unitario_formatado"] = _format_money_br(item["valor_unitario"])
        
        return JSONResponse(content=relatorio)
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


@app.get("/api/relatorio/fechar-caixa")
async def fechar_caixa(
    data: Optional[str] = Query(None, description="Data do fechamento (YYYY-MM-DD, padrão: hoje)"),
):
    """Gera relatório de fechamento de caixa do dia"""
    try:
        data_dt = None
        if data:
            data_dt = datetime.strptime(data, "%Y-%m-%d")
        
        relatorio = history_service.fechar_caixa_dia(data=data_dt)
        
        # Formata valores para exibição
        relatorio["total_ativos_formatado"] = _format_money_br(relatorio["total_ativos"])
        relatorio["total_cancelados_formatado"] = _format_money_br(relatorio["total_cancelados"])
        relatorio["total_geral_formatado"] = _format_money_br(relatorio["total_geral"])
        
        # Formata cupons para exibição
        for cupom in relatorio["cupons"]:
            cupom["total_formatado"] = _format_money_br(cupom["total"])
            for item in cupom["itens"]:
                item["valor_unitario_formatado"] = _format_money_br(item["valor_unitario"])
        
        # Adiciona data formatada
        data_relatorio = data_dt if data_dt else datetime.now()
        relatorio["data_formatada"] = data_relatorio.strftime("%d/%m/%Y")
        
        return JSONResponse(content=relatorio)
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


@app.get("/api/relatorio/periodo/pdf")
async def relatorio_periodo_pdf(
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filtrar por status (ATIVO, CANCELADO)"),
):
    """Gera PDF do relatório por período"""
    try:
        data_inicio_dt = None
        data_fim_dt = None
        
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        relatorio = history_service.get_relatorio_periodo(
            data_inicio=data_inicio_dt,
            data_fim=data_fim_dt,
            status=status,
        )
        
        # Gera HTML do relatório
        html_content = _gerar_html_pdf_periodo(relatorio, data_inicio_dt, data_fim_dt, status)
        
        # Retorna HTML formatado para impressão como PDF
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"inline; filename=relatorio_periodo_{data_inicio or 'periodo'}.html"
            }
        )
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


@app.get("/api/relatorio/fechar-caixa/pdf")
async def fechar_caixa_pdf(
    data: Optional[str] = Query(None, description="Data do fechamento (YYYY-MM-DD, padrão: hoje)"),
):
    """Gera PDF do relatório de fechamento de caixa do dia"""
    try:
        data_dt = None
        if data:
            data_dt = datetime.strptime(data, "%Y-%m-%d")
        
        relatorio = history_service.fechar_caixa_dia(data=data_dt)
        
        # Gera HTML do relatório
        html_content = _gerar_html_pdf_fechar_caixa(relatorio, data_dt)
        
        # Retorna HTML formatado para impressão como PDF
        data_str = data_dt.strftime("%Y-%m-%d") if data_dt else datetime.now().strftime("%Y-%m-%d")
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"inline; filename=fechamento_caixa_{data_str}.html"
            }
        )
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


@app.get("/api/relatorio/fechar-samaritano")
async def fechar_caixa_samaritano(
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filtrar por status (ATIVO, CANCELADO)"),
):
    """Gera relatório de fechamento de caixa apenas para serviços do Samaritano"""
    try:
        data_inicio_dt = None
        data_fim_dt = None
        
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        relatorio = history_service.fechar_caixa_samaritano(
            data_inicio=data_inicio_dt,
            data_fim=data_fim_dt,
            status=status,
        )
        
        # Formata valores para exibição
        relatorio["total_ativos_formatado"] = _format_money_br(relatorio["total_ativos"])
        relatorio["total_cancelados_formatado"] = _format_money_br(relatorio["total_cancelados"])
        relatorio["total_geral_formatado"] = _format_money_br(relatorio["total_geral"])
        
        # Formata cupons para exibição
        for cupom in relatorio["cupons"]:
            cupom["total_formatado"] = _format_money_br(cupom["total"])
            for item in cupom["itens"]:
                item["valor_unitario_formatado"] = _format_money_br(item["valor_unitario"])
        
        # Adiciona datas formatadas
        if data_inicio_dt:
            relatorio["data_inicio_formatada"] = data_inicio_dt.strftime("%d/%m/%Y")
        else:
            relatorio["data_inicio_formatada"] = "Início"
        
        if data_fim_dt:
            relatorio["data_fim_formatada"] = data_fim_dt.strftime("%d/%m/%Y")
        else:
            relatorio["data_fim_formatada"] = "Fim"
        
        relatorio["data_inicio"] = data_inicio or ""
        relatorio["data_fim"] = data_fim or ""
        relatorio["filtro_status"] = status or ""
        
        return JSONResponse(content=relatorio)
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


@app.get("/api/relatorio/fechar-samaritano/pdf")
async def fechar_caixa_samaritano_pdf(
    data_inicio: Optional[str] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data final (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filtrar por status (ATIVO, CANCELADO)"),
):
    """Gera PDF do relatório de fechamento de caixa Samaritano"""
    try:
        data_inicio_dt = None
        data_fim_dt = None
        
        if data_inicio:
            data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_inicio_dt = data_inicio_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if data_fim:
            data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
            data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        relatorio = history_service.fechar_caixa_samaritano(
            data_inicio=data_inicio_dt,
            data_fim=data_fim_dt,
            status=status,
        )
        
        # Gera HTML do relatório
        html_content = _gerar_html_pdf_samaritano(relatorio, data_inicio_dt, data_fim_dt, status)
        
        # Retorna HTML formatado para impressão como PDF
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f"inline; filename=fechamento_samaritano_{data_inicio or 'periodo'}.html"
            }
        )
    except ValueError as e:
        return JSONResponse(
            content={"error": f"Data inválida: {str(e)}"},
            status_code=400
        )


def _gerar_html_pdf_periodo(
    relatorio: Dict[str, Any],
    data_inicio: datetime | None,
    data_fim: datetime | None,
    status: str | None,
) -> str:
    """Gera HTML formatado para impressão/PDF do relatório por período"""
    data_inicio_str = data_inicio.strftime("%d/%m/%Y") if data_inicio else "Início"
    data_fim_str = data_fim.strftime("%d/%m/%Y") if data_fim else "Fim"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Relatório por Período</title>
        <style>
            @media print {{
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #3498db;
                margin: 0;
            }}
            .info {{
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }}
            .totais {{
                display: flex;
                justify-content: space-around;
                margin: 30px 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
            }}
            .total-item {{
                text-align: center;
            }}
            .total-item strong {{
                display: block;
                font-size: 1.5em;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            .status-ativo {{
                color: #27ae60;
                font-weight: bold;
            }}
            .status-cancelado {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                font-size: 0.9em;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CHAVEIRO BROTERO</h1>
            <h2>Relatório por Período</h2>
        </div>
        
        <div class="info">
            <p><strong>Período:</strong> {data_inicio_str} a {data_fim_str}</p>
            <p><strong>Status:</strong> {status if status else 'Todos'}</p>
            <p><strong>Data de Emissão:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        </div>
        
        <div class="totais">
            <div class="total-item">
                <span>Total Ativos</span>
                <strong>R$ {_format_money_br(relatorio["total_ativos"])}</strong>
            </div>
            <div class="total-item">
                <span>Total Cancelados</span>
                <strong>R$ {_format_money_br(relatorio["total_cancelados"])}</strong>
            </div>
            <div class="total-item">
                <span>Total Geral</span>
                <strong>R$ {_format_money_br(relatorio["total_geral"])}</strong>
            </div>
            <div class="total-item">
                <span>Quantidade</span>
                <strong>{relatorio["quantidade"]}</strong>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Data/Hora</th>
                    <th>Tipo</th>
                    <th>Status</th>
                    <th>Itens</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for cupom in relatorio["cupons"]:
        data_emissao = datetime.fromisoformat(cupom["data_emissao"]).strftime("%d/%m/%Y %H:%M")
        itens_str = "<br>".join([
            f"{item['quantidade']}x {item['descricao']} - R$ {_format_money_br(item['valor_unitario'])}"
            for item in cupom["itens"]
        ])
        status_class = "status-ativo" if cupom.get("status") == "ATIVO" else "status-cancelado"
        tipo_cupom = "🩺 Samaritano" if cupom.get("samaritano") else "📄 Padrão"
        
        html += f"""
                <tr>
                    <td>{data_emissao}</td>
                    <td>{tipo_cupom}</td>
                    <td class="{status_class}">{cupom.get('status', 'ATIVO')}</td>
                    <td>{itens_str}</td>
                    <td>R$ {_format_money_br(cupom['total'])}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Chaveiro Brotero</p>
            <p>Para imprimir como PDF, use Ctrl+P e selecione "Salvar como PDF"</p>
        </div>
    </body>
    </html>
    """
    
    return html


def _gerar_html_pdf_fechar_caixa(
    relatorio: Dict[str, Any],
    data: datetime | None,
) -> str:
    """Gera HTML formatado para impressão/PDF do fechamento de caixa do dia"""
    data_str = data.strftime("%d/%m/%Y") if data else datetime.now().strftime("%d/%m/%Y")
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Fechamento de Caixa - {data_str}</title>
        <style>
            @media print {{
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #3498db;
                margin: 0;
            }}
            .info {{
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }}
            .totais {{
                display: flex;
                justify-content: space-around;
                margin: 30px 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
            }}
            .total-item {{
                text-align: center;
            }}
            .total-item strong {{
                display: block;
                font-size: 1.5em;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            .status-ativo {{
                color: #27ae60;
                font-weight: bold;
            }}
            .status-cancelado {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                font-size: 0.9em;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CHAVEIRO BROTERO</h1>
            <h2>Fechamento de Caixa - {data_str}</h2>
        </div>
        
        <div class="info">
            <p><strong>Data:</strong> {data_str}</p>
            <p><strong>Data de Emissão:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        </div>
        
        <div class="totais">
            <div class="total-item">
                <span>Total Ativos</span>
                <strong>R$ {_format_money_br(relatorio["total_ativos"])}</strong>
            </div>
            <div class="total-item">
                <span>Total Cancelados</span>
                <strong>R$ {_format_money_br(relatorio["total_cancelados"])}</strong>
            </div>
            <div class="total-item">
                <span>Total do Dia</span>
                <strong>R$ {_format_money_br(relatorio["total_geral"])}</strong>
            </div>
            <div class="total-item">
                <span>Quantidade</span>
                <strong>{relatorio["quantidade"]}</strong>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Data/Hora</th>
                    <th>Tipo</th>
                    <th>Status</th>
                    <th>Itens</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for cupom in relatorio["cupons"]:
        data_emissao = datetime.fromisoformat(cupom["data_emissao"]).strftime("%d/%m/%Y %H:%M")
        itens_str = "<br>".join([
            f"{item['quantidade']}x {item['descricao']} - R$ {_format_money_br(item['valor_unitario'])}"
            for item in cupom["itens"]
        ])
        status_class = "status-ativo" if cupom.get("status") == "ATIVO" else "status-cancelado"
        tipo_cupom = "🩺 Samaritano" if cupom.get("samaritano") else "📄 Padrão"
        
        html += f"""
                <tr>
                    <td>{data_emissao}</td>
                    <td>{tipo_cupom}</td>
                    <td class="{status_class}">{cupom.get('status', 'ATIVO')}</td>
                    <td>{itens_str}</td>
                    <td>R$ {_format_money_br(cupom['total'])}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Chaveiro Brotero</p>
            <p>Para imprimir como PDF, use Ctrl+P e selecione "Salvar como PDF"</p>
        </div>
    </body>
    </html>
    """
    
    return html


def _gerar_html_pdf_samaritano(
    relatorio: Dict[str, Any],
    data_inicio: datetime | None,
    data_fim: datetime | None,
    status: str | None,
) -> str:
    """Gera HTML formatado para impressão/PDF do relatório Samaritano"""
    data_inicio_str = data_inicio.strftime("%d/%m/%Y") if data_inicio else "Início"
    data_fim_str = data_fim.strftime("%d/%m/%Y") if data_fim else "Fim"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Fechamento de Caixa - Samaritano</title>
        <style>
            @media print {{
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
            }}
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #3498db;
                margin: 0;
            }}
            .info {{
                margin-bottom: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }}
            .totais {{
                display: flex;
                justify-content: space-around;
                margin: 30px 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 8px;
            }}
            .total-item {{
                text-align: center;
            }}
            .total-item strong {{
                display: block;
                font-size: 1.5em;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            .status-ativo {{
                color: #27ae60;
                font-weight: bold;
            }}
            .status-cancelado {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .footer {{
                margin-top: 40px;
                text-align: center;
                font-size: 0.9em;
                color: #7f8c8d;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CHAVEIRO BROTERO</h1>
            <h2>Fechamento de Caixa - Samaritano</h2>
        </div>
        
        <div class="info">
            <p><strong>Período:</strong> {data_inicio_str} a {data_fim_str}</p>
            <p><strong>Status:</strong> {status if status else 'Todos'}</p>
            <p><strong>Data de Emissão:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        </div>
        
        <div class="totais">
            <div class="total-item">
                <span>Total Ativos</span>
                <strong>R$ {_format_money_br(relatorio["total_ativos"])}</strong>
            </div>
            <div class="total-item">
                <span>Total Cancelados</span>
                <strong>R$ {_format_money_br(relatorio["total_cancelados"])}</strong>
            </div>
            <div class="total-item">
                <span>Total Geral</span>
                <strong>R$ {_format_money_br(relatorio["total_geral"])}</strong>
            </div>
            <div class="total-item">
                <span>Quantidade</span>
                <strong>{relatorio["quantidade"]}</strong>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Data/Hora</th>
                    <th>OS</th>
                    <th>Status</th>
                    <th>Itens</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for cupom in relatorio["cupons"]:
        data_emissao = datetime.fromisoformat(cupom["data_emissao"]).strftime("%d/%m/%Y %H:%M")
        itens_str = "<br>".join([
            f"{item['quantidade']}x {item['descricao']} - R$ {_format_money_br(item['valor_unitario'])}"
            for item in cupom["itens"]
        ])
        status_class = "status-ativo" if cupom.get("status") == "ATIVO" else "status-cancelado"
        
        html += f"""
                <tr>
                    <td>{data_emissao}</td>
                    <td>{cupom.get('numero_os', '-')}</td>
                    <td class="{status_class}">{cupom.get('status', 'ATIVO')}</td>
                    <td>{itens_str}</td>
                    <td>R$ {_format_money_br(cupom['total'])}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>Relatório gerado automaticamente pelo sistema Chaveiro Brotero</p>
            <p>Para imprimir como PDF, use Ctrl+P e selecione "Salvar como PDF"</p>
        </div>
    </body>
    </html>
    """
    
    return html


@app.get("/api/nfse/download/{pdf_id}")
async def download_nfse(pdf_id: str):
    """Endpoint para download do PDF da DANFSE"""
    pdf_path = BASE_DIR / "_nfse" / f"{pdf_id}.pdf"
    
    if not pdf_path.exists():
        return JSONResponse(
            content={"error": "PDF não encontrado"},
            status_code=404
        )
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"DANFSE_{pdf_id}.pdf",
        headers={
            "Content-Disposition": f"attachment; filename=DANFSE_{pdf_id}.pdf"
        }
    )

