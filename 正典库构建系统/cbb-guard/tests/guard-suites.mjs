#!/usr/bin/env node
/**
 * guard-suites.mjs — cbb-guard 的回归夹具（38 例），自包含、零外部依赖
 *
 * 跑法：node cbb-guard/tests/guard-suites.mjs [guard.mjs 路径]     默认取 ../hooks/guard.mjs
 * 旧版基线对照：git show ecb15f2:cbb-guard/hooks/guard.mjs > /tmp/guard-0.1.0.mjs
 *              node cbb-guard/tests/guard-suites.mjs /tmp/guard-0.1.0.mjs
 *   实测 2026-09-24：本版 38/38 合预期；v0.1.0 只有 22/38（不符 16 ＝ 误伤 7／漏拦 1／
 *   拦截缺命中面 1／旁通作用域 5／旁通路数 2）
 *
 * 全部写入只发生在一个临时夹具根里（跑完自删），不碰真实项目根；
 * CBB_GUARD_ROOT 逐次注入，所以"根路径指错"这类环境错配也能判。
 *
 * 夹具自避一坑：临时目录名**不得**含以 rm/rd/del 收尾的词（如 cbb-guard-…）。旧版那条 sloppily
 * 正则会把这种名字当清理动词命中，于是"该拦"例靠**误伤**假通过，把真漏拦（shutil.rmtree）盖掉；
 * 换成 cbb-hook-fixture- 之后该项才如实报不符。
 *
 * 三组：
 *   ① 主套 26 ＋附检 2 —— 真危险 13（rm／del／move／&& 后 rm／sudo rm／xargs rm／os.remove／
 *       shutil.rmtree／Remove-Item／Write 覆盖既有冻结件／红区 schema 整写／红区前缀下新件／红区决策账）
 *       ＋设计放行 13（词尾 rm|rd 的普通英文词 7 条＋冻结目录下新建／红区 Edit 追加／无冻结名的 rm／
 *       无冻结名的词尾 rd／只读工具／无关键词）＋附检（非 JSON 输入不阻断、拦截回执带命中面）
 *   ② 路数 5 —— 账可写则留痕／账不可写（账位做成目录）则拒放／根不存在则拒放且告警／不凭空建目录／无旁通不漏账
 *   ③ 作用域 5 —— 绑定式覆盖→放且入账带 scope+rule／绑定式不覆盖→照拦／挂 env 做无关写→放行但不入账／
 *       全局式→放＋入账记 global＋打提醒
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const GUARD = path.resolve(process.argv[2] || path.join(import.meta.dirname, "..", "hooks", "guard.mjs"));
if (!fs.existsSync(GUARD)) { console.error("guard 件不存在：" + GUARD); process.exit(2); }

const FIX = path.join(os.tmpdir(), "cbb-hook-fixture-" + process.pid).replace(/\\/g, "/");
const LED = FIX + "/决策账.jsonl";
const FROZEN_FILE = FIX + "/迷深实战-本体库/ledger.jsonl";      // 已存在的冻结件 ⇒ 覆盖必拦
const SCHEMA = FIX + "/cbb/contracts/record.schema.json";
const GHOST = FIX + "-ghost";                                   // 故意不存在

function fresh(opts = {}) {
  fs.rmSync(FIX, { recursive: true, force: true });
  fs.rmSync(GHOST, { recursive: true, force: true });
  fs.mkdirSync(path.join(FIX, "迷深实战-本体库"), { recursive: true });
  fs.mkdirSync(path.join(FIX, "cbb/contracts"), { recursive: true });
  fs.writeFileSync(FROZEN_FILE, "{}\n");
  fs.writeFileSync(SCHEMA, "{}\n");
  if (opts.ledgerIsDir) fs.mkdirSync(LED); else fs.writeFileSync(LED, "");
}
const call = (tool, payload, env = {}) => spawnSync("node", [GUARD], {
  input: JSON.stringify({ tool_name: tool, tool_input: payload }), encoding: "utf8",
  env: { ...process.env, CBB_GUARD_ROOT: FIX + "/", ...env },
});
const withBypass = (bypass, payload, tool = "write", env = {}) =>
  call(tool, payload, { CBB_HOOK_BYPASS: bypass, ...env });
const ledger = () => fs.readFileSync(LED, "utf8").split("\n").filter(Boolean);

let bad = 0, n = 0;
const chk = (ok, group, msg) => { n++; if (!ok) { bad++; console.log(`!! 不符 [${group}] ${msg}`); } };

/* ---------- ① 主套 ---------- */
fresh();   // 冻结件必须先存在：拦A 的语义是"覆盖已有才拦"，夹具不在就等于放行（那不是缺陷）
const DANGEROUS = [
  [`rm -rf ${FIX}/迷深实战-本体库`, "rm -rf 冻结目录"],
  [`del ${FIX}/迷深实战-工单.md`, "del 冻结件"],
  [`move ${FIX}/迷深实战-发车件.md x.bak`, "move 冻结件"],
  [`git status && rm -rf ${FIX}/迷深实战-本体库`, "&& 之后 rm"],
  [`sudo rm -rf ${FIX}/迷深实战-本体库`, "sudo rm"],
  [`xargs rm -rf < list.txt # ${FIX}/迷深实战-本体库`, "xargs rm"],
  [`py -c "import os;os.remove('${FIX}/迷深实战-工单.md')"`, "os.remove"],
  [`py -c "import shutil;shutil.rmtree('${FIX}/迷深实战-本体库')"`, "shutil.rmtree"],
  [`powershell Remove-Item ${FIX}/迷深实战-工单.md`, "Remove-Item"],
];
for (const [cmd, note] of DANGEROUS)
  chk(call("bash", { command: cmd }).status === 2, "主套/该拦", note);
