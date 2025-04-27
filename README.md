# Variant Annotator CLI

A Python command-line tool to annotate dbSNP RSIDs using the Ensembl VEP API.

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

## Installation

### Prerequisites

- Python 

### Steps

1. Clone this repository:
   ```
   git clone https://github.com/mantavya0807/BilliontoOne
   cd BilliontoOne
   ```


3. Install dependencies:
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
- `INPUT_FILE` is a text file with one RSID per line
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
- `--verbose` or `-v`: Show detailed progress info
- `--force` or `-f`: Overwrite output file if it already exists

Example with advanced options:
```
python variant_annotator.py --input rs_ids.txt --output annotations.tsv --species human --verbose --force
```

## Output Format

The tool creates a tab-separated values (TSV) file with these columns:

- `rsid`: The dbSNP RSID
- `start`: Start position of the variant
- `end`: End position of the variant
- `most_severe_consequence`: The most severe consequence
- `gene_symbols`: Comma-separated list of affected genes

## Running Tests

```
python -m unittest test_variant_annotator.py
```
