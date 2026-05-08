# 软著说明书产物

本目录用于存放 `Heater Zoning Optimizer V1.0` 软件著作权登记配套说明书及其生成素材。

## 目录说明

- `Heater_Zoning_Optimizer_V1.0_软件使用说明书.docx`
  - 正式版 Word 说明书
- `Heater_Zoning_Optimizer_V1.0_软件使用说明书.pdf`
  - 由 Word 文档导出的 PDF 版本
- `assets/`
  - 文档中引用的界面截图、图表、功能模块图、流程图
- `generated/`
  - 基于默认示例数据自动生成的示例 Excel 报告与 PDF 摘要

## 生成方式

使用项目本地 Python 环境运行：

```powershell
D:\miniconda3\envs\heater_zoning_optimizer\python.exe scripts\generate_softcopyright_manual.py
```

脚本会自动执行以下动作：

1. 使用默认示例数据运行分析
2. 生成示例 Excel 报告与 PDF 摘要
3. 生成图表、界面截图、功能模块图、操作流程图
4. 生成软著风格 Word 说明书
5. 通过本机 Microsoft Word 导出 PDF

## 依赖说明

- `python-docx`
- `pywin32`
- 本机已安装 Microsoft Word（用于 PDF 导出）
