// ComfyUI 零基础入门教程 — docx 生成脚本
// 结构：Section1 封面(R1/DM-1) / Section2 目录(罗马页码) / Section3 正文(阿拉伯页码从1起)
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, PageNumber, NumberFormat, AlignmentType, HeadingLevel,
  WidthType, BorderStyle, ShadingType, SectionType, TableLayoutType,
  TableOfContents, PageBreak, LevelFormat, ExternalHyperlink,
} = require("docx");
const fs = require("fs");

// ───────────────────────── 调色板（DM-1 Deep Cyan：AI/科技） ─────────────────────────
const P = {
  bg: "162235",            // 封面深底
  titleColor: "FFFFFF",
  subtitleColor: "B0B8C0",
  metaColor: "90989F",
  footerColor: "687078",
  accent: "37DCF2",        // 封面亮青
  headingDark: "0A1628",   // 正文标题深藏青
  body: "1A2B40",          // 正文近黑
  secondary: "6878A0",     // 次要说明
  tHeaderBg: "1B6B7A",     // 表头（暗化青）
  tHeaderText: "FFFFFF",
  tAccentLine: "1B6B7A",
  tInnerLine: "C8DDE2",
  surface: "EDF3F5",       // 浅青底（提示块/隔行）
};

const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NB, bottom: NB, left: NB, right: NB };
const allNoBorders = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };

