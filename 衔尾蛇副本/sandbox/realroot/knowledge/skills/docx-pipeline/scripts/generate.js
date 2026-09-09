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

// ───────────────────────── 正文内容 ─────────────────────────
const ch1 = [
  h1("第 1 章  开始之前"),
  body("这本教程写给完全没有接触过 AI 绘画、AI 音乐、AI 视频的初学者。你不需要会编程，不需要懂人工智能原理，只需要一台能正常使用的 Windows 电脑和一点耐心。读完并跟着做完前六章，你就能在自己的电脑上装好 ComfyUI，并且亲手生成第一批 AI 图片、歌曲/配音和短视频。"),
  body("ComfyUI 是目前全世界最流行的 AI 生成图形界面之一。它的特点是把整个生成过程画成一张由节点和连线组成的工作流图，你可以清楚地看到一张图是怎么一步步被画出来的，也能随意替换模型、调整参数。刚开始会觉得节点图有点吓人，但请放心：新手阶段你只需要使用别人做好的模板，把模型换成自己的、提示词改成自己写的，就能出结果。"),
  h2("1.1 你将学会什么"),
  body("第一，把 ComfyUI 完整地装进你的电脑并完成中文设置；第二，从国内下载渠道拿到第一批模型，跑通文生图工作流；第三，用 ACE-Step 生成一首带人声的歌，用 TTS 节点做一段配音；第四，用 Wan 2.2 生成一段几秒钟的视频；第五，遇到显存不足、节点报红、模型加载失败这些常见问题时，知道去哪里找答案。"),
  h2("1.2 新手名词卡：先把黑话翻译成人话"),
  body("AI 生成圈的教程经常满屏黑话，这里先把最常见的名词一次性解释清楚。看不懂没关系，后面用到时会反复回来查这张表。", { after: 80 }),
  caption("表 1-1  新手常见名词速查"),
  makeTable(
    ["名词", "人话解释"],
    [
      ["模型 / Checkpoint", "存放在硬盘上的一个能力包文件，相当于一位画师、歌手或摄影师的全部手艺，动辄几个 GB。"],
      ["工作流 / Workflow", "一张节点连线图，描述从输入提示词到输出结果的完整流水线。可以保存成文件分享给别人。"],
      ["节点 / Node", "工作流里的一个功能格子，每个格子只干一件事，比如读模型、写提示词、存图片。"],
      ["提示词 / Prompt", "你打给 AI 的描述文字。写得越具体，结果越接近你想要的样子。"],
      ["LoRA", "小体积的微调补丁，几十到几百 MB，叠在大模型上让画面变成某种固定画风或人物。"],
      ["VAE", "把数据在「像素」和「潜在空间」之间来回翻译的解码器，缺了它出图会发灰发花。"],
      ["量化 / fp8 / GGUF", "把大模型压缩瘦身的技术，体积和显存占用变小，画质略降，低显存显卡的救命稻草。"],
      ["显存 / VRAM", "显卡上的临时工作内存。模型要整个或分块装进显存才能跑，爆显存就是最常见的报错来源。"],
      ["采样步数 / Steps", "画面从噪声逐渐变清晰的迭代次数，一般 20 到 30 步。太少画面糊，太多纯浪费时间。"],
      ["自定义节点 / 插件", "社区写的功能扩展包。装上之后 ComfyUI 才能做音乐、语音、视频等额外的事情。"],
    ],
    [22, 78]
  ),
  h2("1.3 学习心态：先跑通，再弄懂"),
  body("新手最大的误区是想先把每个参数都搞明白再动手。正确的顺序恰恰相反：先原封不动地照着教程跑出第一个结果，获得成就感，然后再逐个节点去理解它在做什么。ComfyUI 的每一个模板都可以随便改、随便试，最坏情况就是删掉工作流重新打开一份，不会有任何损失。"),
];

