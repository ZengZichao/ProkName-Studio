"""Minimal bilingual (zh/en) i18n for ProkName Studio.

Uses a dict-based string table + a Qt signal for live language switching.
Switching language emits ``languageChanged``; views re-translate on that signal
(``QEvent.LanguageChange`` semantics) without restart.
"""
from __future__ import annotations

from PySide6.QtCore import QLocale, QObject, Signal
from PySide6.QtWidgets import QApplication

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "app_title": "ProkName Studio",
        "app_subtitle": "原核生物命名辅助 · 决策支持，非有效性裁定",
        "menu_file": "文件",
        "menu_exit": "退出",
        "menu_help": "帮助",
        "menu_about": "关于",
        "nav_generate": "生成",
        "nav_route": "路由",
        "nav_check": "查重",
        "nav_project": "项目",
        "nav_data": "数据资产",
        # -- generate view --
        "gen_stem": "词干",
        "gen_type": "类型",
        "gen_rank": "阶元",
        "gen_genus": "属名",
        "gen_person_gender": "被纪念者性别",
        "gen_male": "男",
        "gen_female": "女",
        "gen_genus_gender": "属名性别（专家覆盖）",
        "gen_auto": "自动",
        "gen_advanced": "高级",
        "gen_genus_suffix": "属名词尾提示",
        "gen_adjective_formation": "形容词构词",
        "adj_place": "地名式（-ensis / -ense）",
        "adj_second_declension": "第二变格法（-us / -a / -um）",
        "adj_third_declension": "第三变格法（-is / -is / -e）",
        "adj_loving": "嗜好型（-philus / -phila / -philum）",
        "adj_nourishing": "营养型（-trophicus / -trophica / -trophicum）",
        "gen_button": "生成",
        "gen_results": "候选结果",
        "col_name": "名称",
        "col_category": "类别",
        "col_gender": "性别",
        "col_compliant": "合规",
        "col_derivation": "推导",
        "gen_empty": "请输入词干后点击生成。",
        "gen_err": "生成失败：",
        "add_to_project": "加入项目",
        "add_ok": "已加入项目：",
        "add_prompt": "项目名称",
        "add_default_project": "默认项目",
        # -- route view --
        "route_source": "数据来源",
        "route_candidatus": "Candidatus（候选种）",
        "route_icnp_occupied": "ICNP 先占状态",
        "route_icnp_auto": "未检查 (auto)",
        "route_icnp_yes": "是 — LPSN 已有有效发表名",
        "route_icnp_no": "否 — LPSN 无记录",
        "route_button": "路由",
        "route_viable_paths": "可行路径",
        "route_col_code": "法典",
        "route_col_role": "角色",
        "route_col_tradeoffs": "利弊",
        "route_warnings": "警告",
        "route_notes": "备注",
        "route_no_paths": "无可行路径（请检查来源或 ICNP 先占状态）。",
        "route_empty": "选择来源后点击路由查看可行路径。",
        "source_pure_culture": "纯培养 (pure_culture)",
        "source_MAG": "MAG（宏基因组拼接基因组）",
        "source_SAG": "SAG（单细胞基因组）",
        "source_unknown": "未知来源",
        "role_default": "默认路径",
        "role_alternative": "备选路径",
        "role_only_viable": "唯一可行（受限）",
        "role_conflict_guidance": "冲突引导",
        "role_unknown": "未知角色",
        # -- check view --
        "check_name": "候选名",
        "check_near_match_mode": "近似匹配口径",
        "check_max_distance": "最大编辑距离",
        "check_online": "在线查询（需凭据，M0 门控前禁用）",
        "check_button": "查重",
        "check_verdict": "结论",
        "check_sources": "来源",
        "check_col_source": "来源",
        "check_col_tier": "层级",
        "check_col_status": "状态",
        "check_col_detail": "详情",
        "check_near_matches": "近似匹配",
        "check_col_corpus": "语库名",
        "check_col_distance": "距离",
        "check_col_nm_source": "来源",
        "check_warnings": "警告",
        "check_empty": "输入候选名后点击查重。",
        "check_no_matches": "无近似匹配。",
        "near_match_whole": "整体名 (whole)",
        "near_match_stem": "词干 (stem)",
        "near_match_both": "全部 (both)",
        "verdict_conflict": "冲突",
        "verdict_parahomonym_warning": "近似同名警告",
        "verdict_verify_warning": "需核实",
        "verdict_blocked": "已阻塞",
        "verdict_no_clear_conflict": "无明确冲突",
        "verdict_unknown": "未知（无法判定）",
        "check_online_tooltip": (
            "Studio 只作离线查证，且此勾选不会被读取：LPSN 需凭据与网络，"
            "而 SeqCode 注册中心没有按名查询能力（2026-09-25 实测）。"
            "已在 SeqCode 注册的名字在这里仍会给出冲突；要得到三个「干净」"
            "结论，请在终端运行 prokname check --online。"
        ),
        "check_blocked_note": (
            "权威来源不可用，因此无法判定 —— 无法查证绝不等于未发现。"
            "Studio 目前只做离线查证：LPSN 需凭据联网，SeqCode 侧只能"
            "确认已注册的名字、无法确认未注册。若名字已在 LPSN/SeqCode "
            "注册，命令行 prokname check --online 会给出冲突；离线时"
            "已注册的 SeqCode 名字也会给出冲突。"
        ),
        "check_failed": "查重失败：",
        # -- project view --
        "proj_projects": "项目列表",
        "proj_create": "创建项目",
        "proj_name": "项目名称",
        "proj_data_source": "数据来源",
        "proj_target_code": "目标法典",
        "proj_create_btn": "创建",
        "proj_delete": "删除项目",
        "proj_delete_confirm": "确认删除项目",
        "proj_candidates": "候选名",
        "proj_export": "导出",
        "proj_export_json": "JSON",
        "proj_export_csv": "CSV",
        "proj_export_md": "Markdown",
        "proj_empty": "选择一个项目或创建新项目。",
        "proj_no_candidates": "该项目暂无候选名。",
        "proj_rate_prompt": "评分 (0-5)：",
        "proj_rate_btn": "保存评分",
        "proj_meta_any": "（未指定）",
        "proj_col_name": "名称",
        "proj_col_category": "类别",
        "proj_col_compliant": "合规",
        "proj_col_score": "评分",
        "proj_export_ok": "已导出：",
        "proj_export_err": "导出失败：",
        # -- data view --
        "data_title": "数据资产状态",
        "data_col_file": "文件",
        "data_col_version": "版本",
        "data_col_status": "状态",
        "data_empty": "暂无数据资产信息。",
        # -- getting-started guide (opened only from its button/menu entry) --
        "guide_button": "新手引导",
        "guide_title": "新手引导",
        "guide_prev": "上一步",
        "guide_next": "下一步",
        "guide_go": "前往该页面",
        "guide_close": "关闭",
        "guide_step_overview": "概览与工作流",
        "guide_step_check": "① 查重",
        "guide_step_generate": "② 生成",
        "guide_step_route": "③ 路由",
        "guide_step_project": "④ 项目",
        "guide_step_data": "⑤ 数据资产",
        "guide_step_tips": "界面操作技巧",
        "guide_content_overview": (
            "<p>ProkName Studio 是 prokname 命名引擎的桌面前端，按推荐工作流组织成五个页面：</p>"
            "<ol>"
            "<li><b>查重</b> —— 输入候选名，核对权威来源的冲突裁定与近似同名；</li>"
            "<li><b>生成</b> —— 按词干与法典规则批量生成合规候选学名；</li>"
            "<li><b>路由</b> —— 依据数据来源在 ICNP / SeqCode 双法典间选择可行路径；</li>"
            "<li><b>项目</b> —— 把候选名入库、评分并导出 JSON / CSV / Markdown 交付物；</li>"
            "<li><b>数据资产</b> —— 查看规则语料与词表的版本和状态。</li>"
            "</ol>"
            "<p>顶部工具栏可随时切换语言与外观。本引导默认不打开，"
            "需要时点击工具栏右侧的「新手引导」按钮即可。</p>"
        ),
        "guide_content_check": (
            "<p>1. 在「候选名」框输入要核查的名称（如 <i>Bacillus wukongus</i>）；<br>"
            "2. 选择近似匹配口径与最大编辑距离；<br>"
            "3. 点击「查重」，阅读结论徽标、逐权威源结果表与近似匹配清单。</p>"
            "<p>Studio 只做离线查证：「无法查证」不等于「未发现」，界面会明确区分两者。"
            "查重结论会随同名候选进入项目，保证可追溯。</p>"
        ),
        "guide_content_generate": (
            "<p>1. 输入<b>词干</b>（如 <i>Wukong</i>），选择类型与阶元；种级名称需填写属名；<br>"
            "2. 点击「生成」，在「候选结果」表格中查看候选名、类别、性别与合规状态；<br>"
            "3. 点击表格任意一行，下方即渲染该候选名的完整推导树；<br>"
            "4. 选中一行后点击「加入项目」，候选名即写入所选项目。</p>"
            "<p>表格各列宽度可通过拖动表头分隔线调节；表格与推导树之间的上下分界线"
            "也可拖动，以放大推导树。</p>"
        ),
        "guide_content_route": (
            "<p>1. 选择数据来源（纯培养 / MAG / SAG / 未知）；<br>"
            "2. 勾选是否为 <i>Candidatus</i>（候选种），并选择 ICNP 先占状态；<br>"
            "3. 点击「路由」，在「可行路径」表中查看各法典的角色与利弊，"
            "下方展示警告与备注。</p>"
            "<p>路径表与警告/备注之间的上下分界线可拖动，方便阅读较长的利弊列表。</p>"
        ),
        "guide_content_project": (
            "<p>左侧为项目列表：输入项目名称与元数据后点击「创建」；不再需要的项目可删除。</p>"
            "<p>右侧为所选项目的候选名表格：选中一行后在下方录入评分（0–5），"
            "并可通过「导出」生成 JSON / CSV / Markdown 交付物（含免责声明与数据来源署名）。</p>"
            "<p>左右两块之间的竖直分界线可拖动，自由调节两块的宽度。</p>"
        ),
        "guide_content_data": (
            "<p>「数据资产」面板报告引擎各规则文件的版本、门控状态与消费方。"
            "仍在等待专家签字的资产会如实标注，便于了解当前能力的边界。</p>"
        ),
        "guide_content_tips": (
            "<ul>"
            "<li><b>拖动分界线</b>：页面内的竖直/横向分界线均可用鼠标拖动，"
            "自由调节相邻区域的大小。</li>"
            "<li><b>拖动列宽</b>：「候选结果」等表格的列宽可拖动表头分隔线调节；"
            "最后一列自动填满剩余宽度。</li>"
            "<li><b>语言与外观</b>：顶部工具栏可即时切换中文 / English 与亮 / 暗色主题，"
            "无需重启。</li>"
            "<li><b>再次打开本引导</b>：点击顶部工具栏的「新手引导」按钮，"
            "或「帮助」菜单中的同名条目。</li>"
            "</ul>"
        ),
        # -- common --
        "lang": "语言",
        "lang_auto": "自动",
        "theme": "外观",
        "theme_auto": "跟随系统",
        "theme_light": "亮色",
        "theme_dark": "暗色",
        "disclaimer": "ProkName 仅提供命名辅助决策；名称有效性由 ICNP/SeqCode 正式发表决定。",
        "compliant_yes": "是",
        "compliant_no": "否",
        "compliant_review": "待审",
        "compliant_yes_inferred": "是（性别为推理所得，待审）",
        "compliant_yes_unverified": "是（依据未核验，待审）",
        "gen_inferred_hint": (
            "属名性别来自词尾启发式推理，置信度低：推理永不等于权威，"
            "请专家复核或补充词表。"
        ),
        "category_adjective": "形容词",
        "category_genitive": "属格名词",
        "category_appositive": "同位语名词",
        "type_feature": "特征",
        "type_place": "地名",
        "type_person": "人名",
        "type_thing": "事物",
        "gender_m": "阳性 (m)",
        "gender_f": "阴性 (f)",
        "gender_n": "中性 (n)",
        "warnings_label": "警告",
    },
    "en": {
        "app_title": "ProkName Studio",
        "app_subtitle": (
            "Prokaryotic nomenclature assistant · "
            "Decision support, not validity ruling"
        ),
        "menu_file": "File",
        "menu_exit": "Exit",
        "menu_help": "Help",
        "menu_about": "About",
        "nav_generate": "Generate",
        "nav_route": "Route",
        "nav_check": "Check",
        "nav_project": "Project",
        "nav_data": "Data Assets",
        # -- generate view --
        "gen_stem": "Stem",
        "gen_type": "Type",
        "gen_rank": "Rank",
        "gen_genus": "Genus",
        "gen_person_gender": "Honoured person gender",
        "gen_male": "Male",
        "gen_female": "Female",
        "gen_genus_gender": "Genus gender (expert override)",
        "gen_auto": "Auto",
        "gen_advanced": "Advanced",
        "gen_genus_suffix": "Genus suffix hint",
        "gen_adjective_formation": "Adjective formation",
        "adj_place": "Place-style (-ensis / -ense)",
        "adj_second_declension": "Second declension (-us / -a / -um)",
        "adj_third_declension": "Third declension (-is / -is / -e)",
        "adj_loving": "Loving (-philus / -phila / -philum)",
        "adj_nourishing": "Nourishing (-trophicus / -trophica / -trophicum)",
        "gen_button": "Generate",
        "gen_results": "Candidates",
        "col_name": "Name",
        "col_category": "Category",
        "col_gender": "Gender",
        "col_compliant": "Compliant",
        "col_derivation": "Derivation",
        "gen_empty": "Enter a stem and click Generate.",
        "gen_err": "Generation failed: ",
        "add_to_project": "Add to project",
        "add_ok": "Added to project: ",
        "add_prompt": "Project name",
        "add_default_project": "default",
        # -- route view --
        "route_source": "Data source",
        "route_candidatus": "Candidatus",
        "route_icnp_occupied": "ICNP pre-emption",
        "route_icnp_auto": "Not checked (auto)",
        "route_icnp_yes": "Yes — LPSN reports a validly published name",
        "route_icnp_no": "No — not in LPSN",
        "route_button": "Route",
        "route_viable_paths": "Viable paths",
        "route_col_code": "Code",
        "route_col_role": "Role",
        "route_col_tradeoffs": "Trade-offs",
        "route_warnings": "Warnings",
        "route_notes": "Notes",
        "route_no_paths": "No viable paths (check source or ICNP occupancy).",
        "route_empty": "Select a source and click Route to see viable paths.",
        "source_pure_culture": "Pure culture",
        "source_MAG": "MAG (metagenome-assembled)",
        "source_SAG": "SAG (single-amplified)",
        "source_unknown": "Unknown",
        "role_default": "Default",
        "role_alternative": "Alternative",
        "role_only_viable": "Only viable (constrained)",
        "role_conflict_guidance": "Conflict guidance",
        "role_unknown": "Unknown role",
        # -- check view --
        "check_name": "Candidate name",
        "check_near_match_mode": "Near-match mode",
        "check_max_distance": "Max edit distance",
        "check_online": "Online query (needs credentials; M0-gated)",
        "check_button": "Check",
        "check_verdict": "Verdict",
        "check_sources": "Sources",
        "check_col_source": "Source",
        "check_col_tier": "Tier",
        "check_col_status": "Status",
        "check_col_detail": "Detail",
        "check_near_matches": "Near matches",
        "check_col_corpus": "Corpus name",
        "check_col_distance": "Distance",
        "check_col_nm_source": "Source",
        "check_warnings": "Warnings",
        "check_empty": "Enter a candidate name and click Check.",
        "check_no_matches": "No near matches.",
        "near_match_whole": "Whole name",
        "near_match_stem": "Stem",
        "near_match_both": "Both",
        "verdict_conflict": "Conflict",
        "verdict_parahomonym_warning": "Parahomonym warning",
        "verdict_verify_warning": "Verify warning",
        "verdict_blocked": "Blocked",
        "verdict_no_clear_conflict": "No clear conflict",
        "verdict_unknown": "Unknown (no ruling)",
        "check_online_tooltip": (
            "Studio checks offline only, and this box is deliberately not read: "
            "LPSN needs credentials and a network, and the SeqCode Registry has "
            "no lookup-by-name (measured 2026-09-25). A name registered under "
            "SeqCode still returns a conflict here; for the three clean "
            "verdicts run `prokname check --online` in a terminal."
        ),
        "check_blocked_note": (
            "An authority could not answer, so no ruling is possible — "
            "'cannot check' is never 'not found'. Studio checks offline "
            "only: LPSN needs credentials and a network, and the SeqCode "
            "side can confirm a registered name but cannot confirm an "
            "unregistered one (see docs/provenance/seqcode-registry-2026-"
            "09-25.md). A name already registered under SeqCode does "
            "return a conflict even offline; for the rest, run "
            "`prokname check --online` on the command line."
        ),
        "check_failed": "Check failed: ",
        # -- project view --
        "proj_projects": "Projects",
        "proj_create": "Create project",
        "proj_name": "Project name",
        "proj_data_source": "Data source",
        "proj_target_code": "Target code",
        "proj_create_btn": "Create",
        "proj_delete": "Delete project",
        "proj_delete_confirm": "Delete this project?",
        "proj_candidates": "Candidates",
        "proj_export": "Export",
        "proj_export_json": "JSON",
        "proj_export_csv": "CSV",
        "proj_export_md": "Markdown",
        "proj_empty": "Select a project or create a new one.",
        "proj_no_candidates": "No candidates in this project.",
        "proj_rate_prompt": "Rating (0-5):",
        "proj_rate_btn": "Save rating",
        "proj_meta_any": "(unspecified)",
        "proj_col_name": "Name",
        "proj_col_category": "Category",
        "proj_col_compliant": "Compliant",
        "proj_col_score": "Score",
        "proj_export_ok": "Exported: ",
        "proj_export_err": "Export failed: ",
        # -- data view --
        "data_title": "Data Assets",
        "data_col_file": "File",
        "data_col_version": "Version",
        "data_col_status": "Status",
        "data_empty": "No data asset information available.",
        # -- getting-started guide (opened only from its button/menu entry) --
        "guide_button": "Getting started",
        "guide_title": "Getting Started",
        "guide_prev": "Previous",
        "guide_next": "Next",
        "guide_go": "Go to this page",
        "guide_close": "Close",
        "guide_step_overview": "Overview & workflow",
        "guide_step_check": "1 · Check",
        "guide_step_generate": "2 · Generate",
        "guide_step_route": "3 · Route",
        "guide_step_project": "4 · Project",
        "guide_step_data": "5 · Data Assets",
        "guide_step_tips": "Interface tips",
        "guide_content_overview": (
            "<p>ProkName Studio is the desktop front-end for the prokname engine, "
            "organised into five pages that follow the recommended workflow:</p>"
            "<ol>"
            "<li><b>Check</b> — enter a candidate name and compare it against "
            "authority verdicts and near matches;</li>"
            "<li><b>Generate</b> — produce compliant candidate names in bulk from a "
            "stem and the code rules;</li>"
            "<li><b>Route</b> — choose viable paths between ICNP / SeqCode from the "
            "data source;</li>"
            "<li><b>Project</b> — store candidates, rate them, and export JSON / "
            "CSV / Markdown deliverables;</li>"
            "<li><b>Data Assets</b> — inspect rule corpora and lexicon versions and "
            "status.</li>"
            "</ol>"
            "<p>The toolbar switches language and appearance at any time. This guide "
            "is never opened on its own: click the Getting-started button on the "
            "right of the toolbar whenever you want it.</p>"
        ),
        "guide_content_check": (
            "<p>1. Type the name to verify into the candidate-name box (e.g. "
            "<i>Bacillus wukongus</i>);<br>"
            "2. choose the near-match mode and the maximum edit distance;<br>"
            "3. click Check, then read the verdict badge, the per-authority table "
            "and the near-match list.</p>"
            "<p>Studio verifies offline only: 'cannot check' is never 'not found', "
            "and the interface keeps the two apart. A verdict travels with its name "
            "into the project, keeping it traceable.</p>"
        ),
        "guide_content_generate": (
            "<p>1. Enter a <b>stem</b> (e.g. <i>Wukong</i>) and pick a type and a "
            "rank; species-rank names need a genus;<br>"
            "2. click Generate and read the candidates, categories, genders and "
            "compliance in the results table;<br>"
            "3. click any row to render that candidate's full derivation tree "
            "below;<br>"
            "4. with a row selected, click Add to project to write it into a "
            "project.</p>"
            "<p>Every column width is adjustable by dragging its header divider, and "
            "the divider between the table and the derivation tree is draggable "
            "too.</p>"
        ),
        "guide_content_route": (
            "<p>1. Choose the data source (pure culture / MAG / SAG / unknown);<br>"
            "2. tick whether the name is <i>Candidatus</i>, and set the ICNP "
            "pre-emption status;<br>"
            "3. click Route and read each code's role and trade-offs in the viable "
            "paths table, with warnings and notes underneath.</p>"
            "<p>The divider between the path table and the warnings/notes pane is "
            "draggable, which helps with long trade-off lists.</p>"
        ),
        "guide_content_project": (
            "<p>The left pane lists projects: type a project name and metadata, then "
            "click Create; projects you no longer need can be deleted.</p>"
            "<p>The right pane shows the selected project's candidates: select a row "
            "and record a rating (0–5) below, then use Export to produce JSON / CSV "
            "/ Markdown deliverables (with the disclaimer and data-source "
            "attribution included).</p>"
            "<p>The vertical divider between the two panes is draggable, so either "
            "side can be widened at will.</p>"
        ),
        "guide_content_data": (
            "<p>The Data Assets page reports each engine rule file's version, gating "
            "status and consumers. Assets still awaiting expert sign-off are "
            "labelled as such, so the current capability boundary stays visible.</p>"
        ),
        "guide_content_tips": (
            "<ul>"
            "<li><b>Drag the dividers</b>: the vertical/horizontal dividers inside "
            "the pages are draggable, so adjacent panes can be resized freely.</li>"
            "<li><b>Drag column widths</b>: in the results table and elsewhere, "
            "columns resize by dragging their header dividers; the last column "
            "absorbs the remaining width.</li>"
            "<li><b>Language & appearance</b>: the toolbar switches Chinese / "
            "English and light / dark without a restart.</li>"
            "<li><b>Open this guide again</b>: click the Getting-started button on "
            "the toolbar, or the same entry in the Help menu.</li>"
            "</ul>"
        ),
        # -- common --
        "lang": "Language",
        "lang_auto": "Auto",
        "theme": "Appearance",
        "theme_auto": "Follow system",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "disclaimer": (
            "ProkName provides decision support only; name validity "
            "is decided by formal publication under ICNP/SeqCode."
        ),
        "compliant_yes": "Yes",
        "compliant_no": "No",
        "compliant_review": "Review",
        "compliant_yes_inferred": "Yes (gender inferred — review)",
        "compliant_yes_unverified": "Yes (basis unverified — review)",
        "gen_inferred_hint": (
            "The genus gender came from an ending heuristic (low confidence): "
            "inference is never authority. Have an expert verify or extend the "
            "gender lexicon."
        ),
        "category_adjective": "adjective",
        "category_genitive": "genitive noun",
        "category_appositive": "noun in apposition",
        "type_feature": "feature",
        "type_place": "place",
        "type_person": "person",
        "type_thing": "thing",
        "gender_m": "Masculine (m)",
        "gender_f": "Feminine (f)",
        "gender_n": "Neuter (n)",
        "warnings_label": "Warnings",
    },
}

