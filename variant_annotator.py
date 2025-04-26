#!/usr/bin/env python3
"""
Variant Annotation CLI Tool

A command-line tool to annotate dbSNP RSIDs using the Ensembl VEP API.
"""

import argparse
import csv
import sys
import time
from typing import Dict, List, Any
import requests


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Annotate dbSNP RSIDs using Ensembl VEP API")
    # Required arguments
    parser.add_argument(
        "--input", "-i", required=True, help="Input file containing dbSNP RSIDs (one per line)"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output TSV file for annotations"
    )
    # Optional arguments with defaults
    parser.add_argument(
        "--species", "-s", default="human", 
        help="Species name for the variants (default: human)"
    )
    parser.add_argument(
        "--additional-fields", "-a", action="append", default=[],
        help="Additional fields to include in the output (can be specified multiple times)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output with detailed progress information"
    )
    parser.add_argument(
        "--max-retries", "-r", type=int, default=3,
        help="Maximum number of retry attempts for failed API requests (default: 3)"
    )
    return parser.parse_args()


def read_rsids(input_file: str) -> List[str]:
    """
    Read RSIDs from the input file.
    
    Args:
        input_file: Path to the input file
        
    Returns:
        List of RSID strings
    """
    try:
        with open(input_file, 'r') as f:
            # Filter out empty lines, strip whitespace, and do basic validation
            rsids = []
            bad_ids = []
            
            for line in f:
                rsid = line.strip()
                if not rsid:
                    continue
                    
                # Check if RSID looks valid (starts with rs + numbers)
                if not rsid.startswith("rs") or not rsid[2:].isdigit():
                    bad_ids.append(rsid)
                    print(f"Warning: '{rsid}' might not be a valid RSID", file=sys.stderr)
                else:
                    rsids.append(rsid)
            
            if bad_ids:
                print(f"Found {len(bad_ids)} possibly invalid RSIDs.", file=sys.stderr)
                
            return rsids
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)


def query_ensembl_api(rsid: str, species: str = "human", max_retries: int = 3) -> Any:
    """
    Query the Ensembl VEP API for a given RSID.
    
    Args:
        rsid: The RSID to query
        species: The species (default: human)
        max_retries: Number of retry attempts
        
    Returns:
        API response data as dictionary, or empty dict if failed
    """
    # Construct API URL
    url = f"https://rest.ensembl.org/vep/{species}/id/{rsid}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    retry_delay = 2  # seconds between retries
    
    # Try to query the API, with retries if it fails
    for attempt in range(max_retries):
        try:
            # Make the API request
            response = requests.get(url, headers=headers)
            
            # Handle common error cases
            if response.status_code == 429:  # Rate limited
                if attempt < max_retries - 1:
                    retry_after = int(response.headers.get('Retry-After', retry_delay))
                    print(f"Rate limited for {rsid}, retrying after {retry_after} seconds...", file=sys.stderr)
                    time.sleep(retry_after)
                    continue
            
            if response.status_code == 400:
                print(f"Bad request for {rsid}: The RSID appears to be invalid", file=sys.stderr)
                return {}
            elif response.status_code == 404:
                print(f"Not found: {rsid} doesn't exist in the database", file=sys.stderr)
                return {}
            elif response.status_code >= 500:
                print(f"Server error ({response.status_code}) for {rsid}", file=sys.stderr)
                if attempt < max_retries - 1:
                    print(f"Retrying ({attempt+1}/{max_retries})...", file=sys.stderr)
                    time.sleep(retry_delay)
                    continue
                return {}
            
            # If we got here, check for any other errors
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error querying API for {rsid}: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                print(f"Retrying ({attempt+1}/{max_retries})...", file=sys.stderr)
                time.sleep(retry_delay)
            else:
                return {}


