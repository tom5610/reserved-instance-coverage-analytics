"""
Unit tests for the utility functions in ri_coverage_analytics.utils.
"""
import pytest
from ri_coverage_analytics.utils import (
    calculate_days,
    get_region_name_code_mapping,
    convert_instance_class,
    DateFormatError,
    RegionMappingError,
    InstanceClassError
)


class TestCalculateDays:
    """Tests for the calculate_days function."""
    
    def test_calculate_days_same_day(self):
        """Test calculation for same day (should be 1)."""
        result = calculate_days("2023-01-01", "2023-01-01")
        assert result == 1
    
    def test_calculate_days_different_days(self):
        """Test calculation for a range of days."""
        result = calculate_days("2023-01-01", "2023-01-31")
        assert result == 31
    
    def test_calculate_days_different_months(self):
        """Test calculation across month boundaries."""
        result = calculate_days("2023-01-15", "2023-02-15")
        assert result == 32
    
    def test_calculate_days_different_years(self):
        """Test calculation across year boundaries."""
        result = calculate_days("2022-12-15", "2023-01-15")
        assert result == 32
    
    def test_calculate_days_invalid_format(self):
        """Test handling of invalid date formats."""
        with pytest.raises(DateFormatError):
            calculate_days("01-01-2023", "2023-01-31")
        
        with pytest.raises(DateFormatError):
            calculate_days("2023-01-01", "01/31/2023")
        
        with pytest.raises(DateFormatError):
            calculate_days("not-a-date", "also-not-a-date")


class TestRegionNameCodeMapping:
    """Tests for the get_region_name_code_mapping function."""
    
    def test_common_regions(self):
        """Test mapping for common AWS regions."""
        assert get_region_name_code_mapping("US East (N. Virginia)") == "us-east-1"
        assert get_region_name_code_mapping("US West (Oregon)") == "us-west-2"
        assert get_region_name_code_mapping("Europe (Frankfurt)") == "eu-central-1"
    
    def test_eu_prefix_handling(self):
        """Test handling of EU prefix vs Europe prefix."""
        assert get_region_name_code_mapping("EU (Ireland)") == "eu-west-1"
        assert get_region_name_code_mapping("Europe (Ireland)") == "eu-west-1"
    
    def test_case_insensitive_fallback(self):
        """Test case-insensitive matching as fallback."""
        # This will test our case-insensitive fallback implementation
        assert get_region_name_code_mapping("us east (n. virginia)") == "us-east-1"
        assert get_region_name_code_mapping("EUROPE (FRANKFURT)") == "eu-central-1"
    
    def test_unknown_region(self):
        """Test handling of unknown regions."""
        with pytest.raises(RegionMappingError):
            get_region_name_code_mapping("Non-existent Region")


class TestConvertInstanceClass:
    """Tests for the convert_instance_class function."""
    
    def test_base_instance_sizes(self):
        """Test handling of the base instance size 'large'."""
        base_size, factor = convert_instance_class("db.m5.large")
        assert base_size == "db.m5.large"
        assert factor == 1.0
    
    def test_xlarge_instance(self):
        """Test handling of 'xlarge' instance sizes."""
        base_size, factor = convert_instance_class("db.m5.xlarge")
        assert base_size == "db.m5.large"
        assert factor == 2.0
    
    def test_multiple_xlarge_instance(self):
        """Test handling of multiple 'xlarge' instance sizes."""
        base_size, factor = convert_instance_class("db.m5.2xlarge")
        assert base_size == "db.m5.large"
        assert factor == 4.0
        
        base_size, factor = convert_instance_class("db.r5.8xlarge")
        assert base_size == "db.r5.large"
        assert factor == 16.0
    
    def test_smaller_than_large_instances(self):
        """Test handling of instances smaller than 'large'."""
        base_size, factor = convert_instance_class("db.t3.medium")
        assert base_size == "db.t3.large"
        assert factor == 0.5
        
        base_size, factor = convert_instance_class("db.t3.small")
        assert base_size == "db.t3.large"
        assert factor == 0.25
        
        base_size, factor = convert_instance_class("db.t3.micro")
        assert base_size == "db.t3.large"
        assert factor == 0.125
    
    def test_invalid_instance_class_format(self):
        """Test handling of invalid instance class formats."""
        with pytest.raises(InstanceClassError):
            convert_instance_class("invalid.format")
        
        with pytest.raises(InstanceClassError):
            convert_instance_class("db.m5")
        
        with pytest.raises(InstanceClassError):
            convert_instance_class("")
    
    def test_unknown_instance_size(self):
        """Test handling of unknown instance sizes."""
        with pytest.raises(InstanceClassError):
            convert_instance_class("db.m5.unknown")
    
    def test_input_validation(self):
        """Test input validation for the instance class parameter."""
        with pytest.raises(InstanceClassError):
            convert_instance_class(None)
        
        with pytest.raises(InstanceClassError):
            convert_instance_class(123)  # type: ignore
    
    def test_case_insensitivity(self):
        """Test case insensitivity for instance sizes."""
        base_size, factor = convert_instance_class("db.m5.LARGE")
        assert base_size == "db.m5.large"
        assert factor == 1.0
        
        base_size, factor = convert_instance_class("db.r5.XLarge")
        assert base_size == "db.r5.large"
        assert factor == 2.0