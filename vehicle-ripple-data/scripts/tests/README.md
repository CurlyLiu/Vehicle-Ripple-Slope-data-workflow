# Vehicle Ripple Data 测试套件

## 测试覆盖率概览

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| `core/condition_matcher.py` | 84% | ✓ |
| `core/vehicle_processor.py` | 86% | ✓ |
| `generate_error_report_cn.py` | 97% | ✓ |
| `generate_excel_report.py` | 61% | ✓ |
| **核心模块总计** | **80%** | ✓ |

## 测试文件说明

### 1. `test_vehicle_processor.py` - 车辆处理器单元测试
测试内容:
- 处理器初始化 (直接传入RIPPLE文件夹、父文件夹自动检测、自定义输出目录)
- 车辆信息解析 (Markdown格式、Excel格式、编码回退)
- 命名规则解析 (测试规则、传感器规则 - 表格和冒号格式)
- 组件发现 (已定义组件、跳过未定义组件、跳过输出文件夹)
- 工况数据处理 (SOC提取、SOC等级映射、图片文件名解析)
- 输出生成 (JSON、SQLite数据库)
- 配置驱动功能
- 边界情况 (空统计文件、缺少统计文件、无效工况行)

### 2. `test_condition_matcher.py` - 条件匹配器单元测试
测试内容:
- 精确匹配
- 规范化匹配 (括号变体、空格去除、大小写不敏感)
- 模糊匹配 (编辑距离、拼写容错)
- 特征匹配 (GBK乱码处理、关键词提取、SOC等级匹配)
- Levenshtein距离计算
- 相似度计算
- 特征提取 (坡度工况、标准工况、GBK乱码)
- 匹配详情获取
- 便捷函数 `get_condition_name`
- 多级匹配策略 (精确 > 规范化 > 模糊 > 特征)

### 3. `test_excel_report.py` - Excel报告生成器单元测试
测试内容:
- 车辆信息值提取 (主键、备用键、优先级)
- SOC提取 (标准格式、坡度格式、无效格式)
- SOC等级映射 (高/中/低电量、Unknown)
- 单位获取 (电压V、电流A、未知)
- Excel报告生成 (完整报告、空组件、坡度工况)
- 各工作表测试 (车辆信息、组件汇总、详细结果)
- JSON数据加载
- 边界情况 (缺少数据、超长字符串)

### 4. `test_error_report_cn.py` - 中文错误报告生成器单元测试
测试内容:
- 基本报告生成
- 包含错误的报告
- 包含警告的报告
- 包含处理统计的报告
- 报告输出位置验证
- 文件移动功能
- 示例报告生成
- 边界情况 (空列表、长字符串、特殊字符、非致命错误)

### 5. `test_integration.py` - 集成测试
测试内容:
- 完整处理流程 (单组件、多组件、坡度工况)
- Excel报告集成
- 错误报告集成
- 数据库集成 (SQLite输出验证)
- 边界情况集成 (缺少图片、空统计、GBK编码)

### 6. `test_regression.py` - 回归测试
测试内容:
- 父文件夹自动检测
- 多格式车辆信息支持
- 输出文件完整性
- Excel车辆信息表不为空
- 错误报告内容验证
- 模糊匹配边界情况
- 数据验证

### 7. `quick_test.py` - 快速回归测试
不依赖pytest，可直接运行的快速测试:
- 多格式车辆信息提取
- 模糊匹配功能
- Excel生成
- 错误报告生成

## 运行测试

### 运行所有测试
```bash
cd /c/Users/31915/.claude/skills/vehicle-ripple-data
python -m pytest scripts/tests/ -v
```

### 运行特定测试文件
```bash
python -m pytest scripts/tests/test_vehicle_processor.py -v
python -m pytest scripts/tests/test_condition_matcher.py -v
python -m pytest scripts/tests/test_excel_report.py -v
python -m pytest scripts/tests/test_error_report_cn.py -v
python -m pytest scripts/tests/test_integration.py -v
python -m pytest scripts/tests/test_regression.py -v
```

### 运行覆盖率检查
```bash
python -m pytest scripts/tests/ --cov=scripts --cov-report=term-missing
```

### 运行快速测试 (不依赖pytest)
```bash
python scripts/tests/quick_test.py
```

## 测试设计原则

1. **独立性**: 每个测试用例独立运行，不依赖其他测试
2. **隔离性**: 使用 `tmp_path` 创建临时目录，避免污染文件系统
3. **全面性**: 覆盖正常路径、边界情况和错误路径
4. **可读性**: 测试名称清晰描述测试目的
5. **可维护性**: 使用参数化测试和辅助函数减少重复代码

## 注意事项

- 测试使用 `tmp_path` fixture 创建临时目录，测试结束后自动清理
- Excel文件在Windows上可能被占用，测试中使用 `shutil.rmtree` 的 `ignore_errors=True` 参数
- 部分测试涉及文件编码 (UTF-8/GBK)，确保正确处理编码问题
