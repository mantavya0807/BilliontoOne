#!/usr/bin/env python3
"""
Variant Annotation CLI Tool

A command-line tool to annotate dbSNP RSIDs using the Ensembl VEP API.
For Bio301 Advanced Genomics Project.
"""

import argparse
import csv
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Any


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Annotate dbSNP RSIDs using Ensembl VEP API")
    parser.add_argument(
        "--input", "-i", required=True, help="Input file containing dbSNP RSIDs (one per line)"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output TSV file for annotations"
    )
    parser.add_argument(
        "--species", "-s", default="human", 
        help="Species name for the variants (default: human)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--force", "-f", action="store_true",
        help="Overwrite output file if it exists"
    )
    return parser.parse_args()


def read_rsids(input_file: str) -> List[str]:
    """Read RSIDs from the input file."""
    try:
        with open(input_file, 'r') as f:
            rsids = []
            invalid_count = 0
            
            for line in f:
                rsid = line.strip()
                if not rsid:
                    continue
                
                # Basic validation - RSIDs start with 'rs' followed by numbers
                if not rsid.startswith('rs') or not rsid[2:].isdigit():
                    print(f"Warning: Skipping invalid RSID format: {rsid}", file=sys.stderr)
                    invalid_count += 1
                    continue
                    
                rsids.append(rsid)
            
            if invalid_count > 0:
                print(f"Skipped {invalid_count} invalid RSIDs", file=sys.stderr)
                
            return rsids
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)


def query_ensembl_api(rsid: str, species: str = "human") -> Any:
    """Query the Ensembl VEP API for a given RSID."""
    url = f"https://rest.ensembl.org/vep/{species}/id/{rsid}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            
            # Handle common error cases
            if response.status_code == 429:  # Rate limited
                if attempt < max_retries - 1:
                    print(f"Rate limited for {rsid}, retrying...", file=sys.stderr)
                    time.sleep(retry_delay)
                    continue
            
            if response.status_code == 400:
                print(f"Bad request for {rsid}: Invalid RSID", file=sys.stderr)
                return {}
            elif response.status_code == 404:
                print(f"Not found: {rsid} doesn't exist", file=sys.stderr)
                return {}
            elif response.status_code >= 500:
                print(f"Server error for {rsid}", file=sys.stderr)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return {}
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error querying API for {rsid}: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {}


def extract_annotations(api_response: Any) -> Dict:
    """Extract required annotations from the API response."""
    annotation = {
        "start": "",
        "end": "",
        "most_severe_consequence": "",
        "gene_symbols": ""
    }
    
    # Check if we have a valid response
    if not api_response or not isinstance(api_response, list) or not api_response:
        return annotation
    
    # Just use the first variant as per requirements
    variant = api_response[0]
    
    # Extract basic fields
    annotation["start"] = str(variant.get("start", ""))
    annotation["end"] = str(variant.get("end", ""))
    annotation["most_severe_consequence"] = variant.get("most_severe_consequence", "")
    
    # Extract gene symbols from transcript consequences
    gene_symbols = set()
    for consequence in variant.get("transcript_consequences", []):
        gene_symbol = consequence.get("gene_symbol")
        if gene_symbol:
            gene_symbols.add(gene_symbol)
    
    annotation["gene_symbols"] = ",".join(sorted(gene_symbols))
    return annotation


def write_tsv(annotations: List[Dict], output_file: str, rsids: List[str]):
    """Write annotations to a TSV file."""
    try:
        with open(output_file, 'w', newline='') as f:
            fieldnames = ["rsid", "start", "end", "most_severe_consequence", "gene_symbols"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            
            writer.writeheader()
            for rsid, annotation in zip(rsids, annotations):
                row = {"rsid": rsid, **annotation}
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


def print_progress_bar(current, total, bar_length=50):
    """Print a simple progress bar."""
    percent = float(current) / total
    arrow = '=' * int(round(percent * bar_length) - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    
    sys.stdout.write(f"\r[{arrow}{spaces}] {int(percent * 100)}% ({current}/{total})")
    sys.stdout.flush()


def main():
    """Main entry point for the CLI."""
    start_time = datetime.now()
    args = parse_arguments()
    
    # Check if output file exists
    if os.path.exists(args.output) and not args.force:
        print(f"Error: Output file '{args.output}' already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)
    
    # Read RSIDs from input file
    rsids = read_rsids(args.input)
    if not rsids:
        print("No valid RSIDs found in input file. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Processing {len(rsids)} RSIDs...")
    
    # Process each RSID
    annotations = []
    success_count = 0
    failed_count = 0
    
    for idx, rsid in enumerate(rsids):
        if args.verbose:
            print(f"Processing {rsid} ({idx + 1}/{len(rsids)})")
        else:
            print_progress_bar(idx + 1, len(rsids))
        
        # Get annotation from API
        api_response = query_ensembl_api(rsid, species=args.species)
        annotation = extract_annotations(api_response)
        annotations.append(annotation)
        
        # Count successes and failures
        if any(annotation.values()):
            success_count += 1
        else:
            failed_count += 1
        
        # Add a small delay to avoid overloading the API
        time.sleep(0.1)
    
    print()  # New line after progress bar
    
    # Write annotations to TSV file
    write_tsv(annotations, args.output, rsids)
    
    # Calculate elapsed time
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    # Print summary
    print(f"\nResults Summary:")
    print(f"  Total RSIDs: {len(rsids)}")
    print(f"  Successfully annotated: {success_count}")
    print(f"  Failed to annotate: {failed_count}")
    print(f"  Time elapsed: {elapsed_time:.2f} seconds")
    print(f"\nAnnotations saved to {args.output}")


if __name__ == "__main__":
    main()