def extract_annotations(api_response: Any, additional_fields: List[str] = None) -> Dict:
    """
    Extract required annotations from the API response.
    
    Args:
        api_response: The API response data
        additional_fields: List of extra fields to extract
        
    Returns:
        Dictionary of extracted annotations
    """
    # Default annotation fields we always want
    annotation = {
        "start": "",
        "end": "",
        "most_severe_consequence": "",
        "gene_symbols": ""
    }
    
    # Add any additional fields requested
    if additional_fields:
        for field in additional_fields:
            annotation[field] = ""
    
    # Check if we have a valid response
    if not api_response or not isinstance(api_response, list) or not api_response:
        return annotation
    
    # Just use the first variant as specified in the requirements
    variant = api_response[0]
    
    # Extract standard fields
    annotation["start"] = str(variant.get("start", ""))
    annotation["end"] = str(variant.get("end", ""))
    annotation["most_severe_consequence"] = variant.get("most_severe_consequence", "")
    
    # Extract gene symbols - this is trickier
    # Need to get unique gene symbols from all transcript consequences
    gene_symbols = set()
    for consequence in variant.get("transcript_consequences", []):
        gene_symbol = consequence.get("gene_symbol")
        if gene_symbol:
            gene_symbols.add(gene_symbol)
    
    # Sometimes the API returns gene_symbol directly in variant
    if not gene_symbols and variant.get("gene_symbol"):
        gene_symbols.add(variant.get("gene_symbol"))
    
    annotation["gene_symbols"] = ",".join(sorted(gene_symbols))
    
    # TODO: Add support for getting consequence details
    
    # Extract additional requested fields
    if additional_fields:
        for field in additional_fields:
            # Try to get field from variant
            if field in variant:
                annotation[field] = str(variant.get(field, ""))
            # If not in variant, check in transcript consequences
            elif variant.get("transcript_consequences"):
                for consequence in variant.get("transcript_consequences", []):
                    if field in consequence:
                        annotation[field] = str(consequence.get(field, ""))
                        break
    
    return annotation


def write_tsv(annotations: List[Dict], output_file: str, rsids: List[str]):
    """
    Write annotations to a TSV file.
    
    Args:
        annotations: List of annotation dictionaries
        output_file: Path to the output file
        rsids: List of RSIDs
    """
    try:
        # Figure out all the fields we need to include
        all_fields = set(["rsid"])
        for annotation in annotations:
            all_fields.update(annotation.keys())
        
        # Make sure our standard fields come first, then any extras alphabetically
        standard_fields = ["rsid", "start", "end", "most_severe_consequence", "gene_symbols"]
        extra_fields = sorted(list(all_fields - set(standard_fields)))
        fieldnames = standard_fields + extra_fields
        
        # Write the TSV file
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            
            writer.writeheader()
            for rsid, annotation in zip(rsids, annotations):
                row = {"rsid": rsid, **annotation}
                writer.writerow(row)
    except Exception as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Read RSIDs from input file
    rsids = read_rsids(args.input)
    print(f"Processing {len(rsids)} RSIDs...")
    
    # Process each RSID
    annotations = []
    success_count = 0
    error_count = 0
    
    total = len(rsids)
    
    for i, rsid in enumerate(rsids):
        # Show progress
        if args.verbose:
            print(f"Processing {rsid} ({i + 1}/{total})")
        else:
            print(f"Processing {rsid} ({i + 1}/{total})", end="\r")
        
        # Get data from API
        api_data = query_ensembl_api(rsid, species=args.species, max_retries=args.max_retries)
        result = extract_annotations(api_data, args.additional_fields)
        annotations.append(result)
        
        # Track success/failure
        if any(value for key, value in result.items() if key != "rsid"):
            success_count += 1
        else:
            error_count += 1
        
        # Avoid hammering the API too hard
        time.sleep(0.1)
    
    # Clear the progress line
    if not args.verbose:
        print(" " * 80, end="\r")
    
    # Write results to file
    write_tsv(annotations, args.output, rsids)
    
    # Show results summary
    print(f"\nResults Summary:")
    print(f"  Total RSIDs: {total}")
    print(f"  Successfully annotated: {success_count}")
    print(f"  Failed to annotate: {error_count}")
    
    if error_count > 0:
        print(f"  Failure rate: {error_count/total:.1%}")
    
    print(f"\nAnnotations saved to {args.output}")


if __name__ == "__main__":
    main()