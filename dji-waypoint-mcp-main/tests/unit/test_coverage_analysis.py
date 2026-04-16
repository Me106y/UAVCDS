"""
Unit tests for coverage analysis utilities.
"""

import pytest
import math
from unittest.mock import patch, MagicMock
from shapely.geometry import Polygon

from dji_waypoint_mcp.utils.coverage_analysis import CoverageAnalyzer, coverage_analyzer
from dji_waypoint_mcp.models import Coordinates, Waypoint, FlightPath, HeightMode, ActionGroup, Action, ActionTrigger, ActionType, ActionTriggerType


class TestCoverageAnalyzer:
    """Test cases for coverage analysis utilities."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
        
        # Standard camera specs for testing
        self.camera_specs = {
            "sensor_width": 23.5,    # mm
            "sensor_height": 15.6,   # mm
            "focal_length": 24.0,    # mm
            "image_width": 5472,     # pixels
            "image_height": 3648     # pixels
        }
        
        # Test coordinates
        self.test_position = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        self.test_position2 = Coordinates(latitude=40.7138, longitude=-74.0060, altitude=100.0)  # ~1.1km north
        
        # Test survey area (small square)
        self.survey_area = [
            Coordinates(latitude=40.7120, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0050),
            Coordinates(latitude=40.7120, longitude=-74.0050)
        ]
    
    def test_calculate_photo_footprint(self):
        """Test photo footprint calculation."""
        footprint = self.analyzer.calculate_photo_footprint(
            self.test_position, 100.0, self.camera_specs
        )
        
        assert isinstance(footprint, Polygon)
        assert footprint.area > 0
        
        # Footprint should be centered on the position
        centroid = footprint.centroid
        assert abs(centroid.x - self.test_position.longitude) < 0.001
        assert abs(centroid.y - self.test_position.latitude) < 0.001
    
    def test_photo_footprint_with_gimbal_pitch(self):
        """Test photo footprint with different gimbal pitch angles."""
        # Nadir (straight down)
        footprint_nadir = self.analyzer.calculate_photo_footprint(
            self.test_position, 100.0, self.camera_specs, gimbal_pitch=-90.0
        )
        
        # Forward angle
        footprint_forward = self.analyzer.calculate_photo_footprint(
            self.test_position, 100.0, self.camera_specs, gimbal_pitch=-45.0
        )
        
        # Forward angle should create larger footprint
        assert footprint_forward.area > footprint_nadir.area
    
    def test_calculate_overlap_between_photos(self):
        """Test overlap calculation between two photos."""
        # Photos close together should have high overlap
        overlap = self.analyzer.calculate_overlap_between_photos(
            self.test_position, self.test_position2, 100.0, self.camera_specs
        )
        
        assert 0 <= overlap <= 100
        assert isinstance(overlap, float)
        
        # Very distant photos should have no overlap
        distant_position = Coordinates(latitude=41.0, longitude=-74.0, altitude=100.0)
        distant_overlap = self.analyzer.calculate_overlap_between_photos(
            self.test_position, distant_position, 100.0, self.camera_specs
        )
        
        assert distant_overlap == 0.0
    
    def test_calculate_sidelap_between_lines(self):
        """Test sidelap calculation between flight lines."""
        line1 = [
            Coordinates(latitude=40.7120, longitude=-74.0060, altitude=100.0),
            Coordinates(latitude=40.7140, longitude=-74.0060, altitude=100.0)
        ]
        
        line2 = [
            Coordinates(latitude=40.7120, longitude=-74.0050, altitude=100.0),
            Coordinates(latitude=40.7140, longitude=-74.0050, altitude=100.0)
        ]
        
        sidelap = self.analyzer.calculate_sidelap_between_lines(
            line1, line2, 100.0, self.camera_specs
        )
        
        assert 0 <= sidelap <= 100
        assert isinstance(sidelap, float)
    
    def test_analyze_flight_path_coverage(self):
        """Test flight path coverage analysis."""
        # Create test flight path
        waypoints = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7125, longitude=-74.0065, altitude=100.0)),
            Waypoint(index=1, coordinates=Coordinates(latitude=40.7130, longitude=-74.0065, altitude=100.0)),
            Waypoint(index=2, coordinates=Coordinates(latitude=40.7135, longitude=-74.0065, altitude=100.0)),
            Waypoint(index=3, coordinates=Coordinates(latitude=40.7135, longitude=-74.0055, altitude=100.0)),
            Waypoint(index=4, coordinates=Coordinates(latitude=40.7130, longitude=-74.0055, altitude=100.0)),
            Waypoint(index=5, coordinates=Coordinates(latitude=40.7125, longitude=-74.0055, altitude=100.0))
        ]
        
        flight_path = FlightPath(
            waypoints=waypoints,
            global_height=100.0,
            height_mode=HeightMode.EGM96
        )
        
        coverage_analysis = self.analyzer.analyze_flight_path_coverage(
            flight_path, self.survey_area, self.camera_specs
        )
        
        assert "total_coverage_percentage" in coverage_analysis
        assert "overlap_statistics" in coverage_analysis
        assert "coverage_gaps" in coverage_analysis
        assert "redundant_coverage" in coverage_analysis
        
        assert 0 <= coverage_analysis["total_coverage_percentage"] <= 100
        assert coverage_analysis["photo_count"] == len(waypoints)
        assert coverage_analysis["survey_area_m2"] > 0
    
    def test_overlap_statistics_calculation(self):
        """Test overlap statistics calculation."""
        waypoints = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=1, coordinates=Coordinates(latitude=40.7130, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=2, coordinates=Coordinates(latitude=40.7132, longitude=-74.0060, altitude=100.0))
        ]
        
        stats = self.analyzer._calculate_overlap_statistics(
            waypoints, 100.0, self.camera_specs, -90.0
        )
        
        assert "average_forward_overlap" in stats
        assert "min_forward_overlap" in stats
        assert "max_forward_overlap" in stats
        assert "forward_overlap_std" in stats
        
        assert 0 <= stats["average_forward_overlap"] <= 100
        assert 0 <= stats["min_forward_overlap"] <= 100
        assert 0 <= stats["max_forward_overlap"] <= 100
        assert stats["forward_overlap_std"] >= 0
    
    def test_validate_overlap_requirements(self):
        """Test overlap requirements validation."""
        waypoints = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=1, coordinates=Coordinates(latitude=40.7129, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=2, coordinates=Coordinates(latitude=40.7130, longitude=-74.0060, altitude=100.0))
        ]
        
        flight_path = FlightPath(waypoints=waypoints, global_height=100.0)
        
        validation = self.analyzer.validate_overlap_requirements(
            flight_path, self.camera_specs, required_forward_overlap=80.0
        )
        
        assert "meets_requirements" in validation
        assert "issues" in validation
        assert "warnings" in validation
        assert "forward_overlap_check" in validation
        assert "sidelap_check" in validation
        
        assert isinstance(validation["meets_requirements"], bool)
        assert isinstance(validation["issues"], list)
        assert isinstance(validation["warnings"], list)
    
    def test_optimize_photo_positions(self):
        """Test photo position optimization."""
        line_start = Coordinates(latitude=40.7120, longitude=-74.0060, altitude=100.0)
        line_end = Coordinates(latitude=40.7140, longitude=-74.0060, altitude=100.0)
        
        optimized_positions = self.analyzer.optimize_photo_positions(
            line_start, line_end, 100.0, self.camera_specs, target_overlap=80.0
        )
        
        assert len(optimized_positions) > 0
        assert all(isinstance(pos, Coordinates) for pos in optimized_positions)
        assert optimized_positions[0].latitude == line_start.latitude
        assert optimized_positions[-1].latitude == line_end.latitude
        
        # Check that positions are spaced for target overlap
        if len(optimized_positions) > 1:
            for i in range(len(optimized_positions) - 1):
                overlap = self.analyzer.calculate_overlap_between_photos(
                    optimized_positions[i], optimized_positions[i + 1],
                    100.0, self.camera_specs
                )
                # Should be close to target overlap (within reasonable tolerance)
                assert 70 <= overlap <= 90  # Allow some tolerance around 80%
    
    def test_calculate_ground_resolution(self):
        """Test ground resolution calculation."""
        resolution = self.analyzer.calculate_ground_resolution(100.0, self.camera_specs)
        
        assert resolution > 0
        assert isinstance(resolution, float)
        
        # Higher altitude should give lower resolution (larger cm/pixel)
        resolution_high = self.analyzer.calculate_ground_resolution(200.0, self.camera_specs)
        assert resolution_high > resolution
    
    def test_estimate_photo_count(self):
        """Test photo count estimation."""
        estimate = self.analyzer.estimate_photo_count(
            self.survey_area, 100.0, self.camera_specs, 
            forward_overlap=80.0, sidelap=70.0
        )
        
        assert "estimated_photos" in estimate
        assert "coverage_area_m2" in estimate
        assert "photo_footprint_m2" in estimate
        assert "effective_coverage_per_photo_m2" in estimate
        assert "ground_resolution_cm_per_pixel" in estimate
        
        assert estimate["estimated_photos"] > 0
        assert estimate["coverage_area_m2"] > 0
        assert estimate["photo_footprint_m2"] > 0
        assert estimate["effective_coverage_per_photo_m2"] > 0
        assert estimate["ground_resolution_cm_per_pixel"] > 0
    
    def test_empty_flight_path_handling(self):
        """Test handling of empty flight path."""
        empty_flight_path = FlightPath(waypoints=[], global_height=100.0)
        
        coverage_analysis = self.analyzer.analyze_flight_path_coverage(
            empty_flight_path, self.survey_area, self.camera_specs
        )
        
        assert coverage_analysis["total_coverage_percentage"] == 0.0
        assert coverage_analysis["photo_count"] == 0
        
        validation = self.analyzer.validate_overlap_requirements(
            empty_flight_path, self.camera_specs
        )
        
        assert validation["meets_requirements"] is False
        assert len(validation["issues"]) > 0
    
    def test_single_waypoint_handling(self):
        """Test handling of single waypoint."""
        single_waypoint = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0))
        ]
        
        flight_path = FlightPath(waypoints=single_waypoint, global_height=100.0)
        
        coverage_analysis = self.analyzer.analyze_flight_path_coverage(
            flight_path, self.survey_area, self.camera_specs
        )
        
        assert coverage_analysis["photo_count"] == 1
        assert coverage_analysis["total_coverage_percentage"] >= 0
        
        # Single waypoint should have no forward overlap
        stats = self.analyzer._calculate_overlap_statistics(
            single_waypoint, 100.0, self.camera_specs, -90.0
        )
        
        assert stats["average_forward_overlap"] == 0.0
    
    def test_identical_positions_overlap(self):
        """Test overlap calculation for identical positions."""
        overlap = self.analyzer.calculate_overlap_between_photos(
            self.test_position, self.test_position, 100.0, self.camera_specs
        )
        
        # Identical positions should have 100% overlap
        assert overlap == 100.0
    
    def test_different_camera_specs(self):
        """Test calculations with different camera specifications."""
        # Wide angle camera
        wide_camera = {
            "sensor_width": 35.0,
            "sensor_height": 24.0,
            "focal_length": 16.0,
            "image_width": 6000,
            "image_height": 4000
        }
        
        # Telephoto camera
        tele_camera = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 85.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        footprint_wide = self.analyzer.calculate_photo_footprint(
            self.test_position, 100.0, wide_camera
        )
        
        footprint_tele = self.analyzer.calculate_photo_footprint(
            self.test_position, 100.0, tele_camera
        )
        
        # Wide angle should have larger footprint
        assert footprint_wide.area > footprint_tele.area
        
        # Ground resolution should be different
        resolution_wide = self.analyzer.calculate_ground_resolution(100.0, wide_camera)
        resolution_tele = self.analyzer.calculate_ground_resolution(100.0, tele_camera)
        
        assert resolution_wide != resolution_tele
    
    def test_coverage_gaps_detection(self):
        """Test coverage gap detection."""
        # Create sparse waypoints that won't fully cover survey area
        sparse_waypoints = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7125, longitude=-74.0065, altitude=100.0)),
            Waypoint(index=1, coordinates=Coordinates(latitude=40.7135, longitude=-74.0055, altitude=100.0))
        ]
        
        flight_path = FlightPath(waypoints=sparse_waypoints, global_height=100.0)
        
        coverage_analysis = self.analyzer.analyze_flight_path_coverage(
            flight_path, self.survey_area, self.camera_specs
        )
        
        # Should detect coverage gaps
        gaps = coverage_analysis["coverage_gaps"]
        if coverage_analysis["total_coverage_percentage"] < 100:
            assert len(gaps) > 0
            for gap in gaps:
                assert "area_m2" in gap
                assert "percentage_of_survey" in gap
                assert gap["area_m2"] > 0
                assert gap["percentage_of_survey"] > 0
    
    def test_redundant_coverage_calculation(self):
        """Test redundant coverage calculation."""
        # Create overlapping footprints
        from shapely.geometry import Polygon
        
        footprint1 = Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1)])
        footprint2 = Polygon([(0, -1), (2, -1), (2, 1), (0, 1)])  # 50% overlap
        
        redundant = self.analyzer._calculate_redundant_coverage([footprint1, footprint2])
        
        assert redundant > 0
        assert isinstance(redundant, float)
        
        # No overlap case
        footprint3 = Polygon([(3, -1), (5, -1), (5, 1), (3, 1)])  # No overlap
        redundant_none = self.analyzer._calculate_redundant_coverage([footprint1, footprint3])
        
        assert redundant_none == 0.0
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty survey area
        empty_area = []
        estimate = self.analyzer.estimate_photo_count(
            empty_area, 100.0, self.camera_specs
        )
        assert estimate["estimated_photos"] == 0
        
        # Zero flight height
        with pytest.raises(Exception):
            self.analyzer.calculate_photo_footprint(
                self.test_position, 0.0, self.camera_specs
            )
        
        # Invalid camera specs
        invalid_specs = {"focal_length": 0}
        with pytest.raises(Exception):
            self.analyzer.calculate_photo_footprint(
                self.test_position, 100.0, invalid_specs
            )


class TestGlobalCoverageAnalyzer:
    """Test the global coverage analyzer instance."""
    
    def test_global_instance_exists(self):
        """Test that global coverage analyzer instance exists."""
        assert coverage_analyzer is not None
        assert isinstance(coverage_analyzer, CoverageAnalyzer)
    
    def test_global_instance_functionality(self):
        """Test that global instance works correctly."""
        camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        position = Coordinates(latitude=40.7128, longitude=-74.0060, altitude=100.0)
        
        footprint = coverage_analyzer.calculate_photo_footprint(
            position, 100.0, camera_specs
        )
        
        assert isinstance(footprint, Polygon)
        assert footprint.area > 0


class TestCoverageAnalysisIntegration:
    """Integration tests for coverage analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
        self.camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
    
    def test_complete_coverage_workflow(self):
        """Test complete coverage analysis workflow."""
        # Define survey area
        survey_area = [
            Coordinates(latitude=40.7120, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0050),
            Coordinates(latitude=40.7120, longitude=-74.0050)
        ]
        
        # Create flight path with good coverage
        waypoints = []
        for i, lat in enumerate([40.7122, 40.7126, 40.7130, 40.7134, 40.7138]):
            for j, lon in enumerate([-74.0068, -74.0062, -74.0056, -74.0052]):
                waypoints.append(Waypoint(
                    index=len(waypoints),
                    coordinates=Coordinates(latitude=lat, longitude=lon, altitude=100.0)
                ))
        
        flight_path = FlightPath(waypoints=waypoints, global_height=100.0)
        
        # Analyze coverage
        coverage_analysis = self.analyzer.analyze_flight_path_coverage(
            flight_path, survey_area, self.camera_specs
        )
        
        # Validate requirements
        validation = self.analyzer.validate_overlap_requirements(
            flight_path, self.camera_specs, required_forward_overlap=75.0
        )
        
        # Estimate photo count
        estimate = self.analyzer.estimate_photo_count(
            survey_area, 100.0, self.camera_specs
        )
        
        # Verify results
        assert coverage_analysis["total_coverage_percentage"] > 50  # Should have decent coverage
        assert coverage_analysis["photo_count"] == len(waypoints)
        assert len(coverage_analysis["overlap_statistics"]) > 0
        
        assert "meets_requirements" in validation
        assert estimate["estimated_photos"] > 0
        
        # Ground resolution should be reasonable for 100m altitude
        assert 2 < estimate["ground_resolution_cm_per_pixel"] < 10
    
    def test_optimization_workflow(self):
        """Test photo position optimization workflow."""
        # Define flight line
        line_start = Coordinates(latitude=40.7120, longitude=-74.0060)
        line_end = Coordinates(latitude=40.7140, longitude=-74.0060)
        
        # Optimize positions for different overlap targets
        positions_80 = self.analyzer.optimize_photo_positions(
            line_start, line_end, 100.0, self.camera_specs, target_overlap=80.0
        )
        
        positions_60 = self.analyzer.optimize_photo_positions(
            line_start, line_end, 100.0, self.camera_specs, target_overlap=60.0
        )
        
        # Lower overlap should require fewer photos
        assert len(positions_60) <= len(positions_80)
        
        # Verify overlap targets are met
        if len(positions_80) > 1:
            overlap = self.analyzer.calculate_overlap_between_photos(
                positions_80[0], positions_80[1], 100.0, self.camera_specs
            )
            assert 70 <= overlap <= 90  # Should be close to 80% target
    
    def test_different_flight_heights(self):
        """Test coverage analysis at different flight heights."""
        position = Coordinates(latitude=40.7128, longitude=-74.0060)
        
        # Test different heights
        heights = [50.0, 100.0, 200.0]
        footprints = []
        resolutions = []
        
        for height in heights:
            footprint = self.analyzer.calculate_photo_footprint(
                position, height, self.camera_specs
            )
            resolution = self.analyzer.calculate_ground_resolution(height, self.camera_specs)
            
            footprints.append(footprint.area)
            resolutions.append(resolution)
        
        # Higher altitude should give larger footprint and lower resolution
        assert footprints[0] < footprints[1] < footprints[2]  # Increasing footprint area
        assert resolutions[0] < resolutions[1] < resolutions[2]  # Decreasing resolution (higher cm/pixel)


