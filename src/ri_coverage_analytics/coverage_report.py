import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import base64
from io import BytesIO
from ri_coverage_analytics.coverage_result import CoverageResult

def output_picture_format(result: CoverageResult, output_dir: Path = None, ri_service_type: str = "RDS"):
    """
    Generate visualizations for RI coverage analysis.
    
    Args:
        result: CoverageResult object containing the analysis data
        output_dir: Directory to save the generated charts (defaults to current directory)
    """
    # Create base reports directory
    reports_dir = Path.cwd() / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Create dated subfolder
    current_date = datetime.now().strftime("%Y-%m-%d")
    report_dir = reports_dir / f"ri-cost-coverage-report-{current_date}"
    
    # Remove and recreate the report directory
    if report_dir.exists():
        for file_path in report_dir.glob("*"):
            file_path.unlink()
        report_dir.rmdir()
    report_dir.mkdir()
    
    # Use the report directory for output
    output_dir = report_dir
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create overall coverage pie chart
    plt.figure(figsize=(10, 6))
    labels = [f'RI Coverage\n(${result.overall_ri_cost:,.2f})', 
             f'On-Demand\n(${result.overall_od_cost:,.2f})']
    sizes = [result.overall_ri_coverage, 100 - result.overall_ri_coverage]
    colors = ['#66b3ff', '#ff9999']
    explode = (0.1, 0)  # explode the 1st slice (RI Coverage)
    
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=90)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.title(f'Overall RI Coverage: {result.overall_ri_coverage:.2f}%\nTotal Cost: ${(result.overall_ri_cost + result.overall_od_cost):,.2f}',
              pad=20, weight='bold')
    plt.savefig(output_dir / f"overall_coverage_{timestamp}.png")
    plt.close()
    
    # Create per-region coverage charts
    if result.ri_coverage_per_region:
        plt.figure(figsize=(12, 8))
        regions = list(result.ri_coverage_per_region.keys())
        coverage_values = list(result.ri_coverage_per_region.values())
        
        # Sort by coverage percentage
        sorted_indices = np.argsort(coverage_values)[::-1]  # descending order
        regions = [regions[i] for i in sorted_indices]
        coverage_values = [coverage_values[i] for i in sorted_indices]
        
        plt.bar(regions, coverage_values, color='skyblue')
        plt.axhline(y=result.overall_ri_coverage, color='r', linestyle='-', label=f'Overall Avg: {result.overall_ri_coverage:.2f}%')
        plt.xlabel('AWS Region')
        plt.ylabel('Coverage Percentage (%)')
        plt.title('RI Coverage by Region')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.legend()
        plt.savefig(output_dir / f"region_coverage_{timestamp}.png")
        plt.close()
        
        # Create pie charts for each region
        for region, coverage in result.ri_coverage_per_region.items():
            plt.figure(figsize=(8, 6))
            ri_cost = result.ri_cost_per_region[region]
            od_cost = result.od_cost_per_region[region]
            labels = [f'RI Coverage\n(${ri_cost:,.2f})', 
                     f'On-Demand\n(${od_cost:,.2f})']
            sizes = [coverage, 100 - coverage]
            colors = ['#66b3ff', '#ff9999']
            explode = (0.1, 0)
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=90)
            plt.axis('equal')
            plt.title(f'RI Coverage for Region {region}: {coverage:.2f}%\nTotal Cost: ${(ri_cost + od_cost):,.2f}',
                     pad=20, weight='bold')
            plt.savefig(output_dir / f"region_{region}_coverage_{timestamp}.png")
            plt.close()
    
    # Create per-database-engine coverage charts
    if result.ri_coverage_per_database_engine:
        plt.figure(figsize=(12, 8))
        engines = list(result.ri_coverage_per_database_engine.keys())
        coverage_values = list(result.ri_coverage_per_database_engine.values())
        
        # Sort by coverage percentage
        sorted_indices = np.argsort(coverage_values)[::-1]  # descending order
        engines = [engines[i] for i in sorted_indices]
        coverage_values = [coverage_values[i] for i in sorted_indices]
        
        plt.bar(engines, coverage_values, color='lightgreen')
        plt.axhline(y=result.overall_ri_coverage, color='r', linestyle='-', label=f'Overall Avg: {result.overall_ri_coverage:.2f}%')
        plt.xlabel('Database Engine')
        plt.ylabel('Coverage Percentage (%)')
        plt.title('RI Coverage by Database Engine')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.legend()
        plt.savefig(output_dir / f"engine_coverage_{timestamp}.png")
        plt.close()
        
        # Create pie charts for each database engine
        for engine, coverage in result.ri_coverage_per_database_engine.items():
            plt.figure(figsize=(8, 6))
            ri_cost = result.ri_cost_per_database_engine[engine]
            od_cost = result.od_cost_per_database_engine[engine]
            labels = [f'RI Coverage\n(${ri_cost:,.2f})', 
                     f'On-Demand\n(${od_cost:,.2f})']
            sizes = [coverage, 100 - coverage]
            colors = ['#66b3ff', '#ff9999']
            explode = (0.1, 0)
            
            plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=90)
            plt.axis('equal')
            plt.title(f'RI Coverage for {engine}: {coverage:.2f}%\nTotal Cost: ${(ri_cost + od_cost):,.2f}',
                     pad=20, weight='bold')
            plt.savefig(output_dir / f"engine_{engine.replace(' ', '_')}_coverage_{timestamp}.png")
            plt.close()
    
    # Generate HTML report
    html_content = generate_html_report(
        result,
        timestamp,
        output_dir,
        result.overall_ri_coverage,
        ri_service_type=ri_service_type
    )
    
    # Save HTML report
    html_file = output_dir / "ri-cost-coverage-report.html"
    with open(html_file, "w") as f:
        f.write(html_content)
    
    print(f"Generated reports saved to {report_dir}")
    print(f"HTML report saved as {html_file}")
    print(f"Report directory: {report_dir}")

