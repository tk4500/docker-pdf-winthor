import re

import pdfplumber
import io
import logging

logger = logging.getLogger("PDFProcessor")

class PDFProcessor:
    def __init__(self):
        pass

    def extract_text_optimized(self, file_bytes: bytes) -> dict:
        """
        Converte bytes de um PDF em uma string formatada preservando o layout visual.
        Otimizado para LLMs entenderem tabelas baseadas em espaçamento.
        """
        full_text = ""
        page_count = 0
        
        try:
            # Abre o PDF a partir da memória (bytes)
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                page_count = len(pdf.pages)
                
                for i, page in enumerate(pdf.pages):
                    # --- ESTRATÉGIA DE EXTRAÇÃO ---
                    # x_tolerance=1: Tenta manter caracteres próximos juntos
                    # layout=True: Tenta imitar o layout físico (essencial para tabelas sem linhas)
                    # density: Ajusta a "resolução" da extração
                    text = page.extract_text(x_tolerance=2, y_tolerance=3, layout=True)
                    
                    if text:
                        full_text += f"\n=== PÁGINA {i+1} ===\n{text}\n"
                    else:
                        logger.warning(f"Página {i+1} retornou vazio. Pode ser imagem.")
                        full_text += f"\n=== PÁGINA {i+1} (SEM TEXTO DETECTADO) ===\n"
                pattern = r'(\d{2}\.\d{3}\.\d{3}/\d{4}-)\s*\n\s*(\d{2})'
                full_text = re.sub(pattern, r'\1\2', full_text)

            return {"text": full_text, "pages": page_count}

        except Exception as e:
            logger.error(f"Erro ao processar PDF: {e}")
            raise ValueError("Arquivo inválido ou corrompido.")

    def debug_save_text(self, text: str, filename: str = "debug_output.txt"):
        """Utilitário para salvar o texto em arquivo local para inspeção manual"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)