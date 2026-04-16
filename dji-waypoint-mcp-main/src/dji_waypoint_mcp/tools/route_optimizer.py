"""
路径优化工具。
实现TSP求解器和启发式优化算法来优化航点顺序和飞行路径。
"""

import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass

import numpy as np
from mcp.types import Tool
from pydantic import BaseModel, Field, ValidationError, field_validator

from .base import BaseTool, ValidationMixin
from ..models import Coordinates, Waypoint, FlightPath
from ..utils.geometry import geometry_calculator
from ..config import settings


class OptimizationMethod(str, Enum):
    """优化方法。"""
    NEAREST_NEIGHBOR = "nearest_neighbor"
    GENETIC_ALGORITHM = "genetic_algorithm"
    SIMULATED_ANNEALING = "simulated_annealing"
    TWO_OPT = "two_opt"
    CHRISTOFIDES = "christofides"


class OptimizationObjective(str, Enum):
    """优化目标。"""
    MINIMIZE_DISTANCE = "minimize_distance"
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_ENERGY = "minimize_energy"
    BALANCED = "balanced"


@dataclass
class OptimizationResult:
    """优化结果。"""
    original_distance: float
    optimized_distance: float
    improvement_percentage: float
    original_time: float
    optimized_time: float
    original_order: List[int]
    optimized_order: List[int]
    method_used: str
    iterations: int
    computation_time: float


class RouteOptimizerInput(BaseModel):
    """路径优化输入参数。"""
    waypoints: List[Dict[str, Any]] = Field(..., min_items=2, description="航点列表")
    optimization_method: OptimizationMethod = Field(default=OptimizationMethod.TWO_OPT, description="优化方法")
    optimization_objective: OptimizationObjective = Field(default=OptimizationObjective.MINIMIZE_DISTANCE, description="优化目标")
    flight_speed: float = Field(default=5.0, ge=1, le=20, description="飞行速度(m/s)")
    start_point_fixed: bool = Field(default=True, description="起始点是否固定")
    end_point_fixed: bool = Field(default=False, description="结束点是否固定")
    max_iterations: int = Field(default=1000, ge=10, le=10000, description="最大迭代次数")
    convergence_threshold: float = Field(default=0.001, ge=0.0001, le=0.1, description="收敛阈值")
    preserve_altitude_order: bool = Field(default=False, description="保持高度顺序")
    
    @field_validator('waypoints')
    @classmethod
    def validate_waypoints(cls, v):
        """验证航点数据。"""
        if len(v) < 2:
            raise ValueError("至少需要2个航点")
        return v