class TestOverlapParameterValidation:
    """Test cases for overlap parameter validation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
        self.camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
    
    def test_validate_overlap_parameters_valid(self):
        """Test validation with valid overlap parameters."""
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=80.0,
            sidelap=70.0,
            flight_height=100.0,
            camera_specs=self.camera_specs,
            flight_speed=5.0
        )
        
        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0
        assert "calculated_parameters" in validation
        
        params = validation["calculated_parameters"]
        assert "ground_width_m" in params
        assert "ground_height_m" in params
        assert "forward_spacing_m" in params
        assert "side_spacing_m" in params
        assert "time_interval_s" in params
        assert "distance_interval_m" in params
        
        assert params["ground_width_m"] > 0
        assert params["ground_height_m"] > 0
        assert params["forward_spacing_m"] > 0
        assert params["side_spacing_m"] > 0
        assert params["time_interval_s"] > 0
        assert params["distance_interval_m"] > 0
    
    def test_validate_overlap_parameters_invalid_ranges(self):
        """Test validation with invalid overlap ranges."""
        # Test negative overlap
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=-10.0,
            sidelap=70.0,
            flight_height=100.0,
            camera_specs=self.camera_specs
        )
        
        assert validation["is_valid"] is False
        assert len(validation["issues"]) > 0
        assert "out of valid range" in validation["issues"][0]
        
        # Test overlap > 95%
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=98.0,
            sidelap=70.0,
            flight_height=100.0,
            camera_specs=self.camera_specs
        )
        
        assert validation["is_valid"] is False
        assert len(validation["issues"]) > 0
    
    def test_validate_overlap_parameters_warnings(self):
        """Test validation warnings for suboptimal parameters."""
        # Test low overlap warning
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=50.0,
            sidelap=20.0,
            flight_height=100.0,
            camera_specs=self.camera_specs
        )
        
        assert validation["is_valid"] is True
        assert len(validation["warnings"]) >= 2  # Should warn about both low overlaps
        assert any("below 60%" in warning for warning in validation["warnings"])
        assert any("below 30%" in warning for warning in validation["warnings"])
        
        # Test high overlap warning
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=92.0,
            sidelap=85.0,
            flight_height=100.0,
            camera_specs=self.camera_specs
        )
        
        assert validation["is_valid"] is True
        assert len(validation["warnings"]) >= 2  # Should warn about both high overlaps
    
    def test_validate_overlap_parameters_recommendations(self):
        """Test parameter recommendations."""
        # Test very short time interval
        validation = self.analyzer.validate_overlap_parameters(
            forward_overlap=95.0,  # Very high overlap
            sidelap=70.0,
            flight_height=50.0,   # Low height
            camera_specs=self.camera_specs,
            flight_speed=10.0     # High speed
        )
        
        assert len(validation["recommendations"]) > 0
        assert any("Time interval" in rec for rec in validation["recommendations"])


class TestFlightLineCoverageAnalysis:
    """Test cases for flight line coverage analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
        self.camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        # Test survey area
        self.survey_area = [
            Coordinates(latitude=40.7120, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0070),
            Coordinates(latitude=40.7140, longitude=-74.0050),
            Coordinates(latitude=40.7120, longitude=-74.0050)
        ]
        
        # Test flight lines
        self.flight_lines = [
            # Line 1
            [
                Coordinates(latitude=40.7122, longitude=-74.0068),
                Coordinates(latitude=40.7126, longitude=-74.0068),
                Coordinates(latitude=40.7130, longitude=-74.0068),
                Coordinates(latitude=40.7134, longitude=-74.0068),
                Coordinates(latitude=40.7138, longitude=-74.0068)
            ],
            # Line 2
            [
                Coordinates(latitude=40.7138, longitude=-74.0062),
                Coordinates(latitude=40.7134, longitude=-74.0062),
                Coordinates(latitude=40.7130, longitude=-74.0062),
                Coordinates(latitude=40.7126, longitude=-74.0062),
                Coordinates(latitude=40.7122, longitude=-74.0062)
            ],
            # Line 3
            [
                Coordinates(latitude=40.7122, longitude=-74.0056),
                Coordinates(latitude=40.7126, longitude=-74.0056),
                Coordinates(latitude=40.7130, longitude=-74.0056),
                Coordinates(latitude=40.7134, longitude=-74.0056),
                Coordinates(latitude=40.7138, longitude=-74.0056)
            ]
        ]
    
    def test_analyze_flight_line_coverage_basic(self):
        """Test basic flight line coverage analysis."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            self.flight_lines,
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        assert "total_coverage_percentage" in analysis
        assert "line_coverage_details" in analysis
        assert "sidelap_analysis" in analysis
        assert "coverage_uniformity" in analysis
        assert "efficiency_metrics" in analysis
        
        assert 0 <= analysis["total_coverage_percentage"] <= 100
        assert len(analysis["line_coverage_details"]) == len(self.flight_lines)
        assert analysis["total_photos"] > 0
        assert analysis["survey_area_m2"] > 0
    
    def test_analyze_flight_line_coverage_details(self):
        """Test detailed flight line coverage analysis."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            self.flight_lines,
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        # Check line coverage details
        for i, line_detail in enumerate(analysis["line_coverage_details"]):
            assert line_detail["line_index"] == i
            assert line_detail["photo_count"] == len(self.flight_lines[i])
            assert 0 <= line_detail["coverage_percentage"] <= 100
            assert line_detail["line_length_m"] > 0
            
            # Check forward overlap stats
            overlap_stats = line_detail["forward_overlap_stats"]
            assert "average" in overlap_stats
            assert "min" in overlap_stats
            assert "max" in overlap_stats
            assert "std" in overlap_stats
            
            if len(self.flight_lines[i]) > 1:
                assert overlap_stats["average"] >= 0
                assert overlap_stats["min"] >= 0
                assert overlap_stats["max"] >= 0
                assert overlap_stats["std"] >= 0
    
    def test_analyze_flight_line_coverage_sidelap(self):
        """Test sidelap analysis between flight lines."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            self.flight_lines,
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        sidelap_analysis = analysis["sidelap_analysis"]
        assert "average_sidelap" in sidelap_analysis
        assert "min_sidelap" in sidelap_analysis
        assert "max_sidelap" in sidelap_analysis
        assert "sidelap_std" in sidelap_analysis
        assert "line_pairs" in sidelap_analysis
        
        # Should have n-1 line pairs for n lines
        expected_pairs = len(self.flight_lines) - 1
        assert len(sidelap_analysis["line_pairs"]) == expected_pairs
        
        for pair in sidelap_analysis["line_pairs"]:
            assert "line1_index" in pair
            assert "line2_index" in pair
            assert "sidelap_percentage" in pair
            assert 0 <= pair["sidelap_percentage"] <= 100
    
    def test_analyze_flight_line_coverage_efficiency(self):
        """Test efficiency metrics calculation."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            self.flight_lines,
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        efficiency = analysis["efficiency_metrics"]
        assert "photos_per_hectare" in efficiency
        assert "coverage_per_photo" in efficiency
        assert "flight_distance_per_hectare" in efficiency
        assert "total_flight_distance_m" in efficiency
        
        assert efficiency["photos_per_hectare"] > 0
        assert efficiency["coverage_per_photo"] > 0
        assert efficiency["flight_distance_per_hectare"] > 0
        assert efficiency["total_flight_distance_m"] > 0
    
    def test_analyze_flight_line_coverage_empty(self):
        """Test flight line coverage analysis with empty input."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            [],
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        assert analysis["total_coverage_percentage"] == 0.0
        assert len(analysis["line_coverage_details"]) == 0
        assert analysis["total_photos"] == 0
    
    def test_coverage_uniformity_calculation(self):
        """Test coverage uniformity calculation."""
        analysis = self.analyzer.analyze_flight_line_coverage(
            self.flight_lines,
            self.survey_area,
            100.0,
            self.camera_specs
        )
        
        uniformity = analysis["coverage_uniformity"]
        assert 0 <= uniformity <= 1
        assert isinstance(uniformity, float)


class TestShootingIntervalConfiguration:
    """Test cases for shooting interval and trigger configuration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
        self.camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        # Create test flight path
        waypoints = [
            Waypoint(index=0, coordinates=Coordinates(latitude=40.7120, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=1, coordinates=Coordinates(latitude=40.7125, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=2, coordinates=Coordinates(latitude=40.7130, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=3, coordinates=Coordinates(latitude=40.7135, longitude=-74.0060, altitude=100.0)),
            Waypoint(index=4, coordinates=Coordinates(latitude=40.7140, longitude=-74.0060, altitude=100.0))
        ]
        
        self.flight_path = FlightPath(
            waypoints=waypoints,
            global_height=100.0,
            global_speed=5.0
        )
    
    def test_configure_shooting_intervals_distance(self):
        """Test distance-based shooting interval configuration."""
        config = self.analyzer.configure_shooting_intervals(
            self.flight_path,
            self.camera_specs,
            target_overlap=80.0,
            trigger_type="distance"
        )
        
        assert config["success"] is True
        assert len(config["action_groups"]) == 1
        assert "shooting_parameters" in config
        assert "coverage_estimate" in config
        
        # Check action group
        action_group = config["action_groups"][0]
        assert action_group.group_id == 0
        assert action_group.start_index == 0
        assert action_group.end_index == len(self.flight_path.waypoints) - 1
        assert action_group.trigger.trigger_type == ActionTriggerType.MULTIPLE_DISTANCE
        assert action_group.trigger.trigger_param > 0
        assert len(action_group.actions) == 1
        assert action_group.actions[0].action_type == ActionType.TAKE_PHOTO
        
        # Check shooting parameters
        params = config["shooting_parameters"]
        assert params["trigger_type"] == "distance"
        assert params["photo_spacing_m"] > 0
        assert params["expected_photos"] > 0
        assert params["target_overlap_percent"] == 80.0
        assert params["time_interval_s"] is None
    
    def test_configure_shooting_intervals_time(self):
        """Test time-based shooting interval configuration."""
        config = self.analyzer.configure_shooting_intervals(
            self.flight_path,
            self.camera_specs,
            target_overlap=75.0,
            trigger_type="time"
        )
        
        assert config["success"] is True
        assert len(config["action_groups"]) == 1
        
        # Check action group
        action_group = config["action_groups"][0]
        assert action_group.trigger.trigger_type == ActionTriggerType.MULTIPLE_TIMING
        assert action_group.trigger.trigger_param > 0
        
        # Check shooting parameters
        params = config["shooting_parameters"]
        assert params["trigger_type"] == "time"
        assert params["time_interval_s"] > 0
        assert params["target_overlap_percent"] == 75.0
    
    def test_configure_shooting_intervals_waypoint(self):
        """Test waypoint-based shooting interval configuration."""
        config = self.analyzer.configure_shooting_intervals(
            self.flight_path,
            self.camera_specs,
            target_overlap=80.0,
            trigger_type="waypoint"
        )
        
        assert config["success"] is True
        assert len(config["action_groups"]) == len(self.flight_path.waypoints)
        
        # Check each action group
        for i, action_group in enumerate(config["action_groups"]):
            assert action_group.group_id == i
            assert action_group.start_index == i
            assert action_group.end_index == i
            assert action_group.trigger.trigger_type == ActionTriggerType.REACH_POINT
            assert action_group.trigger.trigger_param is None
            assert len(action_group.actions) == 1
            assert action_group.actions[0].action_type == ActionType.TAKE_PHOTO
            assert f"wp_{i:03d}" in action_group.actions[0].parameters["fileSuffix"]
        
        # Expected photos should equal waypoint count
        params = config["shooting_parameters"]
        assert params["expected_photos"] == len(self.flight_path.waypoints)
    
    def test_configure_shooting_intervals_empty_path(self):
        """Test shooting interval configuration with empty flight path."""
        empty_path = FlightPath(waypoints=[], global_height=100.0)
        
        config = self.analyzer.configure_shooting_intervals(
            empty_path,
            self.camera_specs,
            target_overlap=80.0,
            trigger_type="distance"
        )
        
        assert config["success"] is False
        assert "No waypoints" in config["error"]
        assert len(config["action_groups"]) == 0
    
    def test_configure_shooting_intervals_coverage_estimate(self):
        """Test coverage estimation in shooting interval configuration."""
        config = self.analyzer.configure_shooting_intervals(
            self.flight_path,
            self.camera_specs,
            target_overlap=80.0,
            trigger_type="distance"
        )
        
        assert config["success"] is True
        
        coverage_estimate = config["coverage_estimate"]
        assert "ground_coverage_per_photo_m2" in coverage_estimate
        assert "effective_coverage_with_overlap" in coverage_estimate
        
        assert coverage_estimate["ground_coverage_per_photo_m2"] > 0
        assert coverage_estimate["effective_coverage_with_overlap"] > 0
        
        # Effective coverage should be less than total coverage due to overlap
        assert coverage_estimate["effective_coverage_with_overlap"] < coverage_estimate["ground_coverage_per_photo_m2"]
    
    def test_configure_shooting_intervals_different_overlaps(self):
        """Test shooting interval configuration with different overlap targets."""
        config_80 = self.analyzer.configure_shooting_intervals(
            self.flight_path, self.camera_specs, target_overlap=80.0, trigger_type="distance"
        )
        
        config_60 = self.analyzer.configure_shooting_intervals(
            self.flight_path, self.camera_specs, target_overlap=60.0, trigger_type="distance"
        )
        
        assert config_80["success"] is True
        assert config_60["success"] is True
        
        # Higher overlap should result in smaller photo spacing
        spacing_80 = config_80["shooting_parameters"]["photo_spacing_m"]
        spacing_60 = config_60["shooting_parameters"]["photo_spacing_m"]
        
        assert spacing_80 < spacing_60
        
        # Higher overlap should result in more photos
        photos_80 = config_80["shooting_parameters"]["expected_photos"]
        photos_60 = config_60["shooting_parameters"]["expected_photos"]
        
        assert photos_80 >= photos_60


class TestCoverageAnalysisHelperMethods:
    """Test cases for helper methods in coverage analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = CoverageAnalyzer()
    
    def test_calculate_line_length(self):
        """Test flight line length calculation."""
        line_positions = [
            Coordinates(latitude=40.7120, longitude=-74.0060),
            Coordinates(latitude=40.7125, longitude=-74.0060),
            Coordinates(latitude=40.7130, longitude=-74.0060)
        ]
        
        length = self.analyzer._calculate_line_length(line_positions)
        
        assert length > 0
        assert isinstance(length, float)
        
        # Empty line should have zero length
        empty_length = self.analyzer._calculate_line_length([])
        assert empty_length == 0.0
        
        # Single point should have zero length
        single_length = self.analyzer._calculate_line_length([line_positions[0]])
        assert single_length == 0.0
    
    def test_analyze_sidelap_between_lines(self):
        """Test sidelap analysis between flight lines."""
        flight_lines = [
            [
                Coordinates(latitude=40.7120, longitude=-74.0060),
                Coordinates(latitude=40.7130, longitude=-74.0060)
            ],
            [
                Coordinates(latitude=40.7120, longitude=-74.0050),
                Coordinates(latitude=40.7130, longitude=-74.0050)
            ]
        ]
        
        camera_specs = {
            "sensor_width": 23.5,
            "sensor_height": 15.6,
            "focal_length": 24.0,
            "image_width": 5472,
            "image_height": 3648
        }
        
        sidelap_analysis = self.analyzer._analyze_sidelap_between_lines(
            flight_lines, 100.0, camera_specs, -90.0
        )
        
        assert "average_sidelap" in sidelap_analysis
        assert "min_sidelap" in sidelap_analysis
        assert "max_sidelap" in sidelap_analysis
        assert "sidelap_std" in sidelap_analysis
        assert "line_pairs" in sidelap_analysis
        
        assert len(sidelap_analysis["line_pairs"]) == 1
        assert 0 <= sidelap_analysis["average_sidelap"] <= 100
    
    def test_calculate_coverage_uniformity(self):
        """Test coverage uniformity calculation."""
        from shapely.geometry import Polygon
        
        # Create test polygons
        survey_polygon = Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1)])
        
        # Uniform coverage
        uniform_footprints = [
            Polygon([(-0.8, -0.8), (-0.2, -0.8), (-0.2, -0.2), (-0.8, -0.2)]),
            Polygon([(-0.2, -0.8), (0.4, -0.8), (0.4, -0.2), (-0.2, -0.2)]),
            Polygon([(-0.8, -0.2), (-0.2, -0.2), (-0.2, 0.4), (-0.8, 0.4)]),
            Polygon([(-0.2, -0.2), (0.4, -0.2), (0.4, 0.4), (-0.2, 0.4)])
        ]
        
        uniformity = self.analyzer._calculate_coverage_uniformity(uniform_footprints, survey_polygon)
        
        assert 0 <= uniformity <= 1
        assert isinstance(uniformity, float)
        
        # Empty footprints should return 0
        empty_uniformity = self.analyzer._calculate_coverage_uniformity([], survey_polygon)
        assert empty_uniformity == 0.0