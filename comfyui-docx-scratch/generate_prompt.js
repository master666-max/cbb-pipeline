// AI 绘画提示词工程教程 — docx 生成脚本（与 ComfyUI 教程同系列，DM-1 配色）
// 结构：Section1 封面(R1/DM-1) / Section2 目录(罗马页码) / Section3 正文(阿拉伯页码从1起)
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, PageNumber, NumberFormat, AlignmentType, HeadingLevel,
  WidthType, BorderStyle, ShadingType, SectionType, TableLayoutType,
  TableOfContents, PageBreak, LevelFormat, ExternalHyperlink,
} = require("docx");
const fs = require("fs");

// ───────── 调色板（DM-1 Deep Cyan） ─────────
const P = {
  bg: "162235", titleColor: "FFFFFF", subtitleColor: "B0B8C0",
  metaColor: "90989F", footerColor: "687078", accent: "37DCF2",
  headingDark: "0A1628", body: "1A2B40", secondary: "6878A0",
  tHeaderBg: "1B6B7A", tHeaderText: "FFFFFF", tAccentLine: "1B6B7A",
  tInnerLine: "C8DDE2", surface: "EDF3F5",
};
const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: NB, bottom: NB, left: NB, right: NB };
const allNoBorders = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };

// ───────── 封面工具函数（design-system 标准实现） ─────────
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

// ───────── 正文构件 ─────────
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
function runsFrom(text) {
  if (typeof text === "string") return [new TextRun({ text, size: 24, color: P.body })];
  return text.map(part => {
    if (typeof part === "string") return new TextRun({ text: part, size: 24, color: P.body });
    return new TextRun({ text: part.t, bold: !!part.b, size: 24, color: part.c || P.body });
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
function callout(label, text) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    indent: { left: 240, right: 120 },
    spacing: { line: 312, before: 120, after: 160 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: P.tHeaderBg, space: 10 } },
    shading: { type: ShadingType.CLEAR, fill: P.surface },
    children: [new TextRun({ text: label + "  ", bold: true, size: 22, color: P.tHeaderBg }), ...runsFrom(text)],
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
// 示例行：英文标签加粗突显
function tagRow(zh, en, note) { return [[{ t: zh, b: true }, "  " + en], note]; }
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
      children: [new Paragraph({ spacing: { line: 280 }, children: runsFrom(text) })],
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

// ───────── 编号列表（每个列表独立 reference，避免连号 bug） ─────────
const listRefs = [
  "list-engine", "list-iter", "list-tools", "list-practice",
];
const numberingConfig = listRefs.map(ref => ({
  reference: ref,
  levels: [{
    level: 0, format: LevelFormat.DECIMAL, text: "%1.",
    alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 620, hanging: 360 } } },
  }],
}));

// ───────── 正文内容 ─────────
const ch1 = [
  h1("第 1 章  开始之前"),
  body("这本教程只讲一件事：怎么把「我想要一张什么图」翻译成 AI 听得懂的话。它是《ComfyUI 零基础入门教程》的姐妹篇——那本解决「怎么把软件跑起来」，这本解决「为什么同一个模型，别人出的图就是比你好」。答案多半不在参数里，在提示词里。"),
  body("好消息是：提示词工程的原理跨软件通用。无论你用 ComfyUI、Stable Diffusion WebUI、即梦、LiblibAI 在线出图还是 Midjourney，本教程前八章的方法完全一致；第九章专门讲各家引擎的方言差异。教程里的示例以英文标签为主（SD 系模型的主流写法），所有英文词都配了中文解释，不需要背单词，用到时回来查表即可。"),
  h2("1.1 一个先入为主的纠偏"),
  body("很多新手以为提示词是「咒语」——背下一串神秘词汇就能出神图。实际上模型理解提示词的方式更接近「阅读理解」：它逐段读取你的描述，把每个词转化成画面特征，然后调和出一个各方都满意的结果。所以写提示词的本质是描述画面，不是念咒。你描述得越像一张已经存在的好照片或好插画，模型画得越好。"),
  h2("1.2 学完你能做到什么"),
  body("第一，拿到任何题材都能按万能公式组装出一条结构完整的提示词；第二，知道光影、镜头、风格这三类「性价比词汇」，用少量词大幅拉高画质观感；第三，会用负面提示词和权重微调修图；第四，掌握「固定种子、只改一词」的对照练习法，让每一次生图都变成一次学习。"),
  callout("建议", "本教程所有示例都建议亲手跑一遍。没有装本地 ComfyUI 的读者，用 LiblibAI 等在线平台同样能练，重点是动手。"),
];

