# ProkName Studio —— 设计规格

[English](STUDIO_PLAN.md) | [中文](STUDIO_PLAN.zh.md)

> 本文是 [STUDIO_PLAN.md](STUDIO_PLAN.md) 的中文对照版，以英文原文为权威文本。
>
> 范围：[prokname](https://github.com/ZengZichao/ProkName) 原生桌面前端的设计。用户需要
> 据以行动的事实见 [README](../README.md) 与 [CHANGELOG](../CHANGELOG.md)，贡献规则见
> [CONTRIBUTING](../CONTRIBUTING.md)。本文解释的是这个前端*为什么*长成这样，好让后续
> 改动能被论证，而不是被猜测。
>
> 渲染层：**PySide6 (Qt)** —— 独立桌面应用，不依赖浏览器。平台：**保证 macOS**
> —— 从源码安装在 Apple Silicon 与 Intel 上都可用，而冻结的 `.app` 按构建机架构产出
> （当前是 arm64）；Windows 与 Linux 作为安装与测试目标覆盖。界面：**中/英
> 双语实时切换**与**亮暗外观切换**。

---

## 1. 定位

| 维度 | 决策 | 理由 |
|---|---|---|
| 角色 | **adoption 杠杆**，不是独立的研究贡献 | 让不常驻终端的微生物学家/分类学家用上引擎 |
| 形态 | **独立原生桌面应用** | 双击启动、独立窗口；PyInstaller 冻结，用户无需安装 Python |
| 能力 | **自身不产生任何能力** | 屏幕上每个数字、裁定与徽标都来自 `prokname` 的公开 API |
| 依赖方向 | **单向** | Studio 需要引擎，引擎永远不需要 Qt；依赖以包名与仓库 URL 表达，绝不以路径 |
| 技术栈 | **Python + PySide6 (Qt)** | 原生控件、跨平台、LGPL 对 MIT 项目友好、易冻结为 macOS `.app` |
| 隐私 | **完全本地、零网络** | 命名优先权敏感；无服务端的桌面应用不可能把候选名发出去 |
| 平台 | **保证 macOS** | 用户主力在 macOS；其它平台在 CI 中被支持，但不做冻结分发 |
| 界面语言 | **中/英实时切换** | 默认跟随系统区域设置，同时服务国内外用户 |
| 外观 | **亮/暗实时切换** | 同一个裁定在任一底色上都必须可读 |

**为什么是 Qt 而不是网页 UI。** 由浏览器渲染的 UI 不满足「不依赖浏览器」这一硬性要求，
而把 WebView 装进一个窗口（Tauri、Electron）底层依然是浏览器引擎。Qt 直接绘制操作系统
的**原生控件**，因此严格意义上就是桌面应用；并且 `QTableWidget`、`QTreeWidget`、
`QTextBrowser` 正好是候选表、推导树与查重裁定需要的形态。代价是比 Web 框架多写布局与
事件代码——这是「可独立分发的软件」必然要付的价格。

---

## 2. 设计原则

1. **引擎是唯一真相。** Studio 调用 `prokname` 的公开 API 并渲染其返回。规则变更发生在
   引擎里，这里自动继承；在这里重写一条规则，等于制造一条可能与终端不一致的规则。
2. **可审计性就是可见的产品。** 引擎的 `derivation`、`warnings`、`compliant` 被画出来
   ——步骤树 + 三色合规徽标——因为把「为什么」变得可见，是前端相对 CLI 的全部增量价值。
3. **裁定绝不被说软。** `unavailable` 与 `not_found` 在界面上长相不同；免责声明随结果
   一起走；数据资产面板显示哪些规则仍在等待专家签字。
4. **渐进披露。** 普通用户看到一个表单和一个答案。推导树、扫描口径开关、性别覆盖可以
   抵达，但不喧哗。
5. **本地优先、零网络。** 不起 HTTP 服务、没有服务端、不做遥测。`ProjectStore` 的本地
   JSON 是数据唯一的落点。
6. **两种语言，一处词条来源。** 每条 UI 文案必须同时存在于两张表，否则测试失败；文档
   适用同一条规则。
7. **只有一条线程规则。** 引擎计算在 worker `QThread` 上运行；`QThread` 绝不触碰控件。

---

## 3. 结构

```
src/prokname_studio/
├── __init__.py            # __version__（唯一真源）、MIN_PROKNAME_VERSION
├── __main__.py            # python -m prokname_studio
├── app.py                 # 参数解析、QApplication 引导
├── launcher.py            # PyInstaller 入口
├── main_window.py         # 导航、开关栏、关于框
├── state.py               # StudioState：各视图共享的会话
├── i18n.py                # 中英词条表与语言信号
├── appearance.py          # 亮暗调色板与应用样式表
├── icons.py               # SVG 加载、运行时栅格化、降级字形
├── worker.py              # QThread 契约与重入保护
├── assets/icon.svg        # 其余一切由此派生的唯一画稿
├── views/                 # gen_view · route_view · check_view · project_view · data_view
└── components/            # derivation_view · verdict_view · project_table
```

本项目可导入的引擎模块是一份**固定契约**（`tests/test_boundaries.py`）。`prokname.cli`
不在其中：命令行入口不是 API。没有任何代码读取引擎的源码树。

**会话状态**（`state.py`）持有当前候选名列表、所选项目与最近一次裁定。全部是派生数据
——重读引擎即可重建——这里不持久化任何规则。`projects_changed` 信号保证某个视图写入
存储之后，项目视图依然如实。

---

## 4. 五个视图

### 4.1 生成

`generate(stem, type, rank, genus=None, person_gender=None, gender_override=None,
genus_suffix=None, adjective_formation=None)`。

- 输入：词干（必填）、词源类型、阶元，以及阶元需要时的属名；`person_gender` 只在
  `type=person` 时出现，属名性别覆盖只在属名已填后出现。高级字段收在可折叠分组里。
- 输出：候选表（名称、类别、性别、合规、推导）加上**推导树**——这才是这个面板的意义：
  *Beijing → 地名形容词 → 随属名性别变格 → 中性 Rhizobium ⇒ -ense ⇒
  Rhizobium beijingense*。合规以绿/黄/红呈现，警告逐条列出。
- 「加入项目」通过 `ProjectStore` 写入选中的候选。

### 4.2 路由

`route(source, candidatus=False, icnp_occupied=None)`。

路径卡，每条可行法典路径一张，各自显示法典、角色与利弊对比。警告与说明——ICNP 先占、
GTDB 边界——以陈述句呈现，不塞进 tooltip。名称已被占用的情形下，引导被高亮，而不是被
呈现成死路。

### 4.3 查重

`check_name(name, online=False, near_match=True, max_distance=2, near_match_mode="whole")`。

- 输入：名称、扫描口径（whole / stem / both）、最大距离、联网开关。
- 输出：裁定徽标、逐权威源结果表（`found*` 与 `not_found` 一眼可辨）、按所用口径标注的
  近似名清单。
- 联网开关以禁用态呈现，旁边写着真正的原因——LPSN 需要凭据，SeqCode Registry 不提供按名
  查询——而不是一个不解释的灰框。

### 4.4 项目

`ProjectStore` 的 create / load / list / add_candidate / rate_candidate / export / delete。

项目列表、带 0–5 就地评分的候选表、一键导出。导出复用引擎的写出器，因此免责声明与
LPSN / SeqCode 署名在 Studio 看到文件之前就已经在文件里了。

### 4.5 数据资产

`data_assets.asset_status()`——每个规则资产的版本、门控状态与消费方，以及仍等待专家
核验的断言条数。这个面板的存在理由，是让引擎当前的能力边界不读源码也能看清。

---

## 5. 国际化

- `i18n.py` 里的 `STRINGS = {"zh": {...}, "en": {...}}` 是所有 UI 可见字符串的**唯一
  来源**；视图通过 `tr(key)` 取串。
- `install(app, lang)` 由桌面 `QLocale` 解析 `auto`；中文系映射到 `zh`，其余默认 `en`。
- `set_language(lang)` 发出 `languageChanged`；主窗口就地重译每个控件。切换是即时的：
  不重启、不丢候选名、不丢当前选中项。
- 范围边界：引擎的自由文本输出由引擎负责本地化。引擎尚未翻译的字符串按引擎写出的原样
  显示，不在这里改写。
- `tests/test_i18n_parity.py` 直接从源码读取词条表，只存在于单一语言的键、无人翻译的
  引用与空译文都会让它失败，因此半个界面的翻译无法被发布。

---

## 6. 外观

- 三个模式：跟随系统、固定亮色、固定暗色。`auto` 在系统切换配色的瞬间重新应用；显式
  选择会被存储；`--theme` 只影响本次运行且不写入任何东西。
- 引擎的语义色值 token 是相对亮底定义的。在暗底上每个都被**提亮**（`appearance.py`），
  且每个提亮值都必须相对暗底色达到 4.5:1 对比度——这是测试，不是肉眼看。
- 暗底上的裁定徽标变成带描边的淡色胶囊，而不是一块实心亮色；表格前景色与被抑制的占位
  文字遵循同一映射。
- 外观与语言是两个互不干扰的开关，谁都不打扰谁，也不动会话。

---

## 7. 线程

契约由 `worker.py` 持有：引擎调用在 `QThread` 上运行，结果通过信号送回 UI，worker 绝不
触碰控件。重入受保护，因此第二次点击不可能启动第二次扫描，而「把按钮还回去」的重置只
存在一处。引擎拒绝时会把异常类型一并报出，因为裸的 `str(KeyError)` 是空字符串，而一个
空的错误框什么也教不会用户。

---

## 8. 图标与打包

- **一份矢量文件** `assets/icon.svg` 随 wheel 发布。`icons.py` 在运行时按 16 px 到
  512 px 栅格化并设为窗口图标；若 Qt 的 SVG 插件缺失，改用同一几何形状绘制的降级字形，
  而不是平台的通用图块。
- 外壳图标 `ProkNameStudio.icns` 是**构建产物**，由 `scripts/make_bundle_icon.py` 从
  SVG 生成。把它纳入版本控制就等于放第二份画稿进去，而且没有任何东西保证两者同步。
- `ProkNameStudio.spec` 构建 onedir 的 `.app`，`windowed`，并按构建机架构冻结
  （`target_arch=None`）。它从
  `__init__.py` 读取版本而不是复制一份，因此 `Info.plist`、`--version` 与关于框不可能
  互相矛盾；并且当数据资产未能解析时，它拒绝冻结出一个坏包。
- 引擎的规则资产通过 `collect_data_files` 随包走，而不是靠手工清单：往
  `src/prokname/data/` 新增一个资产，不应该要求这里同步改一笔才能出现在应用里。
- CI 构建包之后，校验冻结的模块集等于 `src/`，校验图标、引擎资产与 Qt SVG 插件确实在
  物理上位于包内，最后真的把冻结窗口启动起来，并要求它几秒后仍然存活。

---

## 9. 分发

`.app` 通过 GitHub Releases 提供；非技术用户把它拖进 Applications。明确**不做**只读的
托管网页 demo：那会把候选名放上一台服务器，而这正是这个前端存在要避免的事。
notarization 是可选项，只用于消除「未知开发者」提示。

---

## 10. 测试

前端不重写规则，因此不重复引擎的测试；它测这层壳：

- **视图冒烟**（`test_views_smoke.py`、`test_ui_polish.py`）——每个视图都能在离屏 Qt 下
  构造、关键控件存在、生成能产出候选、引擎调用是 await 而非阻塞线程。
- **状态**（`test_state.py`）——共享会话的读、写与重置。
- **契约**（`test_worker_contract.py`、`test_decision.py`）——Studio 从引擎读回的字段必须
  与引擎公布的一致；裁定只能落到它被取得时查询的那个名称上。
- **表现层**（`test_appearance.py`、`test_icons.py`、`test_i18n.py`、
  `test_i18n_parity.py`）——模式解析、对比度、降级字形、词条奇偶校验。
- **结构**（`test_boundaries.py`、`test_spec.py`、`test_asset_freshness.py`、
  `test_citation_metadata.py`、`test_doc_language_pairs.py`、`test_doc_links.py`、
  `test_no_iteration_residue.py`）——导入契约、打包描述、文档语言配对、可解析的链接，
  以及迭代残留。

**任何测试都不得以「缺 Qt」为由跳过。** PySide6 是运行期依赖，无法导入 Qt 的运行意味着
安装已损坏；CI 解析 JUnit XML，只要有任何用例因 Qt 原因跳过就判红。被跳过的门控不是门控。

---

## 11. 风险

| 风险 | 缓解 |
|---|---|
| 原生 GUI 代码比 Web UI 重 | 视图保持薄：表单 → 一次调用 → 渲染。复杂交互控制在五个面板内。 |
| 引擎 API 变更打破窗口 | 契约测试与 CI 冒烟先于用户变红。 |
| 两张词条表漂移 | 奇偶校验测试读源码并判失败；CI 无条件运行它。 |
| 暗底让裁定不可读 | 每个 token 都有实测的暗色写法与对比度断言。 |
| 冻结包漏带资产 | 打包作业比对冻结模块集与 `src/`，并逐个检查磁盘上的文件。 |
| 在引擎拿到专家签字之前过度投入 GUI | Studio 不新增规则。面板呈现引擎已经决定的东西，包括它拒绝决定的东西。 |

---

## 12. 已确定的决策

1. **语言**：中英双语、即时切换、默认跟随系统。
2. **项目存储**：沿用引擎 `ProjectStore` 的默认目录；Studio 不自定义路径。
3. **范围**：本仓库永不承载命名逻辑。
4. **平台**：macOS 做冻结与冒烟；Windows 与 Linux 做安装与测试。
5. **主题**：亮暗两套，默认跟随系统。

---

## 附录 —— 本前端调用的引擎 API

```python
from prokname.engine.generate import generate          # 由词源生成候选名
from prokname.engine.gender import get_genus_gender    # 词表查找 + 词尾推断
from prokname.engine.orthography import validate_agreement
from prokname.dedup import check_name, Verdict         # 两级查重报告
from prokname.routing import route, RouteSource        # 双法典路径 + 利弊
from prokname.storage import ProjectStore, Candidate   # 会话编辑的项目
from prokname.engine import data as data_assets        # 资产版本与门控状态
from prokname.presentation import decision, theme      # 裁定 → 颜色契约
from prokname import __version__, DISCLAIMER           # 关于框所报告的内容
```

这里每个签名都在测试期与已安装的 `prokname` 发行包核对；引擎若重构，契约测试会先报出来。
