<p align="center">
  <img src="src/prokname_studio/assets/icon.svg" width="128" height="128" alt="ProkName Studio">
</p>

# ProkName Studio

[English](README.md) | [中文](README.zh.md)

**[prokname](https://github.com/ZengZichao/ProkName)（原核生物命名辅助引擎）的原生桌面前端**：确定性的词源驱动命名生成、性数一致校验、双法典（ICNP / SeqCode）路由与两级查重——把终端里的能力放进一个窗口。

**天生双语、双色调**：界面可在中文与英文之间即时切换，也可在亮色与暗色之间切换，无需重启。

Studio 只是*前端*。它不重写任何命名规则：屏幕上的每个数字、裁定与徽标都来自 `prokname` 的公开 API。依赖是单向的——Studio 需要引擎，引擎永远不需要 Qt。

---

## 目录

1. [安装](#安装)
2. [启动](#启动)
3. [窗口能做什么](#窗口能做什么)
4. [语言与外观](#语言与外观)
5. [图标](#图标)
6. [开发](#开发)
7. [Studio 与 prokname 的关系](#studio-与-prokname-的关系)
8. [引用](#引用)
9. [许可](#许可)

## 安装

Studio 依赖 `prokname` 发行包。该包尚未发布到 PyPI，因此先从其源码仓库安装引擎，再安装本前端：

```bash
# 1. 引擎（同时装上它自己的运行依赖 typer + rich）
pip install "git+https://github.com/ZengZichao/ProkName.git"

# 2. 本前端（会拉取 Qt 绑定 PySide6）
pip install "git+https://github.com/ZengZichao/ProkName-Studio.git"
```

若已克隆本仓库，第 2 步可写为 `pip install -e .`；其中 `prokname` 依赖同任何普通依赖一样，由发布渠道解析。本项目没有任何代码读取引擎的源码树。

环境要求：Python ≥ 3.11（已测 3.11–3.14）、经 PySide6 提供的 Qt 6.7+，以及一个桌面会话（macOS / Windows / Linux X11 或 Wayland）。

## 启动

```bash
prokname-studio                 # 界面语言与外观都跟随系统
prokname-studio --lang zh       # 强制中文界面
prokname-studio --lang en       # 强制英文界面
prokname-studio --theme dark    # 仅本次运行；工具栏里的选择会被记住
prokname-studio --help
prokname-studio --version       # 同时打印 Studio 与引擎的版本
```

`python -m prokname_studio` 与上述命令等价。`--debug` 会把引擎通常吞掉的第三方客户端输出回显到 stderr，不改变任何裁定与退出码。

## 窗口能做什么

五个面板，每个都是引擎某一部分的薄前端：

| 面板 | 引擎调用 | 内容 |
|---|---|---|
| **生成** | `generate()` | 由词干产出候选名，附语法类别、性别、合规判定与逐步推导 |
| **路由** | `route()` | 按来源类型给出可行发表路径（ICNP、SeqCode 或两者）及其角色与利弊 |
| **查重** | `check_name()` | 查重结论、各权威来源结果与近似匹配 |
| **项目** | `ProjectStore` | 建项目、收集候选名、评分、导出 JSON / CSV / Markdown |
| **数据资产** | `engine.data.asset_status()` | 引擎正在使用的规则资产、版本与评审状态 |

两条从 CLI 继承的诚实性保证，也正是这套工具的意义所在：

- **没能做出的查证，绝不会被报成干净名字。** Studio 只做离线查证：LPSN 需要凭据与网络，SeqCode 注册中心没有按名查询能力。因此“无明确冲突”只意味着“在我够得着的范围里没有”，窗口在显示该结论处也如此说明。要拿到可联网的答案，请在终端执行 `prokname check --online`。
- **建立在推理之上的合规勾选会表明自己是推理。** 若属名性别来自词尾启发式而非词库或专家覆盖，“合规”单元格会显示为待审，而不是绿色对勾。

## 语言与外观

两者都是顶栏里的下拉开关，选择立即生效。

**语言**——`自动` 跟随系统区域设置；`中文` 与 `English` 为固定选择。所有文案都翻译，包括引擎返回值（`adjective` → 形容词、`only-viable` → 唯一可行）。若某个键只存在于一种语言、或某个视图引用了无人翻译的键，奇偶校验测试会失败。

**外观**——`跟随系统`（默认）、`亮色`、`暗色`。`跟随系统` 会在操作系统于明暗之间切换时重新读取桌面配色方案，Studio 随之改变而无需重启。显式选择会写入系统原生的偏好存储（macOS：`~/Library/Preferences` 下的 plist；Windows：注册表），下次启动仍然有效；`--theme` 只影响单次运行，不写入任何内容。

两个开关互不干扰：切到暗色不会切换语言，任何一项都不会重启窗口或丢失当前会话的候选名。

## 图标

`src/prokname_studio/assets/icon.svg` 既是美术原件也是唯一事实来源：一个矢量文件随应用打包，运行时再栅格化为 16 px 工具栏图标直到 512 px 窗口徽标。若 Qt 的 SVG 插件缺失（精简的 Qt 安装，或未打包 `imageformats/qsvg` 的冻结构建），程序会退回到用同一几何形状绘制的简化徽标，而不是使用平台的通用应用图标。

*安装包*外壳图标是另一件产物——macOS 需要 `.icns`，Windows 需要 `.ico`——它由 SVG 派生，绝不另画一份：

```bash
python scripts/make_bundle_icon.py          # 生成 ProkNameStudio.icns
python scripts/make_bundle_icon.py --check   # 缺失？还是比 SVG 旧？
```

脚本用项目已有的 PySide6 栅格化 SVG（不必再装 `rsvg-convert` 或 Inkscape），并按 `iconutil` 要求的尺寸打包。`.icns` 属于构建产物，不入库；`ProkNameStudio.spec` 在它存在时嵌入，缺失时照常构建并打印提示。CI 会在打包作业前先生成它，因此发布的 `.app` 不会带着平台通用图标出门。

## 开发

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "git+https://github.com/ZengZichao/ProkName.git"   # 引擎
pip install -e ".[dev]"                                        # Studio + pytest、pytest-qt、ruff

pytest                         # 整套测试（Qt 离屏）
QT_QPA_PLATFORM=offscreen pytest
ruff check src tests conftest.py
```

目录结构：`src/prokname_studio/` —— `app.py`（入口与参数解析）、`appearance.py`（亮暗调色板与样式表）、`i18n.py`（中英词条表与语言信号）、`icons.py`（SVG 加载与降级徽标）、`main_window.py`（导航与开关栏）、`state.py`（视图共享的会话状态）、`views/`（五个面板）、`components/`（面板组合使用的控件）。

贡献规则——导入边界、双语词条奇偶校验、线程规则与打包约定——见
[CONTRIBUTING.zh.md](CONTRIBUTING.zh.md)（[English](CONTRIBUTING.md)）。

改动之前值得先了解的测试：

- `tests/test_appearance.py`——模式解析、每个语义色值的暗色拼写及其在暗底上的对比度、实时切换是否真的抵达徽标/表格前景/占位文字，以及什么会被持久化、什么只属于单次运行。
- `tests/test_i18n_parity.py`——直接从源码读取词条表，因此无需 Qt 会话即可揪出单语键、无人翻译的引用与空译文。
- `tests/test_icons.py`——打包的 SVG 结构合法、当前环境能渲染、承诺的每个尺寸都存在、降级徽标不是空白方块。
- `tests/test_spec.py`——以桩件 `exec()` PyInstaller spec，检查它派生版本号、收集两个包的数据资产，并在资产树缺失时拒绝构建。

本套件里没有 `pytest.importorskip("PySide6")`。PySide6 是本包的运行时依赖，导入不了就是安装坏了；把这种情况报成“跳过即通过”正是本仓库拒绝的失败模式。

冻结桌面应用（macOS `.app`、Windows `.exe`）是发布环节：

```bash
pip install -e ".[build]"
pyinstaller ProkNameStudio.spec --noconfirm
```

## Studio 与 prokname 的关系

| | |
|---|---|
| 依赖 | [`prokname`](https://github.com/ZengZichao/ProkName)——在 `pyproject.toml` 中声明为 `prokname>=0.1.0` |
| 导入 | 引擎公开 API：`engine.generate`、`engine.gender`、`engine.orthography`、`dedup.check_name`、`routing.route`、`storage.ProjectStore`、`presentation.decision`、`presentation.theme` |
| 绝不导入 | `prokname.cli`（命令行入口不是 API）；本项目也没有任何代码读取引擎的源码树 |
| 自己负责 | 窗口、中英词条、亮暗调色板、图标、PyInstaller 打包 |
| 报告 | 两个版本号：`prokname-studio --version` 同时给出 Studio 版本与其运行所依据的引擎版本 |

引擎问题（性别判断有误、权威来源不可达、规则资产需要专家评审）请提到[引擎的 issue 列表](https://github.com/ZengZichao/ProkName/issues)；界面、翻译、外观与打包问题请提到[这里](https://github.com/ZengZichao/ProkName-Studio/issues)。

## 引用

若您使用 ProkName Studio，请引用本软件（[`CITATION.cff`](CITATION.cff)）：

- **Zichao Zeng**（ORCID [0000-0001-6553-970X](https://orcid.org/0000-0001-6553-970X)）

Studio 只是前端，屏幕上呈现的命名工作属于引擎，因此方法学引用应同时指向
[prokname](https://github.com/ZengZichao/ProkName) 及其
[`CITATION.cff`](https://github.com/ZengZichao/ProkName/blob/main/CITATION.cff)。
`prokname-studio --version` 会同时打印两个版本号，这正是复现一张界面截图所需的信息。

## 许可

MIT，见 [LICENSE](LICENSE)。Studio 展示的规则资产属于引擎，沿用引擎的数据条款。