const ch2 = [
  h1("第 2 章  万能公式：提示词的基本结构"),
  body("先给出全书最核心的一张公式，后面所有章节都是对它的展开：", { after: 80 }),
  callout("万能公式", "主体 + 细节动作 + 环境氛围 + 风格 + 画质词。按这个顺序用英文短语罗列，逗号分隔。"),
  h2("2.1 三条铁律"),
  body([
    { t: "铁律一：写看得见的东西。", b: true },
    { t: "「孤独的感觉」模型画不出来，「a person sitting alone on an empty bench at dusk」（黄昏空长椅上独坐的人）就能画出来。把情绪翻译成可见的画面元素，是提示词工程的第一课。" },
  ]),
  body([
    { t: "铁律二：顺序就是权重。", b: true },
    { t: "越靠前的词影响越大。你最想要的主体永远放第一个；画风词如果比主体还靠前，模型会先照顾画风而牺牲主体准确度。" },
  ]),
  body([
    { t: "铁律三：先准再多。", b: true },
    { t: "二十个精准的词胜过八十个堆砌的词。词与词会互相稀释，写太多反而四不像。SD1.5 和 SDXL 常规二十到四十个词足够；Flux 可以写更长的自然语言句子。" },
  ]),
  h2("2.2 一条完整提示词的解剖"),
  body("下面这条提示词逐段标注了公式五段的位置，读懂它就懂了全书结构：", { after: 80 }),
  callout("示例", "1girl, long silver hair, white dress（主体与细节）， sitting by the window, reading a book（动作）， warm sunlight, dust particles in the air（环境氛围）， anime style, soft color palette（风格）， highly detailed, best quality（画质词）"),
  h2("2.3 token：模型一次能读多少字"),
  body("模型读取提示词以 token（词块）为单位。SD1.5 和 SDXL 的文本编码器每 75 个 token 为一块，超出后继续分块，块数越多越容易被忽略或截断，所以控制长度本身就是控制质量。Flux 使用的 T5 编码器能读长句，这也是它能理解自然语言长描述的原因。新手阶段记住结论即可：SD 系别贪长，Flux 可以放开写。"),
  caption("表 2-1  公式五段速查"),
  makeTable(
    ["段落", "回答的问题", "示例"],
    [
      ["主体", "画谁 / 画什么", "1girl, orange cat, ancient temple"],
      ["细节动作", "长什么样 / 在干什么", "long silver hair, holding an umbrella, smiling"],
      ["环境氛围", "在哪里 / 什么时间天气", "cherry blossom street, dusk, light rain"],
      ["风格", "什么画风 / 什么媒介", "anime style, watercolor, film photography"],
      ["画质词", "成品质量声明", "highly detailed, masterpiece, 8k"],
    ],
    [18, 34, 48]
  ),
];

