# Design Document

## Overview

This project extracts information from PMC articles using the BioC-PMC and PubTator APIs, storing the results in a DuckDB database.

## Components

- **Input Processor**: Handles user input and orchestrates the extraction and storage process.
- **BioC Extractor**: Fetches and parses BioC-formatted XML data from the BioC-PMC API.
- **PubTator Extractor**: Submits figure captions to the PubTator API and retrieves annotated entities.
- **Data Storer**: Stores the extracted data into a DuckDB database.

## Data Flow

1. User provides a PMC ID.
2. BioC Extractor fetches the article's title, abstract, and figures.
3. For each figure, the caption is sent to the PubTator Extractor to retrieve entities.
4. The combined data is stored in the DuckDB database.

## Dependencies

- `requests`: For making HTTP requests to the APIs.
- `duckdb`: For local storage of the extracted data.
- `xml.etree.ElementTree`: For parsing XML data from the BioC-PMC API.
