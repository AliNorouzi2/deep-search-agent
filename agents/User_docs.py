import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List
from openai import OpenAI
from time import sleep
from random import uniform
import xml.etree.ElementTree as ET
from utils.exceptions import ResumeProcessingError
import logging
from pypdf import PdfReader
logger = logging.getLogger(__name__)

import requests
class UserDocs:
    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
        api_key: str = "ollama",
    ):
        self.model = model
        self.client = OpenAI(base_url=base_url, api_key=api_key)
    def analyze_pdfs(self, file_paths: List[str], max_tokens: int = 2000, max_input_chars: int = 15000) -> List[Dict]:
        """Analyze a list of PDF files one by one.
    
        Each PDF is processed independently; if one file fails, the rest
        of the batch still gets processed. The result is a list where each
        element is the analysis output for one PDF.
        """
        results: List[Dict] = []
    
        for file_path in file_paths:
            try:
                analysis = self._analyze_single_pdf(file_path, max_tokens, max_input_chars)
                results.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {str(e)}", exc_info=True)
                results.append({
                    "file_path": file_path,
                    "error": str(e),
                })
            sleep(uniform(0.2, 0.5))
    
        return results
    
    def _analyze_single_pdf(self, file_path: str, max_tokens: int, max_input_chars: int) -> Dict:
        """Extract text from a single PDF and run analysis on it."""
        text = self._extract_text_from_pdf(file_path)   
        analysis_result = self._run_analysis(text, max_tokens, max_input_chars)        
    
        return {
            "file_path": file_path,
            "analysis": analysis_result,
        }
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract raw text from a single PDF file."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    def _run_analysis(self, text: str, max_tokens: int = 2000, max_input_chars: int = 15000) -> str:
        """Run a detailed, research-grade analysis on the extracted document text."""
        # Limit input to avoid overwhelming the model with noise from huge books
        # (table of contents, references, index, etc.)
        truncated_text = text[:max_input_chars]

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a research assistant producing a detailed, academic-level "
                        "analysis of a document, for a technical audience (e.g. a computer "
                        "science graduate student or researcher). Your analysis must be "
                        "thorough and long-form, not a short 3-line summary. Structure your "
                        "response with the following, when applicable to the document:\n"
                        "1. Objective/purpose of the work — what problem it addresses.\n"
                        "2. Methodology — the approach, models, or techniques used, including "
                        "any key formulas, algorithms, or architectures described.\n"
                        "3. Section/chapter-by-chapter breakdown of the main content.\n"
                        "4. Key findings, results, or contributions.\n"
                        "5. Limitations or open challenges mentioned, if any.\n"
                        "Be specific and technical — extract real details from the text rather "
                        "than giving generic statements. If the document appears to be a "
                        "reference list, index, or unrelated boilerplate, say so explicitly "
                        "instead of fabricating a summary."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Analyze the following document in detail:\n\n{truncated_text}",
                },
            ],
        )
        return response.choices[0].message.content