chk(call("write", { file_path: FROZEN_FILE }).status === 2, "主套/该拦", "Write 覆盖既有冻结件");
chk(call("write", { file_path: SCHEMA }).status === 2, "主套/该拦", "红区 schema 整写");
chk(call("write", { file_path: FIX + "/cbb/contracts/新建件.json" }).status === 2, "主套/该拦", "红区前缀下新文件");
chk(call("write", { file_path: LED }).status === 2, "主套/该拦", "红区决策账整写");

const INNOCENT = [
  [`ls ${FIX}/迷深实战-本体库 # cbb-guard 排查`, "词尾 rd（guard，含插件自身名）"],
  [`py x.py --store ${FIX}/迷深实战-本体库 | tee third.log`, "词尾 rd（third）"],
  [`git log --oneline -- ${FIX}/迷深实战-本体库 > record.txt`, "词尾 rd（record）"],
  [`cat ${FIX}/迷深实战-本体库/a.json | head -3 # platform 版`, "词尾 rm（platform）"],
  [`git commit -m '补 ${FIX}/迷深实战-工单.md 的 warm 段'`, "词尾 rm（warm）"],
  [`py y.py ${FIX}/迷深实战-本体库 # standard confirm`, "词尾 rd/rm（standard/confirm）"],
  [`git remote remove origin && echo ${FIX}/迷深实战-工单.md`, "remote remove 不是删文件"],
];
for (const [cmd, note] of INNOCENT)
  chk(call("bash", { command: cmd }).status === 0, "主套/应放", note);