const ch3 = [
  h1("第 3 章  主体描述：把画面说清楚"),
  body("主体是提示词的地基。模型对主体的理解完全来自你的描述，你没说的它就自由发挥——而它的自由发挥往往就是翻车现场。"),
  h2("3.1 人物五件套"),
  body("写人物时按「外貌、服装、动作、表情、数量」五件套逐项检查，缺一项就等于把决定权交给运气。", { after: 80 }),
  caption("表 3-1  人物描述五件套"),
  makeTable(
    ["项目", "示例词", "提示"],
    [
      ["外貌", "long black hair, blue eyes, ponytail", "发型瞳色是动漫模型最吃的特征词"],
      ["服装", "white dress, school uniform, hoodie", "材质词如 silk, denim 能提升质感"],
      ["动作", "sitting, looking back, holding a paper cup", "一个动作即可，多个动作容易崩"],
      ["表情", "gentle smile, serious, closed eyes", "比动作更容易被忽略，值得单独写"],
      ["数量", "1girl, two boys, solo", "务必写清数量，见下方陷阱"],
    ],
    [14, 46, 40]
  ),
  callout("常见陷阱", "数量词的歧义：想要一个人就明确写 1girl 或 solo，只写 girls 时模型可能自作主张画出两三个人；写 two girls 又常常生成四人。数量是提示词里最不可靠的一类词，人物越多越乱，新手阶段尽量画单人。"),
  h2("3.2 场景与物品同理"),
  body("画风景、物品时，五件套换成「对象、材质、颜色、状态、环境」。例如一只猫：a fluffy orange cat（对象+材质+颜色）， sleeping, curled up（状态）， on a windowsill（环境）。材质词（fluffy、metallic、glass）和状态词（sleeping、broken、blooming）是提升真实感的杠杆，比堆画质词有效得多。"),
  h2("3.3 抽象需求的翻译练习"),
  body("遇到「治愈的感觉」「赛博朋克风」这类抽象要求，先翻译成可见元素再写词。治愈 = soft warm light, pastel colors, cozy room, plants；赛博朋克 = neon lights, rain, holographic signs, night city。平时刷到喜欢的图，练习在心里做一次反向翻译：这张图由哪些可见元素组成？这是提示词工程最核心的内功。"),
];

const ch4 = [
  h1("第 4 章  光影与氛围：性价比最高的一类词"),
  body("如果说主体决定「画什么」，光影决定「好不好看」。同一句话加上两三个光影词，画面质感往往脱胎换骨，而这只需要你多打几个词——所以光影词是全书画质性价比之王，务必背熟常用的一半。"),
  caption("表 4-1  常用光影词速查（中英对照）"),
  makeTable(
    ["中文", "英文", "效果"],
    [
      ["黄金时刻", "golden hour, sunset light", "暖调低角度阳光，人像神器"],
      ["电影感布光", "cinematic lighting, dramatic lighting", "强对比、氛围浓，出大片感"],
      ["轮廓光", "rim light, backlighting", "人物边缘一圈亮边，主体瞬间立体"],
      ["体积光", "volumetric lighting, god rays", "可见光束，教堂/森林场景必杀"],
      ["柔光", "soft lighting, diffused light", "皮肤通透，日系清新风标配"],
      ["霓虹光", "neon lights, glowing signs", "夜景、赛博朋克、雨夜街头的灵魂"],
      ["月光", "moonlight, starry night", "冷调夜景，配 fog 氛围更浓"],
      ["影棚光", "studio lighting, softbox", "电商产品图、证件感人像"],
      ["逆光", "backlit, silhouette", "剪影效果，情绪拉满"],
      ["窗光", "window light, light through curtains", "室内人像自然光，慵懒日常感"],
    ],
    [16, 40, 44]
  ),
  h2("4.1 时间与天气是氛围的免费调料"),
  body("dawn（黎明）、dusk（黄昏）、midnight（深夜）、overcast（阴天）、light rain（小雨）、fog（雾）、snowing（下雪）——这些词同时改变光线和情绪，一词多用。雨天配霓虹就是赛博朋克，雾天配森林就是神秘幽深，黄昏配逆光就是温情大片。"),
  h2("4.2 氛围情绪词的正确用法"),
  body("serene（宁静）、epic（史诗）、cozy（温馨）、melancholy（忧郁）、mysterious（神秘）这类氛围词可以用，但单独用效果弱，正确姿势是与具象光影词搭配：epic + volumetric lighting + dramatic sky 的组合，远比只写 epic 一个词稳定。抽象词是调味料，具象词才是主菜。"),
  callout("练习", "固定种子，给同一条提示词分别加 golden hour、neon lights、soft lighting 各生成一次，直观感受光影词的力量。这是理解本教程最快的实验。"),
];

