# data/ 三层数据流约定

```
data/
├── raw/         # 原始数据：只读！一旦写入不改——要改就在下游用脚本处理
├── interim/     # 中间产物：可删可重生成，保留复现链即可
└── processed/   # 最终数据
```
- 单向流：raw → interim → processed，禁止逆向写。
- raw/ 内放一个 README.md 说明来源与获取日期。
