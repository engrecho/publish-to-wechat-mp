#!/usr/bin/env python3
"""
公众号图片对抗去重工具
====================
功能:
  1. 感知哈希去重 - 剔除文章内重复/近似图片
  2. 微信原创对抗 - 三层绕过 (pHash扰动 + SIFT扰动 + CNN Embedding对抗)
  3. 朱雀AI检测对抗 - 破坏AI图频域特征, 降低被标"AI生成"概率
  4. 头图生成 - 900×383 (2.35:1)

用法:
  python3 anti_dedup.py --input ./images/ --output ./images_out/ --epsilon 8 --steps 200
  python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode dedup       # 仅去重
  python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode anti       # 仅对抗
  python3 anti_dedup.py --input ./images/ --output ./images_out/ --mode all        # 全流程

依赖:
  pip install pillow numpy imagehash opencv-python-headless scipy torch torchvision
"""

import argparse
import hashlib
import io
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont


# ============================================================
# 0. 配置常量
# ============================================================

WECHAT_COVER_WIDTH = 900
WECHAT_COVER_HEIGHT = 383
COVER_RATIO = 2.35

PHASH_REPEAT_THRESHOLD = 5      # ≤5 判为重复
PHASH_SIMILAR_MIN = 6           # 6-10 为疑似相似
PHASH_SIMILAR_MAX = 10

IMAGESET_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}


# ============================================================
# 1. 感知哈希去重 (消除文章内重复图)
# ============================================================

class PerceptualDedup:
    """基于 aHash / pHash / dHash 的图片去重"""

    def __init__(self):
        try:
            import imagehash
            self.imagehash = imagehash
            self._loaded = True
        except ImportError:
            self._loaded = False

    @staticmethod
    def md5_hash(path: str) -> str:
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def file_size(path: str) -> int:
        return os.path.getsize(path)

    def compute_phashes(self, img: Image.Image) -> Dict[str, str]:
        """计算三种感知哈希"""
        if not self._loaded:
            return {}
        return {
            'ahash': str(self.imagehash.average_hash(img)),
            'phash': str(self.imagehash.phash(img)),
            'dhash': str(self.imagehash.dhash(img)),
        }

    @staticmethod
    def hamming_distance(h1: str, h2: str) -> int:
        if len(h1) != len(h2):
            return 64
        x = int(h1, 16) ^ int(h2, 16)
        return bin(x).count('1')

    def dedup(self, image_paths: List[str]) -> Tuple[List[str], List[dict]]:
        """
        对一组图片路径做去重。
        返回: (保留的路径列表, 被剔除的记录列表)
        """
        if not self._loaded:
            print("[!] imagehash 未安装, 跳过感知哈希去重", file=sys.stderr)
            return image_paths, []

        # Step 0: MD5 去重 (完全相同文件)
        md5_dict: Dict[str, str] = {}
        unique_paths = []
        removed = []
        for p in image_paths:
            md5 = self.md5_hash(p)
            if md5 in md5_dict:
                removed.append({
                    'path': p,
                    'reason': f'md5_dup of {md5_dict[md5]}',
                })
            else:
                md5_dict[md5] = p
                unique_paths.append(p)

        # Step 1: 感知哈希两两比对
        hashes = []
        for p in unique_paths:
            try:
                img = Image.open(p).convert('RGB')
                h = self.compute_phashes(img)
                hashes.append((p, h))
            except Exception as e:
                print(f"[!] 无法读取 {p}: {e}", file=sys.stderr)

        keep = []
        for i, (path, h) in enumerate(hashes):
            is_dup = False
            for j, (kept_path, kept_h) in enumerate([(kp, kh) for kp, kh in [(h_[0], h_[1]) for h_ in hashes[:i]]]):
                # pHash 主判据
                if not h.get('phash') or not kept_h.get('phash'):
                    continue
                ph_dist = self.hamming_distance(h['phash'], kept_h['phash'])
                dh_dist = self.hamming_distance(h.get('dhash', ''), kept_h.get('dhash', ''))

                if ph_dist <= PHASH_REPEAT_THRESHOLD:
                    # 分辨率高的保留
                    if self.file_size(path) > self.file_size(kept_path):
                        # 替换
                        removed.append({'path': kept_path, 'reason': f'phash_dist={ph_dist} → replaced by {path}'})
                        keep = [p for p in keep if p != kept_path]
                        keep.append(path)
                    else:
                        removed.append({'path': path, 'reason': f'phash_dist={ph_dist} dup of {kept_path}'})
                    is_dup = True
                    break
                elif ph_dist <= PHASH_SIMILAR_MAX and dh_dist <= PHASH_REPEAT_THRESHOLD:
                    removed.append({'path': path, 'reason': f'similar phash_dist={ph_dist} dhash_dist={dh_dist} of {kept_path}'})
                    is_dup = True
                    break

            if not is_dup:
                keep.append(path)

        return keep, removed


