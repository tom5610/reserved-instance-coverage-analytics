"""
Data processing module for Reserved Instance coverage analytics.

This module contains functions for processing and transforming AWS Cost Explorer data
related to Reserved Instance (RI) coverage and utilization.
"""
import pandas as pd
from typing import Tuple, Dict, List, Any
from datetime import datetime
from pathlib import Path

from ri_coverage_analytics.utils import (
    calculate_days,
    convert_instance_class,
    get_region_name_code_mapping,
    InstanceClassError
)
from ri_coverage_analytics.coverage_result import CoverageResult


def process_instance_data(
    df: pd.DataFrame,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Process RDS instance data to calculate RI coverage metrics.
    
    This function transforms raw instance data by:
    1. Calculating estimated instance amounts
    2. Normalizing instance sizes
    3. Computing RI coverage metrics
    
    Args:
        df: DataFrame containing raw instance data
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        DataFrame with processed instance data including calculated metrics
    """
    # Calculate total days
    total_days = calculate_days(start_date, end_date)
    
    # Prepare empty arrays for calculated columns
    num_rows = len(df)
    base_sizes = pd.Series([''] * num_rows, index=df.index)
    size_factors = pd.Series([1.0] * num_rows, index=df.index)
    
    # Calculate (est.) Instance amount using vectorized operations
    est_instance_amounts = df['Total running hours'] / (24 * total_days)
    
    # Process instance classes
    for idx, row in df.iterrows():
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
                    base_sizes[idx] = instance_class
                    size_factors[idx] = 1.0
                else:
                    base_size, size_factor = convert_instance_class(instance_class)
                    base_sizes[idx] = base_size
                    size_factors[idx] = size_factor
            except InstanceClassError as e:
                # Log the error and continue with defaults
                print(f"Warning: {str(e)}")
                base_sizes[idx] = row['Instance class']
                size_factors[idx] = 1.0
        else:
            # For other engines, use the instance class as is
            base_sizes[idx] = row['Instance class']
            size_factors[idx] = 1.0
    
    # Calculate total amounts and RI covered amounts
    total_amounts = est_instance_amounts * size_factors
    # Double for Multi-AZ deployments
    total_amounts = total_amounts.where(df['Deployment option'] != 'Multi-AZ', total_amounts * 2)
    
    # Calculate RI covered amount
    ri_covered_amounts = est_instance_amounts * size_factors * df['Average coverage']
    
    # Add calculated columns to dataframe
    df_processed = df.copy()
    df_processed['Total days'] = total_days
    df_processed['(est.) Instance amount'] = est_instance_amounts
    df_processed['Base instance size'] = base_sizes
    df_processed['Instance size factor'] = size_factors
    df_processed['Total amount'] = total_amounts
    df_processed['RI covered amount'] = ri_covered_amounts
    
    # Add region codes
    df_processed['region_code'] = df['Region'].apply(get_region_name_code_mapping)
    
    return df_processed


def calculate_coverage_metrics(
    recommendations_df: pd.DataFrame, 
    utilization_df: pd.DataFrame,
    days: int = 30
) -> CoverageResult:
    """
    Calculate RI coverage metrics based on recommendations and utilization data.
    
    Args:
        recommendations_df: DataFrame containing RI recommendations
        utilization_df: DataFrame containing RI utilization data
        days: Number of days covered by the utilization report
        
    Returns:
        CoverageResult object containing coverage percentages and cost metrics
    """
    # Add RegionCode column to recommendations dataframe if not empty
    if not recommendations_df.empty:
        recommendations_df['RegionCode'] = recommendations_df['Region'].apply(get_region_name_code_mapping)
        # consolidate on-demand cost equivalent for specified days
        recommendations_df['On-Demand cost equivalent'] = (
            recommendations_df['Upfront cost'] / (12 * recommendations_df['Term'].astype(int)) + 
            recommendations_df['Recurring monthly cost'] + 
            recommendations_df['Estimated savings']
        ) * 12 / 365 * days
    else:
        recommendations_df['RegionCode'] = pd.Series(dtype='str')
        recommendations_df['On-Demand cost equivalent'] = pd.Series(dtype='float64')
    
    # Process utilization dataframe if not empty
    if not utilization_df.empty:
        utilization_df['RegionCode'] = utilization_df['Region'].apply(get_region_name_code_mapping)
    else:
        utilization_df['RegionCode'] = pd.Series(dtype='str')
    
    # Calculate overall coverage
    total_ri_cost = utilization_df['On-Demand cost equivalent'].sum()
    total_od_cost = recommendations_df['On-Demand cost equivalent'].sum()
    
    # Calculate overall coverage percentage (handle division by zero)
    total_cost = total_ri_cost + total_od_cost
    if total_cost > 0:
        overall_coverage = total_ri_cost / total_cost * 100
    else:
        overall_coverage = 0.0
    
    # Calculate coverage per region
    unique_regions = set(utilization_df['RegionCode'].unique()).union(recommendations_df['RegionCode'].unique())
    region_coverage = {}
    ri_cost_per_region = {}
    od_cost_per_region = {}
    
    for region in unique_regions:
        region_ri_cost = utilization_df[utilization_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        region_od_cost = recommendations_df[recommendations_df['RegionCode'] == region]['On-Demand cost equivalent'].sum()
        
        ri_cost_per_region[region] = region_ri_cost
        od_cost_per_region[region] = region_od_cost
        
        region_total_cost = region_ri_cost + region_od_cost
        if region_total_cost > 0:
            region_coverage[region] = region_ri_cost / region_total_cost * 100
        else:
            region_coverage[region] = 0.0
    
    # Calculate coverage per database engine
    unique_engines = set(utilization_df['Database engine'].unique()).union(recommendations_df['Database engine'].unique())
    engine_coverage = {}
    ri_cost_per_engine = {}
    od_cost_per_engine = {}
    
    for engine in unique_engines:
        engine_ri_cost = utilization_df[utilization_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        engine_od_cost = recommendations_df[recommendations_df['Database engine'] == engine]['On-Demand cost equivalent'].sum()
        
        ri_cost_per_engine[engine] = engine_ri_cost
        od_cost_per_engine[engine] = engine_od_cost
        
        engine_total_cost = engine_ri_cost + engine_od_cost
        if engine_total_cost > 0:
            engine_coverage[engine] = engine_ri_cost / engine_total_cost * 100
        else:
            engine_coverage[engine] = 0.0
    
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
    
    return coverage_result


def create_coverage_analysis(
    df: pd.DataFrame,
    detailed_coverage: pd.DataFrame,
    target_coverage: float
) -> pd.DataFrame:
    """
    Create RI coverage analysis with recommendations to reach target coverage.
    
    Args:
        df: The processed instance data DataFrame
        detailed_coverage: DataFrame with detailed coverage metrics
        target_coverage: Target percentage for RI coverage
        
    Returns:
        DataFrame containing recommendations to reach target coverage
    """
    # Create pivot table for analysis
    pivot = pd.pivot_table(
        df,
        values=['RI covered amount', 'Total amount'],
        index=['region_code', 'Database engine', 'Base instance size'],
        aggfunc='sum'
    )
    
    # Calculate recommendations based on target coverage
    recommendations = []
    
    for (region, engine, instance_size), row in detailed_coverage.iterrows():
        current_coverage = row['Coverage percentage']
        current_total = row['Total amount']
        current_covered = row['RI covered amount']
        
        # Calculate how many instances need to be added or removed
        target_covered_amount = (target_coverage / 100) * current_total
        difference = target_covered_amount - current_covered
        
        recommendations.append({
            'Region': region,
            'Database engine': engine,
            'Base instance size': instance_size,
            'Current coverage (%)': current_coverage,
            'Current covered amount': current_covered,
            'Current total amount': current_total,
            'Target covered amount': target_covered_amount,
            'Required change': difference
        })
    
    return pd.DataFrame(recommendations)