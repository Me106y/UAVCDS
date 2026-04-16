// 主要JavaScript功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initImageManager();
    initNavigation();
    initTabs();
    initScrollEffects();
    initCodeBlocks();
    initTooltips();
    initSearch();
    
    console.log('🚀 大疆航线规划MCP服务文档网站已加载');
});

// 图片管理器
class ImageManager {
    constructor() {
        this.loadedImages = new Set();
        this.observers = new Map();
        this.retryAttempts = new Map();
        this.maxRetries = 3;
    }
    
    // 懒加载图片
    lazyLoad(selector = 'img[data-src]') {
        const images = document.querySelectorAll(selector);
        const observer = new IntersectionObserver(this.handleIntersection.bind(this), {
            rootMargin: '50px 0px',
            threshold: 0.01
        });
        
        images.forEach(img => {
            observer.observe(img);
            this.observers.set(img, observer);
        });
    }
    
    // 处理图片进入视窗
    handleIntersection(entries, observer) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                this.loadImage(img);
                observer.unobserve(img);
            }
        });
    }
    
    // 加载单个图片
    loadImage(img) {
        const src = img.dataset.src || img.src;
        if (this.loadedImages.has(src)) return;
        
        // 显示加载状态
        img.classList.add('loading');
        
        const tempImg = new Image();
        tempImg.onload = () => {
            img.src = src;
            img.classList.remove('loading');
            img.classList.add('loaded');
            this.loadedImages.add(src);
        };
        
        tempImg.onerror = () => {
            this.handleImageError(img, src);
        };
        
        tempImg.src = src;
    }
    
    // 处理图片加载错误
    handleImageError(img, src) {
        const attempts = this.retryAttempts.get(src) || 0;
        
        if (attempts < this.maxRetries) {
            // 重试加载
            this.retryAttempts.set(src, attempts + 1);
            setTimeout(() => {
                this.loadImage(img);
            }, 1000 * Math.pow(2, attempts)); // 指数退避
        } else {
            // 使用占位符
            this.useFallback(img);
        }
    }
    
    // 使用占位符图片
    useFallback(img) {
        const fallbackSrc = img.dataset.fallback || this.getDefaultFallback(img);
        if (fallbackSrc && img.src !== fallbackSrc) {
            img.src = fallbackSrc;
            img.classList.add('fallback');
        }
        img.classList.remove('loading');
    }
    
    // 获取默认占位符
    getDefaultFallback(img) {
        const alt = img.alt.toLowerCase();
        if (alt.includes('logo')) {
            return 'assets/images/placeholders/logo-placeholder.svg';
        } else if (alt.includes('hero') || alt.includes('planning')) {
            return 'assets/images/placeholders/hero-placeholder.svg';
        }
        return null;
    }
    
    // 预加载关键图片
    preload(urls) {
        return Promise.all(urls.map(url => {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    this.loadedImages.add(url);
                    resolve(url);
                };
                img.onerror = reject;
                img.src = url;
            });
        }));
    }
    
    // 检查浏览器支持的图片格式
    checkImageSupport() {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        
        return {
            webp: canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0,
            avif: canvas.toDataURL('image/avif').indexOf('data:image/avif') === 0
        };
    }
}

// 初始化图片管理器
function initImageManager() {
    const imageManager = new ImageManager();
    
    // 预加载关键图片
    const criticalImages = [
        'assets/images/logo.svg',
        'assets/images/drone-planning.svg'
    ];
    
    imageManager.preload(criticalImages).catch(error => {
        console.warn('预加载图片失败:', error);
    });
    
    // 为所有图片添加错误处理
    document.querySelectorAll('img').forEach(img => {
        if (!img.onerror) {
            img.onerror = function() {
                imageManager.useFallback(this);
            };
        }
        
        // 添加加载状态样式
        if (!img.complete) {
            img.classList.add('loading');
        }
        
        img.onload = function() {
            this.classList.remove('loading');
            this.classList.add('loaded');
        };
    });
    
    // 启用懒加载（如果有data-src属性的图片）
    imageManager.lazyLoad();
    
    // 将图片管理器添加到全局对象
    window.DJIWaypointMCP = window.DJIWaypointMCP || {};
    window.DJIWaypointMCP.imageManager = imageManager;
}