const ch2 = [
  h1("第 2 章  你的电脑能玩吗：硬件与准备"),
  body("本地跑 AI 生成，最重要的硬件是显卡（GPU），其次是内存和硬盘。本章以一台 NVIDIA RTX 5070 Ti Laptop（12GB 显存）+ 32GB 内存的笔记本为实测基准，这也是目前主流游戏本的常见配置。你的显卡不用和它一模一样，只要显存不低于表中参考值，就能获得相应的体验。"),
  h2("2.1 显存需求速查"),
  caption("表 2-1  各类生成任务的显存需求（以 12GB 显卡为基准实测参考）"),
  makeTable(
    ["任务类型", "新手推荐模型", "显存参考", "12GB 显卡体验"],
    [
      ["生图（入门）", "SDXL 系列大模型", "6-8GB", "流畅，出一张图约 10-30 秒"],
      ["生图（高质量）", "Flux.1-dev（fp8 / GGUF 量化）", "8-13GB", "流畅，建议用量化版"],
      ["生成歌曲", "ACE-Step（3.5B）", "6-8GB", "流畅"],
      ["语音合成 / 音色克隆", "IndexTTS、CosyVoice 等", "4-6GB", "流畅"],
      ["生视频（入门）", "Wan 2.2 TI2V-5B（fp8）", "约 10-12GB", "可以跑，速度较慢"],
      ["生视频（进阶）", "Wan 2.2 14B（GGUF 量化）", "10-14GB", "可以跑，需要耐心"],
    ],
    [20, 34, 18, 28]
  ),
  body("简单总结：12GB 显存玩生图和生音频非常从容，玩生视频则需要用量化模型并把分辨率和时长控制得保守一些。显存低于 8GB 的显卡优先玩生图和生音频，视频建议直接看第 9 章的云端方案。"),
  h2("2.2 硬盘和内存"),
  body("所有模型建议放在固态硬盘（SSD）上，加载速度差别巨大。模型文件普遍很大：一个 SDXL 大模型约 6.5GB，Flux 系列全套（主模型 + 文本编码器 + VAE）约 15GB，视频模型动辄 10-25GB。玩得越广，磁盘占用越大，建议至少预留 200GB 的 SSD 空间。内存建议 16GB 起步，32GB 更稳妥。"),
  h2("2.3 动手前先装好三样东西"),
  stepItem("list-prep", "NVIDIA 显卡驱动：到 NVIDIA 官网或用 NVIDIA App 把驱动更新到最新版本，老驱动会直接导致生成报错。"),
  stepItem("list-prep", "7-Zip：免费的解压软件，ComfyUI 便携版是 7z 格式压缩包，系统自带的解压工具打不开它。"),
  stepItem("list-prep", "一个顺手的浏览器：ComfyUI 的界面在浏览器里运行，Edge 或 Chrome 都可以。"),
  callout("注意", "下载模型和安装包时尽量避开满速下载高峰，部分国外渠道下载几 GB 的文件容易中途断掉。优先使用第 4 章推荐的国内渠道。"),
  h2("2.4 RTX 50 系显卡用户必读（5070 Ti / 5080 / 5090 等）"),
  body([{
    t: "如果你的显卡是 RTX 50 系（Blackwell 架构），有一个其他教程很少提到的大坑：这类显卡必须使用基于 CUDA 12.8 编译的 PyTorch（即 PyTorch 2.7 及以上版本），否则启动就会报错 sm_120 is not compatible，或者干脆只用 CPU 慢慢爬。",
  }]),
  body("好消息是，只要按本教程安装，这个坑会自动绕过去：ComfyUI 官方 Desktop 安装包和 2025 年中之后发布的便携包，内置的 PyTorch 都已经是兼容版本。你唯一要记住的是：不要自己手动降级或重装 Python 环境里的 PyTorch；也暂时不要安装 xformers 这类老版本加速插件，它们与 RTX 50 系不兼容。"),
];

