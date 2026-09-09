const fs=require('fs');
// usage: node cardcheck.js <cardfile> <kbRoot>
const [,,cf, kb] = process.argv;
const card = fs.readFileSync(cf,'utf-8');
const report={sections:[], quotes:[]};
const secRe=/^## ● (.+)$/gm; let m;
const needed=['基本信息','外貌描写','性格','语言风格与口头禅','心理独白','动作','人际关系','人物关系','隐瞒身份','剧情锚点','精选台词'];
const found=[]; while((m=secRe.exec(card))) found.push(m[1]);
report.sections={found, missing:needed.filter(n=>!found.some(f=>f.includes(n)))};
// collect quotes
const qRe=/「([^」]{4,})」/g; let q; const quotes=[];
while((q=qRe.exec(card))) quotes.push(q[1]);
report.quotesCount=quotes.length;
// trace each quote against corpus (normalized, prefix 20 chars)
const dir=kb+'/分析/清洗标注版';
const files=fs.readdirSync(dir).filter(x=>x.endsWith('.md'));
const cache={};
function trace(q){
  const key=q.slice(0,20);
  if(cache[key]!==undefined) return cache[key];
  for(const fn of files){
    const txt=fs.readFileSync(dir+'/'+fn,'utf-8');
    if(txt.includes(key)){ cache[key]=fn; return fn; }
  }
  cache[key]=null; return null;
}
const traced=quotes.map(q=>({q:q.slice(0,40), src:trace(q)})).filter(x=>x.src);
report.traced=traced.length;
report.untraced=quotes.length-traced.length;
report.untracedList=quotes.map(q=>({q:q.slice(0,40), src:trace(q)})).filter(x=>!x.src).slice(0,10);
console.log(JSON.stringify(report,null,1));
