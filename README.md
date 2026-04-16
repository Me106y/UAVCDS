# UAVCDS: 无人机综合指挥调度系统 (UAV Comprehensive Command and Dispatch System)

[![Status](https://img.shields.io/badge/Status-Ongoing_Updates-brightgreen)]()
[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![Framework](https://img.shields.io/badge/Framework-LangGraph%20%7C%20Streamlit-orange)]()

UAVCDS 是一个基于 **Multi-Agent (多智能体) 架构** 的无人机指挥调度原型系统。它通过接入多种 **MCP (Model Context Protocol)** 服务，实现了从目标搜索、航迹规划到航线文件生成的全流程自动化调度。

---

## 🌟 核心功能

### 🤖 多智能体协同 (Multi-Agent)
系统采用 **LangGraph ReAct 架构**，由指挥官智能体 (Orchestrator Agent) 统一调度：
- **感知智能体**：负责通过 Playwright 抓取大疆司空 2 (DJI FlyHub 2) 仪表盘实时状态。
- **规划智能体**：负责调用地图与航线规划工具生成执行方案。

### 🗺️ 地图与 POI 感知 (AMAP MCP)
集成 `amap-maps-mcp-server`：
- 支持通过自然语言搜索地点。

### ✈️ 航迹规划与 DJI 兼容性 (DJI MCP)
集成 `dji-waypoint-mcp` 服务：
- **自动化规划**：根据 AOI 坐标自动规划无人机巡航航迹。
- **KMZ 深度修复**：
  - **痛点解决**：修复了标准生成工具中文件位于根目录导致大疆司空 2、大疆智图或 Pilot 2 格式校验失败的问题。
  - **格式规范**：严格遵循 DJI WPML 规范，将 `waylines.wpml` 和 `template.kml` 封装在 `wpmz/` 文件夹下，确保 100% 导入成功率。
- **绝对路径输出**：生成完成后直接提供 KMZ 文件的绝对路径，方便快速部署。

---

## 📸 系统截图

> 
> <img width="2400" height="1494" alt="image" src="https://github.com/user-attachments/assets/1d301c52-520d-485b-8082-feb8c993b9fd" />
> <img width="2880" height="1626" alt="image" src="https://github.com/user-attachments/assets/c95971cf-4f94-4c04-ab10-e168caf0b7e4" />
> <img width="2880" height="1626" alt="image" src="https://github.com/user-attachments/assets/a0b7ea76-17c1-4654-bff6-b563ee0bdf72" />
> <img width="430" height="424" alt="image" src="https://github.com/user-attachments/assets/54480732-e816-4c14-b06e-8790a1ad5222" />





---

## 🛠️ 快速部署

### 1. 环境准备
确保已安装 Python 3.9+ 环境。

```bash
git clone https://github.com/YourUsername/UAVCDS.git
cd UAVCDS
pip install -r requirements.txt
```

### 2. 配置文件说明
- **`config.json`**: 配置通义千问 (DashScope) API Key、大疆司空 2 URL 以及默认飞行参数（高度、速度等）。
- **`mcp_settings.json`**: 配置本地各 MCP 服务器的启动命令（如 `dji-waypoint-mcp` 的路径）。

### 3. 启动系统
```bash
streamlit run app.py
```

---

## 📈 项目状态

本项目目前处于 **持续更新中 (Active Development)**。
- [x] 多智能体基础架构搭建
- [x] 高德地图 MCP 接入
- [x] 大疆航线规划与 KMZ 格式修复
- [ ] 空域冲突实时检测 (Airspace Monitor)
- [ ] 更多型号无人机参数适配

---

## 📄 开源协议
[MIT License](LICENSE)
