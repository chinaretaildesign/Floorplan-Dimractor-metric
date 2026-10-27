#!/usr/bin/env python3
"""
Main script for Floorplan Dimension Extractor
"""

import argparse
import json
import os
from datetime import datetime
from src.pdf_processor import PDFProcessor
from src.visualizer import PDFVisualizer
from src.utils import (setup_logging, validate_pdf_path, save_json_output, 
                      generate_output_filename, ensure_directories)

def main():
    parser = argparse.ArgumentParser(description='Floorplan Dimension Extractor')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', help='Output JSON file path (optional)')
    parser.add_argument('--visualize', '-v', action='store_true', help='Generate visualization')
    parser.add_argument('--method', '-m', choices=['pdfplumber', 'pymupdf'], default='pymupdf', 
                       help='PDF processing method')
    parser.add_argument('--default-unit', default='mm', choices=['mm', 'cm', 'm'],
                       help='无单位后缀的纯数字按此单位处理（默认 mm）')
    parser.add_argument('--bare-mm', action='store_true',
                       help='把无单位的纯数字也当 mm 尺寸提取（图纸全为公制 mm 时启用）')
    
    args = parser.parse_args()
    logger = setup_logging()
    
    # Ensure directories exist
    ensure_directories()
    
    # Validate input
    if not validate_pdf_path(args.pdf_path):
        logger.error(f"Invalid PDF path: {args.pdf_path}")
        return
    
    logger.info(f"Processing PDF: {args.pdf_path}")
    
    # Generate output path if not provided
    if args.output is None:
        args.output = generate_output_filename(args.pdf_path)
    
    # Process PDF
    processor = PDFProcessor(default_unit=args.default_unit, bare_as_mm=args.bare_mm)
    
    if args.method == 'pdfplumber':
        results = processor.extract_with_pdfplumber(args.pdf_path)
    else:
        results = processor.extract_with_pymupdf(args.pdf_path)
    
    # Add metadata
    results["metadata"] = {
        "processed_at": datetime.now().isoformat(),
        "pdf_file": os.path.basename(args.pdf_path),
        "processing_method": args.method,
        "total_pages": len(results["pages"])
    }
    
    # Save results
    if save_json_output(results, args.output):
        logger.info(f"Results saved to: {args.output}")
    else:
        logger.error("Failed to save results")
    
    # Generate visualization if requested
    if args.visualize:
        visualizer = PDFVisualizer()
        viz_output = args.output.replace('.json', '_visualized.pdf')
        visualizer.draw_bounding_boxes(args.pdf_path, results, viz_output)
        logger.info(f"Visualization saved to: {viz_output}")
    
    # Print summary
    total_dimensions = sum(len(page["dimensions"]) for page in results["pages"])
    total_codes = sum(len(page["codes"]) for page in results["pages"])
    
    logger.info(f"Extraction completed: {total_dimensions} dimensions, {total_codes} codes found")

if __name__ == "__main__":
    main()