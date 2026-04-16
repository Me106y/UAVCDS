"""
Coverage analysis and overlap rate calculation utilities.
"""

import math
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
import logging

from ..models import Coordinates, Waypoint, FlightPath, ActionGroup, Action, ActionTrigger, ActionType, ActionTriggerType
from .geometry import geometry_calculator

logger = logging.getLogger(__name__)


class CoverageAnalyzer:
    """Analyzes flight path coverage and calculates overlap rates."""
    
    def __init__(self):
        """Initialize the coverage analyzer."""
        self.geometry_calc = geometry_calculator
    
    def calculate_photo_footprint(
        self,
        position: Coordinates,
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float = -90.0
    ) -> Polygon:
        """Calculate photo footprint polygon on the ground."""
        # Default camera specs if not provided
        default_specs = {
            "sensor_width": 23.5,    # mm
            "sensor_height": 15.6,   # mm
            "focal_length": 24.0,    # mm
            "image_width": 5472,     # pixels
            "image_height": 3648     # pixels
        }
        
        specs = {**default_specs, **camera_specs}
        
        # Calculate ground coverage dimensions
        # Adjust for gimbal pitch (nadir = -90°, forward = 0°)
        pitch_rad = math.radians(abs(gimbal_pitch))
        height_factor = 1.0 / math.cos(pitch_rad) if pitch_rad < math.pi/2 else 1.0
        
        effective_height = flight_height * height_factor
        
        # Ground coverage width and height
        ground_width = (specs["sensor_width"] * effective_height) / specs["focal_length"]
        ground_height = (specs["sensor_height"] * effective_height) / specs["focal_length"]
        
        # Convert to degrees (approximate)
        center_lat = position.latitude
        lat_factor = math.cos(math.radians(center_lat))
        
        width_degrees = ground_width / (self.geometry_calc.earth_radius * math.pi / 180 * lat_factor)
        height_degrees = ground_height / (self.geometry_calc.earth_radius * math.pi / 180)
        
        # Create footprint polygon centered on position
        half_width = width_degrees / 2
        half_height = height_degrees / 2
        
        footprint_coords = [
            (position.longitude - half_width, position.latitude - half_height),
            (position.longitude + half_width, position.latitude - half_height),
            (position.longitude + half_width, position.latitude + half_height),
            (position.longitude - half_width, position.latitude + half_height)
        ]
        
        return Polygon(footprint_coords)
    
    def calculate_overlap_between_photos(
        self,
        photo1_pos: Coordinates,
        photo2_pos: Coordinates,
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float = -90.0
    ) -> float:
        """Calculate overlap percentage between two photos."""
        # Get footprints for both photos
        footprint1 = self.calculate_photo_footprint(photo1_pos, flight_height, camera_specs, gimbal_pitch)
        footprint2 = self.calculate_photo_footprint(photo2_pos, flight_height, camera_specs, gimbal_pitch)
        
        # Calculate intersection
        intersection = footprint1.intersection(footprint2)
        
        if intersection.is_empty:
            return 0.0
        
        # Calculate overlap percentage
        intersection_area = intersection.area
        footprint1_area = footprint1.area
        
        if footprint1_area == 0:
            return 0.0
        
        overlap_percentage = (intersection_area / footprint1_area) * 100
        return min(overlap_percentage, 100.0)
    
    def calculate_sidelap_between_lines(
        self,
        line1_positions: List[Coordinates],
        line2_positions: List[Coordinates],
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float = -90.0
    ) -> float:
        """Calculate sidelap percentage between two flight lines."""
        if not line1_positions or not line2_positions:
            return 0.0
        
        # Use middle positions of each line for sidelap calculation
        mid_idx1 = len(line1_positions) // 2
        mid_idx2 = len(line2_positions) // 2
        
        pos1 = line1_positions[mid_idx1]
        pos2 = line2_positions[mid_idx2]
        
        return self.calculate_overlap_between_photos(
            pos1, pos2, flight_height, camera_specs, gimbal_pitch
        )
    
    def analyze_flight_path_coverage(
        self,
        flight_path: FlightPath,
        survey_area: List[Coordinates],
        camera_specs: Dict[str, float],
        gimbal_pitch: float = -90.0
    ) -> Dict[str, Any]:
        """Analyze coverage of flight path over survey area."""
        if not flight_path.waypoints:
            return {
                "total_coverage_percentage": 0.0,
                "overlap_statistics": {},
                "coverage_gaps": [],
                "redundant_coverage": 0.0
            }
        
        # Create survey area polygon
        survey_coords = [(coord.longitude, coord.latitude) for coord in survey_area]
        survey_polygon = Polygon(survey_coords)
        
        # Calculate photo footprints for all waypoints
        photo_footprints = []
        for waypoint in flight_path.waypoints:
            footprint = self.calculate_photo_footprint(
                waypoint.coordinates,
                waypoint.coordinates.altitude or flight_path.global_height or 100.0,
                camera_specs,
                gimbal_pitch
            )
            photo_footprints.append(footprint)
        
        # Calculate total coverage
        if photo_footprints:
            total_coverage = unary_union(photo_footprints)
            coverage_within_survey = total_coverage.intersection(survey_polygon)
            
            coverage_percentage = (coverage_within_survey.area / survey_polygon.area) * 100
        else:
            coverage_percentage = 0.0
        
        # Calculate overlap statistics
        overlap_stats = self._calculate_overlap_statistics(
            flight_path.waypoints, flight_path.global_height or 100.0, camera_specs, gimbal_pitch
        )
        
        # Find coverage gaps
        coverage_gaps = self._find_coverage_gaps(
            survey_polygon, photo_footprints, camera_specs
        )
        
        # Calculate redundant coverage (areas covered multiple times)
        redundant_coverage = self._calculate_redundant_coverage(photo_footprints)
        
        return {
            "total_coverage_percentage": min(coverage_percentage, 100.0),
            "overlap_statistics": overlap_stats,
            "coverage_gaps": coverage_gaps,
            "redundant_coverage": redundant_coverage,
            "photo_count": len(photo_footprints),
            "survey_area_m2": self.geometry_calc.polygon_area(survey_area)
        }
    
    def _calculate_overlap_statistics(
        self,
        waypoints: List[Waypoint],
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float
    ) -> Dict[str, float]:
        """Calculate overlap statistics for waypoints."""
        if len(waypoints) < 2:
            return {
                "average_forward_overlap": 0.0,
                "min_forward_overlap": 0.0,
                "max_forward_overlap": 0.0,
                "forward_overlap_std": 0.0
            }
        
        forward_overlaps = []
        
        # Calculate forward overlap between consecutive waypoints
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i + 1]
            
            height1 = wp1.coordinates.altitude or flight_height
            height2 = wp2.coordinates.altitude or flight_height
            avg_height = (height1 + height2) / 2
            
            overlap = self.calculate_overlap_between_photos(
                wp1.coordinates, wp2.coordinates, avg_height, camera_specs, gimbal_pitch
            )
            forward_overlaps.append(overlap)
        
        if forward_overlaps:
            return {
                "average_forward_overlap": np.mean(forward_overlaps),
                "min_forward_overlap": np.min(forward_overlaps),
                "max_forward_overlap": np.max(forward_overlaps),
                "forward_overlap_std": np.std(forward_overlaps)
            }
        else:
            return {
                "average_forward_overlap": 0.0,
                "min_forward_overlap": 0.0,
                "max_forward_overlap": 0.0,
                "forward_overlap_std": 0.0
            }
    
    def _find_coverage_gaps(
        self,
        survey_polygon: Polygon,
        photo_footprints: List[Polygon],
        camera_specs: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Find areas within survey polygon that are not covered."""
        if not photo_footprints:
            return [{
                "area_m2": survey_polygon.area * (self.geometry_calc.earth_radius * math.pi / 180) ** 2,
                "percentage_of_survey": 100.0,
                "description": "No photo coverage"
            }]
        
        # Calculate total coverage
        total_coverage = unary_union(photo_footprints)
        
        # Find uncovered areas
        uncovered = survey_polygon.difference(total_coverage)
        
        gaps = []
        if not uncovered.is_empty:
            if hasattr(uncovered, 'geoms'):
                # Multiple gaps
                for gap in uncovered.geoms:
                    if isinstance(gap, Polygon):
                        gap_area_deg2 = gap.area
                        gap_area_m2 = gap_area_deg2 * (self.geometry_calc.earth_radius * math.pi / 180) ** 2
                        gap_percentage = (gap_area_deg2 / survey_polygon.area) * 100
                        
                        gaps.append({
                            "area_m2": gap_area_m2,
                            "percentage_of_survey": gap_percentage,
                            "description": f"Coverage gap of {gap_area_m2:.1f} m²"
                        })
            else:
                # Single gap
                if isinstance(uncovered, Polygon):
                    gap_area_deg2 = uncovered.area
                    gap_area_m2 = gap_area_deg2 * (self.geometry_calc.earth_radius * math.pi / 180) ** 2
                    gap_percentage = (gap_area_deg2 / survey_polygon.area) * 100
                    
                    gaps.append({
                        "area_m2": gap_area_m2,
                        "percentage_of_survey": gap_percentage,
                        "description": f"Coverage gap of {gap_area_m2:.1f} m²"
                    })
        
        return gaps
    
    def _calculate_redundant_coverage(self, photo_footprints: List[Polygon]) -> float:
        """Calculate percentage of area covered multiple times."""
        if len(photo_footprints) < 2:
            return 0.0
        
        # Calculate total area if no overlap
        total_individual_area = sum(footprint.area for footprint in photo_footprints)
        
        # Calculate actual covered area (with overlaps removed)
        if photo_footprints:
            actual_covered_area = unary_union(photo_footprints).area
        else:
            actual_covered_area = 0.0
        
        if actual_covered_area == 0:
            return 0.0
        
        # Redundant coverage percentage
        redundant_area = total_individual_area - actual_covered_area
        redundant_percentage = (redundant_area / actual_covered_area) * 100
        
        return max(redundant_percentage, 0.0)
    
    def validate_overlap_requirements(
        self,
        flight_path: FlightPath,
        camera_specs: Dict[str, float],
        required_forward_overlap: float = 80.0,
        required_sidelap: float = 70.0,
        gimbal_pitch: float = -90.0
    ) -> Dict[str, Any]:
        """Validate that flight path meets overlap requirements."""
        validation_results = {
            "meets_requirements": True,
            "issues": [],
            "warnings": [],
            "forward_overlap_check": {},
            "sidelap_check": {}
        }
        
        if not flight_path.waypoints:
            validation_results["meets_requirements"] = False
            validation_results["issues"].append("No waypoints in flight path")
            return validation_results
        
        # Check forward overlap
        overlap_stats = self._calculate_overlap_statistics(
            flight_path.waypoints,
            flight_path.global_height or 100.0,
            camera_specs,
            gimbal_pitch
        )
        
        min_forward_overlap = overlap_stats.get("min_forward_overlap", 0.0)
        avg_forward_overlap = overlap_stats.get("average_forward_overlap", 0.0)
        
        validation_results["forward_overlap_check"] = {
            "required": required_forward_overlap,
            "actual_min": min_forward_overlap,
            "actual_avg": avg_forward_overlap,
            "meets_requirement": min_forward_overlap >= required_forward_overlap
        }
        
        if min_forward_overlap < required_forward_overlap:
            validation_results["meets_requirements"] = False
            validation_results["issues"].append(
                f"Minimum forward overlap ({min_forward_overlap:.1f}%) below requirement ({required_forward_overlap}%)"
            )
        
        if avg_forward_overlap < required_forward_overlap:
            validation_results["warnings"].append(
                f"Average forward overlap ({avg_forward_overlap:.1f}%) below requirement ({required_forward_overlap}%)"
            )
        
        # For sidelap check, we would need to identify flight lines
        # This is a simplified check - in practice, you'd group waypoints by flight lines
        validation_results["sidelap_check"] = {
            "required": required_sidelap,
            "actual": "Not calculated (requires flight line identification)",
            "meets_requirement": True  # Assume OK for now
        }
        
        return validation_results
    
    def optimize_photo_positions(
        self,
        flight_line_start: Coordinates,
        flight_line_end: Coordinates,
        flight_height: float,
        camera_specs: Dict[str, float],
        target_overlap: float = 80.0,
        gimbal_pitch: float = -90.0
    ) -> List[Coordinates]:
        """Optimize photo positions along a flight line for target overlap."""
        # Calculate ground coverage length
        specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            **camera_specs
        }
        
        # Adjust for gimbal pitch
        pitch_rad = math.radians(abs(gimbal_pitch))
        height_factor = 1.0 / math.cos(pitch_rad) if pitch_rad < math.pi/2 else 1.0
        effective_height = flight_height * height_factor
        
        ground_length = (specs["sensor_height"] * effective_height) / specs["focal_length"]
        
        # Calculate photo spacing for target overlap
        overlap_factor = (100 - target_overlap) / 100
        photo_spacing = ground_length * overlap_factor
        
        # Calculate total line distance
        line_distance = self.geometry_calc.haversine_distance(flight_line_start, flight_line_end)
        
        if line_distance == 0:
            return [flight_line_start]
        
        # Calculate number of photos needed
        num_photos = max(1, int(math.ceil(line_distance / photo_spacing)) + 1)
        
        # Generate photo positions
        photo_positions = []
        bearing = self.geometry_calc.calculate_bearing(flight_line_start, flight_line_end)
        
        for i in range(num_photos):
            distance_along_line = (i * line_distance) / (num_photos - 1) if num_photos > 1 else 0
            
            photo_pos = self.geometry_calc.destination_point(
                flight_line_start, distance_along_line, bearing
            )
            photo_pos.altitude = flight_height
            photo_positions.append(photo_pos)
        
        return photo_positions
    
    def calculate_ground_resolution(
        self,
        flight_height: float,
        camera_specs: Dict[str, float]
    ) -> float:
        """Calculate ground resolution in cm/pixel."""
        specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648,
            **camera_specs
        }
        
        # Ground resolution = (sensor_width * flight_height) / (focal_length * image_width)
        ground_resolution_mm = (specs["sensor_width"] * flight_height * 1000) / (
            specs["focal_length"] * specs["image_width"]
        )
        
        # Convert to cm/pixel
        return ground_resolution_mm / 10
    
    def estimate_photo_count(
        self,
        survey_area: List[Coordinates],
        flight_height: float,
        camera_specs: Dict[str, float],
        forward_overlap: float = 80.0,
        sidelap: float = 70.0
    ) -> Dict[str, Any]:
        """Estimate number of photos needed for survey area."""
        if not survey_area:
            return {"estimated_photos": 0, "coverage_area_m2": 0}
        
        # Calculate survey area
        area_m2 = self.geometry_calc.polygon_area(survey_area)
        
        # Calculate photo footprint area
        footprint = self.calculate_photo_footprint(
            survey_area[0],  # Use first point as reference
            flight_height,
            camera_specs
        )
        
        # Convert footprint area from degrees² to m²
        footprint_area_deg2 = footprint.area
        footprint_area_m2 = footprint_area_deg2 * (self.geometry_calc.earth_radius * math.pi / 180) ** 2
        
        if footprint_area_m2 == 0:
            return {"estimated_photos": 0, "coverage_area_m2": area_m2}
        
        # Account for overlaps
        forward_factor = (100 - forward_overlap) / 100
        sidelap_factor = (100 - sidelap) / 100
        
        effective_coverage_per_photo = footprint_area_m2 * forward_factor * sidelap_factor
        
        # Estimate number of photos
        estimated_photos = max(1, int(math.ceil(area_m2 / effective_coverage_per_photo)))
        
        return {
            "estimated_photos": estimated_photos,
            "coverage_area_m2": area_m2,
            "photo_footprint_m2": footprint_area_m2,
            "effective_coverage_per_photo_m2": effective_coverage_per_photo,
            "ground_resolution_cm_per_pixel": self.calculate_ground_resolution(flight_height, camera_specs)
        }
    
    def validate_overlap_parameters(
        self,
        forward_overlap: float,
        sidelap: float,
        flight_height: float,
        camera_specs: Dict[str, float],
        flight_speed: float = 5.0
    ) -> Dict[str, Any]:
        """Validate overlap rate parameters and provide recommendations."""
        validation_result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "calculated_parameters": {}
        }
        
        # Validate overlap percentages
        if not (0 <= forward_overlap <= 95):
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"Forward overlap {forward_overlap}% is out of valid range (0-95%)")
        
        if not (0 <= sidelap <= 95):
            validation_result["is_valid"] = False
            validation_result["issues"].append(f"Sidelap {sidelap}% is out of valid range (0-95%)")
        
        # Check for typical mapping requirements
        if forward_overlap < 60:
            validation_result["warnings"].append("Forward overlap below 60% may result in poor reconstruction quality")
        
        if sidelap < 30:
            validation_result["warnings"].append("Sidelap below 30% may result in poor side coverage")
        
        if forward_overlap > 90:
            validation_result["warnings"].append("Forward overlap above 90% may be inefficient and increase flight time")
        
        if sidelap > 80:
            validation_result["warnings"].append("Sidelap above 80% may be inefficient and increase number of flight lines")
        
        # Calculate derived parameters
        try:
            # Calculate photo spacing based on overlap
            specs = {
                "sensor_width": 23.5,
                "sensor_height": 15.6,
                "focal_length": 24.0,
                **camera_specs
            }
            
            ground_width = (specs["sensor_width"] * flight_height) / specs["focal_length"]
            ground_height = (specs["sensor_height"] * flight_height) / specs["focal_length"]
            
            forward_spacing = ground_height * (100 - forward_overlap) / 100
            side_spacing = ground_width * (100 - sidelap) / 100
            
            # Calculate shooting intervals
            time_interval = forward_spacing / flight_speed
            distance_interval = forward_spacing
            
            validation_result["calculated_parameters"] = {
                "ground_width_m": ground_width,
                "ground_height_m": ground_height,
                "forward_spacing_m": forward_spacing,
                "side_spacing_m": side_spacing,
                "time_interval_s": time_interval,
                "distance_interval_m": distance_interval,
                "ground_resolution_cm_per_pixel": self.calculate_ground_resolution(flight_height, camera_specs)
            }
            
            # Provide recommendations
            if time_interval < 1.0:
                validation_result["recommendations"].append(
                    f"Time interval ({time_interval:.2f}s) is very short. Consider reducing speed or overlap."
                )
            
            if time_interval > 10.0:
                validation_result["recommendations"].append(
                    f"Time interval ({time_interval:.2f}s) is long. Consider increasing speed or overlap for better coverage."
                )
            
        except Exception as e:
            validation_result["issues"].append(f"Error calculating parameters: {str(e)}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    def analyze_flight_line_coverage(
        self,
        flight_lines: List[List[Coordinates]],
        survey_area: List[Coordinates],
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float = -90.0
    ) -> Dict[str, Any]:
        """Analyze coverage provided by multiple flight lines."""
        if not flight_lines:
            return {
                "total_coverage_percentage": 0.0,
                "line_coverage_details": [],
                "sidelap_analysis": {},
                "coverage_uniformity": 0.0,
                "efficiency_metrics": {}
            }
        
        # Create survey area polygon
        survey_coords = [(coord.longitude, coord.latitude) for coord in survey_area]
        survey_polygon = Polygon(survey_coords)
        survey_area_m2 = self.geometry_calc.polygon_area(survey_area)
        
        # Analyze each flight line
        line_coverage_details = []
        all_footprints = []
        
        for line_idx, line_positions in enumerate(flight_lines):
            if not line_positions:
                continue
            
            # Calculate footprints for this line
            line_footprints = []
            for pos in line_positions:
                footprint = self.calculate_photo_footprint(pos, flight_height, camera_specs, gimbal_pitch)
                line_footprints.append(footprint)
                all_footprints.append(footprint)
            
            # Calculate line coverage
            if line_footprints:
                line_coverage = unary_union(line_footprints)
                line_coverage_in_survey = line_coverage.intersection(survey_polygon)
                line_coverage_percentage = (line_coverage_in_survey.area / survey_polygon.area) * 100
            else:
                line_coverage_percentage = 0.0
            
            # Calculate forward overlap within line
            forward_overlaps = []
            if len(line_positions) > 1:
                for i in range(len(line_positions) - 1):
                    overlap = self.calculate_overlap_between_photos(
                        line_positions[i], line_positions[i + 1], flight_height, camera_specs, gimbal_pitch
                    )
                    forward_overlaps.append(overlap)
            
            line_details = {
                "line_index": line_idx,
                "photo_count": len(line_positions),
                "coverage_percentage": min(line_coverage_percentage, 100.0),
                "forward_overlap_stats": {
                    "average": np.mean(forward_overlaps) if forward_overlaps else 0.0,
                    "min": np.min(forward_overlaps) if forward_overlaps else 0.0,
                    "max": np.max(forward_overlaps) if forward_overlaps else 0.0,
                    "std": np.std(forward_overlaps) if forward_overlaps else 0.0
                },
                "line_length_m": self._calculate_line_length(line_positions)
            }
            line_coverage_details.append(line_details)
        
        # Calculate total coverage
        if all_footprints:
            total_coverage = unary_union(all_footprints)
            total_coverage_in_survey = total_coverage.intersection(survey_polygon)
            total_coverage_percentage = (total_coverage_in_survey.area / survey_polygon.area) * 100
        else:
            total_coverage_percentage = 0.0
        
        # Analyze sidelap between adjacent lines
        sidelap_analysis = self._analyze_sidelap_between_lines(flight_lines, flight_height, camera_specs, gimbal_pitch)
        
        # Calculate coverage uniformity (how evenly covered is the area)
        coverage_uniformity = self._calculate_coverage_uniformity(all_footprints, survey_polygon)
        
        # Calculate efficiency metrics
        total_photos = sum(len(line) for line in flight_lines)
        total_flight_distance = sum(self._calculate_line_length(line) for line in flight_lines)
        
        efficiency_metrics = {
            "photos_per_hectare": total_photos / (survey_area_m2 / 10000) if survey_area_m2 > 0 else 0,
            "coverage_per_photo": total_coverage_percentage / total_photos if total_photos > 0 else 0,
            "flight_distance_per_hectare": total_flight_distance / (survey_area_m2 / 10000) if survey_area_m2 > 0 else 0,
            "total_flight_distance_m": total_flight_distance
        }
        
        return {
            "total_coverage_percentage": min(total_coverage_percentage, 100.0),
            "line_coverage_details": line_coverage_details,
            "sidelap_analysis": sidelap_analysis,
            "coverage_uniformity": coverage_uniformity,
            "efficiency_metrics": efficiency_metrics,
            "total_photos": total_photos,
            "survey_area_m2": survey_area_m2
        }
    
    def configure_shooting_intervals(
        self,
        flight_path: FlightPath,
        camera_specs: Dict[str, float],
        target_overlap: float = 80.0,
        trigger_type: str = "distance"
    ) -> Dict[str, Any]:
        """Configure shooting intervals and triggers for optimal coverage."""
        if not flight_path.waypoints:
            return {
                "success": False,
                "error": "No waypoints in flight path",
                "action_groups": []
            }
        
        try:
            # Calculate optimal shooting parameters
            flight_height = flight_path.global_height or 100.0
            flight_speed = flight_path.global_speed or 5.0
            
            specs = {
                "sensor_width": 23.5,
                "sensor_height": 15.6,
                "focal_length": 24.0,
                **camera_specs
            }
            
            # Calculate ground coverage and spacing
            ground_height = (specs["sensor_height"] * flight_height) / specs["focal_length"]
            photo_spacing = ground_height * (100 - target_overlap) / 100
            
            # Configure trigger parameters based on type
            action_groups = []
            
            if trigger_type.lower() == "distance":
                # Distance-based triggering
                trigger = ActionTrigger(
                    trigger_type=ActionTriggerType.MULTIPLE_DISTANCE,
                    trigger_param=photo_spacing
                )
                
                # Create action group for the entire flight path
                take_photo_action = Action(
                    action_id=0,
                    action_type=ActionType.TAKE_PHOTO,
                    parameters={
                        "payloadPositionIndex": 0,
                        "fileSuffix": "mapping",
                        "useGlobalPayloadLensIndex": True
                    }
                )
                
                action_group = ActionGroup(
                    group_id=0,
                    start_index=0,
                    end_index=len(flight_path.waypoints) - 1,
                    trigger=trigger,
                    actions=[take_photo_action]
                )
                action_groups.append(action_group)
                
            elif trigger_type.lower() == "time":
                # Time-based triggering
                time_interval = photo_spacing / flight_speed
                
                trigger = ActionTrigger(
                    trigger_type=ActionTriggerType.MULTIPLE_TIMING,
                    trigger_param=time_interval
                )
                
                take_photo_action = Action(
                    action_id=0,
                    action_type=ActionType.TAKE_PHOTO,
                    parameters={
                        "payloadPositionIndex": 0,
                        "fileSuffix": "mapping",
                        "useGlobalPayloadLensIndex": True
                    }
                )
                
                action_group = ActionGroup(
                    group_id=0,
                    start_index=0,
                    end_index=len(flight_path.waypoints) - 1,
                    trigger=trigger,
                    actions=[take_photo_action]
                )
                action_groups.append(action_group)
                
            elif trigger_type.lower() == "waypoint":
                # Waypoint-based triggering (take photo at each waypoint)
                for i, waypoint in enumerate(flight_path.waypoints):
                    trigger = ActionTrigger(
                        trigger_type=ActionTriggerType.REACH_POINT,
                        trigger_param=None
                    )
                    
                    take_photo_action = Action(
                        action_id=0,
                        action_type=ActionType.TAKE_PHOTO,
                        parameters={
                            "payloadPositionIndex": 0,
                            "fileSuffix": f"wp_{i:03d}",
                            "useGlobalPayloadLensIndex": True
                        }
                    )
                    
                    action_group = ActionGroup(
                        group_id=i,
                        start_index=i,
                        end_index=i,
                        trigger=trigger,
                        actions=[take_photo_action]
                    )
                    action_groups.append(action_group)
            
            # Calculate expected photo count
            if trigger_type.lower() in ["distance", "time"]:
                total_distance = sum(
                    self.geometry_calc.haversine_distance(
                        flight_path.waypoints[i].coordinates,
                        flight_path.waypoints[i + 1].coordinates
                    )
                    for i in range(len(flight_path.waypoints) - 1)
                )
                expected_photos = max(1, int(total_distance / photo_spacing))
            else:
                expected_photos = len(flight_path.waypoints)
            
            return {
                "success": True,
                "action_groups": action_groups,
                "shooting_parameters": {
                    "trigger_type": trigger_type,
                    "photo_spacing_m": photo_spacing,
                    "time_interval_s": photo_spacing / flight_speed if trigger_type == "time" else None,
                    "expected_photos": expected_photos,
                    "target_overlap_percent": target_overlap,
                    "ground_resolution_cm_per_pixel": self.calculate_ground_resolution(flight_height, camera_specs)
                },
                "coverage_estimate": {
                    "ground_coverage_per_photo_m2": (ground_height * specs["sensor_width"] * flight_height / specs["focal_length"]),
                    "effective_coverage_with_overlap": (ground_height * specs["sensor_width"] * flight_height / specs["focal_length"]) * (100 - target_overlap) / 100
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error configuring shooting intervals: {str(e)}",
                "action_groups": []
            }
    
    def _calculate_line_length(self, line_positions: List[Coordinates]) -> float:
        """Calculate total length of a flight line in meters."""
        if len(line_positions) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(len(line_positions) - 1):
            distance = self.geometry_calc.haversine_distance(line_positions[i], line_positions[i + 1])
            total_length += distance
        
        return total_length
    
    def _analyze_sidelap_between_lines(
        self,
        flight_lines: List[List[Coordinates]],
        flight_height: float,
        camera_specs: Dict[str, float],
        gimbal_pitch: float
    ) -> Dict[str, Any]:
        """Analyze sidelap between adjacent flight lines."""
        if len(flight_lines) < 2:
            return {
                "average_sidelap": 0.0,
                "min_sidelap": 0.0,
                "max_sidelap": 0.0,
                "sidelap_std": 0.0,
                "line_pairs": []
            }
        
        sidelaps = []
        line_pairs = []
        
        for i in range(len(flight_lines) - 1):
            line1 = flight_lines[i]
            line2 = flight_lines[i + 1]
            
            if line1 and line2:
                sidelap = self.calculate_sidelap_between_lines(
                    line1, line2, flight_height, camera_specs, gimbal_pitch
                )
                sidelaps.append(sidelap)
                
                line_pairs.append({
                    "line1_index": i,
                    "line2_index": i + 1,
                    "sidelap_percentage": sidelap
                })
        
        if sidelaps:
            return {
                "average_sidelap": np.mean(sidelaps),
                "min_sidelap": np.min(sidelaps),
                "max_sidelap": np.max(sidelaps),
                "sidelap_std": np.std(sidelaps),
                "line_pairs": line_pairs
            }
        else:
            return {
                "average_sidelap": 0.0,
                "min_sidelap": 0.0,
                "max_sidelap": 0.0,
                "sidelap_std": 0.0,
                "line_pairs": []
            }
    
    def _calculate_coverage_uniformity(self, footprints: List[Polygon], survey_polygon: Polygon) -> float:
        """Calculate how uniformly the area is covered (0-1, where 1 is perfectly uniform)."""
        if not footprints or survey_polygon.is_empty:
            return 0.0
        
        try:
            # Create a grid over the survey area
            bounds = survey_polygon.bounds
            grid_size = 10  # 10x10 grid
            
            x_step = (bounds[2] - bounds[0]) / grid_size
            y_step = (bounds[3] - bounds[1]) / grid_size
            
            coverage_counts = []
            
            # Count coverage at each grid point
            for i in range(grid_size):
                for j in range(grid_size):
                    x = bounds[0] + (i + 0.5) * x_step
                    y = bounds[1] + (j + 0.5) * y_step
                    point = Point(x, y)
                    
                    if survey_polygon.contains(point):
                        count = sum(1 for footprint in footprints if footprint.contains(point))
                        coverage_counts.append(count)
            
            if not coverage_counts:
                return 0.0
            
            # Calculate uniformity as inverse of coefficient of variation
            mean_coverage = np.mean(coverage_counts)
            if mean_coverage == 0:
                return 0.0
            
            std_coverage = np.std(coverage_counts)
            coefficient_of_variation = std_coverage / mean_coverage
            
            # Convert to uniformity score (0-1)
            uniformity = 1.0 / (1.0 + coefficient_of_variation)
            return min(uniformity, 1.0)
            
        except Exception:
            return 0.0


# Global coverage analyzer instance
coverage_analyzer = CoverageAnalyzer()