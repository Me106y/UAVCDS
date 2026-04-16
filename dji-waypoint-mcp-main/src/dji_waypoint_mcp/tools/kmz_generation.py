"""
KMZ file generation MCP tools.
"""

import os
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError

from .base import BaseTool, ValidationMixin
from ..models import (
    FlightPlan,
    FlightPath,
    Waypoint,
    MissionConfig,
    AircraftModel,
    PayloadModel,
    HeightMode,
    ActionType,
)
from ..config import settings


class KMZGenerationInput(BaseModel):
    """Input schema for KMZ generation."""
    flight_plan: Dict[str, Any] = Field(..., description="Complete flight plan data")
    output_filename: str = Field(default="mission.kmz", description="Output KMZ filename")
    include_template: bool = Field(default=True, description="Include template.kml file")
    include_resources: bool = Field(default=False, description="Include resource files")
    author: Optional[str] = Field(None, description="Mission author")


class WPMLGenerator:
    """Generates WPML-compliant XML files."""
    
    def __init__(self):
        """Initialize the WPML generator."""
        self.namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'wpml': 'http://www.dji.com/wpmz/1.0.2'
        }
    
    def generate_template_kml(self, flight_plan: FlightPlan, flight_path: FlightPath) -> str:
        """Generate template.kml file content."""
        # Create root KML element
        kml = Element('kml')
        kml.set('xmlns', self.namespaces['kml'])
        kml.set('xmlns:wpml', self.namespaces['wpml'])
        
        document = SubElement(kml, 'Document')
        
        # Add creation information
        self._add_creation_info(document, flight_plan)
        
        # Add mission configuration
        self._add_mission_config(document, flight_plan.mission_config)
        
        # Add template folder
        self._add_template_folder(document, flight_path)
        
        return self._prettify_xml(kml)
    
    def generate_waylines_wpml(self, flight_plan: FlightPlan, flight_path: FlightPath) -> str:
        """Generate waylines.wpml file content."""
        # Create root KML element
        kml = Element('kml')
        kml.set('xmlns', self.namespaces['kml'])
        kml.set('xmlns:wpml', self.namespaces['wpml'])
        
        document = SubElement(kml, 'Document')
        
        # Add mission configuration
        self._add_mission_config(document, flight_plan.mission_config)
        
        # Add wayline folder
        self._add_wayline_folder(document, flight_path)
        
        return self._prettify_xml(kml)
    
    def _add_creation_info(self, document: Element, flight_plan: FlightPlan) -> None:
        """Add file creation information."""
        if flight_plan.author:
            author = SubElement(document, 'wpml:author')
            author.text = flight_plan.author
        
        create_time = SubElement(document, 'wpml:createTime')
        create_time.text = str(flight_plan.create_time or int(time.time() * 1000))
        
        update_time = SubElement(document, 'wpml:updateTime')
        update_time.text = str(flight_plan.update_time or int(time.time() * 1000))
    
    def _add_mission_config(self, document: Element, config: MissionConfig) -> None:
        """Add mission configuration."""
        mission_config = SubElement(document, 'wpml:missionConfig')
        
        # Flight behavior
        fly_mode = SubElement(mission_config, 'wpml:flyToWaylineMode')
        fly_mode.text = config.fly_to_wayline_mode.value
        
        finish_action = SubElement(mission_config, 'wpml:finishAction')
        finish_action.text = config.finish_action.value
        
        exit_on_rc_lost = SubElement(mission_config, 'wpml:exitOnRCLost')
        exit_on_rc_lost.text = 'goContinue' if not config.exit_on_rc_lost else 'executeLostAction'
        
        if config.exit_on_rc_lost:
            rc_lost_action = SubElement(mission_config, 'wpml:executeRCLostAction')
            rc_lost_action.text = config.rc_lost_action.value
        
        # Safety settings
        takeoff_height = SubElement(mission_config, 'wpml:takeOffSecurityHeight')
        takeoff_height.text = str(config.takeoff_security_height)
        
        transitional_speed = SubElement(mission_config, 'wpml:globalTransitionalSpeed')
        transitional_speed.text = str(config.global_transitional_speed)
        
        rth_height = SubElement(mission_config, 'wpml:globalRTHHeight')
        rth_height.text = str(config.global_rth_height)
        
        # Reference point
        if config.takeoff_ref_point:
            ref_point = SubElement(mission_config, 'wpml:takeOffRefPoint')
            lat, lon, alt = config.takeoff_ref_point
            ref_point.text = f"{lat},{lon},{alt}"
            
            if config.takeoff_ref_point_agl_height:
                agl_height = SubElement(mission_config, 'wpml:takeOffRefPointAGLHeight')
                agl_height.text = str(config.takeoff_ref_point_agl_height)
        
        # Aircraft info
        drone_info = SubElement(mission_config, 'wpml:droneInfo')
        drone_enum = SubElement(drone_info, 'wpml:droneEnumValue')
        drone_enum.text = str(config.aircraft.enum_value)
        drone_sub_enum = SubElement(drone_info, 'wpml:droneSubEnumValue')
        drone_sub_enum.text = str(config.aircraft.sub_enum_value)
        
        # Payload info
        payload_info = SubElement(mission_config, 'wpml:payloadInfo')
        payload_enum = SubElement(payload_info, 'wpml:payloadEnumValue')
        payload_enum.text = str(config.payload.enum_value)
        payload_pos = SubElement(payload_info, 'wpml:payloadPositionIndex')
        payload_pos.text = str(config.payload_position.value)
    
    def _add_template_folder(self, document: Element, flight_path: FlightPath) -> None:
        """Add template folder for waypoint flight."""
        folder = SubElement(document, 'Folder')
        
        # Template type and ID
        template_type = SubElement(folder, 'wpml:templateType')
        template_type.text = 'waypoint'
        
        template_id = SubElement(folder, 'wpml:templateId')
        template_id.text = '0'
        
        # Coordinate system parameters
        coord_sys_param = SubElement(folder, 'wpml:waylineCoordinateSysParam')
        coord_mode = SubElement(coord_sys_param, 'wpml:coordinateMode')
        coord_mode.text = 'WGS84'
        
        height_mode = SubElement(coord_sys_param, 'wpml:heightMode')
        height_mode.text = flight_path.height_mode.value
        
        positioning_type = SubElement(coord_sys_param, 'wpml:positioningType')
        positioning_type.text = 'GPS'
        
        # Flight parameters
        auto_flight_speed = SubElement(folder, 'wpml:autoFlightSpeed')
        auto_flight_speed.text = str(flight_path.global_speed)
        
        gimbal_pitch_mode = SubElement(folder, 'wpml:gimbalPitchMode')
        gimbal_pitch_mode.text = 'usePointSetting'
        
        # Global waypoint settings
        global_turn_mode = SubElement(folder, 'wpml:globalWaypointTurnMode')
        global_turn_mode.text = flight_path.global_turn_mode.value
        
        if flight_path.global_height:
            global_height = SubElement(folder, 'wpml:globalHeight')
            global_height.text = str(flight_path.global_height)
        
        # Add waypoints
        for waypoint in flight_path.waypoints:
            self._add_template_waypoint(folder, waypoint)
    
    def _add_wayline_folder(self, document: Element, flight_path: FlightPath) -> None:
        """Add wayline folder for execution."""
        folder = SubElement(document, 'Folder')
        
        # Template and wayline IDs
        template_id = SubElement(folder, 'wpml:templateId')
        template_id.text = '0'
        
        wayline_id = SubElement(folder, 'wpml:waylineId')
        wayline_id.text = '0'
        
        # Execution parameters
        auto_flight_speed = SubElement(folder, 'wpml:autoFlightSpeed')
        auto_flight_speed.text = str(flight_path.global_speed)
        
        execute_height_mode = SubElement(folder, 'wpml:executeHeightMode')
        execute_height_mode.text = flight_path.height_mode.value
        
        # Add waypoints for execution
        for waypoint in flight_path.waypoints:
            self._add_execution_waypoint(folder, waypoint, flight_path)
    
    def _add_template_waypoint(self, folder: Element, waypoint: Waypoint) -> None:
        """Add waypoint to template folder."""
        placemark = SubElement(folder, 'Placemark')
        
        # Point coordinates
        point = SubElement(placemark, 'Point')
        coordinates = SubElement(point, 'coordinates')
        coordinates.text = waypoint.coordinates.to_kml_coordinates()
        
        # Waypoint properties
        index = SubElement(placemark, 'wpml:index')
        index.text = str(waypoint.index)
        
        if waypoint.coordinates.altitude:
            ellipsoid_height = SubElement(placemark, 'wpml:ellipsoidHeight')
            ellipsoid_height.text = str(waypoint.coordinates.altitude)
            
            height = SubElement(placemark, 'wpml:height')
            height.text = str(waypoint.height or waypoint.coordinates.altitude)
        
        use_global_height = SubElement(placemark, 'wpml:useGlobalHeight')
        use_global_height.text = '1' if waypoint.use_global_height else '0'
        
        use_global_speed = SubElement(placemark, 'wpml:useGlobalSpeed')
        use_global_speed.text = '1' if waypoint.use_global_speed else '0'
        
        use_global_heading = SubElement(placemark, 'wpml:useGlobalHeadingParam')
        use_global_heading.text = '1' if waypoint.use_global_heading else '0'
        
        use_global_turn = SubElement(placemark, 'wpml:useGlobalTurnParam')
        use_global_turn.text = '1' if waypoint.use_global_turn else '0'
        
        if waypoint.gimbal_pitch_angle is not None:
            gimbal_pitch = SubElement(placemark, 'wpml:gimbalPitchAngle')
            gimbal_pitch.text = str(waypoint.gimbal_pitch_angle)
        
        # Add action groups
        for action_group in waypoint.action_groups:
            self._add_action_group(placemark, action_group)
    
    def _add_execution_waypoint(self, folder: Element, waypoint: Waypoint, flight_path: FlightPath) -> None:
        """Add waypoint to execution folder."""
        placemark = SubElement(folder, 'Placemark')
        
        # Point coordinates
        point = SubElement(placemark, 'Point')
        coordinates = SubElement(point, 'coordinates')
        coordinates.text = waypoint.coordinates.to_kml_coordinates()
        
        # Waypoint properties
        index = SubElement(placemark, 'wpml:index')
        index.text = str(waypoint.index)
        
        execute_height = SubElement(placemark, 'wpml:executeHeight')
        execute_height.text = str(waypoint.coordinates.altitude or flight_path.global_height or 100)
        
        waypoint_speed = SubElement(placemark, 'wpml:waypointSpeed')
        waypoint_speed.text = str(waypoint.speed or flight_path.global_speed)
        
        # Heading parameters
        heading_param = SubElement(placemark, 'wpml:waypointHeadingParam')
        heading_mode = SubElement(heading_param, 'wpml:waypointHeadingMode')
        heading_mode.text = waypoint.heading_param.heading_mode.value if waypoint.heading_param else 'followWayline'
        
        # Turn parameters
        turn_param = SubElement(placemark, 'wpml:waypointTurnParam')
        turn_mode = SubElement(turn_param, 'wpml:waypointTurnMode')
        turn_mode.text = waypoint.turn_param.turn_mode.value if waypoint.turn_param else flight_path.global_turn_mode.value
        
        damping_dist = SubElement(turn_param, 'wpml:waypointTurnDampingDist')
        damping_dist.text = str(waypoint.turn_param.damping_distance if waypoint.turn_param and waypoint.turn_param.damping_distance else 0)
        
        # Add action groups
        for action_group in waypoint.action_groups:
            self._add_action_group(placemark, action_group)
    
    def _add_action_group(self, placemark: Element, action_group) -> None:
        """Add action group to waypoint."""
        action_group_elem = SubElement(placemark, 'wpml:actionGroup')
        
        group_id = SubElement(action_group_elem, 'wpml:actionGroupId')
        group_id.text = str(action_group.group_id)
        
        start_index = SubElement(action_group_elem, 'wpml:actionGroupStartIndex')
        start_index.text = str(action_group.start_index)
        
        end_index = SubElement(action_group_elem, 'wpml:actionGroupEndIndex')
        end_index.text = str(action_group.end_index)
        
        group_mode = SubElement(action_group_elem, 'wpml:actionGroupMode')
        group_mode.text = 'sequence'
        
        # Action trigger
        trigger = SubElement(action_group_elem, 'wpml:actionTrigger')
        trigger_type = SubElement(trigger, 'wpml:actionTriggerType')
        trigger_type.text = action_group.trigger.trigger_type.value
        
        if action_group.trigger.trigger_param:
            trigger_param = SubElement(trigger, 'wpml:actionTriggerParam')
            trigger_param.text = str(action_group.trigger.trigger_param)
        
        # Actions
        for action in action_group.actions:
            self._add_action(action_group_elem, action)
    
    def _add_action(self, action_group_elem: Element, action) -> None:
        """Add individual action."""
        action_elem = SubElement(action_group_elem, 'wpml:action')
        
        action_id = SubElement(action_elem, 'wpml:actionId')
        action_id.text = str(action.action_id)
        
        action_func = SubElement(action_elem, 'wpml:actionActuatorFunc')
        action_func.text = action.action_type.value
        
        # Action parameters
        if action.parameters:
            param_elem = SubElement(action_elem, 'wpml:actionActuatorFuncParam')
            self._add_action_parameters(param_elem, action.action_type, action.parameters)
    
    def _add_action_parameters(self, param_elem: Element, action_type: ActionType, parameters: Dict[str, Any]) -> None:
        """Add action-specific parameters."""
        if action_type == ActionType.TAKE_PHOTO:
            # Payload position
            payload_pos = SubElement(param_elem, 'wpml:payloadPositionIndex')
            payload_pos.text = str(parameters.get('payload_position', 0))
            
            # File suffix
            if 'suffix' in parameters:
                file_suffix = SubElement(param_elem, 'wpml:fileSuffix')
                file_suffix.text = str(parameters['suffix'])
            
            # Use global payload lens index
            use_global = SubElement(param_elem, 'wpml:useGlobalPayloadLensIndex')
            use_global.text = str(parameters.get('use_global_lens', 1))
        
        elif action_type == ActionType.HOVER:
            hover_time = SubElement(param_elem, 'wpml:hoverTime')
            hover_time.text = str(parameters.get('time', 5.0))
        
        elif action_type == ActionType.GIMBAL_ROTATE:
            # Payload position
            payload_pos = SubElement(param_elem, 'wpml:payloadPositionIndex')
            payload_pos.text = str(parameters.get('payload_position', 0))
            
            # Gimbal heading yaw base
            yaw_base = SubElement(param_elem, 'wpml:gimbalHeadingYawBase')
            yaw_base.text = 'north'
            
            # Gimbal rotate mode
            rotate_mode = SubElement(param_elem, 'wpml:gimbalRotateMode')
            rotate_mode.text = 'absoluteAngle'
            
            # Pitch rotation
            pitch_enable = SubElement(param_elem, 'wpml:gimbalPitchRotateEnable')
            pitch_enable.text = '1' if 'pitch_angle' in parameters else '0'
            
            if 'pitch_angle' in parameters:
                pitch_angle = SubElement(param_elem, 'wpml:gimbalPitchRotateAngle')
                pitch_angle.text = str(parameters['pitch_angle'])
            
            # Yaw rotation
            yaw_enable = SubElement(param_elem, 'wpml:gimbalYawRotateEnable')
            yaw_enable.text = '1' if 'yaw_angle' in parameters else '0'
            
            if 'yaw_angle' in parameters:
                yaw_angle = SubElement(param_elem, 'wpml:gimbalYawRotateAngle')
                yaw_angle.text = str(parameters['yaw_angle'])
            
            # Roll rotation
            roll_enable = SubElement(param_elem, 'wpml:gimbalRollRotateEnable')
            roll_enable.text = '0'  # Usually not used
            
            roll_angle = SubElement(param_elem, 'wpml:gimbalRollRotateAngle')
            roll_angle.text = '0'
            
            # Rotation time
            time_enable = SubElement(param_elem, 'wpml:gimbalRotateTimeEnable')
            time_enable.text = '0'
            
            rotate_time = SubElement(param_elem, 'wpml:gimbalRotateTime')
            rotate_time.text = '0'
    
    def _prettify_xml(self, elem: Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')


class KMZGenerationTool(BaseTool, ValidationMixin):
    """Tool for generating WPML KMZ files."""
    
    def __init__(self):
        """Initialize the KMZ generation tool."""
        super().__init__()
        self.wpml_generator = WPMLGenerator()
    
    def get_tool_definition(self) -> Tool:
        """Get the MCP tool definition."""
        return Tool(
            name="generate_kmz",
            description="Generate a WPML-compliant KMZ file from flight plan data",
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_plan": {
                        "type": "object",
                        "description": "Complete flight plan data including mission config and waypoints",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "Output KMZ filename",
                        "default": "mission.kmz"
                    },
                    "include_template": {
                        "type": "boolean",
                        "description": "Include template.kml file",
                        "default": True
                    },
                    "include_resources": {
                        "type": "boolean",
                        "description": "Include resource files directory",
                        "default": False
                    },
                    "author": {
                        "type": "string",
                        "description": "Mission author name"
                    }
                },
                "required": ["flight_plan"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute KMZ file generation."""
        try:
            # Validate input arguments
            kmz_input = KMZGenerationInput(**arguments)
            
            self.logger.info(f"Generating KMZ file: {kmz_input.output_filename}")
            
            # Parse flight plan data
            flight_plan_data = kmz_input.flight_plan
            flight_path_data = flight_plan_data.get('flight_path', {})
            
            # Create flight plan and path objects
            flight_plan, flight_path = self._create_flight_objects(flight_plan_data, kmz_input.author)
            
            # Generate KMZ file
            output_path = self._generate_kmz_file(
                flight_plan, 
                flight_path, 
                kmz_input.output_filename,
                kmz_input.include_template,
                kmz_input.include_resources
            )
            
            # Get file statistics
            file_stats = self._get_file_statistics(output_path)
            
            return self.format_success_response(
                f"KMZ file generated successfully: {kmz_input.output_filename}",
                {
                    "output_path": str(output_path.resolve()),
                    "output_filename": kmz_input.output_filename,
                    "file_size": file_stats["size"],
                    "file_size_bytes": file_stats["size_bytes"],
                    "waypoint_count": len(flight_path.waypoints),
                    "includes_template": kmz_input.include_template,
                    "includes_resources": kmz_input.include_resources,
                    "generation_time": file_stats["generation_time"]
                }
            )
            
        except ValidationError as e:
            self.logger.error(f"Validation error in KMZ generation: {e}")
            return self.format_error_response(f"Invalid input parameters: {e}")
        
        except Exception as e:
            self.logger.error(f"Unexpected error in KMZ generation: {e}", exc_info=True)
            return self.format_error_response(f"KMZ generation failed: {e}")
    
    def _create_flight_objects(self, flight_plan_data: Dict[str, Any], author: Optional[str]):
        """Create flight plan and path objects from input data."""
        # This is a simplified version - in practice, you'd need more robust parsing
        from ..models import (
            FlightPlan, FlightPath, MissionConfig, AircraftSpecs, PayloadSpecs,
            Waypoint, Coordinates
        )
        
        # Create basic aircraft and payload specs
        aircraft = AircraftSpecs(
            model=AircraftModel.M30,
            enum_value=67,
            max_flight_speed=15.0,
            max_flight_height=500.0,
            max_flight_distance=50000.0,
            battery_life=45.0
        )
        
        payload = PayloadSpecs(
            model=PayloadModel.M30_DUAL_CAMERA,
            enum_value=52
        )
        
        # Create mission config
        mission_config = MissionConfig(aircraft=aircraft, payload=payload)
        
        # Create flight plan
        flight_plan = FlightPlan(
            mission_config=mission_config,
            author=author,
            create_time=int(time.time() * 1000),
            update_time=int(time.time() * 1000)
        )
        
        # Create waypoints from flight path data
        waypoints = []
        waypoints_data = flight_plan_data.get('waypoints', [])
        
        for i, wp_data in enumerate(waypoints_data):
            coords = Coordinates(
                latitude=wp_data['latitude'],
                longitude=wp_data['longitude'],
                altitude=wp_data.get('altitude', 100.0)
            )
            
            waypoint = Waypoint(index=i, coordinates=coords)
            waypoints.append(waypoint)
        
        # Create flight path
        flight_path = FlightPath(
            waypoints=waypoints,
            global_speed=flight_plan_data.get('flight_speed', 5.0),
            height_mode=HeightMode.EGM96
        )
        
        return flight_plan, flight_path
    
    def _generate_kmz_file(
        self,
        flight_plan: FlightPlan,
        flight_path: FlightPath,
        filename: str,
        include_template: bool,
        include_resources: bool
    ) -> Path:
        """Generate the actual KMZ file."""
        # Ensure output directory exists
        output_dir = settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / filename
        
        # Create KMZ file (ZIP archive)
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as kmz_file:
            kmz_file.writestr('wpmz/', '')
            kmz_file.writestr('wpmz/res/', '')
            
            # Generate and add waylines.wpml (execution file)
            waylines_content = self.wpml_generator.generate_waylines_wpml(flight_plan, flight_path)
            kmz_file.writestr('wpmz/waylines.wpml', waylines_content)
            
            # Generate and add template.kml if requested
            if include_template:
                template_content = self.wpml_generator.generate_template_kml(flight_plan, flight_path)
                kmz_file.writestr('wpmz/template.kml', template_content)
            
            if include_resources:
                kmz_file.writestr('wpmz/res/.keep', '')
        
        self.logger.info(f"KMZ file generated: {output_path}")
        return output_path
    
    def _get_file_statistics(self, file_path: Path) -> Dict[str, Any]:
        """Get file statistics."""
        if not file_path.exists():
            return {"size": "0 B", "size_bytes": 0, "generation_time": "N/A"}
        
        size_bytes = file_path.stat().st_size
        
        # Format file size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        
        return {
            "size": size_str,
            "size_bytes": size_bytes,
            "generation_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