// ───────────────────────── 封面工具函数（design-system 标准实现） ─────────────────────────
function splitTitleLines(title, charsPerLine) {
  if (title.length <= charsPerLine) return [title];
  const breakAfter = new Set([..."，。、；：！？", ..."的与和及之在于为", ..."-_—–·/", ..." \t"]);
  const lines = [];
  let remaining = title;
  while (remaining.length > charsPerLine) {
    let breakAt = -1;
    for (let i = charsPerLine; i >= Math.floor(charsPerLine * 0.6); i--) {
      if (i < remaining.length && breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
    }
    if (breakAt === -1) {
      const limit = Math.min(remaining.length, Math.ceil(charsPerLine * 1.3));
      for (let i = charsPerLine + 1; i < limit; i++) {
        if (breakAfter.has(remaining[i - 1])) { breakAt = i; break; }
      }
    }
    if (breakAt === -1) {
      breakAt = charsPerLine;
      const prevChar = remaining[breakAt - 1], nextChar = remaining[breakAt];
      if (prevChar && nextChar && !breakAfter.has(prevChar) && !breakAfter.has(nextChar) &&
          /[\u4e00-\u9fff]/.test(prevChar) && /[\u4e00-\u9fff]/.test(nextChar)) breakAt = breakAt - 1;
    }
    lines.push(remaining.slice(0, breakAt).trim());
    remaining = remaining.slice(breakAt).trim();
  }
  if (remaining) lines.push(remaining);
  if (lines.length > 1 && lines[lines.length - 1].length <= 2) {
    const last = lines.pop();
    lines[lines.length - 1] += last;
  }
  return lines;
}

function calcTitleLayout(title, maxWidthTwips, preferredPt = 40, minPt = 24) {
  const charWidth = (pt) => pt * 20;
  const charsPerLine = (pt) => Math.floor(maxWidthTwips / charWidth(pt));
  let titlePt = preferredPt, lines;
  while (titlePt >= minPt) {
    const cpl = charsPerLine(titlePt);
    if (cpl < 2) { titlePt -= 2; continue; }
    lines = splitTitleLines(title, cpl);
    if (lines.length <= 3) break;
    titlePt -= 2;
  }
  if (!lines || lines.length > 3) {
    lines = splitTitleLines(title, charsPerLine(minPt));
    titlePt = minPt;
  }
  return { titlePt, titleLines: lines };
}

function calcCoverSpacing(params) {
  const {
    titleLineCount = 1, titlePt = 36, hasSubtitle = false, hasEnglishLabel = false,
    metaLineCount = 0, fixedHeight = 800, pageHeight = 16838, marginTop = 0, marginBottom = 0,
  } = params;
  const SAFETY = 1200;
  const usableHeight = pageHeight - marginTop - marginBottom - SAFETY;
  const titleHeight = titleLineCount * (titlePt * 23 + 200);
  const subtitleHeight = hasSubtitle ? (12 * 23 + 600) : 0;
  const englishLabelHeight = hasEnglishLabel ? (9 * 23 + 600) : 0;
  const metaHeight = metaLineCount * (10 * 23 + 100);
  const implicitParaHeight = 3 * 300;
  const contentHeight = titleHeight + subtitleHeight + englishLabelHeight + metaHeight + fixedHeight + implicitParaHeight;
  const remainingSpace = usableHeight - contentHeight;
  const safeRemaining = Math.max(remainingSpace, 400);
  const FOOTER_MIN = 800;
  const rawTop = Math.floor(safeRemaining * 0.45);
  const rawBottom = Math.floor(safeRemaining * 0.45);
  const bottomSpacing = Math.max(rawBottom, FOOTER_MIN);
  const topSpacing = Math.max(rawTop - Math.max(0, FOOTER_MIN - rawBottom), 400);
  const midSpacing = Math.max(safeRemaining - topSpacing - bottomSpacing, 0);
  return { topSpacing, midSpacing, bottomSpacing };
}

// Recipe R1：整页深底 + 左对齐（零嵌套表格）
function buildCoverR1(config) {
  const padL = 1200, padR = 800;
  const availableWidth = 11906 - padL - padR - 300;
  const { titlePt, titleLines } = calcTitleLayout(config.title, availableWidth, 40, 24);
  const titleSize = titlePt * 2;
  const spacing = calcCoverSpacing({
    titleLineCount: titleLines.length, titlePt,
    hasSubtitle: !!config.subtitle, hasEnglishLabel: !!config.englishLabel,
    metaLineCount: (config.metaLines || []).length, fixedHeight: 400,
  });
  const accentLeft = { style: BorderStyle.SINGLE, size: 8, color: P.accent, space: 12 };
  const children = [];
  children.push(new Paragraph({ spacing: { before: spacing.topSpacing } }));
  if (config.englishLabel) {
    children.push(new Paragraph({
      indent: { left: padL, right: padR }, spacing: { after: 500 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: P.accent, space: 8 } },
      children: [new TextRun({ text: config.englishLabel.split("").join("  "),
        size: 18, color: P.accent, font: { ascii: "Calibri", eastAsia: "SimHei" }, characterSpacing: 40 })],
    }));
  }
  for (let i = 0; i < titleLines.length; i++) {
    children.push(new Paragraph({
      indent: { left: padL },
      spacing: { after: i < titleLines.length - 1 ? 100 : 300, line: Math.ceil(titlePt * 23), lineRule: "atLeast" },
      children: [new TextRun({ text: titleLines[i], size: titleSize, bold: true,
        color: P.titleColor, font: { eastAsia: "SimHei", ascii: "Arial" } })],
    }));
  }
  if (config.subtitle) {
    children.push(new Paragraph({
      indent: { left: padL }, spacing: { after: 800 },
      children: [new TextRun({ text: config.subtitle, size: 24, color: P.subtitleColor,
        font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  for (const line of (config.metaLines || [])) {
    children.push(new Paragraph({
      indent: { left: padL + 200 }, spacing: { after: 80 },
      border: { left: accentLeft },
      children: [new TextRun({ text: line, size: 24, color: P.metaColor,
        font: { eastAsia: "Microsoft YaHei", ascii: "Arial" } })],
    }));
  }
  children.push(new Paragraph({ spacing: { before: spacing.bottomSpacing } }));
  children.push(new Paragraph({
    indent: { left: padL, right: padR },
    border: { top: { style: BorderStyle.SINGLE, size: 2, color: P.accent, space: 8 } },
    spacing: { before: 200 },
    children: [
      new TextRun({ text: config.footerLeft || "", size: 16, color: P.footerColor, font: { ascii: "Arial" } }),
      new TextRun({ text: "                                        " }),
      new TextRun({ text: config.footerRight || "", size: 16, color: P.footerColor, font: { ascii: "Arial" } }),
    ],
  }));
  return [new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    layout: TableLayoutType.FIXED,
    borders: allNoBorders,
    rows: [new TableRow({
      height: { value: 16838, rule: "exact" },
      children: [new TableCell({
        shading: { type: ShadingType.CLEAR, fill: P.bg }, borders: noBorders,
        children,
      })],
    })],
  })];
}

// ───────────────────────── 正文构件 ─────────────────────────
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 160, line: 380, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, size: 32, color: P.headingDark,
      font: { ascii: "Calibri", eastAsia: "SimHei" } })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 120, line: 340, lineRule: "atLeast" },
    children: [new TextRun({ text, bold: true, size: 28, color: P.headingDark,
      font: { ascii: "Calibri", eastAsia: "SimHei" } })],
  });
}
function body(text, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { firstLine: 420 },
    spacing: { line: 312, after: opts.after ?? 60 },
    children: runsFrom(text),
  });
}
// 支持 [文本, {bold:true}] 混排：传入字符串或数组
function runsFrom(text) {
  if (typeof text === "string") {
    return [new TextRun({ text, size: 24, color: P.body })];
  }
  return text.map(part => {
    if (typeof part === "string") return new TextRun({ text: part, size: 24, color: P.body });
    return new TextRun({ text: part.t, bold: !!part.b, size: 24, color: part.c || P.body });
  });
}
// 提示块：左侧青色竖线 + 浅青底，无首行缩进
function callout(label, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 240, right: 120 },
    spacing: { line: 312, before: 120, after: 160 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: P.tHeaderBg, space: 10 } },
    shading: { type: ShadingType.CLEAR, fill: P.surface },
    children: [
      new TextRun({ text: label + "  ", bold: true, size: 22, color: P.tHeaderBg }),
      ...runsFrom(text).map(r => r),
    ],
  });
}
function stepItem(refName, text) {
  return new Paragraph({
    numbering: { reference: refName, level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: 312, after: 60 },
    children: runsFrom(text),
  });
}
function caption(text) {
  return new Paragraph({
    keepNext: true,
    spacing: { before: 160, after: 80 },
    children: [new TextRun({ text, bold: true, size: 21, color: P.secondary,
      font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
  });
}
function link(text, url) {
  return new ExternalHyperlink({
    link: url,
    children: [new TextRun({ text, size: 24, color: "1284BA", underline: {} })],
  });
}
// 横线式表格（DM-1 表格色板）
function makeTable(headers, rows, widths) {
  const headerRow = new TableRow({
    tableHeader: true, cantSplit: true,
    children: headers.map((text, i) => new TableCell({
      width: { size: widths[i], type: WidthType.PERCENTAGE },
      shading: { type: ShadingType.CLEAR, fill: P.tHeaderBg },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        spacing: { line: 280 },
        children: [new TextRun({ text, bold: true, size: 21, color: P.tHeaderText,
          font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
      })],
    })),
  });
  const dataRows = rows.map((cells, r) => new TableRow({
    cantSplit: true,
    children: cells.map((text, i) => new TableCell({
      width: { size: widths[i], type: WidthType.PERCENTAGE },
      shading: { type: ShadingType.CLEAR, fill: r % 2 === 1 ? P.surface : "FFFFFF" },
      margins: { top: 70, bottom: 70, left: 120, right: 120 },
      children: [new Paragraph({
        spacing: { line: 280 },
        children: runsFrom(text).map(run => run),
      })],
    })),
  }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 6, color: P.tAccentLine },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: P.tAccentLine },
      left: NB, right: NB,
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: P.tInnerLine },
      insideVertical: NB,
    },
    rows: [headerRow, ...dataRows],
  });
}

