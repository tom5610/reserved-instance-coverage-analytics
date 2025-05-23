from datetime import datetime
import re

def calculate_days(start_date: str, end_date: str) -> int:
    """
    Return the days between start-date and end-date inclusively.
    
    Args:
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        
    Returns:
        int: Number of days between start_date and end_date (inclusive)
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    delta = end - start
    return delta.days + 1  # +1 to make it inclusive

def get_region_name_code_mapping(region_name: str) -> str:
    """
    Map a region name to its AWS region code.
    
    Args:
        region_name (str): The AWS region name (e.g. 'US East (N. Virginia)')
        
    Returns:
        str: The AWS region code (e.g. 'us-east-1')
        
    Raises:
        ValueError: If the region name is not found in the mapping
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
        raise ValueError(f"Unknown region name: {region_name}")

def convert_instance_class(instance_class: str) -> tuple:
    """
    Calculate and return (Base instance size, Instance size factor).
    
    Args:
        instance_class (str): Instance class in format "db.{instance_family}.{instance_size}"
        
    Returns:
        tuple: (Base instance size, Instance size factor)
            - Base instance size: String in format "db.{instance_family}.large"
            - Instance size factor: Float representing the size factor relative to large
    """
    # Extract instance family and size
    pattern = r"db\.([a-z0-9]+)\.([a-z0-9]+)"
    match = re.match(pattern, instance_class)
    
    if not match:
        raise ValueError(f"Invalid instance class format: {instance_class}")
    
    family, size = match.groups()
    base_instance = f"db.{family}.large"
    
    # Calculate size factor
    if size == "large":
        factor = 1.0
    elif size == "xlarge":
        factor = 2.0
    elif "xlarge" in size:
        # Extract the multiplier before 'xlarge'
        multiplier = size.split("xlarge")[0]
        if multiplier:
            factor = float(multiplier) * 2.0
        else:
            factor = 2.0
    elif size == "medium":
        factor = 0.5
    elif size == "small":
        factor = 0.25
    elif size == "micro":
        factor = 0.125
    else:
        raise ValueError(f"Unknown instance size: {size}")
    
    return base_instance, factor