const ch5 = [
  h1("第 5 章  构图与镜头：控制视角与景别"),
  body("不懂镜头词的新手，出的图永远是不远不近的「站姿全身照」。加一个景别词、一个视角词，画面立刻有了摄影师的章法。"),
  h2("5.1 景别：拍多近"),
  caption("表 5-1  景别与视角速查"),
  makeTable(
    ["类别", "英文", "效果"],
    [
      ["景别", "extreme close-up, close-up", "特写：面部细节、眼神戏"],
      ["景别", "upper body, portrait", "半身：人像最常用，五官手部最稳"],
      ["景别", "full body, wide shot", "全身/远景：看 outfit 和环境，脸易糊"],
      ["视角", "low angle", "仰拍：气场、压迫感、大长腿"],
      ["视角", "high angle, bird view", "俯拍：渺小感、可爱感"],
      ["视角", "dutch angle", "斜角：动感和不安感"],
      ["视角", "POV, first person view", "第一人称：代入感、游戏感"],
      ["镜头", "85mm, portrait lens", "人像镜头：背景虚化、五官舒服"],
      ["镜头", "bokeh, depth of field", "焦外虚化：主体突出的万能药"],
      ["镜头", "fisheye, macro shot", "鱼眼/微距：特殊效果慎用"],
      ["构图", "rule of thirds, centered composition", "三分法/居中：稳定耐看"],
      ["构图", "symmetrical composition", "对称构图：建筑、仪式感"],
    ],
    [12, 40, 48]
  ),
  h2("5.2 用法要点"),
  body("景别、视角、镜头三类词各选一个就够，贪多会互相打架。新手最稳的组合是 upper body + 85mm + bokeh——半身、人像镜头、背景虚化，五官清晰、主体突出，几乎不会翻车。风景照把主体换成场景即可：wide shot + rule of thirds + golden hour 就是合格的旅行风光配方。"),
  callout("提示", "想要全身照时接受一个现实：分辨率不变的情况下，全身像的脸部像素只有半身像的四分之一左右，脸糊是物理规律。追求脸部精致请优先半身和特写，或先生成半身再外扩（outpaint）。"),
];

const ch6 = [
  h1("第 6 章  风格与画质词"),
  h2("6.1 风格大类速查"),
  caption("表 6-1  常见风格关键词"),
  makeTable(
    ["风格", "关键词", "说明"],
    [
      ["写实摄影", "photorealistic, film photography, RAW photo", "配镜头词效果翻倍"],
      ["日系动漫", "anime style, manga style", "SD 系生态最繁荣的方向"],
      ["精致插画", "illustration, flat color, clean lineart", "扁平插画风，海报常用"],
      ["水彩", "watercolor, ink wash painting", "配留白词更出味道"],
      ["厚涂油画", "oil painting, impasto", "古典质感"],
      ["3D 渲染", "3D render, octane render, pixar style", "卡通 3D 或产品图"],
      ["像素风", "pixel art, 16-bit", "复古游戏感"],
      ["赛博朋克", "cyberpunk, neon, futuristic", "风格+光影双管齐下"],
    ],
    [16, 46, 38]
  ),
  body("风格词的第一原则：一次只主推一种。photorealistic 和 anime style 同时出现时，模型会输出两头不靠的诡异画面。想要「写实的动漫感」这类混合风格，正确做法是选一种为主，另一种降低权重（第 8 章）或干脆换本身就偏混合的大模型。"),
  h2("6.2 画质词的真相"),
  body("masterpiece, best quality, ultra detailed, 8k 这类词在 SD1.5 时代效果显著，几乎人人必加；到 SDXL 时代作用变得微妙——模型本身画质基线高了，加了不亏但不加也不明显；到了 Flux，这类词基本是心理安慰，它更吃你描述的具体程度。结论：SD1.5 加满，SDXL 随意，Flux 不必。"),
  h2("6.3 LoRA 的触发词"),
  body("使用画风 LoRA 时，作者通常会在说明页写明触发词（trigger word），比如某动漫风 LoRA 要求写 xxx style 才激活。下载 LoRA 后第一件事就是去模型页把触发词抄下来加进提示词，这是 LoRA 不生效的第一大原因。触发词一般放风格段的位置。"),
];

