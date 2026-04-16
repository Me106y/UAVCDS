# 大疆航线规划MCP服务

[![测试状态](https://img.shields.io/badge/测试-100%25通过-brightgreen)](./test_report.md)
[![Python版本](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)
[![MCP协议](https://img.shields.io/badge/MCP-兼容-orange)](https://modelcontextprotocol.io)

一个专业的MCP（Model Context Protocol）服务，专注于大疆无人机航线规划和KMZ文件生成。基于大疆WPML（WayPoint Markup Language）标准，提供自动化航线规划、KMZ文件生成和航线优化功能。

## ✨ 主要特性

- 🛩️ **多种飞行模式**: 支持航点飞行、建图航拍、倾斜摄影、航带巡检等
- 🎯 **智能航线规划**: 自动生成最优航线路径，支持复杂测区和多种约束条件
- 📁 **WPML标准**: 生成符合大疆WPML标准的KMZ文件，直接导入DJI Pilot 2使用
- 🔧 **路径优化**: 内置多种优化算法，最小化飞行距离和时间
- 🌐 **坐标转换**: 支持多种坐标系统转换（WGS84、GCJ02、BD09等）
- ✅ **兼容性检查**: 自动验证设备兼容性和参数安全性
- 🚁 **多机型支持**: 支持M300/M350/M30/M3系列等多种大疆无人机

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 支持的操作系统: macOS, Linux, Windows

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd dji-waypoint-mcp

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt
```

### 运行服务

```bash
# 启动MCP服务
python -m src.dji_waypoint_mcp.server

# 或者使用开发模式
python src/dji_waypoint_mcp/server.py
```

### 测试安装

```bash
# 运行完整测试
python test_comprehensive.py

# 查看测试报告
cat test_report.md
```

## 📖 使用指南

### MCP工具概览

| 工具名称 | 功能 | 适用场景 |
|---------|------|---------|
| `plan_waypoint_mission` | 航点飞行规划 | 精确定位作业 |
| `plan_mapping_mission` | 建图航拍规划 | 地形测绘 |
| `plan_oblique_mission` | 倾斜摄影规划 | 三维建模 |
| `plan_strip_mission` | 航带飞行规划 | 线性巡检 |
| `optimize_route` | 路径优化 | 效率提升 |
| `generate_kmz` | KMZ文件生成 | 文件导出 |

### 基础使用示例

#### 1. 航点飞行任务

```python
# 规划简单的航点飞行任务
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

#### 2. 建图航拍任务

```python
# 规划矩形测区建图任务
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
        "direction": 0
    },
    "aircraft_type": "M30"
}
```

#### 3. 生成KMZ文件

```python
# 生成WPML标准的KMZ文件
kmz_config = {
    "flight_plan": {
        "waypoints": [...],  # 航点数据
        "flight_speed": 5.0,
        "aircraft_type": "M30"
    },
    "output_filename": "mission.kmz",
    "include_template": True,
    "author": "航线规划师"
}
```

## 🛠️ 开发指南

### 项目结构

```
dji-waypoint-mcp/
├── src/dji_waypoint_mcp/          # 主要源代码
│   ├── server.py                  # MCP服务器主程序
│   ├── config.py                  # 配置管理
│   ├── models/                    # 数据模型
│   ├── tools/                     # MCP工具实现
│   ├── utils/                     # 工具函数
│   └── data/                      # 数据文件
├── tests/                         # 测试文件
├── docs/                          # 文档
├── mcp/                          # MCP协议实现
└── requirements.txt              # 依赖列表
```

### 添加新工具

1. 在`src/dji_waypoint_mcp/tools/`目录创建新工具文件
2. 继承`BaseTool`类并实现必要方法
3. 在`server.py`中注册新工具
4. 添加相应的测试用例

### 代码规范

- 使用Python类型注解
- 遵循PEP 8代码风格
- 编写完整的文档字符串
- 添加适当的错误处理
- 编写单元测试

## 🔧 配置说明

### 环境变量

```bash
# 日志级别
export LOG_LEVEL=INFO

# 输出目录
export OUTPUT_DIR=./output

# 临时目录
export TEMP_DIR=./temp
```

### 配置文件

主要配置在`src/dji_waypoint_mcp/config.py`中：

```python
# 服务器配置
SERVER_NAME = "dji-waypoint-mcp"
SERVER_VERSION = "1.0.0"

# 文件路径配置
OUTPUT_DIR = Path("./output")
TEMP_DIR = Path("./temp")

# 日志配置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 📊 性能指标

- **测试覆盖率**: 100%
- **支持机型**: 9种大疆无人机
- **工具数量**: 10个专业工具
- **坐标系统**: 支持5种坐标系统转换
- **优化算法**: 5种路径优化算法

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献类型

- 🐛 Bug修复
- ✨ 新功能开发
- 📚 文档改进
- 🎨 代码优化
- 🧪 测试用例

## 📋 更新日志

### v1.0.0 (2024-07-20)

- ✅ 完整的MCP服务实现
- ✅ 10个专业航线规划工具
- ✅ WPML标准KMZ文件生成
- ✅ 多种坐标系统转换
- ✅ 智能路径优化算法
- ✅ 设备兼容性检查
- ✅ 100%测试覆盖率

## 🆘 故障排除

### 常见问题

**Q: 导入模块失败**
```bash
# 确保Python路径正确
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

**Q: 坐标转换不准确**
```bash
# 检查坐标系统设置
# 中国境内使用GCJ02，境外使用WGS84
```

**Q: KMZ文件无法导入DJI Pilot 2**
```bash
# 检查文件格式和WPML标准兼容性
# 确保航点数量不超过99个
```

更多问题请查看 [故障排除指南](docs/故障排除指南.md)

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [大疆创新](https://www.dji.com/) - WPML标准和技术支持
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP协议规范
- 开源社区的各种优秀库和工具

## 📞 联系我们

- 📧 邮箱: [your-email@example.com]
- 🐛 问题反馈: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 讨论: [GitHub Discussions](https://github.com/your-repo/discussions)

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！