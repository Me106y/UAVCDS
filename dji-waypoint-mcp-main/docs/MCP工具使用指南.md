# 大疆航线规划MCP服务 - 工具使用指南

## 概述

大疆航线规划MCP服务提供了一套完整的无人机航线规划工具，支持多种飞行模式和任务类型。本指南详细介绍了每个MCP工具的功能、参数和使用方法。

## 工具列表

| 工具名称 | 功能描述 | 适用场景 |
|---------|---------|---------|
| `plan_waypoint_mission` | 航点飞行任务规划 | 自定义航点飞行、精确定位作业 |
| `plan_mapping_mission` | 建图航拍任务规划 | 地形测绘、正射影像采集 |
| `plan_oblique_mission` | 倾斜摄影任务规划 | 三维建模、倾斜摄影测量 |
| `plan_strip_mission` | 航带飞行任务规划 | 线性巡检、管道巡查 |
| `optimize_route` | 航线路径优化 | 路径优化、飞行效率提升 |
| `coordinate_multi_flights` | 多航线协调 | 复杂任务、多机协同 |
| `query_device_info` | 设备信息查询 | 设备兼容性检查 |
| `validate_mission_compatibility` | 任务兼容性验证 | 安全检查、参数验证 |
| `utility_functions` | 辅助功能工具 | 坐标转换、距离计算 |
| `generate_kmz` | KMZ文件生成 | 航线文件导出 |

---

## 1. 航点飞行任务规划 (plan_waypoint_mission)

### 功能描述
规划自定义航点飞行任务，支持精确的航点定位和动作配置。

### 输入参数

```json
{
  "waypoints": [
    {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 100.0,
      "actions": [
        {
          "type": "take_photo",
          "parameters": {
            "suffix": "wp_001"
          }
        }
      ]
    }
  ],
  "aircraft_type": "M30",
  "flight_params": {
    "speed": 5.0,
    "altitude": 100.0,
    "heading_mode": "follow_wayline",
    "turn_mode": "to_point_stop"
  }
}
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `waypoints` | Array | ✅ | 航点列表，至少2个航点 |
| `aircraft_type` | String | ✅ | 无人机型号 |
| `flight_params` | Object | ✅ | 飞行参数配置 |

### 使用示例

```python
# 基础航点飞行任务
waypoint_mission = {
    "waypoints": [
        {
            "latitude": 39.9042,
            "longitude": 116.4074,
            "altitude": 100.0,
            "actions": [{"type": "take_photo"}]
        },
        {
            "latitude": 39.9142,
            "longitude": 116.4174,
            "altitude": 100.0,
            "actions": [{"type": "take_photo"}]
        }
    ],
    "aircraft_type": "M30",
    "flight_params": {
        "speed": 5.0,
        "altitude": 100.0
    }
}
```

### 返回结果

```json
{
  "success": true,
  "message": "航点任务规划完成",
  "data": {
    "flight_path": {
      "waypoint_count": 2,
      "total_distance": 1234.5,
      "estimated_flight_time": 246.9
    },
    "mission_config": {
      "aircraft_type": "M30",
      "flight_speed": 5.0,
      "flight_altitude": 100.0
    }
  }
}
```

---

## 2. 建图航拍任务规划 (plan_mapping_mission)

### 功能描述
自动生成建图航拍任务，支持矩形和多边形测区的平行航线规划。

### 输入参数

```json
{
  "survey_area": {
    "type": "polygon",
    "coordinates": [
      [116.4074, 39.9042],
      [116.4174, 39.9042],
      [116.4174, 39.9142],
      [116.4074, 39.9142],
      [116.4074, 39.9042]
    ]
  },
  "mapping_params": {
    "altitude": 120.0,
    "overlap_rate": {
      "front": 0.8,
      "side": 0.7
    },
    "direction": 0,
    "margin": 20.0,
    "shoot_type": "distance"
  },
  "aircraft_type": "M30"
}
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `survey_area` | Object | ✅ | 测区范围定义 |
| `mapping_params` | Object | ✅ | 建图参数配置 |
| `aircraft_type` | String | ✅ | 无人机型号 |

### 重叠率配置

- `front`: 航向重叠率 (0.6-0.9)
- `side`: 旁向重叠率 (0.3-0.8)

### 使用示例

