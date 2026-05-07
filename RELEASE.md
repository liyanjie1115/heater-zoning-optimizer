# Release Notes

## Runtime targets

- Desktop GUI: `python desktop_app.py`
- CLI: `python cli.py --help`
- Optional web view: `python app.py`

桌面 GUI 是主入口。

## Windows packaging

仓库里已经提供了两套 PyInstaller 构建入口：

- `scripts/build_windows.ps1`
- `scripts/build_windows.bat`

以及对应的 spec 文件：

- `heater_zoning_optimizer.spec`

### PowerShell

```powershell
.\scripts\build_windows.ps1
```

### Batch

```bat
scripts\build_windows.bat
```

### 指定 Python

如果你后面要切到单独环境，可以显式指定解释器：

```powershell
.\scripts\build_windows.ps1 -PythonExe "D:\anaconda\envs\data_science\python.exe"
```

## Build output

默认产物在 `dist/` 下。

```text
dist\
```

## Release checklist

1. 运行 `python -m unittest discover -s tests -v`
2. 运行 `python cli.py --json`
3. 运行 `python desktop_app.py`
4. 在桌面端验证：
   - 选择示例数据
   - 运行分析
   - 保存参数模板
   - 检查最近文件
   - 导出 Excel
   - 导出 PDF 摘要
5. 运行 PyInstaller 打包脚本
6. 检查 `dist/` 中的 exe 是否可启动
7. 确认 Git 工作区干净后打 tag
