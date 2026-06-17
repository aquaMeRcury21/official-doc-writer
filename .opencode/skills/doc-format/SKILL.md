---
name: doc-format
description: |
  公文格式引擎，严格遵循 GB/T 9704-2012《党政机关公文格式》国家标准。
  提供：层级序号规范、字体字号映射表、页面设置参数、标点符号规则、python-docx 代码模板、API 调用参数。
  适用：需要输出 .docx 时、需要设置字体字号/页边距/版心时、检查格式合规性时。
  不适用：纯文本内容撰写、不涉及排版输出的场景。
  关键词触发：公文格式、套红头、排版、页面设置、字体字号、版心、发文字号、国标格式、docx生成、Python生成公文。
---

# 公文格式引擎

## 格式规范（GB/T 9704-2012）

### 结构层次序数

必须严格按此顺序，不得混用或跳级：

```
一、第一层次（3号黑体）
（一）第二层次（3号楷体_GB2312）
1.第三层次（3号仿宋_GB2312）
（1）第四层次（3号仿宋_GB2312）
```

- 不得混用，如出现"一是、（二）、3."等不统一形式
- 层级逐级展开，不得跳级
- 10 页内文稿控制到二级标题
- 2-3 页文稿使用一、二级标题即可

### 核心字体字号

| 要素 | 字体 | 字号 |
|------|------|------|
| 文件标题 | 方正小标宋简体 | 2号 |
| 正文 | 仿宋_GB2312 | 3号 |
| 一级标题 | 黑体 | 3号 |
| 二级标题 | 楷体_GB2312 | 3号 |
| 发文字号 | 仿宋_GB2312 | 3号（六角括号〔〕）|
| 版记（抄送/印发） | 仿宋_GB2312 | 4号 |

### 标点符号

- 统一全角标点（。，、；：？！""''（）〔〕【】《》）
- 发文字号年份必须用六角括号〔〕，不可用 [] 或【】
- 同一层次并列事项用顿号分隔，同级标题后的标点一致
- **引号必须用中文全角，严禁使用西文半角引号**：双引号用\u201c\u201d，单引号用\u2018\u2019。Python 代码中定义字符串常量时必须用 `\u201c` 和 `\u201d`（或预定义 `LQ`/`RQ` 变量），绝不允许在文本中使用 ASCII 半角 `"`（U+0022）作为引号。⚠️ 生成 docx 前，必须全文扫描确认无半角引号残留；如发现半角引号，必须全部替换为全角引号，不得遗漏一处。

### 标题加粗禁令

- **二级标题**（如（一）、【第X页·xxx】、风险X：等）必须使用**楷体_GB2312**，字号三号（16pt），字形**常规（不加粗）**，两端对齐
- 严禁将二级标题设为黑体或加粗；所有非一级标题的层级标题均视为二级标题，统一适用此规则
- **一级标题**（一、二、三、）使用**黑体**三号（16pt），字形**常规（不加粗）**——黑体本身自带加重视觉效果，无需额外加粗
- ⚠️ 生成文稿时，不得对任何标题设置 `bold=True`；所有标题仅通过字体名称（黑体/楷体）区分层级，不得使用加粗字形。

### Word 文档排版注意事项

- 正文及一级标题均须设置 2 字符首行缩进（`Pt(32)`），不可用厘米近似值
- **抬头不缩进**：\u201c同志们：\u201d\u201c各单位：\u201d\u201c尊敬的各位领导\u201d等称呼语顶格书写，不设首行缩进
- **问候语缩进**：\u201c大家下午好！\u201d\u201c大家好！\u201d等称呼语后的问候句，须设 2 字符首行缩进（`Pt(32)`）
- **结束语缩进**：\u201c谢谢大家！\u201d\u201c谢谢！\u201d等结尾致谢句，须设 2 字符首行缩进（`Pt(32)`）
- 全文西文字体统一为 Times New Roman，中文字体各自按规范
- 正文全部设为两端对齐（JUSTIFY），版头/标题/落款除外
- **标题前空行**：公文标题（致辞、主持词等）前须保留一个空行，标题与讲话人署名之间须保留一个空行
- 待补充数据统一用红色 xx 占位，便于业务科室识别填入
- **关闭孤行控制**：所有段落均须设置 `widow_control = False`，防止段落跨页时出现单行孤行
- 生成 docx 前，必须将文本中的所有西文半角引号转为中文全角引号，确保全部使用\u201c/\u201d而非 U+0022

## 格式速查（GB/T 9704-2012 摘要）