const ch7 = [
  h1("第 7 章  负面提示词：告诉模型别画什么"),
  body("负面提示词（Negative Prompt）是第二个输入框，作用是把不想要的特征「排除」出去。它和正向提示词同等重要，尤其对 SD1.5 这代模型，一份好的负面词能直接把手部畸形率降低一个档次。"),
  h2("7.1 通用起步包"),
  body("下面这组负面词适用于绝大多数 SD1.5 / SDXL 场景，直接抄走即可：", { after: 80 }),
  callout("负面词起步包", "worst quality, low quality, blurry, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed face, watermark, text, signature, jpeg artifacts"),
  h2("7.2 按需追加"),
  caption("表 7-1  常见问题与对应负面词"),
  makeTable(
    ["你想避免的", "追加负面词"],
    [
      ["多人乱入", "multiple people, extra girls, crowd"],
      ["背景杂乱", "cluttered background, complex background"],
      ["画面太亮/太暗", "overexposed / underexposed"],
      ["画风跑偏成写实", "photorealistic, realistic"],
      ["儿童不宜元素", "nsfw"],
      ["多余文字水印", "text, logo, watermark, username"],
    ],
    [40, 60]
  ),
  h2("7.3 负面 Embedding"),
  body("社区把一整套负面特征打包训练成了 embedding 文件（如动漫向常用的 EasyNegative、专治手部的 bad-hands-5），下载后放进 models/embeddings 目录，然后在负面框里只写一个词就能顶一长串。SD1.5 动漫玩家强烈推荐装 EasyNegative，这是回报率最高的一次下载。"),
  h2("7.4 各引擎差异"),
  body("Flux 没有独立负面输入框，靠提示词正面描述控制；Midjourney 用参数 --no 后面接排除词。SD 系（ComfyUI、WebUI）才有独立负面框。迁移引擎时记得这一点。"),
];

const ch8 = [
  h1("第 8 章  权重与进阶语法"),
  h2("8.1 权重语法"),
  body("当某个词「怎么都不听话」时，显式调权重是最后手段。ComfyUI 和 WebUI 通用语法：把词加括号并写数值，如 (blue eyes:1.3) 表示把蓝眼睛的重要性调到 1.3 倍；低于 1 是削弱，如 (background:0.8)。简写形式：一层圆括号约等于 1.1 倍，方括号 [word] 约等于 0.9 倍。"),
  callout("经验", "权重范围建议控制在 0.8 到 1.4 之间。超过 1.4 经常过饱和、颜色溢出甚至画面崩坏；低于 0.8 基本等于没写。先用词序调权重（往前挪），不奏效再上括号。"),
  h2("8.2 进阶语法一览"),
  body([
    { t: "AND 分支：", b: true },
    { t: "a cat AND a dog 允许两个主体并行强调，比逗号并列更强，但也更容易失控，新手少用。" },
  ]),
  body([
    { t: "BREAK 分段：", b: true },
    { t: "在长提示词中插入 BREAK 会强制在此处分块，用于控制 75 token 分块边界的归属，属于精调技巧。" },
  ]),
  body([
    { t: "嵌入 LoRA 语法：", b: true },
    { t: "<lora:名称:0.8> 可在提示词里直接挂 LoRA 并指定强度，ComfyUI 中通常改由独立 LoRA 节点控制，更直观。" },
  ]),
  h2("8.3 长度策略总结"),
  body("SD1.5：正向 20-30 词 + 负面起步包；SDXL：正向 25-40 词，负面可精简；Flux：自然语言整句，几十词起步，把镜头、光线、情绪完整写成一段小作文反而效果最好。原则不变：先准再多，词序即权重。"),
];