// 导航功能
function initNavigation() {
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');
    
    if (hamburger && navMenu) {
        hamburger.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            hamburger.classList.toggle('active');
        });
        
        // 点击菜单项时关闭移动端菜单
        navMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
                hamburger.classList.remove('active');
            });
        });
    }
    
    // 平滑滚动到锚点
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 导航栏滚动效果
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        
        // 添加滚动状态类
        if (scrollTop > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        // 智能隐藏/显示导航栏
        if (scrollTop > lastScrollTop && scrollTop > 100) {
            // 向下滚动，隐藏导航栏
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // 向上滚动，显示导航栏
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop;
    });
}

// 标签页功能
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // 移除所有活动状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanels.forEach(panel => panel.classList.remove('active'));
            
            // 激活当前标签
            this.classList.add('active');
            const targetPanel = document.getElementById(targetTab + '-panel');
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });
}

// 滚动效果
function initScrollEffects() {
    // 创建Intersection Observer
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // 观察需要动画的元素
    document.querySelectorAll('.feature-card, .tool-card, .step, .stat-item').forEach(el => {
        observer.observe(el);
    });
    
    // 滚动进度指示器
    const progressBar = createProgressBar();
    window.addEventListener('scroll', updateProgressBar);
    
    function createProgressBar() {
        const progress = document.createElement('div');
        progress.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: var(--primary-color);
            z-index: 9999;
            transition: width 0.1s ease;
        `;
        document.body.appendChild(progress);
        return progress;
    }
    
    function updateProgressBar() {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        progressBar.style.width = scrollPercent + '%';
    }
}

// 代码块功能
function initCodeBlocks() {
    document.querySelectorAll('.code-block').forEach(block => {
        // 添加复制按钮
        const copyButton = document.createElement('button');
        copyButton.innerHTML = '📋 复制';
        copyButton.className = 'copy-button';
        copyButton.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
        `;
        
        block.style.position = 'relative';
        block.appendChild(copyButton);
        
        copyButton.addEventListener('click', function() {
            const code = block.querySelector('pre').textContent;
            navigator.clipboard.writeText(code).then(() => {
                copyButton.innerHTML = '✅ 已复制';
                copyButton.style.background = 'rgba(16, 185, 129, 0.2)';
                
                setTimeout(() => {
                    copyButton.innerHTML = '📋 复制';
                    copyButton.style.background = 'rgba(255, 255, 255, 0.1)';
                }, 2000);
            }).catch(() => {
                copyButton.innerHTML = '❌ 失败';
                setTimeout(() => {
                    copyButton.innerHTML = '📋 复制';
                }, 2000);
            });
        });
        
        copyButton.addEventListener('mouseenter', function() {
            this.style.background = 'rgba(255, 255, 255, 0.2)';
        });
        
        copyButton.addEventListener('mouseleave', function() {
            this.style.background = 'rgba(255, 255, 255, 0.1)';
        });
    });
    
    // 代码高亮（简单版本）
    document.querySelectorAll('pre code').forEach(block => {
        highlightCode(block);
    });
}

