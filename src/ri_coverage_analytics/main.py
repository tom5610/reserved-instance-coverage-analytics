import typer
import pandas as pd
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
import io
import matplotlib.pyplot as plt
from pydantic import BaseModel
from typing import Dict
from ri_coverage_analytics.output_format import output_to_console, output_to_html
from ri_coverage_analytics.reference_doc_transformer import transform

from ri_coverage_analytics.utils import calculate_days, convert_instance_class, get_region_name_code_mapping

app = typer.Typer()
console = Console()

@app.command()
def analyze_target_coverage(
    csv_path: Path = typer.Argument(..., help="Path to the CSV file with RDS instance data"),
    start_date: str = typer.Option(..., help="Start date in format YYYY-MM-DD"),
    end_date: str = typer.Option(..., help="End date in format YYYY-MM-DD"),
    target_coverage: float = typer.Option(80.0, help="Target coverage percentage (default: 80%)"),
    ri_service_type: str = typer.Option("RDS", help="Type of Reserved Instance (default: RDS)")
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
        csv_path: Path to CSV file containing coverage report data from Cost Explorer.
        start_date: Analysis start date (YYYY-MM-DD)
        end_date: Analysis end date (YYYY-MM-DD)
        target_coverage: Desired RI coverage percentage
        ri_service_type: Type of Reserved Instance being analyzed
    
    Returns:
        DataFrame containing the analyzed instance data with coverage metrics
    
    Raises:
        typer.Exit: If input validation fails (dates, file existence)
        ValueError: If instance class parsing fails
    """

    # Validate dates
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
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
    
    # Calculate total days
    total_days = calculate_days(start_date, end_date)
    console.print(f"Analyzing data for {total_days} days ({start_date} to {end_date})")
    
    # Process each record and add extra columns
    base_sizes = []
    size_factors = []
    est_instance_amounts = []
    total_amounts = []
    ri_covered_amounts = []
    
    for _, row in df.iterrows():
        # Calculate (est.) Instance amount
        est_instance_amount = row['Total running hours'] / (24 * total_days)
        est_instance_amounts.append(est_instance_amount)
        
        # Determine if we should convert the instance class based on database engine
        engine = row['Database engine']
        should_convert = (
            'aurora' in engine.lower() or
            any(e in engine.lower() for e in ['mariadb', 'mysql', 'postgresql']) or
            ('oracle' in engine.lower() and 'byol' in engine.lower())
        )
        
        if should_convert:
            try:
                # Check if instance is smaller than medium
                instance_class = row['Instance class']
                if any(size in instance_class.lower() for size in ['micro', 'small', 'medium']):
                    base_sizes.append(instance_class)
                    size_factors.append(1.0)
                else:
                    base_size, size_factor = convert_instance_class(instance_class)
                    base_sizes.append(base_size)
                    size_factors.append(size_factor)
            except ValueError as e:
                console.print(f"[bold yellow]Warning:[/bold yellow] {str(e)}")
                base_sizes.append(row['Instance class'])
                size_factors.append(1.0)
                continue
        else:
            # For other engines, use the instance class as is
            base_sizes.append(row['Instance class'])
            size_factors.append(1.0)
        
        # Calculate Total amount (double for Multi-AZ deployments)
        total_amount = est_instance_amount * size_factor
        if row['Deployment option'] == 'Multi-AZ':
            total_amount *= 2
        total_amounts.append(total_amount)
        
        # Calculate RI covered amount
        ri_covered_amount = est_instance_amount * size_factor * row['Average coverage']
        ri_covered_amounts.append(ri_covered_amount)
    
    # Add calculated columns to dataframe
    df['Total days'] = total_days
    df['(est.) Instance amount'] = est_instance_amounts
    df['Base instance size'] = base_sizes
    df['Instance size factor'] = size_factors
    df['Total amount'] = total_amounts
    df['RI covered amount'] = ri_covered_amounts
    
    # Add region codes
    df['region_code'] = df['Region'].apply(get_region_name_code_mapping)

    # Create pivot table
    pivot = pd.pivot_table(
        df,
        values=['RI covered amount', 'Total amount'],
        index=['region_code', 'Database engine', 'Base instance size'],
        aggfunc='sum'
    )
    
    # Calculate coverage percentage by region, engine and base instance size
    detailed_coverage = df.groupby(['region_code', 'Database engine', 'Base instance size']).agg({
        'RI covered amount': 'sum',
        'Total amount': 'sum'
    })
    detailed_coverage['Coverage percentage'] = (detailed_coverage['RI covered amount'] / 
                                             detailed_coverage['Total amount'] * 100)
    
    # Get unique regions to organize output
    unique_regions = df['region_code'].unique()
    
    # Output results to console and HTML
    output_to_console(pivot, detailed_coverage, unique_regions, target_coverage, 
                     start_date, end_date, total_days, ri_service_type=ri_service_type)
    
    output_to_html(pivot, detailed_coverage, unique_regions, target_coverage,
                  start_date, end_date, total_days, ri_service_type=ri_service_type)
    return df

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
    recommendations_report: Path = typer.Option(None, help="Path to the RIs recommendations report CSV file"),
    utilization_report: Path = typer.Option(None, help="Path to the RIs utilization report CSV file"),
    days: int = typer.Option(30, help="Number of days for the utilization report"),
    ri_service_type: str = typer.Option("RDS", help="Type of Reserved Instance (default: RDS)")
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
        days: Number of days covered by the utilization report (default: 30)
        ri_service_type: Type of Reserved Instance to analyze (default: RDS)
    
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
        recommendations_df = pd.DataFrame(columns=['Region', 'Database engine', 'Upfront cost', 
                                                 'Recurring monthly cost', 'Estimated savings'])
    
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
    
    # Add RegionCode column to recommendations dataframe if not empty
    if not recommendations_df.empty:
        recommendations_df['RegionCode'] = recommendations_df['Region'].apply(get_region_name_code_mapping)
        # consolidate 30 on-demand cost equivalent.
        recommendations_df['On-Demand cost equivalent'] = (
            recommendations_df['Upfront cost'] / (12 * recommendations_df['Term'].astype(int)) + 
            recommendations_df['Recurring monthly cost'] + 
            recommendations_df['Estimated savings']
        ) * 12 / 365 * 30
    else:
        recommendations_df['RegionCode'] = pd.Series(dtype='str')
        recommendations_df['On-Demand cost equivalent'] = pd.Series(dtype='float64')
    
    # Process utilization dataframe if not empty
    if not utilization_df.empty:
        utilization_df['RegionCode'] = utilization_df['Region'].apply(get_region_name_code_mapping)
    else:
        utilization_df['RegionCode'] = pd.Series(dtype='str')
    
    # Calculate coverage metrics
    from ri_coverage_analytics.coverage_result import CoverageResult
    
    # Calculate overall coverage
    total_ri_cost = utilization_df['On-Demand cost equivalent'].sum()
    total_od_cost = recommendations_df['On-Demand cost equivalent'].sum()
    overall_coverage = total_ri_cost / (total_ri_cost + total_od_cost) * 100
    
    # Calculate coverage per region
    region_coverage = {}
    for region in set(utilization_df['RegionCode'].unique()).union(recommendations_df['RegionCode'].unique()):
        region_ri_cost = utilization_df[utilization_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        region_od_cost = recommendations_df[recommendations_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        if region_ri_cost + region_od_cost > 0:
            region_coverage[region] = region_ri_cost / (region_ri_cost + region_od_cost) * 100
        else:
            region_coverage[region] = 0.0
    
    # Calculate coverage per database engine
    engine_coverage = {}
    for engine in set(utilization_df['Database engine'].unique()).union(recommendations_df['Database engine'].unique()):
        engine_ri_cost = utilization_df[utilization_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        engine_od_cost = recommendations_df[recommendations_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        if engine_ri_cost + engine_od_cost > 0:
            engine_coverage[engine] = engine_ri_cost / (engine_ri_cost + engine_od_cost) * 100
        else:
            engine_coverage[engine] = 0.0
    
    # Calculate costs per region
    ri_cost_per_region = {
        region: utilization_df[utilization_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        for region in region_coverage.keys()
    }
    od_cost_per_region = {
        region: recommendations_df[recommendations_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        for region in region_coverage.keys()
    }

    # Calculate costs per database engine
    ri_cost_per_engine = {
        engine: utilization_df[utilization_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        for engine in engine_coverage.keys()
    }
    od_cost_per_engine = {
        engine: recommendations_df[recommendations_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        for engine in engine_coverage.keys()
    }

    # Create coverage result with all cost information
    coverage_result = CoverageResult(
        overall_ri_coverage=overall_coverage,
        overall_ri_cost=total_ri_cost,
        overall_od_cost=total_od_cost,
        ri_coverage_per_region=region_coverage,
        ri_cost_per_region=ri_cost_per_region,
        od_cost_per_region=od_cost_per_region,
        ri_coverage_per_database_engine=engine_coverage,
        ri_cost_per_database_engine=ri_cost_per_engine,
        od_cost_per_database_engine=od_cost_per_engine
    )
    
    # Generate reports
    from ri_coverage_analytics.coverage_report import output_picture_format
    output_picture_format(coverage_result, ri_service_type=ri_service_type)
    
    console.print(f"[bold green]Analysis completed for {days} days of utilization data[/bold green]")
    
    return coverage_result

def main():
    app()

if __name__ == "__main__":
    main()
