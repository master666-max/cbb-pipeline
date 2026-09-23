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

const ROOT = "d:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/";
const DECISION_LOG = "d:/zcode专用！！！！危险！！！！！！！！！/正典库构建系统/决策账.jsonl";
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

function bypassLog(action, target) {
  try {
    fs.appendFileSync(DECISION_LOG, JSON.stringify({
      type: "hook-bypass", ref: bypass, action, target, at: new Date().toISOString(),
    }) + "\n");
  } catch { /* 账写不进不阻断（但旁通要求账引用，此属异常环境，保守放行） */ }
}

function deny(msg) {
  process.stderr.write(`[cbb-guard] 拦截：${msg}\n` +
    (bypass ? `[cbb-guard] 旁通引用已设（${bypass}），本应放行——请核对引用是否对应真实裁定\n` :
      `（如为已裁定操作：设 CBB_HOOK_BYPASS=<裁定引用> 后重试，旁通将自动入决策账）\n`));
  process.exit(2);
}

// 旁通（有账引用）：放行一切并留账
if (bypass) {
  bypassLog(`${tool} @ ${fp || cmd.slice(0, 80)}`, fp || cmd.slice(0, 80));
  process.exit(0);
}

// ---- 拦 A：冻结线 ----
const isBash = tool === "bash";
if (isBash && /(rm|del|rmdir|rd|move|ren|erase)\b/i.test(cmd) &&
    /迷深实战-(本体库|工作区|工单|发车件|build-state)/i.test(cmd)) {
  deny("冻结线清理/移动操作（迷深实战-* 为资料档，原位保全）");
}
if ((tool === "write" || tool === "edit" || tool === "multiedit") && isFrozen(fp)) {
  const exists = fs.existsSync(rawPath) || fs.existsSync(fp);
  if (exists) {
    deny(`冻结线文件覆盖（${fp.slice(ROOT.length)}）——迷深实战线已冻结为资料档（原位保全），新建文件不受限`);
  }
  // 新文件：允许（additive）
}

// ---- 拦 B：红区 Write 整体覆盖 ----
if (tool === "write" && isRedzoneWrite(fp)) {
  deny(`红区文件 Write 整体覆盖（${fp.slice(ROOT.length)}）——契约/在案工单/决策账只许追加段（Edit）与账引用旁通`);
}

process.exit(0);