| 参数 | 规格 |
|------|------|
| 用纸 | A4（210mm×297mm）|
| 天头（上白边）| 37mm±1mm |
| 订口（左白边）| 28mm±1mm |
| 版心 | 156mm×225mm |
| 默认行距 | 28磅 |
| 每面行数/字数 | 22行×28字 |
| 成文日期格式 | 阿拉伯数字全称（如：2026年6月9日）|
| 发文字号格式 | 机关代字〔年份〕序号号（如：[发文机关代字]发〔2026〕5号）|
| 标题回行 | 梯形或菱形排列 |
| 正文首行 | 缩进2字符 |

**页码规则**（如需此要素）：
- 4号半角宋体阿拉伯数字
- 单页码居右空一字，双页码居左空一字
- 版心下边缘之下 7mm

**附注规则**：
- 在成文日期下一行左空 2 字
- 加圆括号
- 请示类公文保留附注（联系人+联系电话）

## API 调用规范

### 模型分级调度策略

| 任务类型 | 路由模型 | temperature | max_tokens |
|---------|---------|-------------|------------|
| 起草公文正文（draft） | deepseek-chat | **0.15** | 8192 |
| 校对/审核（proofread） | deepseek-reasoner | 0.05 | 4096 |
| 大纲/摘要/关键词（outline） | deepseek-chat | 0.1 | 2048 |
| 润色/改写（rewrite） | deepseek-chat | 0.2 | 4096 |
| 文种判断/分类（classify） | deepseek-chat | 0.0 | 512 |

**强制约束**：
- **temperature 绝对上限 0.2**：公文写作严格禁止高随机性
- **max_tokens 必须设上限**：根据目标字数动态估算（中文约 1 字 ≈ 1.5 token，再加 512 buffer）
- 所有 API 调用必须通过 `utils/api_client.py` 的 `DeepSeekClient` 发起

### 重试与退避机制

| 场景 | 策略 |
|------|------|
| HTTP 429（限流） | 优先读取 Retry-After 头；无此头则指数退避 1s→2s→4s，带随机抖动 |
| HTTP 5xx（服务端错误） | 同上，最多 3 次重试 |
| 请求超时 | connect 超时 30s，read 超时 300s；超时后指数退避重试 |
| 网络连接失败 | 同指数退避，最多 3 次 |
| HTTP 4xx（客户端错误，429 除外） | **不重试**，直接返回错误 |

```python
from utils.api_client import DeepSeekClient, TASK_TYPE

client = DeepSeekClient(api_key='your-key')
result = client.draft('帮我起草一份关于开展XX工作的通知')
if result.success:
    print(f'费用: ¥{result.cost_yuan:.4f}, 重试: {result.retries_used}次')
```

### Token 统计与成本管控

```python
from utils.cost_tracker import get_tracker

tracker = get_tracker(daily_budget_yuan=50.0)
tracker.log(result, task_type=TASK_TYPE.DRAFT)
print(tracker.summary())  # 今日费用：¥1.23 / ¥50.00 (2.5%) [正常]

if not tracker.check_budget():
    raise SystemExit('今日预算已用尽')

report = tracker.monthly_report()
```

## Word 文档生成规范（python-docx）

### 页面设置

| 参数 | 规格 |
|------|------|
| 纸张 | A4（210mm × 297mm） |
| 天头（上边距） | 3.7 cm |
| 下边距 | 3.5 cm |
| 订口（左边距） | 2.8 cm |
| 右边距 | 2.6 cm |
| 行距 | 固定值 28 磅 |
| 西文字体 | Times New Roman（全文底层统一） |
| 对齐方式 | 两端对齐（JUSTIFY），版头/标题/落款除外 |

### 字体字号映射

| 要素 | 中文字体 | 西文字体 | 字号 | 字形 | 对齐 |
|------|----------|----------|------|------|------|
| 版头（发文机关标识） | 方正小标宋简体 | Times New Roman | 二号（22pt） | 常规 | 居中 |
| 发文字号 | 仿宋_GB2312 | Times New Roman | 三号（16pt） | 常规 | 居中 |
| 公文标题 | 方正小标宋简体 | Times New Roman | 二号（22pt） | 常规 | 居中 |
| 主送机关 | 仿宋_GB2312 | Times New Roman | 三号（16pt） | 常规 | 两端对齐 |
| 一级标题（一、…） | 黑体 | Times New Roman | 三号（16pt） | 常规 | 两端对齐 |
| 二级标题（（一）…） | 楷体_GB2312 | Times New Roman | 三号（16pt） | 常规 | 两端对齐 |
| 正文 | 仿宋_GB2312 | Times New Roman | 三号（16pt） | 常规 | 两端对齐 |
| 落款（发文单位+日期） | 仿宋_GB2312 | Times New Roman | 三号（16pt） | 常规 | 右对齐 |

