# app/printer.py
import win32print
from pathlib import Path
from datetime import datetime

try:
    import win32api
    _HAS_WIN32API = True
except ImportError:
    _HAS_WIN32API = False


class PrinterService:
    def __init__(self):
        self.printer_name = self._get_default_printer()

    def _get_default_printer(self):
        return win32print.GetDefaultPrinter()

    def emitir(self, texto: str, samaritano: bool) -> Path:
        path = self._salvar_txt(texto, samaritano)
        self._print_windows_raw(texto)
        return path

    def _salvar_txt(self, texto: str, samaritano: bool) -> Path:
        from pathlib import Path
        base = Path("_cupons_samaritano" if samaritano else "_cupons")
        base.mkdir(exist_ok=True)

        filename = f"cupom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = base / filename
        file_path.write_text(texto, encoding="utf-8")
        return file_path

    def _print_windows_raw(self, texto: str):
        # Comandos ESC/POS para estilo
        ESC = b"\x1b"
        RESET = ESC + b"\x40"          # Reset
        SET_BOLD = ESC + b"\x45\x01"   # Negrito ON
        FONT_A = ESC + b"\x4d\x00"     # Fonte A (melhor contraste)

        # Comando de corte (parcial) ESC/POS
        CUT = b"\x1d\x56\x01"          # GS V 1  -> corte parcial
        # Se não cortar, você pode testar depois: CUT = b"\x1b\x69"  (ESC i - corte total)

        full_data = (
            RESET +
            FONT_A +
            SET_BOLD +
            texto.encode("cp850", "replace") +
            b"\n\n\n" +    # algumas linhas em branco antes do corte
            RESET +
            CUT
        )

        printer = win32print.OpenPrinter(self.printer_name)
        try:
            job = win32print.StartDocPrinter(printer, 1, ("Cupom Chaveiro", None, "RAW"))
            win32print.StartPagePrinter(printer)
            win32print.WritePrinter(printer, full_data)
            win32print.EndPagePrinter(printer)
            win32print.EndDocPrinter(printer)
        finally:
            win32print.ClosePrinter(printer)

    def imprimir_pdf(self, pdf_path: Path) -> None:
        """Envia um arquivo PDF para a impressora padrão (Windows)."""
        if not _HAS_WIN32API:
            raise RuntimeError("win32api não disponível. Impossível imprimir PDF.")
        path_abs = pdf_path.resolve()
        if not path_abs.exists():
            raise FileNotFoundError(f"PDF não encontrado: {path_abs}")
        # ShellExecute com "print" usa o aplicativo associado ao .pdf e imprime
        win32api.ShellExecute(0, "print", str(path_abs), None, ".", 0)