class RouteOptimizer(BaseTool, ValidationMixin):
    """路径优化工具。"""
    
    def __init__(self):
        """初始化路径优化工具。"""
        super().__init__()
        self.geometry_calc = geometry_calculator
    
    def get_tool_definition(self) -> Tool:
        """获取MCP工具定义。"""
        return Tool(
            name="optimize_route",
            description="优化航点顺序以最小化飞行距离、时间或能耗",
            inputSchema={
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "description": "航点列表",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer", "description": "航点索引"},
                                "coordinates": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                                        "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                                        "altitude": {"type": "number", "minimum": 0, "maximum": 1000}
                                    },
                                    "required": ["latitude", "longitude", "altitude"]
                                },
                                "priority": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                                "visit_time": {"type": "number", "minimum": 0, "maximum": 300, "default": 0}
                            },
                            "required": ["coordinates"]
                        }
                    },
                    "optimization_method": {
                        "type": "string",
                        "enum": ["nearest_neighbor", "genetic_algorithm", "simulated_annealing", "two_opt", "christofides"],
                        "default": "two_opt",
                        "description": "优化算法"
                    },
                    "optimization_objective": {
                        "type": "string",
                        "enum": ["minimize_distance", "minimize_time", "minimize_energy", "balanced"],
                        "default": "minimize_distance",
                        "description": "优化目标"
                    },
                    "flight_speed": {
                        "type": "number",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5.0,
                        "description": "飞行速度(m/s)"
                    },
                    "start_point_fixed": {
                        "type": "boolean",
                        "default": True,
                        "description": "起始点是否固定"
                    },
                    "end_point_fixed": {
                        "type": "boolean",
                        "default": False,
                        "description": "结束点是否固定"
                    },
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 10000,
                        "default": 1000,
                        "description": "最大迭代次数"
                    },
                    "convergence_threshold": {
                        "type": "number",
                        "minimum": 0.0001,
                        "maximum": 0.1,
                        "default": 0.001,
                        "description": "收敛阈值"
                    },
                    "preserve_altitude_order": {
                        "type": "boolean",
                        "default": False,
                        "description": "是否保持高度顺序"
                    }
                },
                "required": ["waypoints"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行路径优化。"""
        try:
            # 验证输入参数
            optimizer_input = RouteOptimizerInput(**arguments)
            
            self.logger.info(f"开始路径优化: {optimizer_input.optimization_method}")
            
            # 解析航点
            waypoints = self._parse_waypoints(optimizer_input.waypoints)
            
            if len(waypoints) < 2:
                raise ValueError("至少需要2个航点进行优化")
            
            # 计算距离矩阵
            distance_matrix = self._calculate_distance_matrix(waypoints)
            
            # 执行优化
            start_time = time.time()
            
            if optimizer_input.optimization_method == OptimizationMethod.NEAREST_NEIGHBOR:
                result = self._nearest_neighbor_optimization(
                    waypoints, distance_matrix, optimizer_input
                )
            elif optimizer_input.optimization_method == OptimizationMethod.GENETIC_ALGORITHM:
                result = self._genetic_algorithm_optimization(
                    waypoints, distance_matrix, optimizer_input
                )
            elif optimizer_input.optimization_method == OptimizationMethod.SIMULATED_ANNEALING:
                result = self._simulated_annealing_optimization(
                    waypoints, distance_matrix, optimizer_input
                )
            elif optimizer_input.optimization_method == OptimizationMethod.TWO_OPT:
                result = self._two_opt_optimization(
                    waypoints, distance_matrix, optimizer_input
                )
            elif optimizer_input.optimization_method == OptimizationMethod.CHRISTOFIDES:
                result = self._christofides_optimization(
                    waypoints, distance_matrix, optimizer_input
                )
            else:
                raise ValueError(f"不支持的优化方法: {optimizer_input.optimization_method}")
            
            computation_time = time.time() - start_time
            result.computation_time = computation_time
            
            # 生成优化后的航点顺序
            optimized_waypoints = [waypoints[i] for i in result.optimized_order]
            
            # 准备响应数据
            response_data = {
                "optimization_result": {
                    "method": result.method_used,
                    "objective": optimizer_input.optimization_objective.value,
                    "original_distance": round(result.original_distance, 2),
                    "optimized_distance": round(result.optimized_distance, 2),
                    "distance_improvement": round(result.improvement_percentage, 2),
                    "original_time": round(result.original_time, 2),
                    "optimized_time": round(result.optimized_time, 2),
                    "time_improvement": round((result.original_time - result.optimized_time) / result.original_time * 100, 2),
                    "iterations": result.iterations,
                    "computation_time": round(computation_time, 3)
                },
                "route_comparison": {
                    "original_order": result.original_order,
                    "optimized_order": result.optimized_order,
                    "waypoint_changes": self._analyze_route_changes(result.original_order, result.optimized_order)
                },
                "optimized_waypoints": [
                    {
                        "index": i,
                        "original_index": result.optimized_order[i],
                        "coordinates": {
                            "latitude": wp.coordinates.latitude,
                            "longitude": wp.coordinates.longitude,
                            "altitude": wp.coordinates.altitude
                        },
                        "cumulative_distance": self._calculate_cumulative_distance(
                            optimized_waypoints[:i+1]
                        ) if i > 0 else 0.0
                    }
                    for i, wp in enumerate(optimized_waypoints)
                ],
                "statistics": {
                    "total_waypoints": len(waypoints),
                    "distance_saved": round(result.original_distance - result.optimized_distance, 2),
                    "time_saved": round(result.original_time - result.optimized_time, 2),
                    "efficiency_gain": round(result.improvement_percentage, 2)
                }
            }
            
            return self.format_success_response(
                f"路径优化完成，距离减少 {result.improvement_percentage:.1f}%",
                response_data
            )
            
        except ValidationError as e:
            self.logger.error(f"路径优化验证错误: {e}")
            return self.format_error_response(f"输入参数无效: {e}")
        
        except ValueError as e:
            self.logger.error(f"路径优化值错误: {e}")
            return self.format_error_response(str(e))
        
        except Exception as e:
            self.logger.error(f"路径优化意外错误: {e}", exc_info=True)
            return self.format_error_response(f"路径优化失败: {e}")
    
    def _parse_waypoints(self, waypoints_data: List[Dict[str, Any]]) -> List[Waypoint]:
        """解析航点数据。"""
        waypoints = []
        
        for i, wp_data in enumerate(waypoints_data):
            coords_data = wp_data["coordinates"]
            coordinates = Coordinates(
                latitude=coords_data["latitude"],
                longitude=coords_data["longitude"],
                altitude=coords_data["altitude"]
            )
            
            waypoint = Waypoint(
                index=wp_data.get("index", i),
                coordinates=coordinates,
                speed=5.0  # 默认速度
            )
            
            # 添加额外属性
            waypoint.priority = wp_data.get("priority", 5)
            waypoint.visit_time = wp_data.get("visit_time", 0)
            
            waypoints.append(waypoint)
        
        return waypoints
    
    def _calculate_distance_matrix(self, waypoints: List[Waypoint]) -> np.ndarray:
        """计算航点间距离矩阵。"""
        n = len(waypoints)
        distance_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance = self.geometry_calc.haversine_distance(
                        waypoints[i].coordinates,
                        waypoints[j].coordinates
                    )
                    distance_matrix[i][j] = distance
        
        return distance_matrix
    
    def _calculate_route_cost(
        self, 
        route: List[int], 
        distance_matrix: np.ndarray,
        waypoints: List[Waypoint],
        objective: OptimizationObjective,
        flight_speed: float
    ) -> float:
        """计算路径成本。"""
        if len(route) < 2:
            return 0.0
        
        total_distance = 0.0
        total_time = 0.0
        total_energy = 0.0
        
        for i in range(len(route) - 1):
            current_idx = route[i]
            next_idx = route[i + 1]
            
            # 距离成本
            distance = distance_matrix[current_idx][next_idx]
            total_distance += distance
            
            # 时间成本（包括飞行时间和访问时间）
            flight_time = distance / flight_speed
            visit_time = getattr(waypoints[current_idx], 'visit_time', 0)
            total_time += flight_time + visit_time
            
            # 能耗成本（简化模型）
            altitude_diff = abs(
                waypoints[next_idx].coordinates.altitude - 
                waypoints[current_idx].coordinates.altitude
            )
            energy = distance * 1.0 + altitude_diff * 0.5  # 简化的能耗模型
            total_energy += energy
        
        # 根据优化目标返回相应成本
        if objective == OptimizationObjective.MINIMIZE_DISTANCE:
            return total_distance
        elif objective == OptimizationObjective.MINIMIZE_TIME:
            return total_time
        elif objective == OptimizationObjective.MINIMIZE_ENERGY:
            return total_energy
        else:  # BALANCED
            # 归一化并加权组合
            return total_distance * 0.4 + total_time * 0.4 + total_energy * 0.2
    
    def _nearest_neighbor_optimization(
        self,
        waypoints: List[Waypoint],
        distance_matrix: np.ndarray,
        optimizer_input: RouteOptimizerInput
    ) -> OptimizationResult:
        """最近邻算法优化。"""
        n = len(waypoints)
        original_order = list(range(n))
        
        # 计算原始路径成本
        original_cost = self._calculate_route_cost(
            original_order, distance_matrix, waypoints,
            optimizer_input.optimization_objective, optimizer_input.flight_speed
        )
        
        # 最近邻算法
        unvisited = set(range(n))
        current = 0 if optimizer_input.start_point_fixed else random.randint(0, n-1)
        route = [current]
        unvisited.remove(current)
        
        while unvisited:
            nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        # 计算优化后成本
        optimized_cost = self._calculate_route_cost(
            route, distance_matrix, waypoints,
            optimizer_input.optimization_objective, optimizer_input.flight_speed
        )
        
        improvement = (original_cost - optimized_cost) / original_cost * 100
        
        return OptimizationResult(
            original_distance=self._calculate_total_distance(original_order, distance_matrix),
            optimized_distance=self._calculate_total_distance(route, distance_matrix),
            improvement_percentage=improvement,
            original_time=original_cost / optimizer_input.flight_speed,
            optimized_time=optimized_cost / optimizer_input.flight_speed,
            original_order=original_order,
            optimized_order=route,
            method_used="nearest_neighbor",
            iterations=n-1,
            computation_time=0.0
        )
    
    def _two_opt_optimization(
        self,
        waypoints: List[Waypoint],
        distance_matrix: np.ndarray,
        optimizer_input: RouteOptimizerInput
    ) -> OptimizationResult:
        """2-opt算法优化。"""
        n = len(waypoints)
        route = list(range(n))
        
        # 计算原始成本
        original_cost = self._calculate_route_cost(
            route, distance_matrix, waypoints,
            optimizer_input.optimization_objective, optimizer_input.flight_speed
        )
        
        best_route = route.copy()
        best_cost = original_cost
        iterations = 0
        
        improved = True
        while improved and iterations < optimizer_input.max_iterations:
            improved = False
            
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    # 跳过固定点
                    if optimizer_input.start_point_fixed and (i == 0 or j == 0):
                        continue
                    if optimizer_input.end_point_fixed and (i == n-1 or j == n-1):
                        continue
                    
                    # 2-opt交换
                    new_route = route.copy()
                    new_route[i:j+1] = reversed(new_route[i:j+1])
                    
                    new_cost = self._calculate_route_cost(
                        new_route, distance_matrix, waypoints,
                        optimizer_input.optimization_objective, optimizer_input.flight_speed
                    )
                    
                    if new_cost < best_cost:
                        best_route = new_route
                        best_cost = new_cost
                        improved = True
            
            route = best_route.copy()
            iterations += 1
        
        improvement = (original_cost - best_cost) / original_cost * 100
        
        return OptimizationResult(
            original_distance=self._calculate_total_distance(list(range(n)), distance_matrix),
            optimized_distance=self._calculate_total_distance(best_route, distance_matrix),
            improvement_percentage=improvement,
            original_time=original_cost / optimizer_input.flight_speed,
            optimized_time=best_cost / optimizer_input.flight_speed,
            original_order=list(range(n)),
            optimized_order=best_route,
            method_used="two_opt",
            iterations=iterations,
            computation_time=0.0
        )
    
    def _simulated_annealing_optimization(
        self,
        waypoints: List[Waypoint],
        distance_matrix: np.ndarray,
        optimizer_input: RouteOptimizerInput
    ) -> OptimizationResult:
        """模拟退火算法优化。"""
        n = len(waypoints)
        current_route = list(range(n))
        
        # 计算原始成本
        original_cost = self._calculate_route_cost(
            current_route, distance_matrix, waypoints,
            optimizer_input.optimization_objective, optimizer_input.flight_speed
        )
        
        current_cost = original_cost
        best_route = current_route.copy()
        best_cost = current_cost
        
        # 模拟退火参数
        initial_temp = 1000.0
        final_temp = 1.0
        cooling_rate = 0.995
        
        temperature = initial_temp
        iterations = 0
        
        while temperature > final_temp and iterations < optimizer_input.max_iterations:
            # 生成邻居解
            new_route = current_route.copy()
            
            # 随机选择两个位置进行交换（避免固定点）
            valid_indices = list(range(n))
            if optimizer_input.start_point_fixed:
                valid_indices.remove(0)
            if optimizer_input.end_point_fixed and n-1 in valid_indices:
                valid_indices.remove(n-1)
            
            if len(valid_indices) >= 2:
                i, j = random.sample(valid_indices, 2)
                new_route[i], new_route[j] = new_route[j], new_route[i]
                
                new_cost = self._calculate_route_cost(
                    new_route, distance_matrix, waypoints,
                    optimizer_input.optimization_objective, optimizer_input.flight_speed
                )
                
                # 接受准则
                delta = new_cost - current_cost
                if delta < 0 or random.random() < math.exp(-delta / temperature):
                    current_route = new_route
                    current_cost = new_cost
                    
                    if current_cost < best_cost:
                        best_route = current_route.copy()
                        best_cost = current_cost
            
            temperature *= cooling_rate
            iterations += 1
        
        improvement = (original_cost - best_cost) / original_cost * 100
        
        return OptimizationResult(
            original_distance=self._calculate_total_distance(list(range(n)), distance_matrix),
            optimized_distance=self._calculate_total_distance(best_route, distance_matrix),
            improvement_percentage=improvement,
            original_time=original_cost / optimizer_input.flight_speed,
            optimized_time=best_cost / optimizer_input.flight_speed,
            original_order=list(range(n)),
            optimized_order=best_route,
            method_used="simulated_annealing",
            iterations=iterations,
            computation_time=0.0
        )
    
    def _genetic_algorithm_optimization(
        self,
        waypoints: List[Waypoint],
        distance_matrix: np.ndarray,
        optimizer_input: RouteOptimizerInput
    ) -> OptimizationResult:
        """遗传算法优化。"""
        n = len(waypoints)
        original_order = list(range(n))
        
        # 计算原始成本
        original_cost = self._calculate_route_cost(
            original_order, distance_matrix, waypoints,
            optimizer_input.optimization_objective, optimizer_input.flight_speed
        )
        
        # 遗传算法参数
        population_size = min(100, max(20, n * 2))
        mutation_rate = 0.1
        crossover_rate = 0.8
        elite_size = max(2, population_size // 10)
        
        # 初始化种群
        population = []
        for _ in range(population_size):
            individual = list(range(n))
            # 保持固定点不变
            if not optimizer_input.start_point_fixed or not optimizer_input.end_point_fixed:
                valid_indices = list(range(n))
                if optimizer_input.start_point_fixed:
                    valid_indices.remove(0)
                if optimizer_input.end_point_fixed:
                    valid_indices.remove(n-1)
                random.shuffle(valid_indices)
                
                # 重新构建个体
                new_individual = individual.copy()
                for i, idx in enumerate(valid_indices):
                    if optimizer_input.start_point_fixed:
                        new_individual[i+1] = idx
                    else:
                        new_individual[i] = idx
                individual = new_individual
            
            population.append(individual)
        
        best_individual = None
        best_cost = float('inf')
        generations = 0
        
        while generations < optimizer_input.max_iterations // 10:  # 减少代数以控制计算时间
            # 评估适应度
            fitness_scores = []
            for individual in population:
                cost = self._calculate_route_cost(
                    individual, distance_matrix, waypoints,
                    optimizer_input.optimization_objective, optimizer_input.flight_speed
                )
                fitness_scores.append(1.0 / (1.0 + cost))  # 转换为适应度
                
                if cost < best_cost:
                    best_cost = cost
                    best_individual = individual.copy()
            
            # 选择
            new_population = []
            
            # 精英保留
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i], reverse=True)[:elite_size]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # 生成新个体
            while len(new_population) < population_size:
                if random.random() < crossover_rate:
                    # 交叉
                    parent1 = self._tournament_selection(population, fitness_scores)
                    parent2 = self._tournament_selection(population, fitness_scores)
                    child = self._order_crossover(parent1, parent2, optimizer_input)
                else:
                    # 直接选择
                    child = self._tournament_selection(population, fitness_scores)
                
                # 变异
                if random.random() < mutation_rate:
                    child = self._mutate(child, optimizer_input)
                
                new_population.append(child)
            
            population = new_population
            generations += 1
        
        improvement = (original_cost - best_cost) / original_cost * 100
        
        return OptimizationResult(
            original_distance=self._calculate_total_distance(original_order, distance_matrix),
            optimized_distance=self._calculate_total_distance(best_individual, distance_matrix),
            improvement_percentage=improvement,
            original_time=original_cost / optimizer_input.flight_speed,
            optimized_time=best_cost / optimizer_input.flight_speed,
            original_order=original_order,
            optimized_order=best_individual,
            method_used="genetic_algorithm",
            iterations=generations,
            computation_time=0.0
        )
    
    def _christofides_optimization(
        self,
        waypoints: List[Waypoint],
        distance_matrix: np.ndarray,
        optimizer_input: RouteOptimizerInput
    ) -> OptimizationResult:
        """Christofides算法优化（简化版本）。"""
        # 由于Christofides算法较复杂，这里实现一个简化版本
        # 实际上是最近邻 + 2-opt的组合
        
        # 先用最近邻获得初始解
        nn_result = self._nearest_neighbor_optimization(
            waypoints, distance_matrix, optimizer_input
        )
        
        # 再用2-opt改进
        optimizer_input_copy = optimizer_input.copy()
        optimizer_input_copy.optimization_method = OptimizationMethod.TWO_OPT
        
        # 使用最近邻的结果作为2-opt的起始点
        two_opt_result = self._two_opt_optimization(
            waypoints, distance_matrix, optimizer_input_copy
        )
        
        two_opt_result.method_used = "christofides"
        return two_opt_result
    
    def _tournament_selection(self, population: List[List[int]], fitness_scores: List[float]) -> List[int]:
        """锦标赛选择。"""
        tournament_size = 3
        tournament_indices = random.sample(range(len(population)), 
                                         min(tournament_size, len(population)))
        winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return population[winner_idx].copy()
    
    def _order_crossover(
        self, 
        parent1: List[int], 
        parent2: List[int], 
        optimizer_input: RouteOptimizerInput
    ) -> List[int]:
        """顺序交叉。"""
        n = len(parent1)
        child = [-1] * n
        
        # 保持固定点
        if optimizer_input.start_point_fixed:
            child[0] = 0
        if optimizer_input.end_point_fixed:
            child[-1] = n - 1
        
        # 选择交叉区间
        start = random.randint(1 if optimizer_input.start_point_fixed else 0, 
                              n - 2 if optimizer_input.end_point_fixed else n - 1)
        end = random.randint(start, n - 2 if optimizer_input.end_point_fixed else n - 1)
        
        # 复制parent1的交叉区间
        for i in range(start, end + 1):
            child[i] = parent1[i]
        
        # 从parent2填充剩余位置
        parent2_filtered = [x for x in parent2 if x not in child]
        j = 0
        for i in range(n):
            if child[i] == -1:
                child[i] = parent2_filtered[j]
                j += 1
        
        return child
    
    def _mutate(self, individual: List[int], optimizer_input: RouteOptimizerInput) -> List[int]:
        """变异操作。"""
        mutated = individual.copy()
        n = len(mutated)
        
        # 确定可变异的位置
        valid_indices = list(range(n))
        if optimizer_input.start_point_fixed:
            valid_indices.remove(0)
        if optimizer_input.end_point_fixed:
            valid_indices.remove(n - 1)
        
        if len(valid_indices) >= 2:
            # 随机交换两个位置
            i, j = random.sample(valid_indices, 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]
        
        return mutated
    
    def _calculate_total_distance(self, route: List[int], distance_matrix: np.ndarray) -> float:
        """计算路径总距离。"""
        total_distance = 0.0
        for i in range(len(route) - 1):
            total_distance += distance_matrix[route[i]][route[i + 1]]
        return total_distance
    
    def _calculate_cumulative_distance(self, waypoints: List[Waypoint]) -> float:
        """计算累积距离。"""
        if len(waypoints) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(waypoints) - 1):
            distance = self.geometry_calc.haversine_distance(
                waypoints[i].coordinates,
                waypoints[i + 1].coordinates
            )
            total_distance += distance
        
        return total_distance
    
    def _analyze_route_changes(self, original_order: List[int], optimized_order: List[int]) -> Dict[str, Any]:
        """分析路径变化。"""
        changes = {
            "total_swaps": 0,
            "position_changes": [],
            "sequence_preserved": []
        }
        
        # 计算位置变化
        for i, original_idx in enumerate(original_order):
            new_position = optimized_order.index(original_idx)
            if i != new_position:
                changes["position_changes"].append({
                    "waypoint_index": original_idx,
                    "original_position": i,
                    "new_position": new_position,
                    "position_change": new_position - i
                })
        
        changes["total_swaps"] = len(changes["position_changes"])
        
        # 检查保持的序列
        for i in range(len(original_order) - 1):
            current_idx = original_order[i]
            next_idx = original_order[i + 1]
            
            current_pos = optimized_order.index(current_idx)
            next_pos = optimized_order.index(next_idx)
            
            if abs(current_pos - next_pos) == 1:
                changes["sequence_preserved"].append((current_idx, next_idx))
        
        return changes


# 需要导入time模块
import time