### 首行缩进

```python
from docx.shared import Pt
INDENT_2CHAR = Pt(32)  # 3号（16pt）× 2 = 32pt，严禁使用 Cm(0.85) 等厘米近似值
```

- 所有正文段落（含一级标题"一、""二、""三、"）均设置 `first_line_indent=Pt(32)`
- 版头、发文字号、公文标题、主送机关、落款段落不设缩进

### 占位符处理

- Markdown 中使用 `[待补充]` 或 `[待核实]`
- 生成 .docx 时替换为红色 **xx**（`RGBColor(0xFF, 0x00, 0x00)`）

### 表格格式规范

| 要素 | 字体 | 字号 | 对齐 |
|------|------|------|------|
| 表头 | 黑体 | 小四（12pt） | 水平居中 + 垂直居中 |
| 表体 | 仿宋_GB2312 | 小四（12pt） | 水平居中 + 垂直居中 |
| 边框 | 0.5pt 黑色实线（Table Grid 样式） | — | — |
| 单元格边距 | 上下 2pt，左右 4pt | — | — |

- 表格整体居中于版心
- 表头建议设置灰色底纹（`RGBColor(0xD9, 0xD9, 0xD9)`），可选
- 列宽按内容合理分配，首列或关键列可适当加宽
- 表内文字禁止首行缩进，禁止孤行控制（已全局关闭）
- 表格前后各保留一个空行（`add_para('')`）

### python-docx 代码模板

```python
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# 页面设置
for section in doc.sections:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.7)
    section.bottom_margin = Cm(3.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)

# 默认样式
style = doc.styles['Normal']
style.font.name = 'Times New Roman'
style.font.size = Pt(16)
style.element.rPr.rFonts.set(qn('w:eastAsia'), '仿宋_GB2312')
pf = style.paragraph_format
pf.line_spacing = Pt(28)
pf.space_before = Pt(0)
pf.space_after = Pt(0)
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.widow_control = False

# === 常量 ===
RED = RGBColor(0xFF, 0x00, 0x00)
INDENT_2CHAR = Pt(32)
LQ = '\u201c'  # 左双引号
RQ = '\u201d'  # 右双引号
LS = '\u2018'  # 左单引号
RS = '\u2019'  # 右单引号

_PLACEHOLDER_RE = re.compile(r'(\[待补充\]|\[待核实\])')


def _set_run_font(run, font_name, font_size, bold=False, color=None):
    """统一设置 Run 的字体。同时设置西文字体和中文字体，缺一不可。"""
    run.font.name = 'Times New Roman'
    run.font.size = font_size
    run.bold = bold
    run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
    if color:
        run.font.color.rgb = color


def add_title(text, level):
    """显式标记标题层级。
    level: 0=公文标题  1=一级标题  2=二级标题
    """
    if level == 0:
        return add_para(text, '方正小标宋简体', Pt(22),
                        alignment=WD_ALIGN_PARAGRAPH.CENTER)
    elif level == 1:
        return add_para(text, '黑体', Pt(16),
                        first_line_indent=INDENT_2CHAR)
    elif level == 2:
        return add_para(text, '楷体_GB2312', Pt(16),
                        first_line_indent=INDENT_2CHAR)
    else:
        raise ValueError(f"无效的标题层级 level={level}，只允许 0/1/2")


def add_para(text, font_name='仿宋_GB2312', font_size=Pt(16), bold=False,
             alignment=None, first_line_indent=None):
    """添加段落。自动将 [待补充]/[待核实] 替换为红色 xx。"""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = Pt(28)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.widow_control = False
    if alignment is not None:
        p.alignment = alignment
    else:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if first_line_indent is not None:
        p.paragraph_format.first_line_indent = first_line_indent
    if text == '':
        return p

    parts = _PLACEHOLDER_RE.split(text)
    for part in parts:
        if part == '':
            continue
        is_placeholder = _PLACEHOLDER_RE.fullmatch(part) is not None
        run = p.add_run('xx' if is_placeholder else part)
        _set_run_font(run, font_name, font_size, bold,
                      color=RED if is_placeholder else None)
    return p


def _set_cell_margins(table, top=Pt(2), bottom=Pt(2), left=Pt(4), right=Pt(4)):
    """统一设置表格所有单元格的边距（pt 值）。"""
    for row in table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcMar = OxmlElement('w:tcMar')
            for edge, val in [('top', top), ('bottom', bottom),
                              ('start', left), ('end', right)]:
                mar = OxmlElement(f'w:{edge}')
                mar.set(qn('w:w'), str(int(val.pt * 20)))
                mar.set(qn('w:type'), 'dxa')
                tcMar.append(mar)
            tcPr.append(tcMar)


def _set_cell_border(cell, **kwargs):
    """设置单元格边框。kwargs: top/sz(0-24), bottom/sz, left/sz, right/sz。"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'bottom', 'left', 'right'):
        edge_el = OxmlElement(f'w:{edge}')
        sz = kwargs.get(f'{edge}_sz', 4)
        color = kwargs.get(f'{edge}_color', '000000')
        edge_el.set(qn('w:val'), 'single')
        edge_el.set(qn('w:sz'), str(sz))
        edge_el.set(qn('w:color'), color)
        edge_el.set(qn('w:space'), '0')
        tcBorders.append(edge_el)
    tcPr.append(tcBorders)


def add_table(headers, rows, col_widths=None,
              font_name='仿宋_GB2312', font_size=Pt(12),
              header_font_name='黑体', alignment=WD_ALIGN_PARAGRAPH.CENTER,
              header_bg=None):
    """添加格式化表格。

    Args:
        headers: 表头列表
        rows: 数据行列表，每行为一个列表
        col_widths: 列宽列表（可选），如 [Cm(2), Cm(4), ...]
        font_name: 正文字体，默认仿宋_GB2312
        font_size: 正文字号，默认小四 (12pt)
        header_font_name: 表头字体，默认黑体
        alignment: 单元格水平对齐，默认居中
        header_bg: 表头背景色（RGBColor），默认 None（无填充）
    """
    ncols = len(headers)
    table = doc.add_table(rows=1 + len(rows), cols=ncols)

    # 表头
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        p = cell.paragraphs[0]
        p.alignment = alignment
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(header)
        _set_run_font(run, header_font_name, font_size)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        if header_bg:
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), f'{int(header_bg):06X}')
            shading.set(qn('w:val'), 'clear')
            cell._tc.get_or_add_tcPr().append(shading)

    # 数据行
    for r_idx, row_data in enumerate(rows):
        for c_idx, text in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ''
            p = cell.paragraphs[0]
            p.alignment = alignment
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run(str(text) if text is not None else '')
            _set_run_font(run, font_name, font_size)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # 设置列宽
    if col_widths:
        for i, width in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = width

    # 统一单元格边距
    _set_cell_margins(table)

    return table
```

