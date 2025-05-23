from rich.console import Console
from rich.table import Table
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime

console = Console()

def output_to_console(
    pivot: Any,
    detailed_coverage: Any,
    unique_regions: List[str],
    target_coverage: float,
    start_date: str,
    end_date: str,
    total_days: int,
    ri_service_type: str = "RDS"
) -> None:
    """Output analysis results to console using Rich formatting"""
    console.print("\n[bold green]Pivot Table by Region, Database Engine, and Base Instance Size:[/bold green]")
    formatted_pivot = pivot.round(1)
    console.print(formatted_pivot)
    
    console.print("\n[bold green]Coverage Percentage by Region and Instance Size:[/bold green]")
    
    for region in unique_regions:
        console.print(f"\n[bold blue]Region: {region}[/bold blue]")
        
        # Get unique engines in this region
        region_data = detailed_coverage.loc[region]
        unique_engines = region_data.index.get_level_values('Database engine').unique()
        
        for engine in unique_engines:
            console.print(f"\n[bold cyan]Database Engine: {engine}[/bold cyan]")
            
            table = Table(show_header=True, header_style="bold")
            table.add_column("Base Instance Size")
            table.add_column("Total Amount", justify="right")
            table.add_column("Covered Amount", justify="right")
            table.add_column("Coverage %", justify="right")
            
            engine_data = region_data.xs(engine, level='Database engine')
            for instance_size, row in engine_data.iterrows():
                table.add_row(
                    str(instance_size),
                    f"{row['Total amount']:.1f}",
                    f"{row['RI covered amount']:.1f}",
                    f"{row['Coverage percentage']:.1f}%"
                )
            
            console.print(table)
            
            # Print recommendations table
            recommendations_title = f"Recommendations for {region} - {engine} (Target: {target_coverage}% coverage)"
            rec_table = Table(show_header=True, header_style="bold", title=f"[yellow]{recommendations_title}[/yellow]")
            rec_table.add_column("Base Instance Size")
            rec_table.add_column("Current Coverage %", justify="right")
            rec_table.add_column("Covered Amount", justify="right")
            rec_table.add_column("Current Total", justify="right")
            rec_table.add_column("Required Change", justify="right")
            
            for instance_size, row in engine_data.iterrows():
                current_coverage = row['Coverage percentage']
                current_total = row['Total amount']
                current_covered = row['RI covered amount']
                
                # Calculate how many instances need to be added or removed
                target_covered_amount = (target_coverage / 100) * current_total
                difference = target_covered_amount - current_covered
                
                # Format the recommendation message
                if abs(difference) < 0.01:  # Small enough to consider as meeting target
                    change_msg = "At target"
                else:
                    change_msg = f"{difference:+.1f}"
                
                rec_table.add_row(
                    str(instance_size),
                    f"{current_coverage:.2f}%",
                    f"{current_covered:.2f}",
                    f"{current_total:.2f}",
                    change_msg
                )
            
            console.print(rec_table)


