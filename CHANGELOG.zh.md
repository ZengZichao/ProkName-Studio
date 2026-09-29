# 变更日志

[English](CHANGELOG.md) | [中文](CHANGELOG.zh.md)

> 本文件是 [CHANGELOG.md](CHANGELOG.md) 的中文对照版，以英文原文为权威文本。

ProkName Studio 的所有重要变更都记录在此文件中。

格式遵循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/spec/v2.0.0.html)。

## [0.1.0] - 2026-09-29

**ProkName Studio** 的首个公开发布版，是
[prokname](https://github.com/ZengZichao/ProkName)（原核生物命名辅助引擎）的原生桌面
前端。Studio 把引擎在终端里的能力放进一个窗口：确定性的词源驱动命名生成、性数一致
校验、双法典（ICNP / SeqCode）路由与两级查重。

Studio 只是*前端*。它不重写任何命名规则：屏幕上的每个数字、裁定与徽标都来自 `prokname`
的公开 API。依赖是单向的——Studio 需要引擎，引擎永远不需要 Qt——并且它以包名与仓库 URL
表达这层依赖，绝不写成某台机器上的路径。

### 新增 —— 窗口

- **五个面板**：生成、路由、查重、项目、数据资产。每个面板都是「表单 + 一次引擎调用 +
  结构化结果渲染」——`engine.generate`、`engine.gender`、`engine.orthography`、
  `dedup.check_name`、`routing.route`、`storage.ProjectStore`、`presentation.decision`、
  `presentation.theme`。
- **推导树。** 引擎的 `derivation` 渲染为嵌套的步骤树
  （名称 → 合规 / 阶元 / 类别 / 性别 / 推导 / 警告），于是一个候选名「为什么是这样」变得
  可见，而不只剩那个字符串。合规以三色方案呈现，警告逐条列出。
- **查重裁定与其来源**渲染为一枚居中徽标，外加逐权威源的结果表与近似名清单，并标注所用
  扫描口径。「无法查证」与「未找到」在界面上长相不同，因为它们的含义不同。
- **路由路径**以路径卡呈现，每张带着该法典、它的角色与利弊对比，ICNP 先占与 GTDB 边界被
  摆到明面上而不是埋进注释。
- **项目工作跨界面延续**：候选名写入的是与 `prokname project` 同一个 `ProjectStore`，
  评分可就地录入，导出复用引擎的 JSON / CSV / Markdown 写出器，因此免责声明与
  LPSN / SeqCode 署名随文件一起带走。
- **数据资产面板**报告每个规则文件的版本、门控状态与消费方，也包括仍在等待专家签字的
  资产——不用读源码就能看见引擎当前的能力边界。

### 新增 —— 语言与外观

- **中文 / 英文即时切换**，无需重启、不丢内容：调色板、样式表、裁定徽标、表格前景色、
  占位文字、表头与提示全部跟随；会话里的候选名与当前选中项保持不变。`自动` 跟随系统
  区域设置，显式选择会被记住并跨启动生效，`--lang` 只影响本次运行且不写入任何东西。
- **亮暗外观切换**，同样是三个模式。引擎给出的每个语义色值都有暗色写法，每个都被提亮到
  相对暗底色达到 4.5:1 对比度；裁定徽标在暗底上变成带描边的淡色胶囊，而不是一块刺眼的
  实心亮色。外观与语言互不干扰：切换其一不会切换其二，两者都不重启窗口。
- **每条文案都被翻译**，包括进入界面的引擎词表（`adjective` → 形容词、
  `only-viable` → 唯一可行）。奇偶校验测试直接从源码读取词条表，只存在于单一语言的键、
  无人翻译的引用与空译文都会让它失败。
- **SVG 应用图标**：一份随应用打包的矢量文件，运行时按 16 px 到 512 px 栅格化并设为窗口
  图标。若 Qt 的 SVG 插件缺失，则改用同一几何形状绘制的降级字形，而不是平台的通用图块。

### 新增 —— 版本号与打包

- **自己的版本号。** `prokname-studio --version` 同时报告 Studio 版本与其所依据的引擎
  版本，关于框里两者都显示。版本只在 `src/prokname_studio/__init__.py` 声明一次：构建
  后端动态读取它，PyInstaller 描述回读该字面量而不是复制一份，`CITATION.cff` 镜像它——
  于是一个发布构建不可能带着三个互不相同的版本号。
- **冻结的 macOS 应用**，由 `ProkNameStudio.spec` 构建：onedir 包、按构建机架构冻结
  （`target_arch=None`，即 Apple Silicon 上的 arm64）、无控制台
  窗口、图标由 `scripts/make_bundle_icon.py` 从 SVG 生成，引擎的规则资产被自动收集进包而
  不是手工列举。生成的 `.icns` 刻意不入版本库：一份画稿，其余全部派生。
- 控制台入口命令 `prokname-studio`，与 `python -m prokname_studio` 等价。

### 行为与保证

- **只有一条线程规则。** 引擎计算在 worker `QThread` 上运行，该线程绝不触碰控件；重入
  受保护，因此第二次点击不可能启动第二次扫描；「把按钮还回去」的重置路径只有一处。引擎
  拒绝时会把异常类型一并报出，因为裸的 `str(KeyError)` 是空字符串。
- **本地优先、零网络。** Studio 不起 HTTP 服务、没有服务端。候选名只留在用户磁盘上，不
  收集也不上传任何输入，不存储任何凭据。联网开关以禁用态呈现，旁边写着你现在真正需要
  的东西——LPSN 需要凭据，SeqCode Registry 不提供按名查询——而不是一个过期的借口或一个
  不做解释的灰框。
- **裁定颜色属于引擎的 token。** `prokname.presentation.decision` 与 `.theme` 留在引擎，
  它们是终端与图形界面共用的「裁定—颜色」映射，因此同一个裁定不可能在终端里显得紧急、
  在窗口里显得平静。至于这些 token 在亮底或暗底上具体呈现为何种色调，那是 Studio 的决定，
  写在本仓库里。
- **`--debug`** 转发到 `prokname.diagnostics.configure()`，与引擎 CLI 的调用一致：回显
  引擎通常吞掉的第三方客户端输出，不改变任何裁定与退出码。
- 读取路径全部经过已安装的 `prokname` 发行包——项目存储、规则资产、查重缓存——绝不通过
  旁边的源码树。

### 质量门禁

- `tests/test_appearance.py`——模式解析、每个语义 token 的暗色写法，以及它在暗底上实测的
  对比度。
- `tests/test_icons.py`——SVG 加载与降级字形。
- `tests/test_spec.py`——打包描述能解析版本字面量，会拒绝冻结一个版本号可能与声明漂移的
  包，并确认资产确实进了包。
- `tests/test_i18n_parity.py`——两种语言的词条奇偶校验，直接从源码读取，因此无需 Qt 会话
  即可运行。
- `tests/test_boundaries.py`——Studio 可导入的引擎模块是一份固定契约，`prokname.cli` 绝不
  在其中；任何文档都不得写出只在一台机器上成立的路径。
- `tests/test_doc_language_pairs.py` 与 `tests/test_doc_links.py`——每份文档都以中英两份
  交付且英文在前，任何链接或锚点都不会指向空处。
- `tests/test_citation_metadata.py`——`CITATION.cff` 始终是版本字面量、作者、仓库 URL 与
  切版日期的镜像。
- 视图冒烟测试与 worker 契约测试**无条件运行**：PySide6 是运行期依赖，任何测试都不得以
  「缺 Qt」为由跳过。无法导入 Qt 的运行意味着安装已损坏，而被跳过的门控不是门控。CI 从
  JUnit XML 断言这一点，而不是去刮 stdout。
- CI 的 `bundle` 作业在 macOS 上构建 `.app`，校验冻结的 PYZ 模块集与 `src/` 相等，检查
  图标、引擎规则资产与 Qt SVG 插件确实进了包，最后真的把冻结窗口启动起来并要求它几秒后
  仍然存活。

### 已知限制

- Studio 继承引擎
  [变更日志](https://github.com/ZengZichao/ProkName/blob/main/CHANGELOG.md)里列出的全部
  限制，首先是规则资产仍待专家签字、`check` 目前还不能在实际场景中为名称放行。窗口不会
  把这几个事实说得软一些。
- 引擎的自由文本输出（推导与警告句子）由引擎负责翻译，不由 Studio 负责；引擎尚未本地化的
  字符串会按引擎写出的原样显示。
- 冻结分发在 macOS 上构建并验证，且按构建机的架构产出——发布的 `.app` 是 arm64。Intel
  Mac 由「从源码安装」覆盖。Windows 与 Linux 在 CI 中作为安装与测试目标被覆盖，
  不作为冻结包目标。