// 简单的代码高亮
function highlightCode(block) {
    let code = block.innerHTML;
    
    // JSON高亮
    code = code.replace(/(".*?")/g, '<span style="color: #10b981;">$1</span>');
    code = code.replace(/(\b\d+\.?\d*\b)/g, '<span style="color: #f59e0b;">$1</span>');
    code = code.replace(/\b(true|false|null)\b/g, '<span style="color: #8b5cf6;">$1</span>');
    
    // Shell命令高亮
    code = code.replace(/^(#.*$)/gm, '<span style="color: #6b7280; font-style: italic;">$1</span>');
    code = code.replace(/\b(python|pip|git|docker|npm|yarn)\b/g, '<span style="color: #3b82f6;">$1</span>');
    
    // Python关键字高亮
    code = code.replace(/\b(import|from|def|class|if|else|elif|for|while|try|except|finally|with|as|return|yield|lambda|and|or|not|in|is)\b/g, '<span style="color: #8b5cf6;">$1</span>');
    
    block.innerHTML = code;
}

// 工具提示功能
function initTooltips() {
    // 创建工具提示元素
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.style.cssText = `
        position: absolute;
        background: var(--text-primary);
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        z-index: 1000;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        max-width: 200px;
        word-wrap: break-word;
    `;
    document.body.appendChild(tooltip);
    
    // 为工具卡片添加提示
    document.querySelectorAll('.tool-card').forEach(card => {
        const toolName = card.querySelector('h3').textContent;
        const description = card.querySelector('p').textContent;
        
        card.addEventListener('mouseenter', function(e) {
            tooltip.innerHTML = `<strong>${toolName}</strong><br>${description}`;
            tooltip.style.opacity = '1';
            updateTooltipPosition(e);
        });
        
        card.addEventListener('mousemove', updateTooltipPosition);
        
        card.addEventListener('mouseleave', function() {
            tooltip.style.opacity = '0';
        });
    });
    
    function updateTooltipPosition(e) {
        const x = e.clientX + 10;
        const y = e.clientY + 10;
        
        tooltip.style.left = x + 'px';
        tooltip.style.top = y + 'px';
        
        // 防止工具提示超出视窗
        const rect = tooltip.getBoundingClientRect();
        if (rect.right > window.innerWidth) {
            tooltip.style.left = (x - rect.width - 20) + 'px';
        }
        if (rect.bottom > window.innerHeight) {
            tooltip.style.top = (y - rect.height - 20) + 'px';
        }
    }
}

// 搜索功能
function initSearch() {
    // 创建搜索框
    const searchContainer = document.createElement('div');
    searchContainer.className = 'search-container';
    searchContainer.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1001;
        opacity: 0;
        transform: translateY(-10px);
        transition: all 0.3s ease;
    `;
    
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = '搜索工具和功能...';
    searchInput.style.cssText = `
        padding: 0.5rem 1rem;
        border: 1px solid var(--border-color);
        border-radius: 20px;
        background: var(--background-color);
        box-shadow: var(--shadow-md);
        width: 250px;
        font-size: 0.875rem;
    `;
    
    const searchResults = document.createElement('div');
    searchResults.className = 'search-results';
    searchResults.style.cssText = `
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: var(--background-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        max-height: 300px;
        overflow-y: auto;
        display: none;
        margin-top: 5px;
    `;
    
    searchContainer.appendChild(searchInput);
    searchContainer.appendChild(searchResults);
    document.body.appendChild(searchContainer);
    
    // 键盘快捷键 Ctrl+K 或 Cmd+K
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleSearch();
        }
        
        if (e.key === 'Escape') {
            hideSearch();
        }
    });
    
    // 搜索功能
    let searchData = [];
    
    // 构建搜索索引
    function buildSearchIndex() {
        searchData = [];
        
        // 添加工具信息
        document.querySelectorAll('.tool-card').forEach(card => {
            const title = card.querySelector('h3').textContent;
            const description = card.querySelector('p').textContent;
            const category = card.querySelector('.tool-category').textContent;
            
            searchData.push({
                title,
                description,
                category,
                type: 'tool',
                element: card
            });
        });
        
        // 添加功能特性
        document.querySelectorAll('.feature-card').forEach(card => {
            const title = card.querySelector('h3').textContent;
            const description = card.querySelector('p').textContent;
            
            searchData.push({
                title,
                description,
                type: 'feature',
                element: card
            });
        });
    }
    
    function toggleSearch() {
        if (searchContainer.style.opacity === '1') {
            hideSearch();
        } else {
            showSearch();
        }
    }
    
    function showSearch() {
        buildSearchIndex();
        searchContainer.style.opacity = '1';
        searchContainer.style.transform = 'translateY(0)';
        searchInput.focus();
    }
    
    function hideSearch() {
        searchContainer.style.opacity = '0';
        searchContainer.style.transform = 'translateY(-10px)';
        searchResults.style.display = 'none';
        searchInput.value = '';
    }
    
    // 搜索输入处理
    searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase().trim();
        
        if (query.length < 2) {
            searchResults.style.display = 'none';
            return;
        }
        
        const results = searchData.filter(item => 
            item.title.toLowerCase().includes(query) ||
            item.description.toLowerCase().includes(query) ||
            (item.category && item.category.toLowerCase().includes(query))
        );
        
        displaySearchResults(results);
    });
    
    function displaySearchResults(results) {
        searchResults.innerHTML = '';
        
        if (results.length === 0) {
            searchResults.innerHTML = '<div style="padding: 1rem; color: var(--text-muted);">未找到相关结果</div>';
        } else {
            results.slice(0, 8).forEach(result => {
                const item = document.createElement('div');
                item.style.cssText = `
                    padding: 0.75rem 1rem;
                    border-bottom: 1px solid var(--border-color);
                    cursor: pointer;
                    transition: background 0.2s ease;
                `;
                
                item.innerHTML = `
                    <div style="font-weight: 500; color: var(--text-primary);">${result.title}</div>
                    <div style="font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.25rem;">${result.description}</div>
                    ${result.category ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${result.category}</div>` : ''}
                `;
                
                item.addEventListener('mouseenter', function() {
                    this.style.background = 'var(--surface-color)';
                });
                
                item.addEventListener('mouseleave', function() {
                    this.style.background = 'transparent';
                });
                
                item.addEventListener('click', function() {
                    result.element.scrollIntoView({ behavior: 'smooth' });
                    hideSearch();
                });
                
                searchResults.appendChild(item);
            });
        }
        
        searchResults.style.display = 'block';
    }
    
    // 点击外部关闭搜索
    document.addEventListener('click', function(e) {
        if (!searchContainer.contains(e.target)) {
            hideSearch();
        }
    });
}

