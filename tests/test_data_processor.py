"""
Unit tests for the data processing functions in ri_coverage_analytics.data_processor.
"""
import pytest
import pandas as pd
from ri_coverage_analytics.data_processor import (
    process_instance_data,
    calculate_coverage_metrics,
    create_coverage_analysis
)


class TestProcessInstanceData:
    """Tests for process_instance_data function."""
    
    def test_process_instance_data_basic(self, sample_csv_data):
        """Test the basic processing of instance data."""
        # Get sample data
        df = sample_csv_data['instance_data']
        
        # Process the data
        result_df = process_instance_data(df, '2023-01-01', '2023-01-30')
        
        # Check that all expected columns are present
        expected_columns = [
            'Total days', '(est.) Instance amount', 'Base instance size',
            'Instance size factor', 'Total amount', 'RI covered amount', 'region_code'
        ]
        for col in expected_columns:
            assert col in result_df.columns
        
        # Check that the total days is calculated correctly
        assert result_df['Total days'].iloc[0] == 30
        
        # Verify that instance amounts are calculated correctly (720 hours / (24 * 30) = 1 instance)
        assert all(result_df['(est.) Instance amount'] == 1.0)
    
    def test_multi_az_handling(self, sample_csv_data):
        """Test that Multi-AZ deployments are properly handled."""
        df = sample_csv_data['instance_data']
        result_df = process_instance_data(df, '2023-01-01', '2023-01-30')
        
        # Find the Multi-AZ row
        multi_az_row = result_df[result_df['Deployment option'] == 'Multi-AZ']
        
        # Check that the amount is doubled for Multi-AZ
        assert multi_az_row['Total amount'].iloc[0] == multi_az_row['(est.) Instance amount'].iloc[0] * multi_az_row['Instance size factor'].iloc[0] * 2
    
    def test_instance_class_conversion(self, sample_csv_data):
        """Test that instance classes are properly converted."""
        df = sample_csv_data['instance_data']
        result_df = process_instance_data(df, '2023-01-01', '2023-01-30')
        
        # Check conversion for a sample row with xlarge
        xlarge_row = result_df[result_df['Instance class'] == 'db.r6g.xlarge']
        assert xlarge_row['Base instance size'].iloc[0] == 'db.r6g.large'
        assert xlarge_row['Instance size factor'].iloc[0] == 2.0
        
        # Check conversion for a sample row with 2xlarge
        x2large_row = result_df[result_df['Instance class'] == 'db.r5.2xlarge']
        assert x2large_row['Base instance size'].iloc[0] == 'db.r5.large'
        assert x2large_row['Instance size factor'].iloc[0] == 4.0


class TestCalculateCoverageMetrics:
    """Tests for calculate_coverage_metrics function."""
    
    def test_calculate_coverage_metrics_with_data(self, sample_csv_data):
        """Test coverage calculation with sample data."""
        recommendations_df = sample_csv_data['recommendations_data']
        utilization_df = sample_csv_data['utilization_data']
        
        coverage_result = calculate_coverage_metrics(recommendations_df, utilization_df)
        
        # Verify the overall coverage calculation
        total_ri_cost = utilization_df['On-Demand cost equivalent'].sum()
        total_od_cost = 0  # Will be calculated from recommendations_df
        
        # Calculate the expected on-demand cost from recommendations
        for _, row in recommendations_df.iterrows():
            od_cost = (row['Upfront cost'] / (12 * int(row['Term'])) + 
                      row['Recurring monthly cost'] + 
                      row['Estimated savings']) * 12 / 365 * 30
            total_od_cost += od_cost
        
        expected_coverage = total_ri_cost / (total_ri_cost + total_od_cost) * 100
        assert abs(coverage_result.overall_ri_coverage - expected_coverage) < 0.01
    
    def test_calculate_coverage_metrics_empty_data(self):
        """Test coverage calculation with empty DataFrames."""
        empty_recommendations = pd.DataFrame()
        empty_utilization = pd.DataFrame()
        
        coverage_result = calculate_coverage_metrics(empty_recommendations, empty_utilization)
        
        # With no data, coverage should be 0
        assert coverage_result.overall_ri_coverage == 0
        assert coverage_result.overall_ri_cost == 0
        assert coverage_result.overall_od_cost == 0
        assert len(coverage_result.ri_coverage_per_region) == 0
        assert len(coverage_result.ri_cost_per_region) == 0


class TestCreateCoverageAnalysis:
    """Tests for create_coverage_analysis function."""
    
    def test_create_coverage_analysis(self, sample_csv_data):
        """Test creation of coverage analysis with recommendations."""
        # Set up test data
        df = process_instance_data(sample_csv_data['instance_data'], '2023-01-01', '2023-01-30')
        
        # Create pivot table for testing
        pivot = pd.pivot_table(
            df,
            values=['RI covered amount', 'Total amount'],
            index=['region_code', 'Database engine', 'Base instance size'],
            aggfunc='sum'
        )
        
        # Create detailed coverage data for testing
        detailed_coverage = df.groupby(['region_code', 'Database engine', 'Base instance size']).agg({
            'RI covered amount': 'sum',
            'Total amount': 'sum'
        })
        detailed_coverage['Coverage percentage'] = (detailed_coverage['RI covered amount'] / 
                                                 detailed_coverage['Total amount'] * 100)
        
        # Run the coverage analysis
        target_coverage = 80.0
        recommendations = create_coverage_analysis(df, detailed_coverage, target_coverage)
        
        # Check that the recommendations DataFrame has the expected structure
        expected_columns = [
            'Region', 'Database engine', 'Base instance size', 'Current coverage (%)',
            'Current covered amount', 'Current total amount', 
            'Target covered amount', 'Required change'
        ]
        for col in expected_columns:
            assert col in recommendations.columns
        
        # Check that the required change is calculated correctly for each row
        for _, row in recommendations.iterrows():
            target_covered = (target_coverage / 100) * row['Current total amount']
            required_change = target_covered - row['Current covered amount']
            assert abs(row['Required change'] - required_change) < 0.01