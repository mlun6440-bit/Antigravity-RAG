#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISO PDF Parser Tool
Extracts and structures text from ISO 55000 series standard PDFs for RAG.
"""

import os
import sys
import json
import argparse
import re
from typing import Dict, List, Any
import PyPDF2
import pdfplumber

# Python 3.13 handles UTF-8 natively on Windows
if sys.platform == 'win32':
    import io


class ISOPDFParser:
    """Parses ISO 55000 series PDF documents into structured knowledge base."""

    def __init__(self):
        """Initialize parser."""
        pass

    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """
        Extract text from PDF using PyPDF2.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)

                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()

            return text

        except Exception as e:
            print(f"[ERROR] PyPDF2 extraction failed: {e}")
            return ""

    def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """
        Extract text from PDF using pdfplumber (better quality).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            return text

        except Exception as e:
            print(f"[ERROR] pdfplumber extraction failed: {e}")
            return ""

    def extract_text_with_pages(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF with page number tracking for citations.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with page_number and text
        """
        pages_data = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text()
                    if page_text:
                        pages_data.append({
                            'page_number': page_num,
                            'text': page_text
                        })

            print(f"  [OK] Extracted {len(pages_data)} pages with page tracking")
            return pages_data

        except Exception as e:
            print(f"[ERROR] Page extraction failed: {e}")
            # Fallback to PyPDF2
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            pages_data.append({
                                'page_number': page_num + 1,
                                'text': text
                            })
                print(f"  [OK] Extracted {len(pages_data)} pages (PyPDF2 fallback)")
            except Exception as e2:
                print(f"[ERROR] PyPDF2 fallback also failed: {e2}")

            return pages_data

    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from PDF using best available method.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        print(f"Extracting text from {os.path.basename(pdf_path)}...")

        # Try pdfplumber first (better quality)
        text = self.extract_text_pdfplumber(pdf_path)

        # Fallback to PyPDF2 if pdfplumber fails
        if not text:
            print("  Falling back to PyPDF2...")
            text = self.extract_text_pypdf2(pdf_path)

        if text:
            print(f"  [OK] Extracted {len(text)} characters")
        else:
            print("  [ERROR] Failed to extract text")

        return text

    def chunk_by_sections(self, text: str, iso_standard: str) -> List[Dict[str, Any]]:
        """
        Chunk text into sections based on ISO structure.

        ISO documents typically have numbered clauses like:
        1 Scope
        2 Normative references
        3 Terms and definitions
        4.1 General
        etc.

        Args:
            text: Extracted PDF text
            iso_standard: ISO standard name (55000, 55001, 55002)

        Returns:
            List of chunks with metadata
        """
        chunks = []

        # Pattern to match section headers (e.g., "4.1", "4.1.1", "5.2.3")
        # Matches: "4", "4.1", "4.1.1", "Annex A", etc.
        section_pattern = r'^(\d+(?:\.\d+)*|\b[A-Z]\.\d+)\s+(.+?)$'

        lines = text.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a section header
            match = re.match(section_pattern, line)

            if match:
                # Save previous section
                if current_section and current_content:
                    chunks.append({
                        'iso_standard': iso_standard,
                        'section_number': current_section['number'],
                        'section_title': current_section['title'],
                        'content': '\n'.join(current_content).strip(),
                        'char_count': len('\n'.join(current_content))
                    })

                # Start new section
                current_section = {
                    'number': match.group(1),
                    'title': match.group(2).strip()
                }
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(line)

        # Add final section
        if current_section and current_content:
            chunks.append({
                'iso_standard': iso_standard,
                'section_number': current_section['number'],
                'section_title': current_section['title'],
                'content': '\n'.join(current_content).strip(),
                'char_count': len('\n'.join(current_content))
            })

        return chunks

    def chunk_by_paragraphs(self, text: str, iso_standard: str, max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Chunk text into paragraphs with size limit.

        Args:
            text: Extracted PDF text
            iso_standard: ISO standard name
            max_chunk_size: Maximum characters per chunk

        Returns:
            List of chunks
        """
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_size = len(para)

            # If adding this paragraph exceeds limit, save current chunk
            if current_size + para_size > max_chunk_size and current_chunk:
                chunks.append({
                    'iso_standard': iso_standard,
                    'content': '\n\n'.join(current_chunk),
                    'char_count': current_size,
                    'chunk_type': 'paragraph'
                })
                current_chunk = []
                current_size = 0

            current_chunk.append(para)
            current_size += para_size

        # Add final chunk
        if current_chunk:
            chunks.append({
                'iso_standard': iso_standard,
                'content': '\n\n'.join(current_chunk),
                'char_count': current_size,
                'chunk_type': 'paragraph'
            })

        return chunks

    def parse_iso_pdf(self, pdf_path: str, iso_standard: str, chunking_method: str = 'sections') -> List[Dict[str, Any]]:
        """
        Parse ISO PDF and create chunks.

        Args:
            pdf_path: Path to PDF file
            iso_standard: ISO standard name (55000, 55001, 55002)
            chunking_method: 'sections' or 'paragraphs'

        Returns:
            List of chunks
        """
        # Extract text
        text = self.extract_text(pdf_path)
        if not text:
            return []

        # Chunk based on method
        if chunking_method == 'sections':
            chunks = self.chunk_by_sections(text, iso_standard)
        else:
            chunks = self.chunk_by_paragraphs(text, iso_standard)

        print(f"  [OK] Created {len(chunks)} chunks")
        return chunks

    def parse_iso_pdf_with_citations(self, pdf_path: str, iso_standard: str,
                                    chunk_overlap: int = 150) -> List[Dict[str, Any]]:
        """
        Parse ISO PDF with page number tracking for citations and semantic chunking with overlap.

        Args:
            pdf_path: Path to PDF file
            iso_standard: ISO standard name (e.g., "ISO 55000:2014")
            chunk_overlap: Number of characters to overlap between chunks (default: 150)

        Returns:
            List of chunks with citation metadata (pages, quotes, embeddings ready)
        """
        print(f"Parsing {os.path.basename(pdf_path)} with citation tracking and semantic chunking...")

        # Extract text with page numbers
        pages_data = self.extract_text_with_pages(pdf_path)
        if not pages_data:
            return []

        chunks = []
        section_pattern = r'^(\d+(?:\.\d+)*|\b[A-Z]\.\d+)\s+(.+?)$'

        current_section = None
        current_content = []
        current_pages = set()
        chunk_counter = 0

        for page_data in pages_data:
            page_num = page_data['page_number']
            print(f"    Processing page {page_num}...", flush=True)
            text = page_data['text']
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Check if this is a section header
                match = re.match(section_pattern, line)

                if match:
                    # Save previous section
                    if current_section and current_content:
                        content_text = '\n'.join(current_content).strip()
                        # Extract a quote (first 200 chars)
                        quote = content_text[:200] + '...' if len(content_text) > 200 else content_text

                        chunk_counter += 1
                        chunks.append({
                            'chunk_id': f"{iso_standard.lower().replace(' ', '_')}_{current_section['number']}_c{chunk_counter}",
                            'iso_standard': iso_standard,
                            'section_number': current_section['number'],
                            'title': current_section['title'],  # Separate title for better embedding
                            'text': content_text,  # Main text for embedding
                            'char_count': len(content_text),
                            'pages': sorted(list(current_pages)),
                            'page_range': f"{min(current_pages)}-{max(current_pages)}" if len(current_pages) > 1 else str(min(current_pages)),
                            'quote_excerpt': quote,
                            'metadata': {  # Additional metadata for filtering
                                'standard': iso_standard,
                                'section': current_section['number'],
                                'page': min(current_pages)
                            }
                        })

                    # Start new section
                    current_section = {
                        'number': match.group(1),
                        'title': match.group(2).strip()
                    }
                    current_content = []
                    current_pages = {page_num}
                else:
                    # Add to current section content
                    if current_section:
                        current_content.append(line)
                        current_pages.add(page_num)

        # Add final section
        if current_section and current_content:
            content_text = '\n'.join(current_content).strip()
            quote = content_text[:200] + '...' if len(content_text) > 200 else content_text

            chunk_counter += 1
            chunks.append({
                'chunk_id': f"{iso_standard.lower().replace(' ', '_')}_{current_section['number']}_c{chunk_counter}",
                'iso_standard': iso_standard,
                'section_number': current_section['number'],
                'title': current_section['title'],
                'text': content_text,
                'char_count': len(content_text),
                'pages': sorted(list(current_pages)),
                'page_range': f"{min(current_pages)}-{max(current_pages)}" if len(current_pages) > 1 else str(min(current_pages)),
                'quote_excerpt': quote,
                'metadata': {
                    'standard': iso_standard,
                    'section': current_section['number'],
                    'page': min(current_pages) if current_pages else 0
                }
            })

        # Apply semantic chunking with overlap for large sections
        optimized_chunks = self._apply_semantic_chunking_with_overlap(chunks, chunk_overlap)

        print(f"  [OK] Created {len(optimized_chunks)} chunks with citation metadata and overlap")
        return optimized_chunks

    def _apply_semantic_chunking_with_overlap(self, chunks: List[Dict[str, Any]],
                                             overlap: int = 150, max_chunk_size: int = 800) -> List[Dict[str, Any]]:
        """
        Split large chunks into smaller ones with overlap for better context preservation.

        Args:
            chunks: List of original chunks
            overlap: Number of characters to overlap between sub-chunks
            max_chunk_size: Maximum size for each sub-chunk

        Returns:
            List of optimized chunks
        """
        optimized_chunks = []

        for i, chunk in enumerate(chunks):
            print(f"    Optimizing chunk {i+1}/{len(chunks)} (Size: {chunk['char_count']} chars)...", flush=True)
            text = chunk['text']
            char_count = chunk['char_count']

            # If chunk is small enough, keep it as is
            if char_count <= max_chunk_size:
                optimized_chunks.append(chunk)
                continue

            # Split large chunk into smaller pieces with overlap
            sub_chunks = []
            start = 0
            iteration = 0

            while start < char_count:
                iteration += 1
                if iteration % 100 == 0:
                    print(f"      Loop iteration {iteration} (start={start}/{char_count})...", flush=True)
                end = min(start + max_chunk_size, char_count)
                sub_text = text[start:end]

                # Try to break at sentence boundary
                if end < char_count:
                    last_period = sub_text.rfind('. ')
                    if last_period > max_chunk_size * 0.7:  # Only if we're reasonably far in
                        end = start + last_period + 2
                        sub_text = text[start:end]

                # Create sub-chunk with same metadata
                sub_chunk = chunk.copy()
                sub_chunk['text'] = sub_text.strip()
                sub_chunk['char_count'] = len(sub_text)
                sub_chunk['chunk_id'] = f"{chunk['chunk_id']}_sub{len(sub_chunks)+1}"
                sub_chunk['quote_excerpt'] = sub_text[:200] + '...' if len(sub_text) > 200 else sub_text

                sub_chunks.append(sub_chunk)

                if end >= char_count:
                    break
                
                # Move start forward, accounting for overlap
                new_start = end - overlap
                
                # Safety check to prevent infinite loops
                if new_start <= start:
                    new_start = start + 50 # Force advance by at least 50 chars
                    
                start = new_start

            optimized_chunks.extend(sub_chunks)

        return optimized_chunks

    def create_knowledge_base(self, pdf_files: List[Dict[str, str]], output_file: str = 'data/.tmp/iso_knowledge_base.json') -> Dict[str, Any]:
        """
        Create ISO knowledge base from multiple PDFs.

        Args:
            pdf_files: List of dicts with 'path' and 'standard' keys
            output_file: Path to save knowledge base

        Returns:
            Knowledge base dictionary
        """
        print("\n=== Creating ISO 55000 Knowledge Base ===\n")

        knowledge_base = {
            'standards': {},
            'all_chunks': [],
            'metadata': {
                'total_standards': len(pdf_files),
                'total_chunks': 0
            }
        }

        for pdf_info in pdf_files:
            pdf_path = pdf_info['path']
            iso_standard = pdf_info['standard']

            if not os.path.exists(pdf_path):
                print(f"[ERROR] PDF not found: {pdf_path}")
                continue

            # Use citation-enhanced parsing
            chunks = self.parse_iso_pdf_with_citations(pdf_path, iso_standard)

            knowledge_base['standards'][iso_standard] = {
                'pdf_path': pdf_path,
                'chunks': chunks,
                'total_chunks': len(chunks)
            }

            knowledge_base['all_chunks'].extend(chunks)

        knowledge_base['metadata']['total_chunks'] = len(knowledge_base['all_chunks'])

        # Save knowledge base
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Knowledge base saved to: {output_file}")
        print(f"  - Total standards: {knowledge_base['metadata']['total_standards']}")
        print(f"  - Total chunks: {knowledge_base['metadata']['total_chunks']}")
        for standard, data in knowledge_base['standards'].items():
            print(f"  - {standard}: {data['total_chunks']} chunks")

        return knowledge_base


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description='Parse ISO 55000 PDFs into knowledge base')
    parser.add_argument('--pdf-dir', default='data/.tmp',
                       help='Directory containing ISO PDFs')
    parser.add_argument('--output', default='data/.tmp/iso_knowledge_base.json',
                       help='Output file path')
    parser.add_argument('--method', choices=['sections', 'paragraphs'], default='sections',
                       help='Chunking method')

    args = parser.parse_args()

    # Define ISO PDF files
    pdf_files = [
        {'path': os.path.join(args.pdf_dir, 'ASISO55000-20241.pdf'), 'standard': 'ISO 55000'},
        {'path': os.path.join(args.pdf_dir, 'ASISO55001-20241.pdf'), 'standard': 'ISO 55001'},
        {'path': os.path.join(args.pdf_dir, 'ASISO55002-20241.pdf'), 'standard': 'ISO 55002'}
    ]

    try:
        parser_obj = ISOPDFParser()
        kb = parser_obj.create_knowledge_base(
            pdf_files=pdf_files,
            output_file=args.output
        )

        print("\n[OK] Success! ISO knowledge base created.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