const ch3 = [
  h1("第 3 章  安装 ComfyUI"),
  body("ComfyUI 在 Windows 上有两种主流装法：官方 Desktop 桌面版和绿色便携版。对新手强烈推荐 Desktop 版，一路下一步即可；便携版则胜在不写注册表、整个文件夹可以随意搬动。两种方式效果完全一样，选一种装就好。"),
  h2("3.1 方式一：官方 Desktop 桌面版（推荐）"),
  stepItem("list-desktop", "打开官网 comfy.org，点击 Download 按钮，选择 Windows 版安装包下载；如果打不开官网，也可以到 docs.comfy.org 中文文档的安装页面找到下载链接。"),
  stepItem("list-desktop", "双击安装包，像装普通软件一样一路下一步。安装位置建议选一个空间充足的 SSD 分区。"),
  stepItem("list-desktop", "首次启动时，程序会自动下载并配置运行环境（Python、PyTorch 等），需要联网并等待几分钟到十几分钟，期间不要断网。"),
  stepItem("list-desktop", "进入主界面后，打开设置（左上角菜单或右上角齿轮），在 Language（语言）里选择「中文 / 简体中文」，界面立即变成中文。"),
  stepItem("list-desktop", "在设置里找到模型路径（Model Paths）选项，把模型目录指到一个空间大的盘，比如 D 盘，以后所有模型都放这里。"),
  h2("3.2 方式二：Windows 便携版（绿色免安装）"),
  stepItem("list-portable", "到 ComfyUI 官方 GitHub 仓库的 Releases 页面（或官方文档给出的链接），下载 ComfyUI_windows_portable 压缩包。注意认准带 cu128 标记的新版本，RTX 50 系显卡务必不要下老的 cu121 版本。"),
  stepItem("list-portable", "用 7-Zip 把压缩包解压到一个纯英文路径，例如 D:\\ComfyUI，路径里不要有中文或空格，能避免很多奇怪问题。"),
  stepItem("list-portable", "双击文件夹里的 run_nvidia_gpu.bat，会弹出一个黑色命令行窗口，这是 ComfyUI 的本体，使用期间不要关闭它。"),
  stepItem("list-portable", "稍等片刻，浏览器会自动打开 http://127.0.0.1:8188，这就是 ComfyUI 的操作界面。以后每次使用都是：双击 bat，等浏览器打开，开玩。"),
  h2("3.3 装完第一件事：认识界面和模板库"),
  body("无论哪种安装方式，进入界面后先熟悉四样东西：画布（中间的空白区域，工作流图就摆在这里）、节点（图里的一个个格子）、队列按钮（右侧 Queue，点它就是开始生成）、模板库（菜单 Workflow 里的 Browse Templates，官方自带的新手宝库，按图片、音频、视频分类的现成工作流都在里面）。"),
  body("再记住一个救命习惯：右上角的保存按钮（或 Ctrl+S）可以把当前画布存成一个 json 工作流文件。改出来的好配置随手存一份，搞砸了随时重新打开，也可以直接把这个文件分享给别人。"),
  callout("提示", "新版 ComfyUI 已经内置了 Manager 管理器和中文语言包，不需要额外安装。如果你发现界面上没有 Manager 按钮或没有中文选项，说明版本较旧，请在 Manager 或官方渠道更新到最新版。"),
  h2("3.4 更新 ComfyUI"),
  body("AI 生成社区迭代极快，保持更新能少踩很多坑。Desktop 版在程序内就有检查更新的入口；便携版重新下载新版压缩包解压覆盖，或在 ComfyUI 文件夹里运行自带的 update 脚本即可。"),
];