def output_to_html(
    pivot: pd.DataFrame,
    detailed_coverage: pd.DataFrame,
    unique_regions: List[str],
    target_coverage: float,
    start_date: str,
    end_date: str,
    total_days: int,
    ri_service_type: str = "RDS"
) -> None:
    # Create reports directory structure
    reports_dir = Path.cwd() / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_dir = reports_dir / f"ri-target-coverage-report-{current_date}"
    
    # Remove and recreate the report directory
    if report_dir.exists():
        for file_path in report_dir.glob("*"):
            file_path.unlink()
        report_dir.rmdir()
    report_dir.mkdir()
    
    # Set hardcoded HTML output filename
    html_output = report_dir / "ri-target-coverage-report.html"
    """Generate and save HTML output with proper formatting"""
    html_parts = []
    
    # Start with the HTML template
    html_parts.append("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{ri_service_type} Reserved Instance Coverage Analysis</title>
        <style>
            :root {
                --primary-color: #0066cc;
                --secondary-color: #f6f8fa;
                --border-color: #ddd;
                --header-bg: #2c3e50;
                --warning-color: #e74c3c;
                --success-color: #27ae60;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 0;
                color: #333;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2em;
            }
            
            h1, h2, h3, h4 {
                color: var(--header-bg);
                margin-top: 1.5em;
                margin-bottom: 0.5em;
            }
            
            h1 { 
                text-align: center;
                padding: 1em;
                background: var(--header-bg);
                color: white;
                margin-top: 0;
            }
            
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 1.5em 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            
            th, td {
                border: 1px solid var(--border-color);
                padding: 12px;
                text-align: right;
            }
            
            th {
                background-color: var(--header-bg);
                color: white;
                font-weight: 600;
                text-align: left;
            }
            
            td:first-child {
                text-align: left;
            }
            
            tr:nth-child(even) {
                background-color: var(--secondary-color);
            }
            
            tr:hover {
                background-color: #f0f4f8;
            }
            
            .recommendations {
                border-left: 4px solid var(--primary-color);
                padding-left: 1em;
                margin: 1.5em 0;
            }
            
            .analysis-period {
                text-align: center;
                color: #666;
                margin: 1em 0 2em;
            }
            
            .positive-change {
                color: var(--warning-color);
            }
            
            .negative-change {
                color: var(--success-color);
            }
            
            .at-target {
                color: var(--success-color);
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
    """)
    
    # Add header and analysis period
    html_parts.append(f"""
            <h1>{ri_service_type} Reserved Instance Coverage Analysis</h1>
            <div class="analysis-period">
                Analysis period: {start_date} to {end_date} ({total_days} days)
            </div>
    """)
    
    # Add pivot table
    html_parts.append("""
            <h2>Pivot Table by Region, Database Engine, and Base Instance Size</h2>
    """)
    # Format pivot table with 1 decimal place
    formatted_pivot = pivot.round(1)
    html_parts.append(formatted_pivot.to_html(classes='pivot-table'))
    
    # Add coverage percentage by region and instance size
    html_parts.append("<h2>Coverage Percentage by Region and Instance Size</h2>")
    
    for region in unique_regions:
        html_parts.append(f"<h3>Region: {region}</h3>")
        region_data = detailed_coverage.loc[region]
        unique_engines = region_data.index.get_level_values('Database engine').unique()
        
        for engine in unique_engines:
            html_parts.append(f"<h4>Database Engine: {engine}</h4>")
            
            # Coverage table
            engine_data = region_data.xs(engine, level='Database engine')
            coverage_df = pd.DataFrame({
                'Base Instance Size': engine_data.index,
                'Total Amount': engine_data['Total amount'],
                'Covered Amount': engine_data['RI covered amount'],
                'Coverage %': engine_data['Coverage percentage'].map('{:.1f}%'.format)
            })
            html_parts.append(coverage_df.to_html(index=False, classes='coverage-table'))
            
            # Recommendations table
            html_parts.append(f"""
                <div class="recommendations">
                    <h4>Recommendations for {region} - {engine} (Target: {target_coverage}% coverage)</h4>
            """)
            
            recommendations = []
            for instance_size, row in engine_data.iterrows():
                current_coverage = row['Coverage percentage']
                current_total = row['Total amount']
                current_covered = row['RI covered amount']
                target_covered_amount = (target_coverage / 100) * current_total
                difference = target_covered_amount - current_covered
                
                if abs(difference) < 0.01:
                    change_class = 'at-target'
                    change_msg = 'At target'
                else:
                    change_class = 'positive-change' if difference > 0 else 'negative-change'
                    change_msg = f'{difference:+.2f}'
                
                recommendations.append({
                    'Base Instance Size': instance_size,
                    'Current Coverage %': f'{current_coverage:.1f}%',
                    'Covered Amount': f'{current_covered:.1f}',
                    'Current Total': f'{current_total:.1f}',
                    'Required Change': f'<span class="{change_class}">{change_msg}</span>'
                })
            
            rec_df = pd.DataFrame(recommendations)
            html_parts.append(rec_df.to_html(index=False, classes='recommendations-table', escape=False))
            html_parts.append('</div>')
    
    # Close HTML
    html_parts.append("""
        </div>
    </body>
    </html>
    """)
    
    # Write HTML output to file
    with open(html_output, 'w') as f:
        f.write('\n'.join(html_parts))
    
    console.print(f"[bold green]HTML report saved to:[/bold green] {html_output}")