const ch9 = [
  h1("第 9 章  不同引擎的方言差异"),
  body("同一套原理，不同引擎有不同的「方言」。换平台时看这张表就够了。", { after: 80 }),
  caption("表 9-1  各引擎提示词写法对照"),
  makeTable(
    ["引擎", "写法", "示例", "要点"],
    [
      ["SD1.5 / SDXL", "英文标签罗列", "1girl, silver hair, ...", "本教程主体；负面框独立"],
      ["Flux", "自然语言长句", "A girl with silver hair sits by ...", "不吃标签堆砌；无负面框"],
      ["国产中文模型（Qwen-Image、即梦等）", "直接写中文", "一个银发少女坐在窗边看书，黄昏光线", "中文直书，讲清画面即可"],
      ["Midjourney", "短句 + 参数", "silver hair girl by window --ar 3:4 --stylize 250", "参数控制比例与风格强度；--no 排除"],
      ["在线平台（LiblibAI 等）", "同 SD 系", "见平台模板", "可直接抄平台上成图的提示词"],
    ],
    [22, 20, 34, 24]
  ),
  h2("9.1 迁移心法"),
  stepItem("list-engine", "先判断引擎属于标签式还是自然语言式：SD 系标签式，Flux 和国产中文模型偏自然语言，MJ 介于两者之间。"),
  stepItem("list-engine", "标签式引擎之间（SD1.5 与 SDXL）提示词可以基本通用；标签式转自然语言式时，把罗列改写成完整句子，补上主谓宾。"),
  stepItem("list-engine", "反向迁移（自然语言转标签式）时，把句子拆成短语并按万能公式排序，删掉连接词。"),
  body("一个偷懒技巧：让 AI 聊天助手帮你做格式转换——把你的中文想法连同目标引擎一起告诉它，让它按本教程的公式输出。转换质量通常不错，但生成后再自己按第 2 章铁律检查一遍。"),
];

const ch10 = [
  h1("第 10 章  实战：一张图的五轮迭代"),
  body("本章用一个真实题材演示从「一句话」到「成片」的完整迭代过程。每一轮只解决一个问题——这也是你自己出图时应有的节奏。题材：一只猫。"),
  stepItem("list-iter", "第 0 轮（基线）：a cat。结果可想而知：一只姿势随机、光线平淡、毫无记忆点的猫。这就是不做提示词工程的起点。"),
  stepItem("list-iter", "第 1 轮（补主体）：a fluffy orange cat, sleeping, curled up。加了材质、颜色、动作、状态，猫有了样子，但背景仍然是随机糊弄的白墙。"),
  stepItem("list-iter", "第 2 轮（补环境光影）：...on a wooden windowsill, warm afternoon sunlight, dust particles in the air。位置、光源、氛围到位，画面开始有故事感。"),
  stepItem("list-iter", "第 3 轮（补镜头风格）：加 close-up, shallow depth of field, film photography。特写 + 浅景深 + 胶片质感，观感直接上台阶。"),
  stepItem("list-iter", "第 4 轮（负面与微调）：负面框加上 blurry, extra limbs, watermark；发现毛色偏灰，把 (orange:1.2) 提一点权重。收敛，出片。"),
  h2("10.1 固定种子对照法：最快的自学神器"),
  body("种子（Seed）是生成过程的随机数根源：种子相同，同一提示词永远得到同一张图。因此把种子固定住，每次只改一个词，出图之间的差异就完全归功于这个词——这是学习提示词效率最高的方法，比看十篇教程都有用。每天花十五分钟做这个实验，两周后你对每个词的「手感」会脱胎换骨。"),
  h2("10.2 迭代心法"),
  body("每轮只改一类东西，出四张对比；方向对了就保留，错了就回退。切忌一次改五个地方——出图变好你不知道该谢谁，变坏也不知道该怪谁。把这个纪律守住，你的进步速度就是别人的三倍。"),
];