const ch4 = [
  h1("第 4 章  第一次生图"),
  body("生图是一切的基础，也是最简单的一步。整个流程只有三件事：下载模型、把模型放到正确的文件夹、套用模板点生成。"),
  h2("4.1 模型去哪里下载"),
  body("模型文件动辄几个 GB，下载渠道直接决定你的体验。下面按「国内优先」排序，前三个不需要任何网络工具就能满速下载。", { after: 80 }),
  caption("表 4-1  模型下载渠道一览"),
  makeTable(
    ["渠道", "网址", "特点", "需要科学上网"],
    [
      ["魔搭 ModelScope", "modelscope.cn", "阿里旗下的国内模型仓库，速度快、免费，主流模型基本都有", "不需要"],
      ["hf-mirror", "hf-mirror.com", "HuggingFace 的国内镜像，拿着模型英文名来搜即可", "不需要"],
      ["LiblibAI 哩布哩布", "www.liblib.art", "国内模型与工作流社区，中文页面，还能在线出图", "不需要"],
      ["Civitai", "civitai.com", "全球最大的模型社区，画风模型和成套工作流最多最全", "需要"],
      ["HuggingFace", "huggingface.co", "模型官方发布仓库，最全但需要网络工具", "需要"],
    ],
    [22, 22, 40, 16]
  ),
  h2("4.2 第一个模型怎么选"),
  body([
    { t: "推荐两条路线，任选其一即可。", b: false },
  ]),
  body([
    { t: "路线 A（最省心）：SDXL 系列大模型。", b: true },
    { t: "单个文件约 6.5GB，一个文件走天下，不需要额外的文本编码器和 VAE，显存要求低，中文教程也最多。在 LiblibAI 或 Civitai 搜 SDXL checkpoint，挑一个人气高的下载，例如 DreamShaper XL、Juggernaut XL 等经典款。" },
  ]),
  body([
    { t: "路线 B（画质上限高）：Flux.1-dev。", b: true },
    { t: "目前社区公认质量最好的开放模型之一，但下载时要分清两种形态。「整合版」是一个约 17GB 的 checkpoint 文件，文本编码器和 VAE 都已打包在里面，放进 checkpoints 目录一个文件就能用；「分体版」是主模型（约 12GB 的 fp8 版或 Q4 约 7GB 的 GGUF 量化版）加三个配件（clip_l、t5xxl fp8 文本编码器和 ae.safetensors 这支 VAE），要分别放进表 4-2 对应的目录。12GB 显存属于刚好够用，建议优先选 GGUF 量化版。Flux 官方模型为非商用许可，个人玩耍没有问题。" },
  ]),
  callout("建议", "第一张图用路线 A。SDXL 装一个文件就能出图，成就感来得最快；玩顺了再上 Flux 挑战高质量。"),
  h2("4.3 模型放哪里：目录对照表"),
  body("ComfyUI 靠目录来识别模型，放错位置是新手第一大报错来源。以下目录都在你的 ComfyUI 模型根目录下（Desktop 版可以在设置里一键打开这个文件夹）。", { after: 80 }),
  caption("表 4-2  模型文件摆放对照"),
  makeTable(
    ["文件类型", "放入目录", "说明"],
    [
      ["SDXL 等整合大模型", "models/checkpoints", "一个文件包含全部，最省心"],
      ["Flux / 视频模型主文件", "models/diffusion_models", "旧版本目录名叫 unet，通用"],
      ["文本编码器", "models/text_encoders", "旧名 clip；Flux 需要 clip_l 与 t5xxl"],
      ["VAE", "models/vae", "Flux 的文件名叫 ae.safetensors"],
      ["LoRA 画风补丁", "models/loras", "叠在大模型上用"],
      ["ControlNet 模型", "models/controlnet", "控图用，进阶再玩"],
      ["放大 / 超分模型", "models/upscale_models", "把小图放大变清晰"],
    ],
    [30, 34, 36]
  ),
  body("放好文件后回到 ComfyUI，点击节点上模型下拉框旁边的刷新按钮（小圆圈箭头图标），或者干脆重启一次 ComfyUI，新模型就会出现在列表里。"),
  h2("4.4 跑通你的第一张图"),
  stepItem("list-first-image", "打开菜单 Workflow → Browse Templates 模板库，在基础分类里选择最简单的文生图（Text to Image）模板。"),
  stepItem("list-first-image", "模板加载后，检查有没有红色节点。红色代表缺少模型或插件，按节点提示把对应文件放进表 4-2 的目录再点刷新。"),
  stepItem("list-first-image", "在模型加载节点（Load Checkpoint 或类似名字）的下拉框里选中你刚下载的模型。"),
  stepItem("list-first-image", "在正向提示词框里用英文写你想画的内容，例如：a cute orange cat wearing an astronaut suit, floating in space, stars background, ultra detailed, best quality。"),
  stepItem("list-first-image", "点击右侧 Queue 按钮（或按 Ctrl+Enter）。第一次生成需要先把模型载入显存，等一两分钟很正常，之后的出图速度才代表真实水平。"),
  stepItem("list-first-image", "生成的图片自动保存在 ComfyUI 目录下的 output 文件夹，画布上也能直接看到结果。"),
  h2("4.5 提示词写法入门"),
  body("动笔写提示词之前，先认识一个重要节点：出图尺寸由 Empty Latent Image（空潜空间图，名字可能略有出入）节点控制，改它上面的 width 和 height 就是改图片大小。SDXL 的原生训练分辨率在 1024×1024 一带，竖图可以试 832×1216、横图 1216×832；大幅偏离这个范围（比如直接拉到 2048）画面容易崩。想放大出高清大图，正确姿势是先生成小图，再用放大模型（表 4-2 里的 upscale_models 目录）二次放大。"),
  body("SDXL 这类模型主要吃英文提示词，通用公式是：主体 + 细节动作 + 环境氛围 + 风格 + 画质词。例如：1girl, long silver hair, reading a book by the window, warm sunlight, anime style, highly detailed。逗号分隔每个要素，想强调就把对应的词往前放。负面提示词（Negative Prompt）用来排除你不想要的东西，例如低质量、畸形手指等常用排除词，模板里一般已经写好，先不用动。"),
  body("如果不想写英文，也有两条路：用支持中文提示词的国产模型（如 Qwen-Image 系列，可直书中文描述）；或先用翻译软件把中文翻成英文再粘贴。写提示词没有标准答案，多试多改，感受每个词对画面的影响，是最快的学习方式。"),
  callout("常见困惑", "出图和提示词对不上？先检查是不是在用别人工作流的同时忘了换模型；同一个提示词每次出图都不同是正常现象，固定 Seed（种子）数字才能复现同一张图。"),
];

