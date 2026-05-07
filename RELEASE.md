# Release Notes

## Runtime targets

- Desktop GUI: `python desktop_app.py`
- CLI: `python cli.py --help`
- Optional web view: `python app.py`

## Packaging direction

当前项目适合优先发布为 Windows 桌面工具。

### 方案一：源码发布

适合团队内部直接拉仓库运行：

```bash
python desktop_app.py
```

### 方案二：PyInstaller 打包

建议在独立环境中执行：

```bash
pyinstaller --noconfirm --onefile --windowed --name heater-zoning-optimizer desktop_app.py
```

如果需要把 `data/` 一并打进去，再补 `--add-data` 参数。

## Release checklist

1. 运行 `python -m unittest discover -s tests -v`
2. 运行 `python cli.py --json`
3. 打开 `python desktop_app.py`
4. 用示例数据完成一次分析
5. 检查 `outputs/` 中的 Excel 报告
6. 确认 Git 工作区干净后打 tag