_LM: LanguageManager | None = None


class LanguageManager(QObject):
    languageChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._lang = "en"

    @property
    def lang(self) -> str:
        return self._lang

    def set_language(self, lang: str) -> None:
        if lang not in STRINGS:
            lang = "en"
        if lang != self._lang:
            self._lang = lang
            self.languageChanged.emit(lang)

    def tr(self, key: str) -> str:
        return STRINGS.get(self._lang, STRINGS["en"]).get(key, key)


def _manager() -> LanguageManager:
    global _LM
    if _LM is None:
        _LM = LanguageManager()
    return _LM


def tr(key: str) -> str:
    return _manager().tr(key)


def category_label(value: str | None) -> str:
    """UI label for an engine grammatical-category value ('adjective'|...)."""
    if not value:
        return "-"
    return tr(f"category_{value}") if f"category_{value}" in STRINGS[
        _manager().lang
    ] else value


def gender_label(value: str | None) -> str:
    """UI label for an engine gender value ('m'|'f'|'n')."""
    if not value:
        return "-"
    return tr(f"gender_{value}") if f"gender_{value}" in STRINGS[
        _manager().lang
    ] else value


def install(app: QApplication, lang: str = "auto") -> None:
    """Install the language manager and set the initial language.

    ``app`` is accepted for API symmetry (and future QEvent plumbing) but is
    not required by the current dict-based implementation.
    """
    set_language_auto() if lang == "auto" else set_language(lang)


def set_language_auto() -> None:
    """Resolve and apply the language from the system locale (re-resolvable)."""
    loc = QLocale.system().language()
    _manager().set_language("zh" if loc == QLocale.Chinese else "en")


def set_language(lang: str) -> None:
    _manager().set_language(lang)


def current_language() -> str:
    return _manager().lang


def connect_language_changed(slot) -> None:
    _manager().languageChanged.connect(slot)
