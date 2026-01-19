# app/printer.py
from __future__ import annotations

import os
from pathlib import Path

try:
    from escpos.printer import Usb  # type: ignore
    _HAS_ESCPOS = True
except Exception:
    _HAS_ESCPOS = False
    Usb = object  # type: ignore


BASE_DIR = Path(__file__).resolve().parent.parent
CUPONS_DIR = BASE_DIR / "_cupons"
CUPONS_SAMARITANO_DIR = BASE_DIR / "_cupons_samaritano"

CUPONS_DIR.mkdir(exist_ok=True)
CUPONS_SAMARITANO_DIR.mkdir(exist_ok=True)


class PrinterService:
    """
    Serviço de impressão:
    - Sempre salva o .txt (padrão ou Samaritano)
    - Opcionalmente imprime em ESC/POS se configurado
    """

    def __init__(self) -> None:
        self.backend = os.getenv("PRINTER_BACKEND", "file")  # "file" ou "usb"

        # IDs da impressora (ajuste para seu modelo)
        self.usb_vendor_id = int(os.getenv("USB_VENDOR_ID", "0"), 16)
        self.usb_product_id = int(os.getenv("USB_PRODUCT_ID", "0"), 16)

    def save_txt(self, texto: str, samaritano: bool) -> Path:
        from datetime import datetime as _dt

        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        target_dir = CUPONS_SAMARITANO_DIR if samaritano else CUPONS_DIR
        filename = f"cupom_{ts}.txt"
        path = target_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(texto)
        return path

    def print_escpos_usb(self, texto: str) -> None:
        if not _HAS_ESCPOS:
            raise RuntimeError("Biblioteca python-escpos não instalada.")

        if self.usb_vendor_id == 0 or self.usb_product_id == 0:
            raise RuntimeError("Defina USB_VENDOR_ID e USB_PRODUCT_ID nas variáveis de ambiente.")

        # Conexão com impressora USB ESC/POS
        printer = Usb(self.usb_vendor_id, self.usb_product_id, timeout=0, in_ep=0x82, out_ep=0x01)

        # Envia texto “cru”
        for line in texto.splitlines():
            printer.text(line + "\n")
        printer.cut()

    def emitir(self, texto: str, samaritano: bool) -> Path:
        """
        Função principal chamada pela rota /emitir.
        Sempre salva .txt e, se backend=usb, tenta imprimir.
        """
        path = self.save_txt(texto, samaritano)

        if self.backend == "usb":
            try:
                self.print_escpos_usb(texto)
            except Exception as e:
                # Não quebra o fluxo, apenas loga/propaga se quiser
                raise RuntimeError(f"Erro ao imprimir na impressora ESC/POS: {e}") from e

        return path
