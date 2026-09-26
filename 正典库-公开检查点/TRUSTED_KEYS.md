# TRUSTED KEYS · 正典库公开检查点通道

## 通道说明

本目录存放正典库账本的**签名检查点**（C2SP tlog-tiles 风格）。每个检查点=账本某时点的行数+链尾哈希快照，推送到此处即形成独立于主库的外部锚——防"持有者事后整体重写账本"（split-view）。

验证方式：`cbb2.notary.verify(channel_dir, store_root, origin)` 对账本全链重放后逐字段核对。

## 信任锚

| key id | 算法 | 生效区间 | namespace | 用途 |
|---|---|---|---|---|
| (未配) | Ed25519 | - | canon-checkpoint | 检查点签名 |

## 签名与验证

```
# 签名（发布方）
ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n canon-checkpoint <checkpoint-file>

# 验证（第三方，需 allowed_signers 文件）
echo "identity@context key" > allowed_signers
ssh-keygen -Y verify -f allowed_signers -I identity@context -n canon-checkpoint -s <sig-file> < checkpoint-file
```

## 轮换

新旧 key 双签同一批 checkpoint 形成过渡链；历史验证按时点匹配有效 key（SSH `valid-after`/`valid-before` 原生支持）。
