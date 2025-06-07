"""
Configuration management for Reserved Instance coverage analytics.

This module provides centralized configuration options for the RI coverage analytics
tool, allowing for easy customization of default values and behaviors.
"""
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RICoverageConfig(BaseModel):
    """Configuration settings for RI coverage analytics."""
    
    # Default target coverage percentage
    default_target_coverage: float = Field(
        default=80.0,
        description="Default target coverage percentage for RI recommendations"
    )
    
    # Default RI service type
    default_ri_service_type: str = Field(
        default="RDS",
        description="Default AWS service type for Reserved Instances analysis"
    )
    
    # Default analysis period in days
    default_analysis_days: int = Field(
        default=30,
        description="Default number of days for analysis period"
    )
    
    # Reports directory name
    reports_dir_name: str = Field(
        default="reports",
        description="Directory name for storing generated reports"
    )
    
    # Format for date strings
    date_format: str = Field(
        default="%Y-%m-%d",
        description="Format for date strings (YYYY-MM-DD)"
    )
    
    # Report subdirectory formats
    target_coverage_report_dir_format: str = Field(
        default="ri-target-coverage-report-{date}",
        description="Format for target coverage report directory names"
    )
    
    cost_coverage_report_dir_format: str = Field(
        default="ri-cost-coverage-report-{date}",
        description="Format for cost coverage report directory names"
    )


def load_config() -> RICoverageConfig:
    """
    Load configuration from environment variables and defaults.
    
    Returns:
        RICoverageConfig object with configuration settings
    """
    config_dict = {
        "default_target_coverage": float(os.environ.get(
            "RI_DEFAULT_TARGET_COVERAGE", 80.0)),
        "default_ri_service_type": os.environ.get(
            "RI_DEFAULT_SERVICE_TYPE", "RDS"),
        "default_analysis_days": int(os.environ.get(
            "RI_DEFAULT_ANALYSIS_DAYS", 30)),
        "reports_dir_name": os.environ.get(
            "RI_REPORTS_DIR", "reports"),
        "date_format": os.environ.get(
            "RI_DATE_FORMAT", "%Y-%m-%d"),
        "target_coverage_report_dir_format": os.environ.get(
            "RI_TARGET_COVERAGE_DIR_FORMAT", "ri-target-coverage-report-{date}"),
        "cost_coverage_report_dir_format": os.environ.get(
            "RI_COST_COVERAGE_DIR_FORMAT", "ri-cost-coverage-report-{date}")
    }
    
    return RICoverageConfig(**config_dict)


# Create a global config instance
config = load_config()


def get_reports_dir() -> Path:
    """
    Get the reports directory path, creating it if it doesn't exist.
    
    Returns:
        Path object for the reports directory
    """
    reports_dir = Path.cwd() / config.reports_dir_name
    reports_dir.mkdir(exist_ok=True)
    return reports_dir


def get_report_dir(report_type: str) -> Path:
    """
    Get a specific report directory path for the current date.
    
    Args:
        report_type: Type of report ('target' or 'cost')
        
    Returns:
        Path object for the specific report directory
    
    Raises:
        ValueError: If an invalid report type is provided
    """
    current_date = datetime.now().strftime(config.date_format)
    
    if report_type.lower() == 'target':
        dir_name = config.target_coverage_report_dir_format.format(date=current_date)
    elif report_type.lower() == 'cost':
        dir_name = config.cost_coverage_report_dir_format.format(date=current_date)
    else:
        raise ValueError(f"Invalid report type: {report_type}. Use 'target' or 'cost'.")
    
    report_dir = get_reports_dir() / dir_name
    
    # Remove and recreate the report directory
    if report_dir.exists():
        for file_path in report_dir.glob("*"):
            file_path.unlink()
        report_dir.rmdir()
    report_dir.mkdir()
    
    return report_dir