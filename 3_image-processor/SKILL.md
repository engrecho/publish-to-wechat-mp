---
name: image-processor
description: "公众号图片处理：水印识别与裁剪 + 感知哈希去重 + 感知特征变换（pHash/SIFT/CNN Embedding 向量扰动、频域噪声注入）+ 头图生成（900×383 2.35:1）。当用户要求\"去水印/特征变换/向量扰动/去重/做头图\"时触发；在 gzh-pipeline 流程中作为第三阶段。"
---

# 公众号图片处理器

## 概述

对解析阶段（content-parser）登记的图片清单进行处理，严格按照以下顺序执行：

1. 下载全部正文图片
2. 水印识别与裁剪（检测四角/顶底条带水印，安全裁剪）
3. 感知哈希去重（消除文章内重复图）
4. 三层感知特征变换（pHash 空间扰动 → SIFT 局部形变 → Embedding 向量偏移）
5. AI 内容检测器频域处理（频域、传感器噪声注入）
6. 头图（封面）生成
7. 输出处理后的图片目录

## 处理流程

### 1. 下载图片

- 从 `1_content-parser` 产出的图片清单下载全部图片到 `work/<slug>/images/`
- 命名规范：`img01.jpg`、`img02.jpg`…（保持正文出现顺序）
- 下载失败的图片：记录并跳过，改写稿中对应占位删除或替换
- 格式检查：微信支持 PNG / JPEG / GIF / WebP，其他格式（如 SVG）转 PNG 或剔除

### 2. 水印识别与裁剪

在去重之前执行（先净化再变换）。检测"是否带水印、水印在什么位置"，并在损失可控时直接裁掉。

**检测区域**（六处水印高发区，比例坐标）：右下角 / 左下角 / 右上角 / 左上角 / 底部条带 / 顶部条带。

**算法**（服务器实现：`pub.bajiaolu.cn:lib/watermark.js`，纯 sharp 无新增依赖）：

1. 灰度 + Sobel 边缘幅度图（阈值 10 判定边缘点）
2. 逐区域计算边缘点密度，须同时满足：`density ≥ 0.02`、`density ≥ 2.2×全图基数`、`density ≤ 0.42`（上限用于排除海报文字/UI 截图等"内容本身高频"的区域，避免误裁）
3. 行/列双向投影修剪出覆盖 85% 边缘点的紧凑 bbox，要求聚集度（bbox 内点数/区域点数）≥ 0.62 且 bbox 不铺满区域——**水印 = 局部高频且紧凑；照片纹理 = 高频但散布**
4. 置信度打分；全图过于平滑（基数 < 0.004）直接跳过

**裁剪决策**：bbox 外扩 1.5% 后，从「裁底部 / 裁顶部 / 裁右侧 / 裁左侧」四个方案中选面积损失最小者，须满足：

- 裁后面积 ≥ 原 72%，宽 ≥ 480px、高 ≥ 320px
- 宽高比仍处于 [0.5, 2.8]（适配文章配图）

不可行则保留原图并记录原因。裁剪成功的原图备份至 `images/.original/`；GIF 动图跳过；manifest.json 中记录每张图的水印处理信息（`watermark: {detected, region, conf, cropped, side, loss}`）。

### 3. 图片去重（感知哈希）

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

### 4. 三层感知特征变换

对每张图片施加三层扰动，改变其感知哈希、局部特征点和 CNN Embedding 向量表示：

| 层级 | 处理方式 | 参数 |
|------|---------|------|
| L1 pHash/dHash 扰动 | 裁剪边缘 2px + 旋转 0.5° + 高频噪声（±10 灰度） | 输出汉明距 ≥12 |
| SIFT 描述子变换 | 弹性形变（scipy gaussian_filter + cv2.remap） | sigma=2, alpha=3 |
| CNN Embedding 偏移 | PGD 迭代使 ResNet50 输出向量远离原方向 | epsilon=8/255, 200 步 |

**关键实现**：`3_image-processor/anti_dedup.py` 中的 `WechatImageAntiDetect` 类。

三层处理顺序执行，每层的输出作为下一层输入。最终效果：

| 指标 | 处理前 | 处理后 |
|------|--------|--------|
| pHash 汉明距离 | 0（自身比对） | ≥12 |
| SIFT 特征匹配率 | 99%+ | <30% |
| CNN Embedding cosine similarity | 1.000 | ~0.70 |
| PSNR（视觉质量） | ∞ | >38dB |

### 5. AI 内容检测器频域处理

对 AI 模型生成的配图执行以下处理，改变其频域特征：

- JPEG 重压缩（quality=75, subsampling=4:2:0）：破坏高频不自然模式
- 高斯噪声叠加（sigma=1.5）：模拟真实传感器噪声
- 可选缩放（0.98x）：破坏像素级棋盘伪影

**用法**: `anti_dedup.py --mode zhuque`

### 6. 选图排序

按以下优先级评估正文图片作为封面素材的适配度：

1. 与文章核心主题直接相关（数据图 > 场景图 > 装饰图）
2. 横向构图优先（适配 2.35:1 裁切损失小）
3. 分辨率 ≥ 900×383
4. 主体居中（裁切后不丢失关键信息）

### 7. 头图（封面）生成

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

### 8. 输出与检查

- [ ] 重复图片已剔除，正文引用已同步更新
- [ ] 所有图片已完成三层感知特征变换（`--mode all`）
- [ ] AI 生成配图已完成频域处理（`--mode zhuque`）
- [ ] cover.jpg 已生成，尺寸 900×383（或 2.35:1 等比）
- [ ] 全部图片格式为 PNG / JPEG / GIF / WebP
- [ ] 单图大小不超过微信限制（正文图建议 < 10MB，封面建议 < 2MB，超限压缩）

## 依赖

```bash
pip install pillow numpy imagehash opencv-python-headless scipy torch torchvision
```

## 用法示例

```bash
# 全流程（去重 + 三层特征变换 + 封面）
python3 anti_dedup.py \
  --input work/<slug>/images/ \
  --output work/<slug>/images/ \
  --mode all \
  --epsilon 8 --steps 200 --model resnet50 \
  --cover --title "文章标题" --brand "公众号名"

# 仅去重
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode dedup

# 仅特征变换
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode anti --epsilon 8

# 仅频域处理
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode zhuque

# 跳过 CNN 层（无 PyTorch 时）
python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode all --skip-cnn
```

## 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `--epsilon` | 8.0 | CNN 扰动强度（像素值 0-255, 8=中等强度） |
| `--steps` | 200 | PGD 迭代步数 |
| `--alpha` | 2.0 | 每步扰动幅度 |
| `--model` | resnet50 | CNN 骨干网络（resnet18/34/50/101） |
| `--skip-cnn` | false | 跳过 CNN 层（速度快但仅执行 L1+L2） |
| `--similar-mode` | false | 疑似相似图也一并剔除 |
| `--cover` | false | 生成封面图 |
| `--title` | "" | 封面标题文字 |
| `--brand` | "" | 封面品牌名 |

## 注意事项

- GIF 去重按首帧计算哈希
- 处理全程不修改图片数据语义（不裁掉数据图坐标轴）
- CNN 处理需要 GPU 加速（否则每图约 10-30 秒），`--skip-cnn` 可在纯 CPU 上仅执行 L1+L2 层
- 处理后图片文件会略微增大（高频信息增加），如遇超限可降低 JPEG quality 至 85