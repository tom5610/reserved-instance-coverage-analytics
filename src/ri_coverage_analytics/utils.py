from datetime import datetime
import re
from typing import Tuple
import functools

class RICoverageError(Exception):
    """Base exception class for RI coverage analytics errors."""
    pass

class DateFormatError(RICoverageError):
    """Exception raised when date format is invalid."""
    pass

class RegionMappingError(RICoverageError):
    """Exception raised when region mapping fails."""
    pass

class InstanceClassError(RICoverageError):
    """Exception raised when instance class parsing fails."""
    pass

def calculate_days(start_date: str, end_date: str) -> int:
    """
    Calculate the number of days between start-date and end-date inclusively.
    
    Args:
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        
    Returns:
        Number of days between start_date and end_date (inclusive)
        
    Raises:
        DateFormatError: If either date string is not in the required format
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        delta = end - start
        return delta.days + 1  # +1 to make it inclusive
    except ValueError:
        raise DateFormatError(f"Invalid date format. Both dates must be in YYYY-MM-DD format: start_date='{start_date}', end_date='{end_date}'")

@functools.lru_cache(maxsize=128)
def get_region_name_code_mapping(region_name: str) -> str:
    """
    Map a region name to its AWS region code with caching for performance.
    
    Args:
        region_name: The AWS region name (e.g. 'US East (N. Virginia)')
        
    Returns:
        The AWS region code (e.g. 'us-east-1')
        
    Raises:
        RegionMappingError: If the region name is not found in the mapping
    """
    # Replace 'EU ' with 'Europe ' if present at the start
    if region_name.startswith('EU '):
        region_name = 'Europe ' + region_name[3:]
    region_mapping = {
        'US East (Ohio)': 'us-east-2',
        'US East (N. Virginia)': 'us-east-1', 
        'US West (N. California)': 'us-west-1',
        'US West (Oregon)': 'us-west-2',
        'Africa (Cape Town)': 'af-south-1',
        'Asia Pacific (Hong Kong)': 'ap-east-1',
        'Asia Pacific (Hyderabad)': 'ap-south-2',
        'Asia Pacific (Jakarta)': 'ap-southeast-3',
        'Asia Pacific (Malaysia)': 'ap-southeast-5',
        'Asia Pacific (Melbourne)': 'ap-southeast-4',
        'Asia Pacific (Mumbai)': 'ap-south-1',
        'Asia Pacific (Osaka)': 'ap-northeast-3',
        'Asia Pacific (Seoul)': 'ap-northeast-2',
        'Asia Pacific (Singapore)': 'ap-southeast-1',
        'Asia Pacific (Sydney)': 'ap-southeast-2',
        'Asia Pacific (Thailand)': 'ap-southeast-7',
        'Asia Pacific (Tokyo)': 'ap-northeast-1',
        'Canada (Central)': 'ca-central-1',
        'Canada West (Calgary)': 'ca-west-1',
        'Europe (Frankfurt)': 'eu-central-1',
        'Europe (Ireland)': 'eu-west-1',
        'EU (Ireland)':  'eu-west-1',
        'Europe (London)': 'eu-west-2',
        'Europe (Milan)': 'eu-south-1',
        'Europe (Paris)': 'eu-west-3',
        'Europe (Spain)': 'eu-south-2',
        'Europe (Stockholm)': 'eu-north-1',
        'Europe (Zurich)': 'eu-central-2',
        'Israel (Tel Aviv)': 'il-central-1',
        'Mexico (Central)': 'mx-central-1',
        'Middle East (Bahrain)': 'me-south-1',
        'Middle East (UAE)': 'me-central-1',
        'South America (São Paulo)': 'sa-east-1',
        'AWS GovCloud (US-East)': 'us-gov-east-1',
        'AWS GovCloud (US-West)': 'us-gov-west-1'
    }
    
    try:
        return region_mapping[region_name]
    except KeyError:
        # Attempt a case-insensitive match as fallback
        region_name_lower = region_name.lower()
        for key, value in region_mapping.items():
            if key.lower() == region_name_lower:
                return value
                
        raise RegionMappingError(f"Unknown region name: {region_name}")

def convert_instance_class(instance_class: str) -> Tuple[str, float]:
    """
    Calculate and return the base instance size and size factor.
    
    This function normalizes instance sizes relative to 'large' instances.
    For example, xlarge = 2x large, 2xlarge = 4x large, etc.
    
    Args:
        instance_class: Instance class in format "db.{instance_family}.{instance_size}"
        
    Returns:
        A tuple containing:
            - Base instance size: String in format "db.{instance_family}.large"
            - Instance size factor: Float representing the size multiplier relative to large
            
    Raises:
        InstanceClassError: If the instance class format is invalid or size is unknown
    """
    # Early validation of input
    if not instance_class or not isinstance(instance_class, str):
        raise InstanceClassError(f"Instance class must be a non-empty string, got: {type(instance_class)}")
        
    # Extract instance family and size
    pattern = r"db\.([a-z0-9]+)\.([a-z0-9]+)"
    match = re.match(pattern, instance_class.strip())
    
    if not match:
        raise InstanceClassError(
            f"Invalid instance class format: {instance_class}. Expected format: db.{{family}}.{{size}}")
    
    family, size = match.groups()
    base_instance = f"db.{family}.large"
    
    # Normalize size to lowercase for consistent comparison
    size_lower = size.lower()
    
    # Calculate size factor
    try:
        if size_lower == "large":
            factor = 1.0
        elif size_lower == "xlarge":
            factor = 2.0
        elif "xlarge" in size_lower:
            # Extract the multiplier before 'xlarge'
            multiplier_str = size_lower.split("xlarge")[0]
            if multiplier_str:
                try:
                    factor = float(multiplier_str) * 2.0
                except ValueError:
                    raise InstanceClassError(
                        f"Invalid multiplier in instance class: {instance_class}. Cannot convert '{multiplier_str}' to number.")
            else:
                factor = 2.0
        elif size_lower == "medium":
            factor = 0.5
        elif size_lower == "small":
            factor = 0.25
        elif size_lower == "micro":
            factor = 0.125
        else:
            raise InstanceClassError(f"Unknown instance size: {size} in class {instance_class}")
    except Exception as e:
        if isinstance(e, InstanceClassError):
            raise
        raise InstanceClassError(f"Error processing instance class {instance_class}: {str(e)}")
    
    return base_instance, factor
