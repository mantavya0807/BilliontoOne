#!/usr/bin/env python3
"""
Unit tests for the variant annotation CLI tool.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from variant_annotator import (
    read_rsids,
    extract_annotations,
    query_ensembl_api
)


class TestVariantAnnotator(unittest.TestCase):
    """Test cases for the variant annotation CLI tool."""

    def test_read_rsids(self):
        """Test that we can read RSIDs from a file correctly."""
        # Create a temporary test file with sample RSIDs
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("rs12345\nrs67890\n\nrs11111")
            tmp_filename = tmp.name
        
        try:
            # Try to read the file with our function
            rsids = read_rsids(tmp_filename)
            # Check that we got the expected results
            self.assertEqual(rsids, ["rs12345", "rs67890", "rs11111"])
        finally:
            # Clean up the temp file when we're done
            os.unlink(tmp_filename)

    def test_extract_annotations(self):
        """Test that we can extract annotations from API responses."""
        # This is what a response from the API might look like
        sample_response = [
            {
                "start": 12345,
                "end": 12346,
                "most_severe_consequence": "missense_variant",
                "transcript_consequences": [
                    {"gene_symbol": "GENE1"},
                    {"gene_symbol": "GENE2"},
                    {"gene_symbol": "GENE1"}  # Duplicate to test set behavior
                ]
            }
        ]
        
        # Run our function on the sample data
        result = extract_annotations(sample_response)
        
        # Check that each field was extracted correctly
        self.assertEqual(result["start"], "12345")
        self.assertEqual(result["end"], "12346")
        self.assertEqual(result["most_severe_consequence"], "missense_variant")
        self.assertEqual(result["gene_symbols"], "GENE1,GENE2")  # Should be sorted and deduplicated
    
    @patch("requests.get")
    def test_query_ensembl_api(self, mock_get):
        """Test that our API query function works correctly."""
        # Set up a fake response for the mock
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200  # Set a status code
        mock_response.json.return_value = [{"start": 12345, "end": 12346}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call our function with the mock in place
        result = query_ensembl_api("rs12345")
        
        # Check we got the expected result
        self.assertEqual(result, [{"start": 12345, "end": 12346}])
        
        # Verify the API was called with the right parameters
        mock_get.assert_called_once_with(
            "https://rest.ensembl.org/vep/human/id/rs12345",
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        
    # TODO: Add more tests for error handling


if __name__ == "__main__":
    unittest.main(verbosity=2)