const ch5 = [
  h1("第 5 章  第一次生音频"),
  body("ComfyUI 的音频能力主要靠两条路线：一是官方已原生支持的音乐生成模型 ACE-Step，能写歌词生成完整歌曲；二是社区 TTS（语音合成）自定义节点，把文字变成配音，还能克隆指定人的音色。两类任务对显存要求都不高，是低配显卡玩家的高性价比玩法。"),
  h2("5.1 用 ACE-Step 生成一首歌"),
  body("ACE-Step 是由 ACE Studio 与阶跃星辰联合开源的音乐生成基础模型，输入风格标签和歌词，几分钟内就能产出一首带人声的完整歌曲，支持中文歌词。它走的是「描述歌曲 + 填歌词」的思路，不需要你会任何乐器；社区还有更新的 1.5 版本，基本玩法一致，新手从哪个版本入门都可以。", { after: 80 }),
  stepItem("list-acestep", "在 ComfyUI 模板库（Browse Templates）的音频分类里找 ACE-Step 模板；如果你的版本模板库里没有，就用 Manager 搜索 ACE-Step 相关节点包安装，再从插件说明页复制工作流。"),
  stepItem("list-acestep", "按模板页面或节点说明的指引下载模型文件（主模型约 7GB，国内可在魔搭或 hf-mirror 搜 ACE-Step），放到节点指定的目录。"),
  stepItem("list-acestep", "在风格标签（tags）节点里写曲风，例如：chinese pop, female vocal, emotional, ballad。"),
  stepItem("list-acestep", "在歌词节点里填入你自己写的或 AI 帮你写的歌词，可以用结构标签控制段落，例如 verse、chorus。"),
  stepItem("list-acestep", "点击 Queue 生成，首次要加载模型请耐心等待。完成后在工作流里接一个保存音频节点，成片保存在 output 目录。"),
  h2("5.2 用 TTS 节点做配音和音色克隆"),
  body("TTS（文字转语音）在 ComfyUI 里以社区自定义节点的形式存在，常用的有基于 B 站开源 IndexTTS 的 ComfyUI-Index-TTS、基于阿里 CosyVoice 的 CosyVoice-ComfyUI 等。它们的共同玩法是：准备一段干净的人声参考音频（几秒即可），节点就能模仿这个音色，把你输入的文字朗读出来，非常适合给 AI 视频或电子书配音。", { after: 80 }),
  stepItem("list-tts", "打开 Manager，搜索并安装 Index-TTS 或 CosyVoice 对应的自定义节点包，装完按提示重启 ComfyUI。"),
  stepItem("list-tts", "按节点仓库首页说明下载模型文件并放到指定目录，这一步务必严格照着 README 做，路径放错是 TTS 报错的最主要原因。"),
  stepItem("list-tts", "新建空白工作流，双击画布空白处搜索并添加 TTS 相关节点，接上参考音频和文字输入。"),
  stepItem("list-tts", "输入要朗读的文本，点 Queue 生成，导出音频文件。"),
  callout("注意", "TTS 类节点普遍依赖额外的 Python 库，安装后第一次运行时如果控制台报缺少模块，按报错信息里的模块名用 pip 安装即可，或在 Manager 里找该插件的依赖修复选项。这类问题都有人踩过坑，把报错原句拿去搜索基本都能找到答案。"),
  h2("5.3 生音频的三个实用提醒"),
  body("第一，生成结果默认保存在 output 目录下，不同节点的子文件夹略有差异，找不到就去 output 里翻。第二，参考音频的质量直接决定克隆效果，尽量用无背景音乐、无噪音的干声。第三，音乐和配音可以和生图联动：先出图，再配音，第 6 章生成视频时把素材串起来，就是你自己的 AI 短片流水线。"),
];

