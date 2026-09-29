# ProkName Studio 贡献指南

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh.md)

## 核心原则

**Studio 不新增任何命名逻辑。** 屏幕上的每个裁定、候选名、徽标与颜色都必须来自对
`prokname` 公开 API 的一次调用。在这里重新实现一条规则，就等于制造一条可能与终端
不一致的规则——而两个界面之所以共用同一张映射表，正是为了不让它们不一致。

如果您认为某个视图需要新的计算，那个改动属于
[引擎仓库](https://github.com/ZengZichao/ProkName)，不属于 `views/`。

## 边界

- `tests/test_boundaries.py` 固定了 Studio 可导入的引擎模块集合。新增一项是有意为之的
  动作：它意味着引擎从此必须为 Studio 维持该项契约。
- Studio **绝不**导入 `prokname.cli`。命令行入口不是 API。
- 任何代码都不读取引擎的源码树。依赖以包名（`prokname>=0.1.0`）与仓库 URL 表达，
  绝不写成只在一台机器上成立的同级目录路径。

## 界面规则

- **每条文案都要翻译。** 新增界面文字意味着在 `i18n.py` 的**两张**词条表里各加一个键；
  只存在于单一语言的键、无人翻译的引用、空译文，都会被
  `tests/test_i18n_parity.py` 判为失败。
- **裁定颜色属于引擎的 token，不属于 Studio。** 语义 token 与“裁定—角色”映射来自
  `prokname.presentation.decision`。Studio 只决定同一个 token 在亮底与暗底上分别呈现
  为何种色调（`appearance.py`），且暗底上被提亮的每个色值都必须相对暗底色达到 4.5:1
  对比度。
- **只有一条线程规则。** 引擎计算在 worker `QThread` 上运行；`QThread` 绝不触碰控件。
  重入保护写在 `worker.py`，因此第二次点击 Run 不会启动第二次扫描。

## 文档语言

**英文文档为主，中文文档为伴。** 每个成文文件都以 `NAME.md`（英文）加 `NAME.zh.md`
（中文）两份交付，顶部写明 `[English](…) | [中文](…)` 且英文在前。当文档引用上游原文
（许可页脚、API 响应）时，两份副本中的引文都保留其原始语言，且以英文文件为权威版本。

`docs/STUDIO_PLAN.md` 是设计规格：它解释这个前端为什么长成这样。用户据以行动的活文档是
`README` 与 `CHANGELOG`，两者都不会指向本仓库旁边的某个文件夹。

## 测试

```bash
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest            # 全套
QT_QPA_PLATFORM=offscreen python -m pytest -v tests/test_appearance.py
```

- **PySide6 是运行期依赖，因此任何测试都不得以“缺 Qt”为由跳过。** 无法导入 Qt 的运行
  意味着安装已损坏，而被跳过的门控不是门控。CI 会解析 JUnit XML，只要有任何用例因 Qt
  原因跳过就判红。
- 在无显示的 runner 上需要 `QT_QPA_PLATFORM=offscreen`，否则 `QApplication` 起不来。
- `tests/test_asset_freshness.py` 与 `tests/test_spec.py` 守护图标资产与打包描述；
  `tests/test_citation_metadata.py` 把 `CITATION.cff` 当作 `__version__` 的镜像来守护。

## 打包

`ProkNameStudio.icns` **不入版本库**。它由 `scripts/make_bundle_icon.py` 从
`src/prokname_studio/assets/icon.svg` 派生而来——把同一份画稿的第二副本纳入版本控制，
就等于多出一件需要人工保持同步的东西。CI 的 `bundle` 作业会先生成它、构建 `.app`，
随后校验冻结的 PYZ 模块集与 `src/` 一致，并确认图标与引擎规则资产真的进了包。

## 版本号

版本只在 `src/prokname_studio/__init__.py` 声明一次。`pyproject.toml` 保持
`dynamic = ["version"]`，PyInstaller 描述读取该字面量，`CITATION.cff` 镜像它。
改动时只 bump 那一行，然后同步 CFF 的两处镜像——上面的测试会在它们漂移时判红。
Studio 的版本号属于它自己；引擎版本在运行时读取，除 `MIN_PROKNAME_VERSION` 这个下界
之外不在这里硬编码。

## 议题该提到哪里

引擎问题（性别判断有误、权威来源不可达、规则资产需要专家评审）请提到
[引擎的 issue 列表](https://github.com/ZengZichao/ProkName/issues)；
界面、翻译、外观与打包问题请提到[这里](https://github.com/ZengZichao/ProkName-Studio/issues)。

## 绝不

将 API 凭据、密码或令牌提交进仓库。Studio 不存储任何此类东西：它是本地优先的，
凭据处理由引擎负责。
