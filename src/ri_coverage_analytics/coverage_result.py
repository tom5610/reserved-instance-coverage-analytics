from pydantic import BaseModel
from typing import Dict

class CoverageResult(BaseModel):
    """
    Pydantic model for RI coverage analysis results.
    """
    overall_ri_coverage: float
    overall_ri_cost: float
    overall_od_cost: float
    ri_coverage_per_region: Dict[str, float]
    ri_cost_per_region: Dict[str, float]
    od_cost_per_region: Dict[str, float]
    ri_coverage_per_database_engine: Dict[str, float]
    ri_cost_per_database_engine: Dict[str, float]
    od_cost_per_database_engine: Dict[str, float]