### 用法示例

```python
# === 标题：一律用 add_title(text, level) ===
add_title('中共XX市委宣传部关于XX事项的请示', level=0)
add_title('一、工作开展情况', level=1)
add_title('（一）强化理论学习', level=2)

# === 特殊段落：用 add_para ===
add_para('中共XX市委宣传部', '方正小标宋简体', Pt(22),
         alignment=WD_ALIGN_PARAGRAPH.CENTER)   # 版头居中
add_para('同志们：', first_line_indent=None)      # 抬头顶格
add_para(f'一是持续深化{LQ}理论武装{RQ}，[待补充]次。',
         first_line_indent=INDENT_2CHAR)         # 正文缩进
add_para('中共XX市委宣传部', alignment=WD_ALIGN_PARAGRAPH.RIGHT)  # 落款
add_para('2026年6月[待核实]日', alignment=WD_ALIGN_PARAGRAPH.RIGHT)

# === 附件表格：用 add_table ===
add_para('')  # 表前空行
add_table(
    headers=['序号', '姓名', '单位', '职务', '联系电话'],
    rows=[
        ['1', '张三', '市委宣传部', '科长', '139xxxxxxxx'],
        ['2', '李四', '市教育局', '副科长', '138xxxxxxxx'],
        ['3', '王五', '市文旅局', '一级主任科员', '137xxxxxxxx'],
    ],
    col_widths=[Cm(1.2), Cm(2.5), Cm(3.5), Cm(3.5), Cm(3.0)],
    header_bg=RGBColor(0xD9, 0xD9, 0xD9),  # 浅灰底纹
)
add_para('')  # 表后空行

# === 从数据列表动态生成表格 ===
    人才列表 = [
        ['杨XX', '男', '市委党校', '理论人才', '马克思主义理论', '多年宣讲经验', '理论授课'],
        ['刘XX', '女', '市教育局', '教育人才', '心理学', '心理健康教育', '心理辅导'],
    ]
add_table(
    headers=['姓名', '性别', '所属单位', '人才类型', '专业特长', '实绩表现', '可提供服务内容'],
    rows=人才列表,
    col_widths=[Cm(2), Cm(1.2), Cm(3), Cm(2.5), Cm(3), Cm(3.5), Cm(3.5)],
)

## 生成后校验

每次生成 .docx 后运行以下校验脚本确保格式合规：

```bash
python .opencode/skills/doc-format/scripts/validate_docx.py 路径/文档.docx
```

脚本检查项：纸张A4、页边距、默认字体字号、行距、孤行控制、标题不加粗、首行缩进、全角标点。

```bash
# 校验整个目录
python .opencode/skills/doc-format/scripts/validate_docx.py 路径/目录/

