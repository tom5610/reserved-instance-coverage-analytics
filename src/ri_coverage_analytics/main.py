import typer
import pandas as pd
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
import io
import matplotlib.pyplot as plt

# Import internal modules
from ri_coverage_analytics.config import config
from ri_coverage_analytics.output_format import output_to_console, output_to_html
from ri_coverage_analytics.reference_doc_transformer import transform
from ri_coverage_analytics.data_processor import (
    process_instance_data, 
    calculate_coverage_metrics
)
from ri_coverage_analytics.coverage_report import output_picture_format

app = typer.Typer()
console = Console()

@app.command()
def analyze_target_coverage(
    csv_path: Path = typer.Argument(..., help="Path to the CSV file with RDS instance data"),
    start_date: str = typer.Option(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Option(..., help="End date in format YYYY-MM-DD"),
    target_coverage: float = typer.Option(
        config.default_target_coverage, 
        help=f"Target coverage percentage (default: {config.default_target_coverage}%)"
    ),
    ri_service_type: str = typer.Option(
        config.default_ri_service_type, 
        help=f"Type of Reserved Instance (default: {config.default_ri_service_type})"
    )
):
    """
    Analyze Reserved Instance coverage and provide recommendations to reach target coverage.

    This function processes instance usage data to:
    1. Calculate current RI coverage across regions and instance types
    2. Normalize instance sizes for accurate comparison (e.g., xlarge = 2x large)
    3. Generate recommendations to achieve target coverage percentage
    
    The analysis handles:
    - Multiple AWS regions
    - Different database engines (MySQL, PostgreSQL, Oracle, etc.)
    - Various instance sizes with normalization
    - Special cases like Aurora and BYOL instances
    
    The function generates:
    - Detailed coverage analysis by region and instance type
    - Instance size normalization for flexible RI application
    - Specific recommendations to reach target coverage
    - HTML report in the reports/ri-target-coverage-report-YYYY-MM-DD directory
    
    Args:
        csv_path: Path to CSV file containing coverage report data from Cost Explorer
        start_date: Analysis start date (YYYY-MM-DD)
        end_date: Analysis end date (YYYY-MM-DD)
        target_coverage: Desired RI coverage percentage
        ri_service_type: Type of Reserved Instance being analyzed
    
    Returns:
        DataFrame containing the analyzed instance data with coverage metrics
    
    Raises:
        typer.Exit: If input validation fails (dates, file existence)
        DateFormatError: If date format is invalid
    """
    # Validate dates
    try:
        datetime.strptime(start_date, config.date_format)
        datetime.strptime(end_date, config.date_format)
    except ValueError:
        console.print("[bold red]Error:[/bold red] Dates must be in YYYY-MM-DD format")
        raise typer.Exit(1)
    
    # Check if file exists
    if not csv_path.exists():
        console.print(f"[bold red]Error:[/bold red] File {csv_path} does not exist")
        raise typer.Exit(1)
    
    # Load CSV file
    try:
        df = pd.read_csv(csv_path)
        console.print(f"Loaded {len(df)} records from {csv_path}")
    except Exception as e:
        console.print(f"[bold red]Error loading CSV:[/bold red] {str(e)}")
        raise typer.Exit(1)
    
    # Process instance data
    try:
        df_processed = process_instance_data(df, start_date, end_date)
        total_days = df_processed['Total days'].iloc[0]  # Get the calculated total days
        console.print(f"Analyzing data for {total_days} days ({start_date} to {end_date})")
    except Exception as e:
        console.print(f"[bold red]Error processing data:[/bold red] {str(e)}")
        raise typer.Exit(1)
    
    # Create pivot table for analysis
    pivot = pd.pivot_table(
        df_processed,
        values=['RI covered amount', 'Total amount'],
        index=['region_code', 'Database engine', 'Base instance size'],
        aggfunc='sum'
    )
    
    # Calculate coverage percentage by region, engine and base instance size
    detailed_coverage = df_processed.groupby(['region_code', 'Database engine', 'Base instance size']).agg({
        'RI covered amount': 'sum',
        'Total amount': 'sum'
    })
    detailed_coverage['Coverage percentage'] = (detailed_coverage['RI covered amount'] / 
                                             detailed_coverage['Total amount'] * 100)
    
    # Get unique regions to organize output
    unique_regions = df_processed['region_code'].unique()
    
    # Output results to console and HTML
    output_to_console(
        pivot, detailed_coverage, unique_regions, target_coverage, 
        start_date, end_date, total_days, ri_service_type=ri_service_type
    )
    
    output_to_html(
        pivot, detailed_coverage, unique_regions, target_coverage,
        start_date, end_date, total_days, ri_service_type=ri_service_type
    )
    
    return df_processed

@app.command()
def ref_doc_transform(
    web_page_uri: str = typer.Argument(..., help="URL of the web page to transform"),
    local_file: str = typer.Argument(..., help="Path to save the markdown file")
):
    """
    Download a web page, transform it to markdown format, and save it locally.
    
    Example usage:
    uv run main ref-doc-transform https://example.com output.md
    """
    console.print(f"Transforming web page: {web_page_uri}")
    success = transform(web_page_uri, local_file)
    
    if success:
        console.print(f"[bold green]Successfully transformed and saved to:[/bold green] {local_file}")
    else:
        console.print("[bold red]Failed to transform document[/bold red]")
        raise typer.Exit(1)

@app.command()
def analyze_cost_coverage(
    recommendations_report: Path = typer.Option(
        None, 
        help="Path to the RIs recommendations report CSV file"
    ),
    utilization_report: Path = typer.Option(
        None, 
        help="Path to the RIs utilization report CSV file"
    ),
    days: int = typer.Option(
        config.default_analysis_days, 
        help=f"Number of days for the utilization report (default: {config.default_analysis_days})"
    ),
    ri_service_type: str = typer.Option(
        config.default_ri_service_type, 
        help=f"Type of Reserved Instance (default: {config.default_ri_service_type})"
    )
):
    """
    Analyze Reserved Instances coverage and cost metrics from AWS Cost Explorer reports.
    
    This function processes two optional CSV reports to calculate RI coverage:
    1. RI recommendations report (optional) - Shows potential RI purchases and their cost impact
       If not provided, assumes no On-Demand usage (100% RI coverage)
    2. RI utilization report (optional) - Shows current RI usage and associated costs
       If not provided, assumes no RI usage (0% coverage)
    
    The analysis generates:
    - Overall RI coverage percentage with cost breakdown
    - Per-region coverage percentages and costs (RI vs On-Demand)
    - Per-engine coverage percentages and costs (RI vs On-Demand)
    - Visual reports including pie charts and bar graphs
    - Detailed HTML report in the reports/ri-cost-coverage-report-YYYY-MM-DD directory
    
    Args:
        recommendations_report: Optional CSV file containing RI recommendations
        utilization_report: Optional CSV file showing current RI utilization
        days: Number of days covered by the utilization report
        ri_service_type: Type of Reserved Instance to analyze
    
    Returns:
        CoverageResult object containing coverage percentages and cost metrics
    """
    # Initialize empty DataFrames
    recommendations_df = pd.DataFrame()
    utilization_df = pd.DataFrame()
    
    # Load recommendations report if exists
    if recommendations_report:
        try:
            recommendations_df = pd.read_csv(recommendations_report)
            console.print(f"Loaded {len(recommendations_df)} records from {recommendations_report}")
        except Exception as e:
            console.print(f"[bold red]Error loading recommendations CSV:[/bold red] {str(e)}")
            raise typer.Exit(1)
    else:
        console.print("[bold yellow]Warning:[/bold yellow] No recommendations report provided. Assuming no On-Demand spend.")
        # Create empty DataFrame with required columns
        recommendations_df = pd.DataFrame(columns=[
            'Region', 'Database engine', 'Upfront cost', 'Term',
            'Recurring monthly cost', 'Estimated savings'
        ])
    
    # Load utilization report if exists
    if utilization_report:
        try:
            utilization_df = pd.read_csv(utilization_report)
            console.print(f"Loaded {len(utilization_df)} records from {utilization_report}")
        except Exception as e:
            console.print(f"[bold red]Error loading utilization CSV:[/bold red] {str(e)}")
            raise typer.Exit(1)
    else:
        console.print("[bold yellow]Warning:[/bold yellow] No utilization report provided. Assuming no RI usage.")
        # Create empty DataFrame with required columns
        utilization_df = pd.DataFrame(columns=['Region', 'Database engine', 'On-Demand cost equivalent'])
    
    # Calculate coverage metrics using the extracted functionality
    try:
        coverage_result = calculate_coverage_metrics(recommendations_df, utilization_df, days)
    except Exception as e:
        console.print(f"[bold red]Error calculating coverage metrics:[/bold red] {str(e)}")
        raise typer.Exit(1)
    
    # Generate reports
    output_picture_format(coverage_result, ri_service_type=ri_service_type)
    
    console.print(f"[bold green]Analysis completed for {days} days of utilization data[/bold green]")
    
    return coverage_result

def main():
    """Entry point function for the Reserved Instance coverage analytics tool.
    
    This function serves as the application entry point and launches the Typer
    command-line interface with all available commands:
    - analyze_target_coverage: Analyze and recommend changes to reach target coverage
    - ref_doc_transform: Convert web documentation to markdown format
    - analyze_cost_coverage: Analyze RI cost coverage based on AWS Cost Explorer reports
    
    The function is called when the script is run directly (not imported).
    """
    app()

if __name__ == "__main__":
    main()