# ============================================================
# 2. 微信原创对抗 (图片层面)
# ============================================================

class WechatImageAntiDetect:
    """三层图片原创对抗: pHash + SIFT + CNN Embedding"""

    def __init__(self, epsilon: float = 8.0, steps: int = 200, model_name: str = "resnet50"):
        self.epsilon = epsilon / 255.0
        self.steps = steps
        self.model_name = model_name

        # 归一化空间的有效值域 (ImageNet normalize 后)
        self.norm_min = np.array([(0 - m) / s for m, s in zip([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]).reshape(1, 3, 1, 1)
        self.norm_max = np.array([(1 - m) / s for m, s in zip([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])]).reshape(1, 3, 1, 1)

    # ---- Layer 1: pHash / dHash 对抗 ----
    @staticmethod
    def anti_phash(img: Image.Image, crop_px: int = 2, rotate_deg: float = 0.5, noise_strength: int = 2) -> Image.Image:
        """pHash 对抗: 裁剪 + 微旋转 + 高频噪声"""
        w, h = img.size
        img = img.crop((crop_px, crop_px, w - crop_px, h - crop_px))
        img = img.rotate(rotate_deg, resample=Image.BICUBIC, fillcolor=(255, 255, 255))
        arr = np.array(img, dtype=np.float32)
        noise = np.random.randint(-noise_strength * 5, noise_strength * 5 + 1, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    # ---- Layer 2: SIFT 对抗 ----
    @staticmethod
    def anti_sift(img: Image.Image, method: str = 'elastic', **kwargs) -> Image.Image:
        """SIFT 对抗: 弹性变形 or 高斯模糊"""
        if method == 'blur':
            radius = kwargs.get('radius', 1.0)
            return img.filter(ImageFilter.GaussianBlur(radius=radius))
        elif method == 'elastic':
            alpha = kwargs.get('alpha', 3)
            sigma = kwargs.get('sigma', 2)
            try:
                from scipy.ndimage import gaussian_filter
                import cv2
                arr = np.array(img)
                h, w = arr.shape[:2]
                dx = gaussian_filter(np.random.randn(h, w) * alpha, sigma)
                dy = gaussian_filter(np.random.randn(h, w) * alpha, sigma)
                x, y = np.meshgrid(np.arange(w), np.arange(h))
                map_x = np.clip(x + dx, 0, w - 1).astype(np.float32)
                map_y = np.clip(y + dy, 0, h - 1).astype(np.float32)
                result = np.zeros_like(arr)
                for c in range(arr.shape[2]):
                    result[:, :, c] = cv2.remap(arr[:, :, c], map_x, map_y, cv2.INTER_LINEAR)
                return Image.fromarray(result)
            except ImportError:
                print("[!] scipy/cv2 未安装, SIFT 对抗降级为高斯模糊", file=sys.stderr)
                return img.filter(ImageFilter.GaussianBlur(radius=1.0))
        else:
            raise ValueError(f"未知方法: {method}")

    # ---- Layer 3: CNN 对抗 (PGD) ----
    def anti_cnn(self, img: Image.Image, alpha: float = 2.0) -> Image.Image:
        """CNN Embedding PGD 对抗攻击"""
        try:
            import torch
            import torch.nn.functional as F
            from torchvision import models, transforms
        except ImportError:
            print("[!] PyTorch 未安装, 跳过 CNN 对抗层", file=sys.stderr)
            return img

        device = "cuda" if torch.cuda.is_available() else "cpu"

        # 加载模型
        model_map = {
            'resnet18': models.resnet18,
            'resnet34': models.resnet34,
            'resnet50': models.resnet50,
            'resnet101': models.resnet101,
        }
        if self.model_name not in model_map:
            print(f"[!] 不支持模型 {self.model_name}, 改用 resnet50", file=sys.stderr)
            self.model_name = 'resnet50'

        backbone = model_map[self.model_name](pretrained=True)
        backbone.fc = torch.nn.Identity()
        backbone = backbone.to(device).eval()

        # 归一化参数 (确保 float32)
        mean = torch.tensor([0.485, 0.456, 0.406], device=device, dtype=torch.float32).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=device, dtype=torch.float32).view(1, 3, 1, 1)
        norm_min_t = torch.tensor(self.norm_min, device=device, dtype=torch.float32).reshape(1, 3, 1, 1)
        norm_max_t = torch.tensor(self.norm_max, device=device, dtype=torch.float32).reshape(1, 3, 1, 1)

        # 预处理
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        x_orig = preprocess(img).unsqueeze(0).to(device, dtype=torch.float32)
        x_orig.requires_grad = False

        with torch.no_grad():
            emb_orig = backbone(x_orig)
            emb_orig_norm = F.normalize(emb_orig, dim=-1)

        # Gram-Schmidt 正交化生成伪目标方向
        rand_dir = F.normalize(torch.randn_like(emb_orig), p=2, dim=-1)
        proj = (rand_dir * emb_orig_norm).sum(dim=-1, keepdim=True) * emb_orig_norm
        pseudo_target = F.normalize(rand_dir - proj, p=2, dim=-1)

        alpha_val = alpha / 255.0
        x_adv = x_orig.clone().detach()

        for step in range(self.steps):
            x_adv.requires_grad_(True)
            emb_adv = backbone(x_adv)
            emb_adv_norm = F.normalize(emb_adv, p=2, dim=-1)
            loss = ((emb_adv_norm - pseudo_target.detach()) ** 2).sum()
            grad = torch.autograd.grad(loss, x_adv)[0]
            with torch.no_grad():
                x_adv = x_adv - alpha_val * grad.sign()
                perturbation = torch.clamp(x_adv - x_orig, -self.epsilon, self.epsilon)
                x_adv = torch.clamp(x_orig + perturbation, norm_min_t, norm_max_t).detach()

        # 反归一化并转回 PIL
        with torch.no_grad():
            denorm = x_adv * std + mean
            denorm = torch.clamp(denorm, 0, 1)
            arr = denorm.squeeze(0).cpu().permute(1, 2, 0).numpy()
            arr = (arr * 255).astype(np.uint8)

        return Image.fromarray(arr)

    def run(self, img: Image.Image, skip_cnn: bool = False, alpha: float = 2.0) -> Tuple[Image.Image, Dict]:
        """顺序执行三层对抗, 返回 (对抗后图片, 效果指标)"""
        metrics = {}

        # Layer 1: pHash 对抗
        img = self.anti_phash(img, crop_px=2, rotate_deg=0.5, noise_strength=2)

        # Layer 2: SIFT 对抗
        img = self.anti_sift(img, method='elastic', alpha=3, sigma=2)

        # Layer 3: CNN 对抗
        if not skip_cnn:
            try:
                img = self.anti_cnn(img, alpha=alpha)
            except Exception as e:
                print(f"[!] CNN 对抗失败: {e}", file=sys.stderr)

        return img, metrics


# ============================================================
# 3. 朱雀 AI 检测对抗 (针对图片)
# ============================================================

class ZhuqueDetectorBypass:
    """
    腾讯朱雀 AI 生成图片检测对抗
    原理: AI 图在频域有异常 (高频不自然/伪影), 通过压缩+噪声破坏这些特征
    """

    @staticmethod
    def bypass(img: Image.Image, jpeg_quality: int = 75, noise_sigma: float = 1.5,
               scale_factor: float = 1.0) -> Image.Image:
        """
        对抗朱雀检测:
        - JPEG 重压缩: 破坏 AI 图的高频不自然模式
        - 高斯噪声: 叠加传感器噪声 (接近真实相机拍摄)
        - 可选缩放: 缩放+恢复破坏像素级伪影
        """
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=jpeg_quality, subsampling='4:2:0')
        buf.seek(0)
        img = Image.open(buf).convert('RGB')

        # 叠加高斯噪声
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, noise_sigma, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

        # 可选: 缩放对抗
        if scale_factor != 1.0:
            w, h = img.size
            new_w, new_h = int(w * scale_factor), int(h * scale_factor)
            img = img.resize((new_w, new_h), Image.LANCZOS).resize((w, h), Image.LANCZOS)

        return img


# ============================================================
# 4. 头图生成 (900 × 383, 2.35:1)
# ============================================================

class CoverGenerator:
    """微信公众号头条封面生成"""

    @staticmethod
    def generate(source_img: Image.Image, title: str = "", output_path: str = "cover.jpg",
                 brand_text: str = "") -> str:
        """
        优先级:
        1. 裁切为 2.35:1 (居中, 关键信息避让)
        2. 如有标题文字, 图上叠加
        3. 输出 900×383
        """
        # 缩放到覆盖宽度
        ratio = WECHAT_COVER_WIDTH / source_img.width
        new_h = int(source_img.height * ratio)
        img = source_img.resize((WECHAT_COVER_WIDTH, new_h), Image.LANCZOS)

        # 居中裁切到目标高度
        if img.height > WECHAT_COVER_HEIGHT:
            top = (img.height - WECHAT_COVER_HEIGHT) // 2
            img = img.crop((0, top, WECHAT_COVER_WIDTH, top + WECHAT_COVER_HEIGHT))
        elif img.height < WECHAT_COVER_HEIGHT:
            # 创建底图并居中粘贴
            canvas = Image.new('RGB', (WECHAT_COVER_WIDTH, WECHAT_COVER_HEIGHT), (0, 0, 0))
            top = (WECHAT_COVER_HEIGHT - img.height) // 2
            canvas.paste(img, (0, top))
            img = canvas

        # 如果有标题文字, 叠加
        if title:
            img = CoverGenerator._overlay_title(img, title)
        if brand_text:
            img = CoverGenerator._overlay_brand(img, brand_text)

        img.save(output_path, 'JPEG', quality=90, subsampling=0)
        return output_path

    @staticmethod
    def _overlay_title(img: Image.Image, title: str) -> Image.Image:
        """底部深色渐变 + 标题文字"""
        overlay = img.copy().convert('RGBA')
        w, h = overlay.size
        draw = ImageDraw.Draw(overlay, 'RGBA')

        # 底部渐变
        gradient_h = h // 3
        for y in range(gradient_h):
            alpha = int(180 * (1 - y / gradient_h))
            draw.line([(0, h - gradient_h + y), (w, h - gradient_h + y)], fill=(0, 0, 0, alpha))

        # 文字
        try:
            font_size = max(16, min(28, w // 20))
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # 居中
        bbox = draw.textbbox((0, 0), title, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = h - gradient_h // 2 - th // 2
        draw.text((x, y), title, fill=(255, 255, 255, 255), font=font)

        return Image.alpha_composite(overlay, overlay).convert('RGB')

    @staticmethod
    def _overlay_brand(img: Image.Image, brand_text: str) -> Image.Image:
        """右下角品牌名"""
        overlay = img.copy().convert('RGBA')
        draw = ImageDraw.Draw(overlay, 'RGBA')
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), brand_text, font=font)
        tw = bbox[2] - bbox[0]
        x = overlay.width - tw - 15
        y = overlay.height - 25
        draw.text((x, y), brand_text, fill=(255, 255, 255, 180), font=font)
        return overlay.convert('RGB')


# ============================================================
# 5. CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="公众号图片对抗去重工具")
    parser.add_argument("--input", required=True, help="输入图片目录")
    parser.add_argument("--output", required=True, help="输出图片目录")
    parser.add_argument("--mode", default="all", choices=["dedup", "anti", "zhuque", "all"])
    parser.add_argument("--epsilon", type=float, default=8.0, help="CNN对抗扰动强度 (像素值 0-255)")
    parser.add_argument("--steps", type=int, default=200, help="CNN对抗迭代步数")
    parser.add_argument("--model", default="resnet50", help="CNN模型名")
    parser.add_argument("--alpha", type=float, default=2.0, help="CNN对抗每步幅度")
    parser.add_argument("--cover", action="store_true", help="生成封面图")
    parser.add_argument("--title", default="", help="封面标题文字")
    parser.add_argument("--brand", default="", help="封面品牌名")
    parser.add_argument("--skip-cnn", action="store_true", help="跳过CNN对抗层 (无PyTorch时)")
    parser.add_argument("--input-images", nargs='+', help="指定处理哪些图片 (不传则处理input目录全部)")
    parser.add_argument("--similar-mode", action="store_true",
                        help="疑似相似图也一并剔除 (默认6-10人工确认)")

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    # 收集图片
    if args.input_images:
        image_paths = args.input_images
    else:
        image_paths = sorted([
            os.path.join(args.input, f)
            for f in os.listdir(args.input)
            if os.path.splitext(f)[1].lower() in IMAGESET_FORMATS
        ])

    print(f"[*] 输入图片: {len(image_paths)} 张")
    print(f"[*] 输出目录: {args.output}")
    print(f"[*] 模式: {args.mode}")

    # Step 1: 去重
    dedup = PerceptualDedup()
    kept_paths = image_paths
    removed = []

    if args.mode in ('dedup', 'all'):
        kept_paths, removed = dedup.dedup(image_paths)
        print(f"[去重] 保留 {len(kept_paths)} 张, 剔除 {len(removed)} 张")
        for r in removed:
            print(f"  - {os.path.basename(r['path'])}: {r['reason']}")

        if not args.similar_mode:
            similar = [r for r in removed if r['reason'].startswith('similar')]
            if similar:
                print(f"  ⚠ {len(similar)} 张疑似相似保留在目录中 (--similar-mode 可强制剔除)")

    # Step 2: 对抗处理
    kept_images = []
    for path in kept_paths:
        try:
            img = Image.open(path).convert('RGB')
        except Exception as e:
            print(f"[!] 跳过损坏图片 {path}: {e}")
            continue

        base = os.path.basename(path)
        name, ext = os.path.splitext(base)

        if args.mode in ('anti', 'all'):
            anti = WechatImageAntiDetect(epsilon=args.epsilon, steps=args.steps, model_name=args.model)
            img, _ = anti.run(img, skip_cnn=args.skip_cnn, alpha=args.alpha)
            out_name = f"{name}_anti{ext}"
            out_path = os.path.join(args.output, out_name)
            img.save(out_path, quality=95, subsampling=0)
            kept_images.append(out_path)
            print(f"  [对抗] {base} → {out_name}")

        elif args.mode == 'zhuque':
            zq = ZhuqueDetectorBypass()
            img = zq.bypass(img)
            out_name = f"{name}_human{ext}"
            out_path = os.path.join(args.output, out_name)
            img.save(out_path, quality=90, subsampling='4:2:0')
            kept_images.append(out_path)
            print(f"  [朱雀] {base} → {out_name}")
        else:
            # 仅去重, 直接复制
            out_path = os.path.join(args.output, base)
            img.save(out_path, quality=95)
            kept_images.append(out_path)

    # Step 3: 封面
    if args.cover and kept_images:
        cover_gen = CoverGenerator()
        source = Image.open(kept_images[0]).convert('RGB')
        cover_path = os.path.join(args.output, "cover.jpg")
        cover_gen.generate(source, title=args.title, output_path=cover_path, brand_text=args.brand)
        print(f"[封面] 生成 900×383 → {cover_path}")

    # 输出总结
    print(f"\n✅ 完成! 输出 {len(kept_images)} 张图片至 {args.output}")


if __name__ == "__main__":
    main()