// 工具卡片交互
document.addEventListener('click', function(e) {
    if (e.target.closest('.tool-card')) {
        const toolCard = e.target.closest('.tool-card');
        const toolName = toolCard.querySelector('h3').textContent;
        
        // 添加点击效果
        toolCard.style.transform = 'scale(0.98)';
        setTimeout(() => {
            toolCard.style.transform = '';
        }, 150);
        
        // 如果在工具文档页面，滚动到对应部分
        const toolSection = document.querySelector(`#${toolName.replace('_', '-')}`);
        if (toolSection) {
            toolSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
});

// 性能监控
function initPerformanceMonitoring() {
    // 页面加载性能
    window.addEventListener('load', function() {
        const loadTime = performance.now();
        console.log(`📊 页面加载时间: ${loadTime.toFixed(2)}ms`);
        
        // 发送性能数据（如果需要）
        if (typeof gtag !== 'undefined') {
            gtag('event', 'page_load_time', {
                value: Math.round(loadTime),
                custom_parameter: 'dji_waypoint_mcp_docs'
            });
        }
    });
    
    // 监控长任务
    if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver(function(list) {
            list.getEntries().forEach(entry => {
                if (entry.duration > 50) {
                    console.warn(`⚠️ 长任务检测: ${entry.duration.toFixed(2)}ms`);
                }
            });
        });
        
        observer.observe({ entryTypes: ['longtask'] });
    }
}

// 错误处理
window.addEventListener('error', function(e) {
    console.error('❌ JavaScript错误:', e.error);
    
    // 显示用户友好的错误信息
    showNotification('页面出现了一些问题，请刷新页面重试', 'error');
});

// 通知系统
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        max-width: 300px;
        word-wrap: break-word;
    `;
    
    const colors = {
        info: '#3b82f6',
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444'
    };
    
    notification.style.background = colors[type] || colors.info;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // 自动隐藏
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 5000);
}

// 主题切换功能
function initThemeToggle() {
    const themeToggle = document.createElement('button');
    themeToggle.innerHTML = '🌙';
    themeToggle.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: none;
        background: var(--primary-color);
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        box-shadow: var(--shadow-lg);
        transition: all 0.3s ease;
        z-index: 1000;
    `;
    
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-theme');
        this.innerHTML = document.body.classList.contains('dark-theme') ? '☀️' : '🌙';
        
        // 保存主题偏好
        localStorage.setItem('theme', document.body.classList.contains('dark-theme') ? 'dark' : 'light');
    });
    
    // 恢复主题偏好
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggle.innerHTML = '☀️';
    }
    
    document.body.appendChild(themeToggle);
}

