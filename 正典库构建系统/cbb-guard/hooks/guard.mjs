#!/usr/bin/env node
/**
 * guard.mjs — cbb-guard PreToolUse 守门钩子（U-G02 · 裁定 2026-09-24）
 *
 * 规则（裁定原文见《形态升级-工单-插件化-20260923.md》U-G02；分级=二拦二警照准）：
 *   拦 A  冻结线"覆盖已有文件"——原位保全语义：冻结目录下**新建文件放行、覆盖已有文件拦截**；
 *         Bash 的 rm/del/mv/clean 指向冻结线 → 拦。覆盖范围：迷深实战-{本体库,工作区} 目录
 *         与 迷深实战-{工单,发车件,BUILD-STATE}.md 三件。
 *   拦 B  红区文件 **Write 整体覆盖**——cbb/contracts/*.schema.json、两份在案工单、决策账本身；
 *         Edit 放行（追加段靠 Edit 的 old_string 语义）。
 *   旁通  env CBB_HOOK_BYPASS=<裁定引用> 非空 → 放行，并自动追加"旁通"条目到 决策账.jsonl。
 *         无账引用的绕过 = 硬拦（账引用解锁是唯一合法旁通道）。
 *   其余  exit 0 静默（不加噪音；example-plugin 的 additionalContext 模式会产生每调一行噪音，弃用）。
 *
 * 自检（正负对照）：
 *   printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"D:/…/迷深实战-本体库/ledger.jsonl"}}' | node guard.mjs   → exit 2
 *   printf '%s' '{"tool_name":"Write","tool_input":{"file_path":"D:/…/新建件.md"}}' | node guard.mjs                      → exit 0
 */
import fs from "node:fs";
import path from "node:path";

// 可移植：项目根由 env CBB_GUARD_ROOT 指定（另一台机器/另一路径直接设这个变量即可）；
// 缺省回落到本机原路径（向后兼容，不改既有行为）。
const ROOT = (process.env.CBB_GUARD_ROOT || "d:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/")
  .replace(/\\/g, "/").toLowerCase().replace(/\/+$/, "") + "/";  // 归一并**保证**尾斜杠（缺则补）
const DECISION_LOG = ROOT + "决策账.jsonl";
const FROZEN_DIRS = [ROOT + "迷深实战-本体库/", ROOT + "迷深实战-工作区/"];
const FROZEN_FILES = [ROOT + "迷深实战-工单.md", ROOT + "迷深实战-发车件.md",
                      ROOT + "迷深实战-build-state.md"];
// 红区（Write 拦）：契约 schema + 两份在案工单（本体构筑-工单 亦为在案工单）+ 决策账
const REDZONE_WRITE = [ROOT + "cbb/contracts/", ROOT + "本体构筑-工单.md",
                       ROOT + "迷深实战-工单.md", ROOT + "决策账.jsonl"];

const norm = (p) => String(p || "").replace(/\\/g, "/").toLowerCase();
const isFrozen = (p) => FROZEN_DIRS.some((d) => p.startsWith(d)) || FROZEN_FILES.includes(p);
const isRedzoneWrite = (p) => REDZONE_WRITE.some((d) => p === d || p.startsWith(d));

let raw = "";
process.stdin.setEncoding("utf8");
for await (const chunk of process.stdin) raw += chunk;
let input = {};
try { input = raw.trim() ? JSON.parse(raw) : {}; } catch { process.exit(0); } // 解析失败放行（不因钩子坏而阻断）

const tool = (input.tool_name || input.toolName || "").toLowerCase();
const ti = input.tool_input || {};
const rawPath = String(ti.file_path || ti.path || "");
const fp = norm(rawPath);
const cmd = String(ti.command || "");

const bypass = (process.env.CBB_HOOK_BYPASS || "").trim();

if (process.env.CBB_GUARD_DEBUG) {  // 排查用：CBB_GUARD_DEBUG=1 时打印比对内部值
  process.stderr.write(`[cbb-guard:debug] tool=${tool} ROOT=${ROOT} fp=${fp}\n` +
    `[cbb-guard:debug] frozen=${isFrozen(fp)} redzone_write=${isRedzoneWrite(fp)} exists=${fs.existsSync(rawPath)}\n`);
}