const ch11 = [
  h1("第 11 章  翻车急救表"),
  body("出图不满意时，先对号入座再动手。这张表覆盖新手九成的翻车场景。", { after: 80 }),
  caption("表 11-1  症状与急救"),
  makeTable(
    ["症状", "第一 suspect", "处理"],
    [
      ["手/脸崩坏", "负面词不足", "补 bad hands, bad anatomy；SD1.5 装 bad-hands-5"],
      ["和提示词对不上", "词太多互相稀释", "删到 25 词以内；主体放最前；提高关键词权重"],
      ["人数不对", "数量词缺失或歧义", "明确写 1girl / solo；尽量画单人"],
      ["背景乱成一团", "背景无描述", "明确写背景，或负面加 cluttered background，或用景深虚化"],
      ["颜色又灰又脏", "光影词缺失", "补光源方向与色调词（golden hour / soft light）"],
      ["两张风格混搭打架", "风格词冲突", "一次只主推一种风格，另一种降权或删除"],
      ["画质词毫无作用", "引擎不吃这套", "Flux 换成更具体的描述；SDXL 换模型比堆词有效"],
      ["同词不同图差很大", "种子随机", "正常现象；固定种子才能复现与对照"],
      ["LoRA 完全没效果", "缺触发词或强度太低", "查模型页触发词；LoRA 强度调到 0.7-1.0"],
    ],
    [24, 28, 48]
  ),
];

const ch12 = [
  h1("第 12 章  工具与练习路线"),
  h2("12.1 三个提效工具"),
  stepItem("list-tools", "反推提示词：把任意图片喂给 WD14 tagger（ComfyUI 插件）或平台的「图生图/反推」功能，它会猜出这张图的提示词。看到好图就反推，是最快的积累方式。"),
  stepItem("list-tools", "AI 助手代笔：把中文想法告诉聊天 AI，要求按「主体+细节+环境+风格+画质」公式输出英文标签，再人工按第 2 章铁律修剪。"),
  stepItem("list-tools", "抄成图：Civitai 和 LiblibAI 每张成图旁边都展示完整提示词与参数，直接抄来跑，再逐词替换成自己的题材。"),
  h2("12.2 三阶段练习路线"),
  stepItem("list-practice", "临摹期（第 1 周）：抄平台上十张你喜欢的好图提示词，固定种子逐词删改，感受每个词的作用。"),
  stepItem("list-practice", "改写期（第 2-3 周）：拿临摹熟的提示词当模板，替换主体与场景，保持光影镜头结构，验证公式的可迁移性。"),
  stepItem("list-practice", "原创期（第 4 周起）：只看参考图，先在心里做反向翻译，再徒手写完整提示词，最后与原图的提示词对比找差距。"),
  h2("12.3 收尾"),
  body([
    "提示词工程的全部秘密就是第 2 章那三条铁律加一张万能公式，其余章节都是词库和纪律。配套软件操作请看姐妹篇《ComfyUI 零基础入门教程》；更权威的节点与参数文档见 ",
    link("docs.comfy.org/zh", "https://docs.comfy.org/zh/"),
    "。每天十五分钟固定种子实验，一个月后你会回来感谢现在开始动手的自己。",
  ]),
];

// ───────── 组装文档 ─────────
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
      children: [new TextRun({ text: "AI 绘画提示词工程教程", size: 18, color: "999999",
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

const bodyChildren = [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...ch7, ...ch8, ...ch9, ...ch10, ...ch11, ...ch12];

const doc = new Document({
  creator: "Prompt Engineering Tutorial",
  title: "AI 绘画提示词工程教程",
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
        title: "AI 绘画提示词工程教程",
        subtitle: "从一句话到一张大片：生图提示词的写法与心法",
        englishLabel: "PROMPT ENGINEERING GUIDE",
        metaLines: [
          "适用对象：想让出图质量明显提升的 AI 绘画初学者",
          "适用引擎：ComfyUI / SD WebUI / Flux / 国产中文模型 / Midjourney",
          "姐妹篇：《ComfyUI 零基础入门教程》",
          "编写时间：2026 年 9 月",
        ],
        footerLeft: "PROMPT ENGINEERING TUTORIAL",
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
  fs.writeFileSync("output_prompt.docx", buf);
  console.log("OK output_prompt.docx written, bytes=" + buf.length);
});