// 浏览器特性检测和优雅降级
function initBrowserSupport() {
    // 检测backdrop-filter支持
    const supportsBackdropFilter = CSS.supports('backdrop-filter', 'blur(1px)') || 
                                   CSS.supports('-webkit-backdrop-filter', 'blur(1px)');
    
    if (!supportsBackdropFilter) {
        document.body.classList.add('no-backdrop-filter');
        console.warn('⚠️ 浏览器不支持backdrop-filter，已启用降级方案');
    }
    
    // 检测Intersection Observer支持
    if (!('IntersectionObserver' in window)) {
        console.warn('⚠️ 浏览器不支持IntersectionObserver，部分功能可能受限');
        // 为不支持的浏览器提供简单的滚动监听
        window.addEventListener('scroll', function() {
            document.querySelectorAll('.feature-card, .tool-card').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.top < window.innerHeight && rect.bottom > 0) {
                    el.classList.add('fade-in');
                }
            });
        });
    }
    
    // 检测CSS Grid支持
    if (!CSS.supports('display', 'grid')) {
        document.body.classList.add('no-grid');
        console.warn('⚠️ 浏览器不支持CSS Grid，已启用Flexbox降级方案');
    }
    
    // 检测用户偏好
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.body.classList.add('reduce-motion');
        console.log('🎯 检测到用户偏好减少动画，已调整动画效果');
    }
    
    // 检测高对比度偏好
    if (window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches) {
        document.body.classList.add('high-contrast');
        console.log('🎯 检测到用户偏好高对比度，已调整样式');
    }
}

// 性能优化函数
function optimizePerformance() {
    // 防抖函数
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // 节流函数
    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // 优化滚动事件
    const optimizedScrollHandler = throttle(function() {
        // 滚动相关的处理逻辑
        const scrollTop = window.scrollY;
        const navbar = document.querySelector('.navbar');
        
        if (scrollTop > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }, 16); // 约60fps
    
    window.addEventListener('scroll', optimizedScrollHandler, { passive: true });
    
    // 优化resize事件
    const optimizedResizeHandler = debounce(function() {
        // 重新计算布局相关的逻辑
        console.log('🔄 窗口大小已调整，重新计算布局');
    }, 250);
    
    window.addEventListener('resize', optimizedResizeHandler);
    
    return { debounce, throttle };
}

// 初始化额外功能
document.addEventListener('DOMContentLoaded', function() {
    initBrowserSupport();
    optimizePerformance();
    initPerformanceMonitoring();
    initThemeToggle();
});

// 导出功能供其他脚本使用
window.DJIWaypointMCP = {
    showNotification,
    initSearch,
    initTabs,
    highlightCode
};