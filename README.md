# Amazon Reserved Instance Coverage Analytics

A command-line tool for analyzing AWS Reserved Instance (RI) coverage based on AWS Cost Explorer reports.

> At the moment, only RDS Reserved Instances analysis is supported.

## Overview

This CLI tool helps AWS users analyze their Reserved Instance (RI) coverage for various AWS services like RDS and EC2. It processes CSV reports from AWS Cost Explorer and provides detailed insights into RI coverage and cost metrics across different regions and instance types.

## Installation

### Prerequisites

1. Install Python 3.11 or later
2. Install `uv` - a fast Python package installer and resolver: ([more details](https://docs.astral.sh/uv/getting-started/installation/))

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Project Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd reserved-instance-coverage
```

2. Sync and create virtual environment.
```bash
uv sync
```

3. Install dependencies:

## CLI Commands

The tool provides three main commands:

### 1. analyze-target-coverage

Analyzes RI coverage based on instance usage data and provides recommendations to reach target coverage.

```bash
ri-coverage-analytics analyze-target-coverage \
    path/to/instance_data.csv \
    --start-date 2025-01-01 \
    --end-date 2025-01-31 \
    --target-coverage 85.0 \
    --ri-service-type RDS
```

Parameters:
- `csv_path`: Path to the CSV file with instance data (required)
- `--start-date`: Start date in YYYY-MM-DD format (required)
- `--end-date`: End date in YYYY-MM-DD format (required)
- `--target-coverage`: Target coverage percentage (default: 80%)
- `--ri-service-type`: Type of Reserved Instance to analyze (default: RDS)

### 2. analyze-cost-coverage

Analyzes RI coverage from a cost perspective using AWS Cost Explorer reports.

```bash
# Analyze RDS RIs with custom period
uv run main analyze-cost-coverage  --utilization-report ./samples/rds-ri-utilization-past-30days.csv --recommendations-report ./samples/rds-ri-recommendations-past-30days.csv --days  30
```

Parameters:

- `--recommendations-report`: Path to the RI recommendations report CSV (optional)
- `--utilization-report`: Path to the RI utilization report CSV (optional)
- `--days`: Number of days for the utilization report (default: 30)
- `--ri-service-type`: Type of Reserved Instance to analyze (default: RDS)


### 3. analyze-target-coverage

Analyzes RI coverage from per existing coverage report and provide guidance on what RIs purchase changes are needed for meeting **target coverage**.

```bash
# Analyze RDS RIs with custom period
uv run main analyze-target-coverage ./samples/rds-ri-coverage-past-30days.csv --start-date 2025-04-20 --end-date 2025-05-19 --target-coverage 80
```

### 4. ref-doc-transform

Downloads and converts AWS documentation to markdown format for offline reference. 

```bash
ri-coverage-analytics ref-doc-transform \
    https://aws.amazon.com/rds/reserved-instances/ \
    docs/rds_ri_reference.md
```

Parameters:

- `web_page_uri`: URL of the web page to transform (required)
- `local_file`: Path to save the markdown file (required)

## Output Reports

The tool generates comprehensive reports in the following structure:

```
reports/
├── ri-cost-coverage-report-YYYY-MM-DD/
│   ├── ri-cost-coverage-report.html
│   ├── overall_coverage_*.png
│   ├── region_coverage_*.png
│   └── engine_coverage_*.png
└── ri-target-coverage-report-YYYY-MM-DD/
    └── ri-target-coverage-report.html
```

Each report includes:

- Overall RI coverage with cost breakdown
- Per-region coverage percentages and costs
- Per-engine/instance-type coverage and costs
- Visual charts and graphs
- Recommendations for achieving target coverage

## Technical Details

### Report Generation

- Interactive HTML reports with charts
- Console output with rich formatting
- Detailed recommendations based on target coverage
- Cost analysis with formatted currency values

### Core Components

1. **Data Processing**:
   - Parses CSV data using pandas
   - Calculates derived metrics like estimated instance amounts and normalized instance sizes
   - Maps region names to AWS region codes

2. **Instance Size Normalization**:
   - Converts instance classes to base instance size (e.g., db.r5.large) and size factor
   - Handles different instance families and sizes appropriately

3. **Coverage Analysis**:
   - Creates pivot tables by region, database engine, and instance size
   - Calculates coverage percentages and identifies gaps
   - Generates recommendations for achieving target coverage

4. **Output Generation**:
   - Console output with rich formatting
   - Markdown reports for documentation
   - HTML reports with interactive styling

5. **Web Document Transformation**:
   - Uses Selenium for rendering dynamic web pages
   - Extracts content using BeautifulSoup
   - Converts HTML to markdown format

### Key Technologies

- **Python 3.11+**: Core programming language
- **Typer**: CLI interface framework
- **Pandas**: Data processing and analysis
- **Rich**: Terminal formatting and display
- **Selenium**: Web page rendering for documentation transformation
- **BeautifulSoup**: HTML parsing
- **html2text**: HTML to markdown conversion

## Code Review Summary

The codebase is well-structured with clear separation of concerns:

- **main.py**: Contains the CLI commands and high-level workflow
- **utils.py**: Provides utility functions for calculations and data transformations
- **output_format.py**: Handles different output formats (console, markdown, HTML)
- **reference_doc_transformer.py**: Manages web page transformation to markdown

The implementation follows best practices with comprehensive error handling, clear documentation, and modular design. The code is extensible for future enhancements such as additional output formats or more sophisticated analysis techniques.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
