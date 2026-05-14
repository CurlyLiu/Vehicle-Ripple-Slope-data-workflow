# Changelog / 更新日志

All notable changes to this project will be documented in this file.
所有 notable 的更改都将记录在此文件中。

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/).

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [4.4.0] - 2026-05-11

### Fixed / 修复

- 🔥 **SOC 编码统一为全角** (P1.1) — condition_matcher.py:332-336 模糊评分原使用半角 `>=70%/<=40%`,而生产代码 vehicle_processor.py:770-779 输出全角 `≥70%/≤40%`,导致 SOC 加分永不命中。同步修复 validate_cross_format.py:435 的 SOC dict 与 7 个测试 fixture 文件。
- 🔥 **CR-N4: stage4 import 前 DELETE** — core.py:import_vehicle 增加 import 前 `DELETE FROM ripple_results/slope_results WHERE vehicle_id = ?`,避免减行重导留孤儿数据。
- 🔥 **NEW-1: update.py 原子性修复** — 3 个 importer (json/excel/sqlite) 内部去掉 `conn.commit()`,改由外层 `with DatabaseConnection` 统一控制,确保 `_delete_vehicle + import_vehicle` 在同一事务内的原子性。
- 🔥 **CR-N7: add.py exit 码传播** — add.py 末尾按 success_count 区分 exit 0 (全部成功) / 2 (完全失败) / 3 (部分失败),orchestrator 识别 partial 状态时不更新 cache,避免静默污染。
- 🔥 **CR-N8: _save_cache 原子写 + .bak** — tmp+rename + fsync 防止中途崩溃损坏 cache;_load_cache 损坏时尝试 .bak 恢复。
- 🔥 **CR-N9: batch_log 增量写 + try/except** — 每辆车完成后立即原子写 `.workflow_batch_log.json` (partial=true),避免 batch 中途崩溃丢失全部结果;单车循环 try/except 包裹,异常不中断整批。
- 🔥 **HR-N5: 模板字节相同警告** — 验证发现 ripple/slope 模板 sha256 完全相同 (后续需重制 slope 模板,待用户提供阈值)。

### Changed / 变更

- 🚀 **P1.4a: 新增 `_output_paths(stage)` 方法** — 从 `~/.vehicle_database/config.json` 动态解析 DB 目录,不再依赖硬编码。
- 🚀 **P1.4b/c: stage4 single-flight + 二次规划** — 全局 DB 缺失时单 batch 内仅触发一次重 import;stage2 完成后自动二次规划挂入新出现的 stage3/4。
- 🚀 **P1.3: Stage3 章节标题+表头改写** — 基类 `_rewrite_titles_and_headers` 跨 run 重建段落文本,处理 python-docx run 拆分陷阱。
- 🚀 **P1.5: vehicle_info 纳入指纹** — stage2 输入新增 `vehicle_info.md/xlsx`,修改车型信息会触发重跑。
- 🚀 **CR-N2: 语义指纹** — vehicle_info 走 `_semantic_fingerprint`,xlsx 用 openpyxl cell hash 屏蔽 zip metadata 差异,md 规范化换行,避免误报变更。
- 🚀 **P1.6: cache schema version** — `_schema_version: 2` 标记,旧 cache 加载时打印 INFO 升级提示。
- 🚀 **P1.10/NEW-3: stage1 manual_required 不写 cache** — status 改为 `"manual_required"` 而非 `"success"`,避免虚假完成标记污染。
- 🚀 **P1.2: validator sentinel upsert** — validate_cross_format.py 用 HTML 注释 sentinel 包裹校验块,反复执行不再累积重复内容。
- 🚀 **CR-N5/P2.6: xpp marker 9-tuple** — vehicle_processor.py 扩展到 9-tuple 覆盖 `IPP/VPP/XPP` 全大写。
- 🚀 **NEW-4: scan_vehicles 严格正则** — `re.fullmatch(r'V\d+', name)` 避免匹配 `V0001abc/V0001.backup` 等非标准目录。
- 🚀 **NEW-7: 非组件文件警告** — vehicle_processor 检测到 zip/rar/docx 等可疑文件给出 warning。
- 🚀 **HR-N7/P2.10: vehicle_info md/xlsx mtime 警告** — 两者都存在且 mtime 差异 > 60s 时打印 [WARN]。
- 🚀 **HR-N8/P2.11: datetime 全部 UTC** — incremental_workflow.py 13 处 `datetime.now()` 改为 `datetime.now(timezone.utc)`。
- 🚀 **P2.8/CR-N11: vehicle_info* 旧版警告** — batch 启动预检 `vehicle_info1.xlsx` 等非标命名,提醒用户检查。
- 🚀 **P0: DB 迁移到 `F:/Vehicle_Database/`** — 多字段同步 (顶级 `database_path` + 嵌套 `database.default_path`)。

### Notes / 备注

- 升级后**首次 batch 会触发全部车辆 stage2 一次性重跑** (因为 vehicle_info 纳入指纹改变了 fingerprint 计算),这是预期行为,预估总耗时 4-6 分钟。
- slope_report_template.docx 是 ripple 副本(内容错误),需后续重制 (待 slope 阈值确认)。
- 对齐 plan smooth-sniffing-newt.md V3.5 实现。

