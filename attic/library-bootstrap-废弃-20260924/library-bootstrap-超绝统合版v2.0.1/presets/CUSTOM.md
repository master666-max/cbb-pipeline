# CUSTOM · 自由组合模式

- 不吃嵌套，直接点菜：用户列模块清单（如「m-core+m-index+m-soul，不要 loop」）。
- 安装器先跑 bootstrap_verify.txt --deps 依赖校验，不满足直接拒绝并打印缺项。
- manifest 记 preset=custom + 实际模块清单。
- 建议不常见组合先在空目录试装一遍。