```python
# 矩形测区建图任务
mapping_mission = {
    "survey_area": {
        "type": "rectangle",
        "coordinates": [
            [116.4074, 39.9042],  # 左下角
            [116.4174, 39.9142]   # 右上角
        ]
    },
    "mapping_params": {
        "altitude": 120.0,
        "overlap_rate": {
            "front": 0.8,
            "side": 0.7
        },
        "direction": 45,  # 航线方向角度
        "margin": 20.0    # 边界扩展距离
    },
    "aircraft_type": "M30"
}
```

---

## 3. 倾斜摄影任务规划 (plan_oblique_mission)

### 功能描述
生成倾斜摄影任务，自动规划五个方向的航线（正射+四个倾斜方向）。

### 输入参数

```json
{
  "survey_area": {
    "type": "polygon",
    "coordinates": [...]
  },
  "oblique_params": {
    "altitude": 150.0,
    "overlap_rate": {
      "front": 0.8,
      "side": 0.7
    },
    "oblique_angle": -45.0,
    "directions": [0, 90, 180, 270],
    "nadir_flight": true
  },
  "aircraft_type": "M300_RTK"
}
```

### 倾斜角度配置

- `oblique_angle`: 倾斜角度 (-60° 到 -30°)
- `directions`: 倾斜方向 (0°=北, 90°=东, 180°=南, 270°=西)

### 使用示例

```python
# 倾斜摄影任务
oblique_mission = {
    "survey_area": {
        "type": "polygon",
        "coordinates": [
            [116.4074, 39.9042],
            [116.4174, 39.9042],
            [116.4174, 39.9142],
            [116.4074, 39.9142],
            [116.4074, 39.9042]
        ]
    },
    "oblique_params": {
        "altitude": 150.0,
        "overlap_rate": {
            "front": 0.8,
            "side": 0.7
        },
        "oblique_angle": -45.0,
        "nadir_flight": true  # 是否包含正射航线
    },
    "aircraft_type": "M300_RTK"
}
```

---

## 4. 航带飞行任务规划 (plan_strip_mission)

### 功能描述
规划线性航带飞行任务，适用于走廊巡检、管道巡查等场景。

### 输入参数

```json
{
  "strip_type": "pipeline",
  "flight_pattern": "single_line",
  "path_points": [
    {"latitude": 39.9042, "longitude": 116.4074},
    {"latitude": 39.9142, "longitude": 116.4174},
    {"latitude": 39.9242, "longitude": 116.4274}
  ],
  "strip_width": 100.0,
  "flight_height": 80.0,
  "flight_speed": 6.0,
  "overlap_rate": 80.0,
  "aircraft_type": "M30"
}
```

### 航带类型

- `linear`: 线性航带
- `corridor`: 走廊巡检
- `pipeline`: 管道巡查
- `powerline`: 电力线巡检
- `road`: 道路巡查
- `river`: 河流巡查

### 飞行模式

- `single_line`: 单线飞行
- `parallel_lines`: 平行线飞行
- `zigzag`: 之字形飞行
- `back_and_forth`: 往返飞行

---

## 5. 航线路径优化 (optimize_route)

### 功能描述
优化航点顺序以最小化飞行距离、时间或能耗。

### 输入参数

```json
{
  "waypoints": [
    {
      "coordinates": {
        "latitude": 39.9042,
        "longitude": 116.4074,
        "altitude": 100.0
      },
      "priority": 5,
      "visit_time": 10.0
    }
  ],
  "optimization_method": "two_opt",
  "optimization_objective": "minimize_distance",
  "flight_speed": 5.0,
  "start_point_fixed": true,
  "max_iterations": 1000
}
```

### 优化算法

- `nearest_neighbor`: 最近邻算法
- `genetic_algorithm`: 遗传算法
- `simulated_annealing`: 模拟退火算法
- `two_opt`: 2-opt算法
- `christofides`: Christofides算法

### 优化目标

- `minimize_distance`: 最小化飞行距离
- `minimize_time`: 最小化飞行时间
- `minimize_energy`: 最小化能耗
- `balanced`: 平衡优化

---

## 6. 多航线协调 (coordinate_multi_flights)

### 功能描述
协调多条航线的执行顺序和参数配置。

### 输入参数

```json
{
  "flight_plans": [
    {
      "plan_id": "flight_001",
      "priority": 1,
      "waypoints": [...],
      "aircraft_type": "M30"
    },
    {
      "plan_id": "flight_002",
      "priority": 2,
      "waypoints": [...],
      "aircraft_type": "M30"
    }
  ],
  "coordination_strategy": "sequential",
  "safety_buffer": 50.0,
  "time_constraints": {
    "max_total_time": 3600,
    "max_single_flight": 1800
  }
}
```