// ───────────────────────── 编号列表定义 ─────────────────────────
const listRefs = [
  "list-prep", "list-desktop", "list-portable", "list-first-image", "list-acestep",
  "list-tts", "list-wan", "list-rescue", "list-roadmap",
];
const numberingConfig = listRefs.map(ref => ({
  reference: ref,
  levels: [{
    level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 620, hanging: 360 } } },
  }],
}));

const pgSize = { width: 11906, height: 16838 };
const bodyMargin = { top: 1440, bottom: 1440, left: 1701, right: 1417 };

globalThis.h1 = h1; globalThis.h2 = h2; globalThis.body = body; globalThis.callout = callout;
globalThis.caption = caption; globalThis.makeTable = makeTable; globalThis.link = link; globalThis.stepItem = stepItem;

function pageFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" })],
    })],
  });
}
function docHeader() {
  return new Header({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: P.tInnerLine, space: 4 } },
      children: [new TextRun({ text: "library-bootstrap 建库档位内部机理说明书", size: 18, color: "999999",
        font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" } })],
    })],
  });
}

const tocSectionChildren = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 480, after: 360 },
    children: [new TextRun({ text: "目  录", bold: true, size: 32,
      font: { eastAsia: "SimHei", ascii: "Calibri" }, color: P.headingDark })],
  }),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({
    spacing: { before: 200 },
    children: [new TextRun({
      text: "说明：本目录由域代码自动生成。若编辑文档后页码发生变化，请在目录上点击右键并选择「更新域」以刷新页码。",
      italics: true, size: 18, color: "888888",
    })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

const c1 = require("./content1.js");
const c2 = require("./content2.js");
const bodyChildren = [...c1.ch1, ...c1.ch2, ...c1.ch3, ...c1.ch4, ...c1.ch5, ...c1.ch6, ...c1.ch7,
  ...c2.ch8, ...c2.ch9, ...c2.ch10, ...c2.ch11, ...c2.ch12, ...c2.ch13, ...c2.appendixA, ...c2.appendixB];

const doc = new Document({
  creator: "library-bootstrap",
  title: "library-bootstrap 建库档位内部机理说明书",
  styles: {
    default: {
      document: {
        run: { font: { ascii: "Calibri", eastAsia: "Microsoft YaHei" }, size: 24, color: P.body },
        paragraph: { spacing: { line: 312 } },
      },
      heading1: {
        run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 32, bold: true, color: P.headingDark },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 },
      },
      heading2: {
        run: { font: { ascii: "Calibri", eastAsia: "SimHei" }, size: 28, bold: true, color: P.headingDark },
        paragraph: { spacing: { before: 260, after: 120 }, outlineLevel: 1 },
      },
    },
  },
  numbering: { config: numberingConfig },
  sections: [
    {
      properties: { page: { size: pgSize, margin: { top: 0, bottom: 0, left: 0, right: 0 } } },
      children: buildCoverR1({
        title: "library-bootstrap 建库档位内部机理说明书",
        subtitle: "L0-L9 十档架构 · 内部机理 · 论文出处 · 验收判据",
        englishLabel: "LIBRARY BOOTSTRAP MECHANISM SPEC",
        metaLines: [
          "适用对象：建库体系使用者、评审者与维护者",
          "覆盖范围：L0-L9 十档 · 28 项论文与资料题录 · 58 断言测试体系",
          "文档性质：v2.1 统合修订版 · 严肃模式 · 全文可溯源（W-016 降级声明见 11.6）",
          "编写时间：2026 年 9 月",
        ],
        footerLeft: "LIBRARY-BOOTSTRAP",
        footerRight: "2026.09",
      }),
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: pgSize, margin: bodyMargin,
          pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN } },
      },
      headers: { default: docHeader() },
      footers: { default: pageFooter() },
      children: tocSectionChildren,
    },
    {
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: pgSize, margin: bodyMargin,
          pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } },
      },
      headers: { default: docHeader() },
      footers: { default: pageFooter() },
      children: bodyChildren,
    },
  ],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("manual.docx", buf);
  console.log("OK manual.docx written, bytes=" + buf.length);
});