const ch6 = [
  h1("第 6 章  第一次生视频"),
  body("视频生成是当前对显卡最挑剔的玩法，但 12GB 显存已经可以完整体验。本章主角是阿里通义万相开源的 Wan 2.2 系列：它是目前社区生态最好、ComfyUI 官方原生支持并自带模板的视频模型，质量在国内开源阵营里也属第一梯队。"),
  h2("6.1 12GB 显存的选型策略"),
  caption("表 6-1  视频模型选择参考"),
  makeTable(
    ["模型", "特点", "12GB 显存怎么跑"],
    [
      ["Wan 2.2 TI2V-5B", "5B 轻量版，文生视频和图生视频都行，720p 分辨率", "fp8 版本直接跑，官方模板开箱即用，速度较慢"],
      ["Wan 2.2 14B 系列", "画质上限更高，分文生视频与图生视频两个模型", "下载 GGUF 量化版（Q4/Q5），配合压缩分辨率使用"],
      ["Wan 2.1 1.3B", "更老一代的轻量版", "显存要求最低，追求速度可以选它"],
      ["LTX-Video 系列", "以速度见长的轻量视频模型", "同档位里速度最快，几秒出一段短片，画质相对一般"],
    ],
    [24, 38, 38]
  ),
  h2("6.2 用 Wan 2.2 5B 生成第一段视频"),
  stepItem("list-wan", "打开模板库搜索 Wan2.2，选择 TI2V-5B 对应的文生视频或图生视频模板。"),
  stepItem("list-wan", "按模板指引下载 5B 模型的 fp8 版本（10GB 上下的级别，国内用魔搭或 hf-mirror 搜 Wan2.2），放进指定的模型目录并刷新。"),
  stepItem("list-wan", "图生视频模板会推荐先上传一张图片作为首帧；用第 4 章生成的图最方便，画面的稳定性也明显好过纯文字生视频。"),
  stepItem("list-wan", "写一段描述动作和镜头的提示词，例如：the camera slowly pushes in, the girl turns her head and smiles, cinematic lighting。"),
  stepItem("list-wan", "点 Queue 开始生成。视频生成是逐帧计算的，一段几秒钟的视频在 12GB 显卡上通常需要几分钟到十几分钟，期间显存会被吃得比较满，属于正常现象。"),
  stepItem("list-wan", "完成后视频保存在 output 目录，模板里的视频合并节点会自动把帧序列合成为可播放的 mp4 文件。"),
  h2("6.3 进阶：14B 大模型与量化玩法"),
  body("想冲击更高画质时，选择 14B 版本的 GGUF 量化模型（社区 QuantStack 团队发布的 Q4、Q5 版本），配合 Manager 安装的 ComfyUI-GGUF 节点加载。量化把显存占用压到 12GB 可承受的范围，代价是生成速度更慢、细节略有损失。建议从 480p 分辨率、5 秒时长起步，跑通后再逐步加码。"),
  h2("6.4 显存优化技巧"),
  body("视频生成爆显存时，按顺序尝试这几招：把模型换成更低精度的量化版本（fp8、GGUF Q4）；调低分辨率和总帧数，先把时长压到 5 秒以内；确认已用最新版 ComfyUI（新版本的显存管理会自动把放不下的部分挪到内存）；关掉浏览器硬件加速和其他占显存的程序；最后才是重启 ComfyUI 清空显存缓存。"),
  callout("预期管理", "本地 12GB 显卡做视频，定位是「能跑、能玩、能出片」，但一段视频等十分钟是常态，批量做长视频请直接看第 9 章云端方案。心态放平，先出第一段再说。"),
];

