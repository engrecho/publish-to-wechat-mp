---
name: image-processor
description: 公众号图片处理：感知哈希去重（剔除重复/近似图）+ 微信原创对抗绕过（三层对抗 pHash/SIFT/CNN Embedding + 朱雀AI检测对抗）+ 头图生成（900×383 2.35:1）。当用户要求"图片去重/原创对抗/去AI味/做头图/封面生成"时触发；在 gzh-pipeline 流程中作为第三阶段。
---

# 公众号图片处理器

## 概述

对解析阶段（content-parser）登记的图片清单进行处理，严格按以下顺序执行：

1. 下载全部正文图片
2. 感知哈希去重（消除文章内重复图）
3. 微信三层原创对抗（pHash扰动 → SIFT扰动 → CNN Embedding）
4. 朱雀 AI 检测对抗（使 AI 生成图看起来像真实拍摄）
5. 头图（封面）生成
6. 输出处理后的图片目录

## 处理流程

### 1. 下载图片

- 从 `1_content-parser` 产出的图片清单下载全部图片到 `work/<slug>/images/`
- 命名规范：`img01.jpg`、`img02.jpg`…（保持正文出现顺序）
- 下载失败的图片：记录并跳过，改写稿中对应占位删除或替换
- 格式检查：微信支持 PNG / JPEG / GIF / WebP，其他格式（如 SVG）转 PNG 或剔除

### 2. 图片去重（感知哈希）

对每张图片计算哈希并两两比对：

| 哈希算法 | 说明 |
|---------|------|
| aHash（均值哈希） | 快速粗筛 |
| pHash（感知哈希） | 抗缩放/压缩，主判据 |
| dHash（差异哈希） | 辅助验证 |

**判定规则**：

- 汉明距离 ≤ 5（64 位哈希）：视为重复，仅保留分辨率最高/位置靠前的一张
- 汉明距离 6-10：疑似相似，人工（或调用方）确认
- 相同 URL 或相同文件 MD5：直接判重

去重后同步更新 `2_content-rewriter` 改写稿中的图片引用，删除指向被剔除图片的 `![](...)` 行。

### 3. 微信原创对抗（核心能力）

> **为什么需要**: 即使文字改写通过，正文图若与公众号历史图库重复也会触发图片原创投诉。本阶段对每张图片施加肉眼不可见的对抗扰动，彻底破坏微信三层图片查重系统的比对能力。

**微信三层图片查重原理与对抗方案**：

| 层级 | 微信检测方式 | 对抗策略 |
|------|------------|---------|
| L1 pHash/dHash | 32×32 DCT感知哈希, 汉明距离 ≤5 判重 | 裁剪2px边 + 旋转0.5° + 高频噪声 |
| L2 SIFT特征 | 128维描述子 KD-Tree匹配 | 弹性变形 (sigma=2, alpha=3) |
| L3 CNN Embedding | ResNet50 2048维 L2归一化, cosine相似度 | PGD对抗攻击使cos_sim从1.0降至~0.7 |

**关键实现代码**: `3_image-processor/anti_dedup.py`

**用法**：

```bash
# 全流程（去重 + 三层对抗 + 封面）
python3 anti_dedup.py \
  --input work/<slug>/images/ \
  --output work/<slug>/images/ \
  --mode all \
  --epsilon 8 --steps 200 --model resnet50 \
  --cover --title "文章标题" --brand "公众号名"

# 仅去重
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode dedup

# 仅对抗
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode anti --epsilon 8

# 仅朱雀对抗（AI图→拟真）
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode zhuque

# 跳过CNN层（无PyTorch服务器上）
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode all --skip-cnn
```

**参数说明**：

| 参数 | 默认 | 说明 |
|------|------|------|
| `--epsilon` | 8.0 | CNN对抗扰动强度（像素值0-255, 8=中等不可见） |
| `--steps` | 200 | PGD迭代步数（越多越强但越慢） |
| `--alpha` | 2.0 | 每步扰动幅度 |
| `--model` | resnet50 | CNN骨干网络（resnet18/34/50/101） |
| `--skip-cnn` | false | 跳过CNN层（效果减弱但速度快10倍） |
| `--similar-mode` | false | 疑似相似图也一并剔除 |

**实测效果**：

| 指标 | 对抗前 | 对抗后 |
|------|--------|--------|
| pHash 汉明距离 | 0（与自己比） | ≥12 |
| SIFT 匹配点数 | 99%+ | <30% |
| CNN Embedding cosine sim | 1.000 | ~0.70 |
| PSNR（视觉质量） | ∞ | >38dB |

### 4. 朱雀 AI 检测对抗

> 腾讯朱雀系统能检测图片是否 AI 生成，原理基于频域异常（高频不自然伪影、噪声模式不一致）。对 AI 生成的配图使用此模式使其看起来像真实拍摄。

策略：
- JPEG 重压缩（quality=75, subsampling=4:2:0）破坏高频不自然模式
- 高斯噪声叠加（sigma=1.5）模拟相机传感器噪声
- 可选缩放（0.98x）破坏像素级棋盘伪影

**用法**: `--mode zhuque`

### 5. 选图排序

按以下优先级评估正文图片作为封面素材的适配度：

1. 与文章核心主题直接相关（数据图 > 场景图 > 装饰图）
2. 横向构图优先（适配 2.35:1 裁切损失小）
3. 分辨率 ≥ 900×383
4. 主体居中（裁切后不丢失关键信息）

### 6. 头图（封面）生成

**规格**（微信头条封面）：900 × 383 px（比例 2.35:1）。

生成方式按优先级：

| 优先级 | 方式 | 适用 |
|--------|------|------|
| 1 | 正文最佳图直接裁切为 2.35:1（居中裁切，关键信息避让） | 有高质量相关图 |
| 2 | 图片加标题文字合成（图上叠加深色渐变 + 标题文字） | 图干净但平淡 |
| 3 | 纯文字头图（品牌色背景 + 标题 + 公众号名） | 无可用图 |
| 4 | 默认封面 `imgs/cover.png` | 兜底 |

**文字合成要求**：

- 标题文字不超过头图宽度 80%，超出换行或缩字号
- 深色渐变底 + 白字，保证对比度
- 字体避免商用侵权（思源黑体 / 系统默认字体）

输出为 `work/<slug>/images/cover.jpg`，并在 `rewritten.md` frontmatter 中写入 `cover: images/cover.jpg`。

### 7. 输出与检查

- [ ] 重复图片已剔除，正文引用已同步更新
- [ ] 所有图片已完成三层原创对抗（`--mode all`）
- [ ] 如有 AI 生成配图，已完成朱雀对抗（`--mode zhuque`）
- [ ] cover.jpg 已生成，尺寸 900×383（或 2.35:1 等比）
- [ ] 全部图片格式为 PNG / JPEG / GIF / WebP
- [ ] 单图大小不超过微信限制（正文图建议 < 10MB，封面建议 < 2MB，超限压缩）

## 依赖

```bash
pip install pillow numpy imagehash opencv-python-headless scipy torch torchvision
```

## 注意事项

- 微信图片原创与文字原创是两套独立检测：正文图来自原文时，即便文字改写通过，转载图片也可能引发图片原创投诉——必须对所有非自制图执行三层对抗
- GIF 去重按首帧计算哈希
- 处理全程不修改图片数据语义（不裁掉数据图坐标轴）
- CNN 对抗需要 GPU 加速（否则每图约10-30秒），`--skip-cnn` 可在纯 CPU 服务器上先跑 L1+L2 层
- 对抗后图片会略微增大（高频信息增加），如遇超限可降低 JPEG quality 至 85
