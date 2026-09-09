# -*- coding: utf-8 -*-
import io
path = '迷深清洗工作2/年表输出/final_output/README_汇总.md'
t = io.open(path, encoding='utf-8').read()

t = t.replace('- matched:207 ｜ unmatched:562', '- matched:688 ｜ unmatched:81（补录后：原 562 条 unmatched 中 481 条经咏唱库补录重跑命中；剩余 81 条为非咏唱项——剑技/人名/书史/技能/试练/概念/道具）')
t = t.replace('[P9-P9-11] P8 咏唱 unmatched 缺口(562 条): unmatched 保留并注明推测;8 大高频魔法族建议后续补录咏唱库;非咏唱项从 incantation_links 中标注 type=\'非咏唱项\' 单列,不计入咏唱关联统计。 (confidence=合理推断)',
              '[P9-P9-11] P8 咏唱 unmatched 缺口(562 条): 已通过咏唱库补录（189 条目覆盖 352 个名称）重跑 P8，unmatched 降至 81 条，全部为非咏唱项（剑技/人名/书史/技能/试练/概念/道具），维持 unmatched 并注明。 (confidence=合理推断)')

t += '\n## 咏唱库补录说明（2026 会话）\n'
t += '- 补录文件：异世界迷宫最深部_知识库/分析/咏唱库/咏唱库_main.yaml（incantations 41→230 条）\n'
t += '- 补录条目：189 条（P8 unmatched 高频魔法族：Sehr・Wind 系/世界炎蛇·冰蛇耶梦加得系/星魔法 Reevan·Line 系/Quartz 水晶系/BlackShift 系/治愈·光系/我的世界的物语/行路渐歧 Default/Impulse 系等 + 守护者开场白 guardian_40/50/100 共 4 条）\n'
t += '- 红线：incantation_text 咏唱正句逐字保真（自 web 语料 block 原文提取，170 条逐字校验 0 失败；19 条原文无完整咏唱句，以叙事句+注明处理）\n'
t += '- source 格式：章节 + 话号 + block_id；edition 按语料标注（web_original/web_reconstructed）\n'
t += '- 非咏唱项（剑技/人名/书史/技能/试练/概念/道具 72 个名称/81 条）不补录，维持 unmatched 并注明\n'

io.open(path, 'w', encoding='utf-8').write(t)
print('README updated')