const ch7 = [
  h1("第 7 章  必装插件与效率工具"),
  body("ComfyUI 的强大一半来自社区插件。新手阶段不需要贪多，下面这几个覆盖九成场景，全部通过 Manager 搜索名字即可安装。", { after: 80 }),
  caption("表 7-1  新手必装插件清单"),
  makeTable(
    ["插件", "作用", "获取方式"],
    [
      ["ComfyUI-Manager", "插件与模型的一站式管理器，还能一键安装缺失节点", "新版 ComfyUI 已内置，界面上找 Manager 按钮"],
      ["中文语言包", "界面完整汉化", "设置 → Language → 简体中文"],
      ["ComfyUI-GGUF", "加载 GGUF 量化模型，低显存救星", "Manager 搜索 ComfyUI-GGUF"],
      ["KJNodes", "常用工具节点合集，图像处理万金油", "Manager 搜索 ComfyUI-KJNodes"],
      ["VideoHelperSuite", "视频帧序列的加载、预览与合并导出", "Manager 搜索 VideoHelperSuite"],
    ],
    [26, 44, 30]
  ),
  h2("7.1 常用快捷键"),
  caption("表 7-2  高频操作快捷键"),
  makeTable(
    ["操作", "方法"],
    [
      ["开始生成（入队）", "Ctrl + Enter"],
      ["搜索任意节点", "双击画布空白处，输入名字"],
      ["缩放画布", "按住 Ctrl 滚动滚轮"],
      ["框选多个节点", "在空白处按住左键拖拽"],
      ["删除选中节点", "Delete 键"],
      ["加载别人的工作流", "把工作流 json 文件（或带工作流信息的成图）直接拖进画布"],
      ["刷新模型列表", "点节点上模型下拉框旁的刷新按钮，或重启 ComfyUI"],
    ],
    [40, 60]
  ),
  body("一个重要的省钱习惯：网上看到好看的 AI 图或视频，先问有没有工作流文件。ComfyUI 生成的图片和视频默认内嵌工作流信息，直接把成图拖进画布，整套流程就还原出来了，这是最快的学习方式。"),
];

const ch8 = [
  h1("第 8 章  常见报错自救表"),
  body("报错是玩 ComfyUI 的日常，绝大多数问题都是老问题。遇到报错先别慌，对照下表找症状，九成情况能在五分钟内解决。", { after: 80 }),
  caption("表 8-1  新手常见报错速查"),
  makeTable(
    ["症状", "原因", "解法"],
    [
      ["报错 CUDA out of memory", "显存不够用", "换量化模型；降分辨率和帧数；重启 ComfyUI 清缓存"],
      ["报错含 sm_120 is not compatible", "RTX 50 系遇到了旧版 PyTorch", "使用新版 Desktop 安装包或 cu128 便携包重装"],
      ["节点整个是红色", "缺少自定义节点或节点依赖", "打开 Manager 用 Install Missing Custom Nodes 一键装"],
      ["下拉框里找不到刚下的模型", "模型放错目录或没刷新", "对照表 4-2 检查目录，按 R 刷新或重启"],
      ["报错 value not in list", "工作流引用的模型名与实际不符", "在节点下拉框里重新选择实际存在的模型"],
      ["下载的文件只有几百 MB 或解压报错", "下载不完整", "换国内渠道重新下载，核对文件大小与发布页一致"],
      ["出图全黑、全灰或大花块", "VAE 缺失或与模型不匹配", "补齐对应 VAE 文件；确认步数没有设得过低"],
      ["插件装完没有任何变化", "装完没重启或依赖缺失", "重启 ComfyUI；看控制台红字按提示补装依赖"],
      ["生成速度突然变得极慢", "显存溢出回退到了 CPU", "按 6.4 节的显存优化技巧逐项检查"],
    ],
    [30, 30, 40]
  ),
  h2("8.1 通用三步自救法"),
  stepItem("list-rescue", "看控制台：Desktop 版打开日志窗口，便携版看那个黑色命令行窗口，找到最新的红色报错文字，这是最重要的一手信息。"),
  stepItem("list-rescue", "复制报错原句去搜索，或直接发给 AI 助手让它解释。英文报错不用怕，原句搜索命中率极高，你在中文社区里绝不是第一个踩坑的人。"),
  stepItem("list-rescue", "检查最近一次改动：报错前你换了什么模型、装了什么插件，回退那个改动通常就能恢复。"),
];

const ch9 = [
  h1("第 9 章  云端兜底方案"),
  body("显卡不够、想先尝鲜大模型、或者临时用别人的电脑时，云端平台是很好的替代方案：浏览器里打开就能用，模型和算力都是现成的。国内平台注册即用，部分提供免费额度。", { after: 80 }),
  caption("表 9-1  常用云端生成平台"),
  makeTable(
    ["平台", "特点", "收费模式"],
    [
      ["LiblibAI 哩布哩布", "国内最大的 AI 创作社区，在线出图、在线 ComfyUI、海量模型与工作流", "每日免费额度 + 会员"],
      ["RunningHub", "国内的 ComfyUI 云算力平台，把工作流放到云端跑，适合批量出视频", "按量计费，有体验额度"],
      ["Tensor.Art", "在线模型与工作流平台，界面友好，手机浏览器也能用", "每日免费额度 + 会员"],
      ["HuggingFace Spaces", "各模型的官方在线演示页，免部署试玩", "免费为主"],
    ],
    [24, 52, 24]
  ),
  body("云端和本地并不是二选一的关系。常见的搭配是：平时在本机玩生图和音频；想跑 14B 全精度视频模型、批量生成、或者显卡被工作占用时，把任务丢到云端；模型选型也建议先在云端试跑确认效果满意，再花几 GB 硬盘空间下载到本地。"),
];

