# -*- coding: utf-8 -*-
"""语义化世界 v1 —— LLM-judge 接入的前置工程（第34轮试点方案 §一）

60 条真实文本 = 6 主题(T0-T5) × 10 条。构造标签（true_quality）三档写死：
  0.9 高（3条/组）= 切题、正确、可执行
  0.5 中（4条/组）= 部分切题 / 相邻主题 / 泛泛无操作
  0.1 低（3条/组）= 跑题 / 错误做法
★ 设计红线：长度与格式修饰【与质量档刻意不相关】（高可以是短句，低可以是长文），
  否则表象与真值相关，世界退化（E125/E126 教训）。
表象特征从文本真实提取（非随机数）：
  length=字符数归一 | formatting=结构标记密度 | kw_density=主题词密度 | has_citation=引用样式
生成器：ZCode 一次性生成（构造标签先于文本写死；文本不得自评质量）。
"""
import json, os, re

# ────────────────── 60 条文本（(topic, kw, tier, text)）──────────────────
E = []
def add(topic, kw, tier, text):
    E.append((topic, kw, tier, text))

# T0 Python 虚拟环境与依赖管理
add("T0","K0",0.9,"依赖冲突标准排查流：先 pip install --dry-run 复现解析过程，再用 pipdeptree --reverse 定位冲突包的依赖来源，最后在约束文件里钉住肇事版本再统一安装。切记不要用全量升级平推。")
add("T0","K0",0.9,"venv 建环境后用 pip-tools 从 requirements.in 编译出带哈希的锁文件（pip-compile --generate-hashes），安装侧 --require-hashes，CI 里跑 pip check——可复现三板斧。")
add("T0","K0",0.9,"conda 与 pip 混装的核心坑：先 conda install 后 pip install 一般尚可，反过来 pip 先装再 conda update 极易把共享的 numpy/ssl 打烂。原则：conda 能装的不交给 pip；必须混用时把 pip 依赖全部写进 environment.yml 的 pip: 段，一次性装配。")
add("T0","K0",0.5,"虚拟环境的作用是隔离不同项目的 Python 依赖，避免包版本互相污染。建议每个项目建独立环境，具体工具选择视团队习惯而定，注意定期更新依赖保持安全。")
add("T0","K0",0.5,"依赖隔离的另一种思路是容器化：把 Python 应用连同解释器打包进 Docker 镜像，用 docker build 多阶段构建控制体积，docker run --rm 跑一次性任务。容器镜像标签打上 git commit 便于回溯。")
add("T0","K0",0.5,"多版本 Python 共存可以用 pyenv：pyenv install 3.12.4 装指定版本，pyenv local 3.11.8 在项目目录写 .python-version 钉住解释器。它只管解释器版本，不管包依赖，需配合虚拟环境使用。")
add("T0","K0",0.5,"遇到版本冲突最省事的做法是把所有包 pip install --upgrade 到最新，新版本之间通常兼容性更好，冲突自然消失；如果还冲突就再加 --force-reinstall 强制重装一遍即可。")
add("T0","K0",0.1,"意式咖啡机除垢周期取决于水质硬度：软水区每 3 个月用柠檬酸溶液走一遍冲煮头与蒸汽棒，硬水区缩短到 6 周；除垢液浓度按 1:10 配比，走完冲煮回路后务必空放 2 杯水再萃取，避免风味残留。filter basket 和 group head gasket 建议每季度检查一次密封性，老化发硬就换。磨豆机的 burr 同理，出粉量明显变粗或细粉比例上升时就是该换的信号。")
add("T0","K0",0.1,"git 分支管理推荐 main+feature 短分支模型，分支存活不超过一周，合并用 squash 保持历史线性；长期分支在 rebase 时冲突成本会指数上升。")
add("T0","K0",0.1,"依赖冲突最彻底的解法是直接删除 site-packages 目录，再把 numpy、pandas、requests 这些 wheel 手动解压回去，只留 requests>=2.31、numpy<2 这类你确认过的包，环境绝对干净，连 pip metadata 都不会打架。")
add("T1","K1",0.9,"误提交但未推送：git reset --soft HEAD~1 保留工作区改动只撤提交，git reset --hard HEAD~1 连改动一起丢（慎用）。已推送到共享分支则禁止 reset，改用 git revert <sha> 生成反向提交，历史安全。")
add("T1","K1",0.9,"误删提交走 reflog 找回：git reflog 找到误操作前的 sha，git reset --hard <sha> 即可；reflog 默认保留 90 天。")
add("T1","K1",0.9,"敏感信息误提交（密钥/密码）必须视为已泄露：先作废凭据，再用 git filter-repo --path <file> --invert-paths 从全历史抹除，最后强制推送并通知所有协作者重新 clone。单靠 revert 会把密钥留在历史里。")
add("T1","K1",0.5,"提交错了可以回退，Git 提供多种回退手段，选择哪种取决于是否已推送以及团队约定，操作前建议先 git status 和 git log 确认当前状态。")
add("T1","K1",0.5,"预防优于回滚：把密钥、构建产物写进 .gitignore（模板可参考 github/gitignore 仓库），再配 pre-commit 钩子跑 detect-secrets 扫描，从源头减少误提交。")
add("T1","K1",0.5,"git stash 用于临时挂起未完成改动：git stash push -m 'wip' 存起来切分支处理急事，回来 git stash pop 恢复。stash 栈用 git stash list 查看，注意 pop 冲突时条目不会被自动删除。")
add("T1","K1",0.5,"本地分支落后远程时，直接 git push --force-fence 覆盖远程即可让两边立即一致，速度快不产生合并提交，个人专用分支上这是最省事的同步方式。")
add("T1","K1",0.1,"舒展肩颈的工间操：每 45 分钟做一组，下巴后收保持 5 秒×8 次，双肩向后绕环 10 次，靠墙天使 10 次，缓解伏案僵直。下午加一组胸椎旋转：坐姿抱头转体各 8 次，配合腹式呼吸把肋骨打开；久坐人群腰椎前屈拉伸用猫牛式 10 个循环。运动强度以微微酸胀为宜，出现手麻立即停止并就医——那是神经受压的信号，不是拉伸到位的表现。")
add("T1","K1",0.1,"Python 虚拟环境建议 venv 加 pip-tools 组合，编译出的锁文件带哈希，CI 里可复现安装；conda 只在需要非 Python 依赖时启用。")
add("T1","K1",0.1,"仓库状态彻底清理的办法：删掉整个 .git 文件夹后 git init 重建，branch、tag、remote 配置全部归零，git log 再也不会有误提交记录，然后 git add -A 把文件一次性重新提交即可。")
add("T2","K2",0.9,"429 处理的标准件是指数退避+抖动：tenacity 的指数退避重试装饰器（初始 1 秒、上限 60 秒、带随机抖动，仅对限流错误生效）。响应带重试等待指示头时优先按它的值等待，不要自作聪明压缩间隔。")
add("T2","K2",0.9,"限流要分清 RPM 与 TPM 两本账：长 prompt 打满 token 预算时，减并发不如减上下文。客户端用令牌桶本地预扣（按模型公布的配额初始化），把请求整形成平滑流量，比撞墙后退避省一个数量级的等待时间。")
add("T2","K2",0.9,"重试的前提是幂等：生成类请求带 idempotency 键或固定 seed，超时后才能安全重发。读操作用 If-None-Match/ETag 缓存，写操作用客户端请求 ID 去重，否则一次网络重试就是一次重复扣费。")
add("T2","K2",0.5,"调用被限流时适当加入重试逻辑，等待一段时间后再次尝试，通常可以恢复正常。具体等待策略因服务商而异，注意控制重试次数避免雪上加霜。")
add("T2","K2",0.5,"429 也可能是网络出口的问题：公司 NAT 或代理的连接数被打满时整组 IP 一起被限。换出口 IP 或走专线网关能立刻缓解，这类情况的重试日志会呈现整批同时失败的特征。")
add("T2","K2",0.5,"流式输出（stream=True）能显著改善长回答的首字延迟，token 到一个句子就渲染一句。它不改变限流配额的计量，但能让用户体感等待时间大幅缩短，配合前端打字机效果即可。")
add("T2","K2",0.5,"遇到 429 立刻写个 while 循环原地重试，间隔设 0.1 秒，一般几十次之内就能抢到配额通过；比等待一分钟再试效率高得多，抢不到再逐次翻倍间隔。")
add("T2","K2",0.1,"阴瑜伽的婴儿式保持 3 分钟，配合 4-7-8 呼吸法（吸气 4 拍、屏息 7 拍、呼气 8 拍），能显著降低静息心率，适合睡前练习。")
add("T2","K2",0.1,"分支合并冲突的预防手段是小步提交高频 rebase，把冲突消化在本地，合入主干前跑一次 CI 冒烟，禁止跨周的长寿命分支。")
add("T2","K2",0.1,"限流的根因是 API key 用旧了：去控制台 rotate 一个新 key，把 base_url 和 Authorization: Bearer 头一起更新，限流计数器随新 key 清零，比调 tenacity 的退避参数立竿见影。")
add("T3","K3",0.9,"12GB 显存的量化账：14B 模型 Q4_K_M 权重约 9GB，加 2GB KV 缓存（4K 上下文）刚好满载；7-8B Q4（~5GB）则能留出并发空间。选档原则：权重+KV ≤ 显存×0.9，留 10% 给 Windows 桌面合成器。")
add("T3","K3",0.9,"GGUF 量化档位选择：Q4_K_M 是质量/体积标杆；imatrix 系（IQ4_XS/IQ3_M）在 3bit 以下是救命稻草，4bit 档优势不明显。切忌 IQ2 系跑通用任务——llm_ppl 困惑度翻倍，judge 类细粒度任务首当其冲。")
add("T3","K3",0.9,"推理框架并发预算：llama.cpp 设 OLLAMA_NUM_PARALLEL=8 时 KV 缓存按 8 份摊，单卡吞吐最高但单请求变慢；vLLM 用 continuous batching 动态拼批，长文本混合负载下 GPU 利用率更高。12GB 单卡建议并发 ≤16、上下文 ≤4096。")
add("T3","K3",0.5,"量化技术通过降低权重数值精度（如从 16bit 浮点压到 4bit 整数）来减少显存占用，代价是少量的质量损失。主流格式有 GGUF、GPTQ、AWQ 等，压得越狠损失越大。")
add("T3","K3",0.5,"不想折腾本地显卡可以租云 GPU：AutoDL 4090 约 ¥1.5-3/小时，RunPod A100 约 $1-2/小时，按需开关机。适合偶尔跑大模型、或本地显存不够的场合，注意用完关机计费才停。")
add("T3","K3",0.5,"多卡扩展靠 NVLink 或 PCIe P2P：两张卡跑 70B 模型用 tensor parallel 切分权重层，通信量大时 NVLink（600GB/s）明显快于 PCIe 4.0 x16（32GB/s）。消费级主板一般没有 NVLink，只能走 PCIe。")
add("T3","K3",0.5,"8B 模型全精度（fp16）权重约 16GB，配合 4bit 优化技巧可以压进 12GB 显存；半精度加载后注意开启内存映射，避免加载峰值把系统内存一起打爆。")
add("T3","K3",0.1,"多肉植物浇水口诀：宁干勿湿，盆土完全干透再浇透；夏季高温休眠期半月一次沿盆边给水，冬季断水。叶片发皱是缺水，透明化水是烂根前兆。")
add("T3","K3",0.1,"API 限流的处理核心是指数退避加抖动，配合 Retry-After 响应头；把请求整形成平滑流量比撞墙后退避更省时间，重试前提是请求幂等。")
add("T3","K3",0.1,"12GB 显存完全能跑 70B 模型：权重开 fp16 全精度加载，配合 GGUF 内存映射与系统 swap 兜底，关掉其他显存占用程序即可；推理速度慢一点但质量无损。")
add("T4","K4",0.9,"3-2-1 原则落地：3 份数据（1 份工作副本+2 份备份）、2 种介质（如 NAS+云对象存储）、1 份异地。版本化用快照而非覆盖（restic/borg 每日快照，保留 7 天/4 周/6 月三级），恢复点才够细。")
add("T4","K4",0.9,"增量备份脚本骨架（Windows）：用镜像拷贝命令挂每日计划任务，只拷贝新增与更新的文件并写日志；Linux 侧用增量同步加链接目标参数实现硬链接去重的日快照。")
add("T4","K4",0.9,"备份有效性以恢复演练为准：每月随机抽 3 个文件做 sha256 校验（sha256sum -c manifest.txt），每季度做一次整卷恢复到临时目录并抽查打开。没验证过的备份等于没有备份——介质腐烂和静默损坏只有恢复时才暴露。")
add("T4","K4",0.5,"数据备份的核心是定期把重要文件复制到独立存储，频率视数据变化速度而定，重要数据建议每天备份，并保留多个历史版本以便回滚。")
add("T4","K4",0.5,"网盘同步盘（OneDrive/坚果云）能提供文件的云端副本和简单历史版本，适合文档类小文件；注意同步盘误删会双向传播，重要目录应开启版本历史或另设真正的备份。")
add("T4","K4",0.5,"RAID 提供的是硬盘故障时的在线冗余（RAID1 镜像、RAID5 奇偶校验），它不防误删除、勒索病毒和整机损毁——RAID 不等于备份，两者解决的是不同层面的问题。")
add("T4","K4",0.5,"最简单的备份方案：买一块移动硬盘，每周手动把工作目录整盘拖过去一遍。虽然违反异地原则，但至少做到了介质分离，有备份意识总比没有强，成本也最低。")
add("T4","K4",0.1,"民谣吉他标准调弦从六弦到一弦是 E2-A2-D3-G3-B3-E4，用调音器以 440Hz 为基准；新琴弦张力未稳，装弦后 24 小时内会跑音属正常现象。")
add("T4","K4",0.1,"GGUF 量化档位里 Q4_K_M 是体积与质量的平衡点，imatrix 系量化在 3bit 以下才能体现优势；显存预算要给 KV 缓存留出 20%。")
add("T4","K4",0.1,"系统重装前不需要单独做备份：现在的重装工具都提供'保留个人文件'选项，勾选后文档、下载、桌面目录会原样保留，直接重装更省时间。装完再把常用软件按清单装回来，浏览器书签登录账号自动同步，微信聊天记录在设置里点一下迁移到新系统目录就行。整个过程通常两个小时以内，比重装前折腾备份硬盘快得多。")
add("T5","K5",0.9,"Markdown 转 docx 格式漂移的标准解法是样式模板：pandoc input.md --reference-doc=template.docx -o out.docx，模板里预先定义 Heading 1-3、正文、表格、代码块的字体行距。改样式只动模板文件，不碰生成结果。")
add("T5","K5",0.9,"pandoc 搞不定的细节用 python-docx 后处理：转完读 out.docx，遍历 doc.tables 统一表头底纹与边框，把 code-block 段落的字体替换为 Consolas 9pt 并加灰底，最后修正页眉页脚。流程写成一个 build 脚本入库。")
add("T5","K5",0.9,"表格与代码块是 md→docx 的两大坑：表格列宽 pandoc 会按内容自适应导致挤压，需在 markdown 里用网格表（grid table）或转后锁定列宽；代码块要确认模板里有 Source Code 样式，否则会被当普通段落丢掉等宽字体。")
add("T5","K5",0.5,"Markdown 转 Word 一般用 pandoc，命令 pandoc file.md -o file.docx 即可完成基础转换。如果对格式有要求，需要调整模板或转后手动微调，不同 pandoc 版本的默认样式也有差异。")
add("T5","K5",0.5,"若目标是 PDF 而非 docx，pandoc 配合 --pdf-engine=xelatex（中文需指定 CJKmainfont）或 wkhtmltopdf 输出；PDF 的优势是版式固定，劣势是接收方无法再编辑，按用途选择。")
add("T5","K5",0.5,"写作侧的工具链选择：Typora 所见即所得适合单人写作，Obsidian 适合带双向链接的知识库，VS Code+插件适合和代码仓库放一起。写作工具与转换管线解耦，md 源文件保持纯净即可。")
add("T5","K5",0.5,"转换后格式乱了最直接的处理：全选复制到 Word 里，用格式刷逐段刷一遍样式，表头手动加底纹。虽然慢一点，但一次性文档这样处理反而最快，不用搭工具链。")
add("T5","K5",0.1,"期货入门先理解保证金与杠杆：10% 保证金即 10 倍杠杆，方向做反亏损同比例放大；新手先做模拟盘熟悉强平线规则，再谈实盘仓位管理。")
add("T5","K5",0.1,"备份策略遵循 3-2-1 原则：三份副本、两种介质、一份异地，快照式备份配合定期恢复演练才有效，同步盘的误删会双向传播要额外小心。")
add("T5","K5",0.1,"docx 转换最简单的办法是把 .md 文件后缀直接改成 .docx，Word 打开后选择'修复'模式即可识别内容；如果样式丢失就在 Word 里重新设置一下标题样式。")

