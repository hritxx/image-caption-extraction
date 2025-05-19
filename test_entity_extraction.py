import requests
import json
import os


def test_bern_api(text):
    """
    Tests the BERN2 API with the given text.

    Args:
        text (str): The text to send to the BERN2 API.

    Returns:
        dict or None: The JSON response from the API if successful, None otherwise.
    """
    url = "http://bern2.korea.ac.kr/plain"
    headers = {"Content-Type": "application/json"}
    payload = {"text": text}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {e}")
        return None

def test_multiple_captions():
    """Test BERN2 with a variety of different captions."""
    test_cases = [
        "Patients with HER2-positive breast cancer responded well to trastuzumab.",
        "Fig. 1: H&E staining revealed lung adenocarcinoma with KRAS mutation.",
        "The mice developed metastases in the liver after 4 weeks of treatment with doxorubicin.",
        "IL-6 and TNF-alpha levels were elevated in patients with severe COVID-19.",
        "Immunohistochemistry showed positive staining for p53 in 80% of the tumor cells."
    ]
    
    for i, caption in enumerate(test_cases):
        print(f"\n=== Test Case {i+1} ===")
        print(f"Caption: {caption}")
        results = test_bern_api(caption)
        
        if results and "annotations" in results:
            if results["annotations"]:
                print(f"Found {len(results['annotations'])} entities:")
                for entity in results["annotations"]:
                    print(f"  {entity['mention']} ({entity['obj']})")
            else:
                print("No entities found")
        else:
            print("API request failed")

def test_empty_and_edge_cases():
    """Test BERN2 with edge cases."""
    edge_cases = [
        "",  # Empty string
        "No biomedical terms here.",  # No entities
        "A" * 1000,  # Very long input
        "HER2+ NSCLC pt w/ mets to liver tx w/ TKI",  # Medical abbreviations
        "Figure shows %-change in CD4+ T-cells after 3μg/kg dose"  # Special characters
    ]
    
    for i, case in enumerate(edge_cases):
        print(f"\n=== Edge Case {i+1} ===")
        print(f"Text: {case[:50]}{'...' if len(case) > 50 else ''}")
        results = test_bern_api(case)
        if results:
            print(f"Status: {'Success' if 'annotations' in results else 'Failed'}")
            if 'annotations' in results:
                print(f"Entities found: {len(results['annotations'])}")
        else:
            print("Status: Request failed")

if __name__ == "__main__":
    test_caption = "The tumor showed increased expression of the EGFR protein rna dna."
    results = test_bern_api(test_caption)

    if results and "annotations" in results:
        print("BERN2 API Response:")
        print(json.dumps(results, indent=4))

        if results["annotations"]:
            print("\nExtracted Entities:")
            for entity in results["annotations"]:
                print(f"  Mention: {entity['mention']}")
                print(f"  Type: {entity['obj']}")
                if 'id' in entity and len(entity['id']) > 1:
                    print(f"  Identifier: {entity['id'][1]}")
                print(f"  Span: {entity['span']['begin']}-{entity['span']['end']}")
                print("-" * 20)
        else:
            print("\nNo entities found in the caption.")
    else:
        print("Failed to get a valid response from the BERN2 API.")