const ch10 = [
  h1("第 10 章  学习资源与进阶路线"),
  h2("10.1 值得收藏的资源"),
  body([
    "官方中文文档（安装、节点说明、各模型官方教程）：", 
    link("docs.comfy.org/zh", "https://docs.comfy.org/zh/"),
  ], { after: 40 }),
  body([
    "官方示例工作流仓库（按模型分类的最小可跑模板）：",
    link("github.com/Comfy-Org/ComfyUI_examples", "https://github.com/Comfy-Org/ComfyUI_examples"),
  ], { after: 40 }),
  body([
    "ComfyUI Wiki 中文教程站（从安装到进阶的系统教程）：",
    link("comfyui-wiki.com", "https://comfyui-wiki.com"),
  ], { after: 40 }),
  body("B 站是最适合中文新手的学习阵地，直接搜索 ComfyUI 教程、Wan2.2、Flux、ACE-Step 等关键词，跟着视频一步步做。工作流方面，LiblibAI 的工作流广场和 Civitai 的工作流区有大量可直接拖入画布使用的成品。"),
  h2("10.2 推荐的进阶路线"),
  stepItem("list-roadmap", "第一阶段：把本教程的生图、生音频、生视频三条线各自完整跑通一遍，建立手感。"),
  stepItem("list-roadmap", "第二阶段：打开别人的工作流，逐个节点研究它做了什么，尝试改参数、换模型、加 LoRA。"),
  stepItem("list-roadmap", "第三阶段：学习 ControlNet 控图（让姿势、构图、线条完全听你的）和图生图的常规组合技。"),
  stepItem("list-roadmap", "第四阶段：把图片、配音、视频生成串成完整流水线，做出你自己的 AI 短片；有兴趣再学习训练属于自己画风和音色的专属模型。"),
  body("最后再次强调新手心法：先跑通，再弄懂；先模板，再魔改；先出片，再完美。祝你在 ComfyUI 的世界里玩得开心。"),
];

// ───────────────────────── 组装文档 ─────────────────────────
const pgSize = { width: 11906, height: 16838 };
const bodyMargin = { top: 1440, bottom: 1440, left: 1701, right: 1417 };

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
      children: [new TextRun({ text: "ComfyUI 零基础入门教程", size: 18, color: "999999",
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

const bodyChildren = [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8, ...ch9, ...ch10];

const doc = new Document({
  creator: "ComfyUI Tutorial",
  title: "ComfyUI 零基础入门教程",
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
    { // Section 1：封面（边距 0，无页码无页脚）
      properties: { page: { size: pgSize, margin: { top: 0, bottom: 0, left: 0, right: 0 } } },
      children: buildCoverR1({
        title: "ComfyUI 零基础入门教程",
        subtitle: "生图 · 生音频 · 生视频 · 云端方案，一本教会你",
        englishLabel: "COMFYUI BEGINNER GUIDE",
        metaLines: [
          "适用对象：完全没接触过 AI 生成的初学者",
          "实测基准：NVIDIA RTX 5070 Ti Laptop（12GB 显存）",
          "内容范围：本地安装 · 生图 · 生音频 · 生视频 · 报错自救",
          "编写时间：2026 年 9 月",
        ],
        footerLeft: "COMFYUI TUTORIAL",
        footerRight: "2026.09",
      }),
    },
    { // Section 2：目录（罗马页码）
      properties: {
        type: SectionType.NEXT_PAGE,
        page: { size: pgSize, margin: bodyMargin,
          pageNumbers: { start: 1, formatType: NumberFormat.UPPER_ROMAN } },
      },
      headers: { default: docHeader() },
      footers: { default: pageFooter() },
      children: tocSectionChildren,
    },
    { // Section 3：正文（阿拉伯页码从 1 起）
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
  fs.writeFileSync("output.docx", buf);
  console.log("OK output.docx written, bytes=" + buf.length);
});