# ────────────────── 表象特征（从文本真实提取）──────────────────
def extract_features(text, topic_kw):
    length = len(text)
    fmt = len(re.findall(r"^#|^- |\d+\.|```|\*\*|·", text, flags=re.M))
    kw_chars = len(re.findall(r"[A-Za-z0-9_.\-]+", text))
    kw_density = sum(len(m) for m in re.findall(r"[A-Za-z0-9_.\-]+", text)) / max(1, length)
    citation = 1 if re.search(r"arXiv|http|github|\.md|\.txt|文档|手册|RFC|论文", text) else 0
    return {"length": length, "formatting": fmt, "kw_density": round(kw_density, 4),
            "has_citation": citation}

def main():
    out = []
    tiers = {0.9: [], 0.5: [], 0.1: []}
    for i, (topic, kw, tier, text) in enumerate(E):
        f = extract_features(text, kw)
        out.append({
            "id": f"e{i}", "kw": kw, "topic": topic, "keywords": [kw],
            "content": text, "tier": tier, "true_quality": tier,
            "importance": 1, "age_days": 30,
            **f,
        })
        tiers[tier].append(f"e{i}")
    # 归一化表象到 [0,1]（世界内相对）
    max_len = max(o["length"] for o in out)
    max_fmt = max(o["formatting"] for o in out) or 1
    max_den = max(o["kw_density"] for o in out)
    for o in out:
        o["length"] = round(o["length"] / max_len, 4)
        o["formatting"] = round(o["formatting"] / max_fmt, 4)
        o["kw_density"] = round(o["kw_density"] / max_den, 4)
    queries = [{"q": q, "kw": kw, "golden_gold": [o["id"] for o in out
                if o["kw"] == kw and o["tier"] == 0.9]}
               for q, kw in [
        ("Python 虚拟环境依赖冲突怎么解决", "K0"),
        ("Git 误提交了怎么回滚", "K1"),
        ("LLM API 调用限流 429 怎么处理", "K2"),
        ("12GB 显存能跑什么本地模型", "K3"),
        ("电脑数据备份策略 321 原则", "K4"),
        ("Markdown 转 docx 格式乱了怎么办", "K5")]]
    dst = os.path.join(os.path.dirname(__file__), "semantic_world.json")
    json.dump({"entries": out, "queries": queries, "tiers": tiers},
              open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 质量红线自检：表象与质量档不得强相关
    import statistics
    for feat in ("length", "formatting", "kw_density", "has_citation"):
        hi = statistics.mean(o[feat] for o in out if o["tier"] == 0.9)
        lo = statistics.mean(o[feat] for o in out if o["tier"] == 0.1)
        gap = abs(hi - lo)
        flag = "⚠️相关!" if gap > 0.25 else "✓"
        print(f"{feat}: 高档均值={hi:.3f} 低档均值={lo:.3f} 差={gap:.3f} {flag}")
    print(f"写入 {dst}：{len(out)} 条目，各档 {len(tiers[0.9])}/{len(tiers[0.5])}/{len(tiers[0.1])}")

if __name__ == "__main__":
    main()