def generate_html_report(result, timestamp, output_dir, overall_coverage, ri_service_type="RDS"):
    """Generate HTML report with embedded charts."""
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reserved Instance Cost Coverage Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; }}
            .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .chart {{ margin: 20px 0; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>{ri_service_type} Reserved Instance Cost Coverage Report</h1>
        <div class="section important-note" style="background-color: #fff3cd; border-color: #ffeeba; color: #856404; margin-bottom: 30px;">
            <p style="font-weight: bold;">Important Note:</p>
            <p>The RI coverage cost is the related On-Demand cost equivalent, which will be used for cost coverage calculation. On the other hand, the On-Demand usage estimation is backed by the RI recommendations report, which may not necessarily include all the existing On-Demand usage. e.g. Customer may scale out instances (and they may not be counted for RI coverage given they don't persist 24x7.)</p>
        </div>
        <div class="section">
            <h2>Summary</h2>
            <div class="summary">
                <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Overall RI Coverage:</strong> {overall_coverage:.2f}%</p>
            </div>
            <div class="chart">
                <img src="overall_coverage_{timestamp}.png" alt="Overall Coverage Chart">
            </div>
        </div>
        
        <div class="section">
            <h2>Coverage by Region</h2>
            <div class="chart">
                <img src="region_coverage_{timestamp}.png" alt="Region Coverage Chart">
            </div>
            <h3>Individual Region Details</h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                {''.join([f'<div class="chart"><img src="region_{region}_coverage_{timestamp}.png" alt="Coverage for {region}"></div>' 
                         for region in result.ri_coverage_per_region.keys()])}
            </div>
        </div>
        
        <div class="section">
            <h2>Coverage by Database Engine</h2>
            <div class="chart">
                <img src="engine_coverage_{timestamp}.png" alt="Engine Coverage Chart">
            </div>
            <h3>Individual Engine Details</h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                {''.join([f'<div class="chart"><img src="engine_{engine.replace(" ", "_")}_coverage_{timestamp}.png" alt="Coverage for {engine}"></div>' 
                         for engine in result.ri_coverage_per_database_engine.keys()])}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template