---

## 7. 设备信息查询 (query_device_info)

### 功能描述
查询支持的无人机型号和负载信息。

### 输入参数

```json
{
  "query_type": "aircraft_specs",
  "aircraft_id": "M30",
  "include_payloads": true,
  "include_limitations": true
}
```

### 查询类型

- `aircraft_specs`: 飞机规格
- `payload_specs`: 负载规格
- `compatibility_matrix`: 兼容性矩阵
- `all_devices`: 所有设备信息

---

## 8. 任务兼容性验证 (validate_mission_compatibility)

### 功能描述
验证任务配置的兼容性和安全性。

### 输入参数

```json
{
  "validation_type": "mission_compatibility",
  "aircraft_id": "M30",
  "mission_config": {
    "flight_height": 100.0,
    "flight_speed": 5.0,
    "overlap_rate": 80.0,
    "gimbal_pitch": -90.0
  },
  "auto_fix": false
}
```

### 验证类型

- `mission_compatibility`: 任务兼容性
- `parameter_validation`: 参数验证
- `flight_path_safety`: 航线安全性
- `recommendations`: 参数建议

---

## 9. 辅助功能工具 (utility_functions)

### 功能描述
提供坐标转换、距离计算、航线分析等辅助功能。

### 坐标转换

```json
{
  "function_type": "convert_coordinates",
  "coordinates": [
    {"latitude": 39.9042, "longitude": 116.4074}
  ],
  "source_system": "WGS84",
  "target_system": "GCJ02"
}
```

### 距离计算

```json
{
  "function_type": "calculate_distance",
  "points": [
    {"latitude": 39.9042, "longitude": 116.4074},
    {"latitude": 39.9142, "longitude": 116.4174}
  ],
  "unit": "meters",
  "calculation_method": "haversine"
}
```

### 航线分析

```json
{
  "function_type": "analyze_flight_plan",
  "waypoints": [...],
  "flight_speed": 5.0,
  "include_detailed_stats": true,
  "analyze_efficiency": true
}
```

---

## 10. KMZ文件生成 (generate_kmz)

### 功能描述
生成符合WPML标准的KMZ航线文件。

### 输入参数

```json
{
  "flight_plan": {
    "waypoints": [...],
    "flight_speed": 5.0,
    "aircraft_type": "M30"
  },
  "output_filename": "mission.kmz",
  "include_template": true,
  "include_resources": false,
  "author": "DJI Waypoint Planner"
}
```

---

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| `VALIDATION_ERROR` | 参数验证失败 | 检查输入参数格式和范围 |
| `AIRCRAFT_COMPATIBILITY_ERROR` | 设备兼容性错误 | 选择支持的设备型号 |
| `COORDINATE_ERROR` | 坐标系统错误 | 检查坐标格式和范围 |
| `PERFORMANCE_LIMITATION` | 性能限制 | 调整任务参数或分段执行 |

### 错误响应格式

```json
{
  "success": false,
  "error": true,
  "message": "参数验证失败: 飞行高度超出限制",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "parameter": "flight_height",
    "value": 600,
    "max_allowed": 500
  },
  "suggestions": [
    "将飞行高度调整到500米以下",
    "选择支持更高飞行高度的机型"
  ]
}
```

## 最佳实践

### 1. 参数配置建议

- **飞行高度**: 根据任务需求和法规要求设置，一般在50-200米
- **飞行速度**: 建议3-8m/s，过快影响图像质量
- **重叠率**: 航向80%，旁向70%，确保良好拼接效果
- **安全余量**: 预留20%电量作为安全余量

### 2. 任务规划流程

1. **需求分析** → 确定任务类型和参数要求
2. **设备选择** → 根据任务选择合适的无人机型号
3. **参数配置** → 设置飞行参数和拍摄参数
4. **兼容性验证** → 验证配置的兼容性和安全性
5. **航线优化** → 优化航线路径提高效率
6. **文件生成** → 生成KMZ文件用于飞行执行

### 3. 性能优化建议

- 使用路径优化工具减少飞行距离
- 合理设置重叠率平衡质量和效率
- 考虑风向和地形影响调整航线方向
- 大面积任务建议分段执行

## 技术支持

如需技术支持或有疑问，请参考：
- 项目文档: `docs/README.md`
- 故障排除: `docs/故障排除指南.md`
- API参考: `docs/API参考文档.md`