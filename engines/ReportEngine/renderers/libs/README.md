# 第三方JavaScript库

本目录包含HTML报告渲染所需的第三方JavaScript库。这些库已经被内联到生成的HTML文件中，以便在离线环境中使用。

## 包含的库

1. **chart.js** (204KB) - 用于图表渲染
   - 版本: 4.5.1
   - 来源: https://cdn.jsdelivr.net/npm/chart.js

2. **chartjs-chart-sankey.js** (10KB) - Sankey图表插件
   - 版本: 0.12.0
   - 来源: https://unpkg.com/chartjs-chart-sankey@0.12.0/dist/chartjs-chart-sankey.min.js

3. **html2canvas.min.js** (194KB) - HTML转Canvas工具
   - 版本: 1.4.1
   - 来源: https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js

4. **jspdf.umd.min.js** (356KB) - PDF导出库
   - 版本: 2.5.1
   - 来源: https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js

5. **mathjax.js** (1.1MB) - 数学公式渲染引擎
   - 版本: 3.2.2
   - 来源: https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-mml-chtml.js

## 功能说明

HTML渲染器(`html_renderer.py`)会自动从本目录加载这些库文件，并将它们内联到生成的HTML中。这样做有以下优点：

- ✅ 离线环境可用 - 无需网络连接即可正常显示报告
- ✅ 加载速度快 - 不依赖外部CDN
- ✅ 稳定性高 - 不受CDN服务中断影响
- ✅ 版本固定 - 确保功能的一致性

## 备用机制

如果库文件加载失败（如文件不存在或读取错误），渲染器会自动回退到使用CDN链接，确保在任何情况下都能正常工作。

## 更新库文件

如需更新库文件，请：

1. 从相应的CDN下载最新版本
2. 替换本目录中的对应文件
3. 更新本README文件中的版本信息

## 注意事项

- 总大小约为1.86MB，会增加生成的HTML文件大小
- 对于不需要图表和数学公式的简单报告，这些库仍然会被包含
- 如果需要减小文件大小，可以考虑使用更轻量的替代方案
