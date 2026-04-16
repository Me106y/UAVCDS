# 大疆航线规划MCP服务 - 官网文档

这是大疆航线规划MCP服务的官方文档网站，提供完整的使用指南、API参考和示例代码。

## 网站结构

```
website/
├── index.html              # 主页 - 服务介绍和功能概览
├── tools.html              # 工具文档 - 详细的工具使用说明
├── deployment.html         # 部署指南 - 安装和配置说明
├── examples.html           # 使用示例 - 实际应用案例
├── api.html               # API参考 - 完整的API文档
├── assets/
│   ├── css/
│   │   ├── style.css      # 主样式文件
│   │   └── glassmorphism.css # 毛玻璃效果样式
│   ├── js/
│   │   └── main.js        # 主JavaScript文件 (含图片管理器)
│   └── images/            # 图片资源
│       ├── logo.svg       # SVG格式Logo
│       ├── logo-dark.svg  # 深色主题Logo
│       ├── logo.png       # PNG格式Logo备用
│       ├── favicon.svg    # 网站图标
│       ├── drone-planning.svg # 英雄区域插图
│       └── placeholders/  # 占位符图片
│           ├── logo-placeholder.svg
│           └── hero-placeholder.svg
└── README.md              # 本文件
```

## 功能特性

### 🎨 现代化设计
- 🌟 **毛玻璃效果**: 现代化的半透明背景模糊效果
- 📱 **响应式布局**: 完美适配桌面、平板和移动设备
- 🌙 **深色/浅色主题**: 智能主题切换，支持系统偏好检测
- ✨ **平滑动画**: 60fps流畅动画和微交互效果
- 🎨 **专业代码高亮**: 语法高亮和一键复制功能

### 📚 完整文档
- **工具文档**: 10个MCP工具的详细说明
- **部署指南**: 从安装到生产环境的完整指南
- **使用示例**: 8个实际应用场景的完整代码
- **API参考**: 完整的API接口文档

### 🔍 交互功能
- 全站搜索 (Ctrl+K)
- 代码块一键复制
- 工具提示和悬停效果
- 标签页切换
- 侧边栏导航

### ⚡ 性能优化
- 🖼️ **智能图片管理**: 懒加载、预加载和错误处理
- 🎯 **毛玻璃效果优化**: 硬件加速和移动端性能适配
- 📱 **响应式图片**: SVG矢量图和多格式支持
- ⚡ **JavaScript优化**: 防抖节流和性能监控
- 🔧 **浏览器兼容**: 特性检测和优雅降级
- 💾 **缓存策略**: 资源缓存和版本控制

## 本地开发

### 启动本地服务器

```bash
# 使用Python内置服务器
cd website
python -m http.server 8000

# 或使用Node.js服务器
npx serve .

# 或使用PHP服务器
php -S localhost:8000
```

然后访问 http://localhost:8000

### 文件修改

- **样式修改**: 编辑 `assets/css/style.css`
- **脚本修改**: 编辑 `assets/js/main.js`
- **内容修改**: 编辑对应的HTML文件

## 部署

### 静态网站托管

可以部署到任何静态网站托管服务：

- **GitHub Pages**: 推送到gh-pages分支
- **Netlify**: 连接GitHub仓库自动部署
- **Vercel**: 导入项目自动部署
- **AWS S3**: 上传到S3存储桶

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/website;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
```

## 自定义配置

### 主题颜色

在 `assets/css/style.css` 中修改CSS变量：

```css
:root {
    --primary-color: #2563eb;      /* 主色调 */
    --secondary-color: #64748b;    /* 次要颜色 */
    --accent-color: #f59e0b;       /* 强调色 */
    --success-color: #10b981;      /* 成功色 */
    --warning-color: #f59e0b;      /* 警告色 */
    --error-color: #ef4444;        /* 错误色 */
}
```

### 添加新页面

1. 创建新的HTML文件
2. 复制现有页面的结构
3. 更新导航菜单
4. 添加到侧边栏导航

### 添加图片资源

将图片文件放置在 `assets/images/` 目录下：

```
assets/images/
├── logo.png              # 网站Logo
├── favicon.ico           # 网站图标
├── drone-planning.svg    # 英雄区域图片
└── screenshots/          # 截图文件夹
```

## 浏览器支持

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本文档网站采用 MIT 许可证。

## 联系我们

- GitHub Issues: 报告问题和建议
- 邮箱: your-email@example.com
- 文档反馈: 通过GitHub提交PR

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！