chk(call("write", { file_path: FIX + "/迷深实战-本体库/新件.json" }).status === 0, "主套/应放", "冻结目录下新建（additive）");
chk(call("edit", { file_path: SCHEMA }).status === 0, "主套/应放", "红区 Edit 追加段");
chk(call("bash", { command: `rm -rf ${path.join(os.tmpdir(), "cbb-x").replace(/\\/g, "/")}` }).status === 0, "主套/应放", "有 rm 无冻结名");
chk(call("bash", { command: "ls ~/plugins/cache/local/cbb-guard/0.1.0" }).status === 0, "主套/应放", "有词尾 rd 无冻结名");
chk(call("read", { file_path: FROZEN_FILE }).status === 0, "主套/应放", "只读工具");
chk(call("bash", { command: "echo ok" }).status === 0, "主套/应放", "无关键词");
chk(spawnSync("node", [GUARD], { input: "{不是 json", encoding: "utf8" }).status === 0, "主套/附检", "非 JSON 输入不阻断");
chk(/命中：/.test(call("bash", { command: `rm -rf ${FIX}/迷深实战-本体库` }).stderr), "主套/附检", "拦截回执带命中面");

/* ---------- ② 路数 ---------- */
fresh();
let r = withBypass("裁定：夹具允许", { file_path: FROZEN_FILE });
chk(r.status === 0 && ledger().length === 1, "路数", "根可写＋旁通＋真越权 → 放行且入账 1 行");
fresh({ ledgerIsDir: true });
r = withBypass("裁定：账不可写", { file_path: SCHEMA });
chk(r.status === 2 && /无留痕不越权/.test(r.stderr), "路数", "账写不进去 → 拒绝放行（0.1.0 此处静默放行且零留痕）");
fresh();
r = spawnSync("node", [GUARD], {
  input: JSON.stringify({ tool_name: "bash", tool_input: { command: `rm -rf ${GHOST}/迷深实战-本体库` } }),
  encoding: "utf8", env: { ...process.env, CBB_GUARD_ROOT: GHOST + "/", CBB_HOOK_BYPASS: "裁定：环境错配" },
});
chk(r.status === 2 && /归一值不存在/.test(r.stderr), "路数", "根不存在＋旁通 → 拒绝且告警");
chk(!fs.existsSync(GHOST), "路数", "没凭空建出目录");
r = withBypass("", { file_path: FROZEN_FILE });
chk(r.status === 2 && ledger().length === 0, "路数", "不设旁通 → 该拦仍拦、不漏账");

/* ---------- ③ 作用域 ---------- */
fresh();
r = withBypass(`${FIX}/迷深实战-本体库=裁定：只准动本体库`, { file_path: FROZEN_FILE });
let l = ledger();
chk(r.status === 0 && l.length === 1 && /"scope":"bound:/.test(l[0]) && /"rule":"拦A\/write"/.test(l[0]),
  "作用域", "绑定式覆盖本次越权 → 放且入账带 scope/rule");
fresh();
r = withBypass(`${FIX}/cbb/contracts=裁定：只准动契约`, { file_path: FROZEN_FILE });
chk(r.status === 2 && ledger().length === 0, "作用域", "绑定式不覆盖本次目标 → 照拦、不漏账");
fresh();
r = withBypass(`${FIX}/迷深实战-本体库=裁定：只准动本体库`, { file_path: FIX + "/无关新件.md" });
chk(r.status === 0 && ledger().length === 0, "作用域", "挂 env 做无关写 → 放行且**不**入账（0.1.0 会灌一条假账）");
fresh();
r = withBypass("裁定：老写法", { file_path: FROZEN_FILE });
l = ledger();
chk(r.status === 0 && l.length === 1 && /"scope":"global/.test(l[0]) && /提醒：形态=global/.test(r.stderr),
  "作用域", "全局式（兼容）→ 放、入账记 global、打提醒");
fresh();
r = withBypass("裁定：老写法", { file_path: FIX + "/无关新件.md" });
chk(r.status === 0 && ledger().length === 0, "作用域", "全局式挂 env 做无关写 → 不入账（0.1.0 此处为 1 行）");

fs.rmSync(FIX, { recursive: true, force: true });
fs.rmSync(GHOST, { recursive: true, force: true });
console.log(`\n===== ${path.relative(process.cwd(), GUARD) || GUARD}：${n - bad}/${n} 例合预期，不符 ${bad} 项`);
process.exit(bad ? 1 : 0);