# 静默模式（只输出 pass/fail）
python .opencode/skills/doc-format/scripts/validate_docx.py 路径/文档.docx --quiet
```

## 常见坑清单（python-docx）

### 1. 表格宽度必须双设置

**问题**：表格在 WPS 和 Word 中渲染宽度不一致。

**原因**：python-docx 的 `cell.width` 和 `column_widths` 各控制不同层面的 XML 属性，缺一不可。

**正确做法**：
```python
table = doc.add_table(rows=3, cols=3)
# 同时设置两项
table.columns[0].width = Cm(3)
for row in table.rows:
    row.cells[0].width = Cm(3)
```
更简便：使用本模板的 `add_table()` 函数，它会自动处理好双宽度。

### 2. 列表不要手动编号

**问题**：手动写入"一、""（一）""1." 作为段落文字，跨平台显示不统一。

**正确做法**：用 OxmlElement 插入 w:numPr 自动编号，或用本模板的 `add_title(level=1)` 函数。

```python
# ❌ 错误
add_para('一、提高政治站位')

# ✅ 正确
add_title('一、提高政治站位', level=1)
```

### 3. 行距用固定值，不用多倍行距

**问题**：`line_spacing = 1.5` 在不同字体大小下表现不一致。

**正确做法**：
```python
# ✅ 固定值 28 磅
paragraph.paragraph_format.line_spacing = Pt(28)

# ❌ 错误
paragraph.paragraph_format.line_spacing = 1.5
```

### 4. 段落换行用 add_paragraph，不用 \n

**问题**：在 `TextRun` 中使用 `\n` 会导致跨平台换行不一致。

**正确做法**：
```python
# ✅ 正确
add_para('第一行')
add_para('第二行')

# ❌ 错误
run = paragraph.add_run('第一行\n第二行')
```

### 5. 中文字体必须通过 XML 设置

**问题**：仅 `run.font.name = '仿宋_GB2312'` 只设置西文字体，中文字体不生效。

**正确做法**：
```python
run.font.name = 'Times New Roman'       # 西文
run._element.rPr.rFonts.set(
    qn('w:eastAsia'), '仿宋_GB2312'     # 中文
)
```

### 6. 字号单位用 Pt 避免混淆

**问题**：字号换算时混淆 pt 和 号数（如 3号=16pt）。

| 号数 | pt |
|------|-----|
| 初号 | 42pt |
| 小初 | 36pt |
| 二号 | 22pt |
| 小二号 | 18pt |
| 三号 | 16pt |
| 小三号 | 15pt |
| 四号 | 14pt |
| 小四号 | 12pt |

### 7. 首行缩进用 Pt(32)，不用 Cm

**问题**：`Cm(0.85)` 在字号变化时缩进比例不对。

**正确做法**：
```python
INDENT_2CHAR = Pt(32)  # 3号字16pt × 2 = 32pt
```

### 8. 关闭孤行控制

**问题**：默认 `widow_control = True` 导致段落跨页时出现单行孤行。

**正确做法**：全局关闭
```python
doc.styles['Normal'].paragraph_format.widow_control = False
```

### 9. 分页符必须包在 Paragraph 内

**问题**：直接调用 `doc.add_page_break()` 或使用 `run.add_break()` 时，在某些 WPS 版本中不生效。

**正确做法**：
```python
# ✅ 正确
from docx.enum.text import WD_BREAK
run = paragraph.add_run()
run.add_break(WD_BREAK.PAGE)

# 或使用 PageBreak XML
from docx.oxml import OxmlElement
br = OxmlElement('w:br')
br.set(qn('w:type'), 'page')
run._element.append(br)
```

### 10. 保存前检查半角引号

**问题**：API 返回内容中可能混入西文半角引号 `"`（U+0022）。

**正确做法**：生成 docx 前全文扫描替换
```python
import re
content = re.sub(r'(?<=\u201c)[^」\u201d]*\K"', '\u201d', content)
# 或使用本模板的 add_para() 自动处理
```
```