// 旁通形态（0.1.1 修 G-3）：
//   绑定式  CBB_HOOK_BYPASS='<目标路径前缀>=<裁定引用>'  ⇒ 只放行落在该前缀下的那一次越权
//   全局式  CBB_HOOK_BYPASS='<裁定引用>'                ⇒ 旧行为，保留兼容；每次使用打一行警告，入账记 scope
// 用第一个 "=" 切分：路径前缀不含 "="，裁定引用里的 "=" 全部归引用本身。
const BP = (() => {
  const i = bypass.indexOf("=");
  if (i > 0) {
    const prefix = norm(bypass.slice(0, i).trim());
    const ref = bypass.slice(i + 1).trim();
    return { mode: "bound", prefix, ref: ref || "（空引用：请写 <前缀>=<裁定引用>）" };
  }
  return { mode: "global", prefix: null, ref: bypass };
})();
const covers = (target) => !!BP.prefix &&
  (target.startsWith(BP.prefix) || target.startsWith(BP.prefix.replace(/\/+$/, "") + "/") ||
   (tool === "bash" && target.includes(BP.prefix.replace(/\/+$/, ""))));

// 门找不到自己的根 = 门不存在。这一条只提醒不拦（拦会把无关写也打死），但必须说出来：
// 换机器/换项目时 CBB_GUARD_ROOT 没设对，是这套判定唯一会整体静默失效的方式。
if (bypass && !fs.existsSync(ROOT)) {
  process.stderr.write(
    `[cbb-guard] 警告：旁通已设，但 CBB_GUARD_ROOT 归一值不存在（${ROOT}）\n` +
    `  ⇒ 本次判定看不到任何冻结/红区面，旁通也无账可落；请核对根路径（不带尾斜杠亦可）。\n`);
}

function bypassLog(action, target, extra) {
  try {
    fs.appendFileSync(DECISION_LOG, JSON.stringify({
      type: "hook-bypass", ref: BP.ref, action, target, ...extra, at: new Date().toISOString(),
    }) + "\n");
    return fs.existsSync(DECISION_LOG) ? null : "写后回读：账文件不存在";
  } catch (e) { return e && e.code ? e.code : String(e).slice(0, 60); }
}

function deny(v, extraHint) {
  // 回执必带"命中第几条规则 + 触发片段"：不带命中面的拦截无法排障，
  // 容易被读成宿主故障（0.1.1 修 G-1 时补）。
  process.stderr.write(`[cbb-guard] 拦截：${v.msg}\n` +
    `[cbb-guard] 命中：${v.rule}${v.hit ? " · " + v.hit : ""}\n` +
    (extraHint ? `[cbb-guard] ${extraHint}\n` : "") +
    (bypass
      ? `[cbb-guard] 旁通已设但形态=${BP.mode}${BP.prefix ? `（只覆盖 ${BP.prefix}）` : ""}——` +
        `要放行本次越权请用绑定式：CBB_HOOK_BYPASS='<目标前缀>=<裁定引用>'\n`
      : `（如为已裁定操作：设 CBB_HOOK_BYPASS='<目标前缀>=<裁定引用>' 后重试，旁通将自动入决策账）\n`));
  process.exit(2);
}

function refuseBypassBecauseNoTrail(err, v) {
  // 0.1.1 修 G-2：留痕写不进去就**不放行**。原实现把 appendFileSync 包在 try/catch 里静默吞掉，
  // 于是「CBB_GUARD_ROOT 指错 / 决策账不可写 / 目录不存在」这类环境错配下，旁通越过了全部规则
  // 却一条账都没留——唯一该有痕迹的越权通道，恰好在这种时候没有痕迹（为空被读成通过）。
  process.stderr.write(
    `[cbb-guard] 拒绝旁通：留痕写不进去，无留痕不越权（0.1.0 的行为是静默放行）\n` +
    `  落点：${DECISION_LOG}\n  原因：${err}\n` +
    `  处置：核对 CBB_GUARD_ROOT 是否指向真实项目根（当前归一值 ${ROOT}），且决策账须可追加\n` +
    `  被挡下的这次越权：${v.rule} · ${v.target.slice(0, 100)}\n`);
  process.exit(2);
}

