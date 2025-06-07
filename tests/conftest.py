"""
Pytest configuration and fixtures for Reserved Instance coverage analytics tests.
"""
import pytest
import pandas as pd
from pathlib import Path
import os
import json


@pytest.fixture
def sample_csv_data():
    """
    Fixture providing sample CSV data for testing.
    
    Returns:
        Dict containing sample dataframes for various test scenarios
    """
    # Simple instance data for target coverage analysis
    instance_data = pd.DataFrame({
        'Region': ['US East (N. Virginia)', 'US West (Oregon)', 'Europe (Frankfurt)'],
        'Database engine': ['PostgreSQL', 'MySQL', 'Aurora MySQL'],
        'Instance class': ['db.m5.large', 'db.r5.2xlarge', 'db.r6g.xlarge'],
        'Deployment option': ['Single-AZ', 'Multi-AZ', 'Single-AZ'],
        'Total running hours': [720, 720, 720],
        'Average coverage': [0.75, 0.50, 0.80]
    })
    
    # Sample utilization data
    utilization_data = pd.DataFrame({
        'Region': ['US East (N. Virginia)', 'US West (Oregon)'],
        'Database engine': ['PostgreSQL', 'MySQL'],
        'On-Demand cost equivalent': [1000.0, 1500.0]
    })
    
    # Sample recommendations data
    recommendations_data = pd.DataFrame({
        'Region': ['US East (N. Virginia)', 'US West (Oregon)'],
        'Database engine': ['PostgreSQL', 'MySQL'],
        'Term': ['1', '3'],
        'Upfront cost': [2000.0, 5000.0],
        'Recurring monthly cost': [500.0, 400.0],
        'Estimated savings': [200.0, 300.0]
    })
    
    return {
        'instance_data': instance_data,
        'utilization_data': utilization_data,
        'recommendations_data': recommendations_data
    }


@pytest.fixture
def mock_region_mapping():
    """
    Fixture providing mock region name to code mapping.
    
    Returns:
        Dict mapping region names to region codes
    """
    return {
        'US East (N. Virginia)': 'us-east-1',
        'US East (Ohio)': 'us-east-2',
        'US West (Oregon)': 'us-west-2',
        'US West (N. California)': 'us-west-1',
        'Europe (Ireland)': 'eu-west-1',
        'Europe (Frankfurt)': 'eu-central-1',
        'Asia Pacific (Tokyo)': 'ap-northeast-1',
        'Asia Pacific (Singapore)': 'ap-southeast-1',
        'Asia Pacific (Sydney)': 'ap-southeast-2'
    }


@pytest.fixture
def sample_coverage_result():
    """
    Fixture providing a sample CoverageResult for testing.
    
    Returns:
        Dict representing a sample CoverageResult
    """
    return {
        'overall_ri_coverage': 65.0,
        'overall_ri_cost': 2500.0,
        'overall_od_cost': 1500.0,
        'ri_coverage_per_region': {
            'us-east-1': 70.0,
            'us-west-2': 60.0
        },
        'ri_cost_per_region': {
            'us-east-1': 1000.0,
            'us-west-2': 1500.0
        },
        'od_cost_per_region': {
            'us-east-1': 500.0,
            'us-west-2': 1000.0
        },
        'ri_coverage_per_database_engine': {
            'PostgreSQL': 75.0,
            'MySQL': 55.0
        },
        'ri_cost_per_database_engine': {
            'PostgreSQL': 1200.0,
            'MySQL': 1300.0
        },
        'od_cost_per_database_engine': {
            'PostgreSQL': 700.0,
            'MySQL': 800.0
        }
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """
    Fixture providing a temporary directory for test outputs.
    
    Args:
        tmp_path: Pytest's built-in temporary directory fixture
        
    Returns:
        Path object representing the temporary output directory
    """
    output_dir = tmp_path / "test_reports"
    output_dir.mkdir()
    return output_dir