## [4.3.0] - 2025-04-03

### Added / 新增

- ✨ **Unified CLI Tool** (`vehicle_skills_cli.py`) - Single command for ripple and slope data
  - 统一CLI工具 - 单一命令处理纹波和斜率数据
  - Commands: `process`, `batch`, `validate`, `version`
  - 命令：处理、批量、验证、版本
- 📊 **Progress Display** - Visual progress bars with real-time status
  - 进度显示 - 可视化进度条和实时状态
- 🔧 **Enhanced CLI Arguments** - Support for `--progress`, `--output`, `--workers`
  - 增强CLI参数 - 支持进度条、输出目录、工作进程数
- 📝 **Bilingual Documentation** - English and Chinese README
  - 双语文档 - 中英文README

## [4.2.0] - 2025-04-01

### Added / 新增

- 🎯 **Configuration-Driven Architecture** - All settings managed via YAML files
  - 配置驱动架构 - 所有设置通过YAML文件管理
  - `config/common/vehicle_fields.yaml` - 14 standard vehicle fields
  - `config/common/matching_rules.yaml` - Fuzzy matching rules
  - `config/common/styles.yaml` - Excel styling
  - `config/ripple/excel_template.yaml` - Report template

- 🔍 **4-Level Fuzzy Matching** - Smart condition name matching
  - 四级模糊匹配 - 智能工况名称匹配
  1. Exact match / 精确匹配
  2. Normalized match (bracket removal) / 规范化匹配（去括号）
  3. Fuzzy match (Levenshtein distance) / 模糊匹配（编辑距离）
  4. Feature match (handles GBK encoding) / 特征匹配（处理GBK编码）

- 🖼️ **Absolute Image Paths** - Store absolute paths for reliability
  - 绝对图片路径 - 存储绝对路径以确保可靠性
  - JSON, Excel, SQLite all use absolute paths
  - JSON、Excel、SQLite均使用绝对路径

- 🚀 **Hot-Reload Configs** - No restart needed after config changes
  - 热重载配置 - 修改配置后无需重启
  - Automatic file change detection
  - 自动检测文件变化

### Changed / 变更

- ♻️ **Refactored Core Processor** - Modular architecture with clear separation
  - 重构核心处理器 - 模块化架构，清晰分离
  - Separated config loading, data processing, and report generation
  - 分离配置加载、数据处理和报告生成

### Fixed / 修复

- 🐛 **SQLite Column Issue** - Added automatic column migration for image_path
  - SQLite列问题 - 添加image_path列的自动迁移
- 🔤 **Encoding Issues** - Better handling of GBK/UTF-8 mixed encodings
  - 编码问题 - 更好地处理GBK/UTF-8混合编码

## [4.1.0] - 2025-03-15

### Added / 新增

- 📈 **Excel V3.0 Format** - Enhanced Excel reporting with better formatting
  - Excel V3.0格式 - 增强的Excel报告格式
- 🎨 **Cell Styling** - Support for conditional formatting and custom styles
  - 单元格样式 - 支持条件格式和自定义样式
- 📊 **Component Summary** - Automatic component statistics in Excel
  - 组件摘要 - Excel中自动组件统计

### Fixed / 修复

- 🐛 **Image Matching** - Improved image-to-condition matching accuracy
  - 图片匹配 - 改进图片与工况匹配准确性
- 📝 **Report Generation** - Fixed markdown report formatting issues
  - 报告生成 - 修复Markdown报告格式问题

## [4.0.0] - 2025-03-01

### Added / 新增

- 🎉 **Initial Configuration-Driven Release**
  - 初始配置驱动版本发布
- 🔄 **Incremental Processing** - Support for resuming interrupted processing
  - 增量处理 - 支持恢复中断的处理
- 📁 **Multi-Format Output** - JSON, Excel, SQLite, Markdown reports
  - 多格式输出 - JSON、Excel、SQLite、Markdown报告

### Changed / 变更

- ♻️ **Complete Rewrite** - Migrated from hard-coded to configuration-driven
  - 完全重写 - 从硬编码迁移到配置驱动

## [3.x.x] - 2024 (Legacy)

Legacy hard-coded version with limited flexibility.
旧版硬编码版本，灵活性有限。

---

## Version Format / 版本格式

Given a version number `MAJOR.MINOR.PATCH`, increment the:
给定版本号 `MAJOR.MINOR.PATCH`，按以下规则递增：

1. **MAJOR** - Incompatible API changes / 不兼容的API更改
2. **MINOR** - Added functionality (backwards compatible) / 新增功能（向后兼容）
3. **PATCH** - Bug fixes (backwards compatible) / 错误修复（向后兼容）

## Categories / 分类

- ✨ `feat` - New features / 新功能
- 🐛 `fix` - Bug fixes / 错误修复
- 📚 `docs` - Documentation / 文档
- 💎 `style` - Code style / 代码样式
- ♻️ `refactor` - Refactoring / 重构
- ⚡ `perf` - Performance improvements / 性能优化
- ✅ `test` - Tests / 测试
- 🔧 `chore` - Build/tooling / 构建/工具

---

<div align="center">

**[View Full Documentation](./README.md) | [查看完整文档](./README.md)**

</div>