// ---- 违规判定：先判违规，再决定要不要走旁通 ----
// （0.1.0 的顺序相反：只要 CBB_HOOK_BYPASS 非空就在所有规则之前放行一切并逐条入账——
//   于是 ① 旁通不绑定它要授权的那次操作，② 设着 env 时连完全无关的 Write/Bash 也往决策账里灌条目。）
const isBash = tool === "bash";
// 清理动词的识别（0.1.1 修 G-1）。原式 /(rm|del|rmdir|rd|move|ren|erase)\b/ 只锚**词尾**，
// 词首不设界 ⇒ record / third / guard / platform / warm / standard / confirm 这些以 rm|rd|del
// 收尾的普通英文词全命中；只要同一条命令里还提到 迷深实战-*，就被当成"清理冻结线"拦掉。
// 现改两条：① 动词必须是**独立词**（前后都不接单词字符），② 真删除的 API 写法单独认。
const RM_WORD = /(?<![\w.~-])(?:rm|rmdir|del|erase|rd|move|ren|mv|unlink)(?![\w-])/i;
const RM_API = /\b(?:os\.(?:remove|unlink|replace|rename)|shutil\.(?:rmtree|move|remove)|fs\.(?:unlinkSync|unlink|rmSync|rm|rename)|Remove-Item)\b/i;
const FROZEN_NAME = /迷深实战-(本体库|工作区|工单|发车件|build-state)/i;

function findViolation() {
  const rmHit = cmd.match(RM_WORD) || cmd.match(RM_API);
  const frozenHit = cmd.match(FROZEN_NAME);
  if (isBash && rmHit && frozenHit) {
    const from = Math.max(0, rmHit.index - 14);
    return { rule: "拦A/bash", target: cmd.slice(0, 200),
      msg: "冻结线清理/移动操作（迷深实战-* 为资料档，原位保全）",
      hit: `动词「${rmHit[0]}」于 …${cmd.slice(from, rmHit.index + rmHit[0].length + 14)}… × 冻结名「${frozenHit[0]}」` };
  }
  if ((tool === "write" || tool === "edit" || tool === "multiedit") && isFrozen(fp)) {
    // 原位保全语义：冻结目录下**新建放行、覆盖已有拦截**
    if (fs.existsSync(rawPath) || fs.existsSync(fp)) {
      return { rule: "拦A/write", target: fp,
        msg: `冻结线文件覆盖（${fp.slice(ROOT.length)}）——迷深实战线已冻结为资料档（原位保全），新建文件不受限`,
        hit: "路径落在冻结清单内且文件已存在" };
    }
  }
  if (tool === "write" && isRedzoneWrite(fp)) {
    return { rule: "拦B/write", target: fp,
      msg: `红区文件 Write 整体覆盖（${fp.slice(ROOT.length)}）——契约/在案工单/决策账只许追加段（Edit）与账引用旁通`,
      hit: "路径前缀命中红区清单" };
  }
  return null;
}

const v = findViolation();
if (!v) process.exit(0);                      // 无越权：静默放行，也不入账
if (!bypass) deny(v);
if (BP.mode === "bound" && !covers(v.target)) {
  deny(v, `绑定式引用只覆盖「${BP.prefix}」，本次目标不在其下 ⇒ 不放行`);
}
const err = bypassLog(`${tool} @ ${v.target.slice(0, 160)}`, v.target, {
  scope: BP.mode === "global" ? "global(全规则)" : `bound:${BP.prefix}`, rule: v.rule,
});
if (err) refuseBypassBecauseNoTrail(err, v);   // 无留痕不越权（G-2）
if (BP.mode === "global") {
  process.stderr.write(
    `[cbb-guard] 提醒：形态=global 的旁通会放行本会话**此后所有** Write/Edit/Bash 越权，且逐条入账。\n` +
    `  本次已放行：${v.rule} · ${v.target.slice(0, 80)}\n` +
    `  只授权这一件请改：CBB_HOOK_BYPASS='<目标前缀>=<裁定引用>'\n`);
}
process.exit(0);
