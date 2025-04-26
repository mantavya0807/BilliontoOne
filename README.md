# Variant Annotator CLI

A Python command-line tool to annotate dbSNP RSIDs using the Ensembl VEP API.
Created for Bio301 Advanced Genomics Project.

## Features

- Takes a file with a list of dbSNP RSIDs
- Queries the Ensembl Variant Effect Predictor (VEP) API
- Handles API errors and retries failed requests
- Extracts annotation data including:
  - Start position
  - End position
  - Most severe consequence
  - List of affected genes
- Outputs results as a TSV file

## Files

- **variant_annotator.py**: Main script that performs the variant annotation using Ensembl VEP API
- **test_variant_annotator.py**: Unit tests to verify the main functionality
- **rs_ids.txt**: Sample input file with RSIDs to query
- **annotations.tsv**: Output file containing the annotation results

## Installation

### Prerequisites

- Python 3.6 or later
- pip (Python package installer)

### Steps

1. Clone this repository:
   ```
   git clone https://github.com/mantavya0807/BilliontoOne.git
   cd BilliontoOne
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the tool with this command:

```
python variant_annotator.py --input INPUT_FILE --output OUTPUT_FILE
```

Where:
- `INPUT_FILE` is a text file with one RSID per line (e.g., "rs12345")
- `OUTPUT_FILE` is where the TSV results will be saved

Example:
```
python variant_annotator.py --input rs_ids.txt --output annotations.tsv
```

### Advanced Options

The tool has several additional options:

```
python variant_annotator.py --input INPUT_FILE --output OUTPUT_FILE [OPTIONS]
```

Available options:
- `--species` or `-s`: Species name (default: "human")
- `--additional-fields` or `-a`: Include extra fields in the output
- `--verbose` or `-v`: Show detailed progress info
- `--max-retries` or `-r`: Number of retry attempts (default: 3)

Example with advanced options:
```
python variant_annotator.py --input rs_ids.txt --output annotations.tsv --species human --additional-fields variant_class --verbose
```

## Output Format

The tool creates a tab-separated values (TSV) file with these columns:

- `rsid`: The dbSNP RSID
- `start`: Start position of the variant
- `end`: End position of the variant
- `most_severe_consequence`: The most severe consequence
- `gene_symbols`: Comma-separated list of affected genes
- Any additional fields requested with `--additional-fields`

## Running Tests

```
python -m unittest test_variant_annotator.py
```