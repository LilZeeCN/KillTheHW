#!/usr/bin/env python3
"""裁掉截图四周的空白，只保留有内容的部分。

原理：与纯白的差值按阈值二值化，统计每行/每列的内容像素数；
计数低于下限的行/列视为空白或细线（窗口边框、滚动条），不进入内容范围。
需要 Pillow 和 numpy。

用法：
  python3 crop_content.py 输入目录 输出目录 [--pad 24] [--max-width 1800] [--thresh 20]
同名输出；跳过输出目录中已存在的同名文件。
"""
import argparse
from pathlib import Path

from PIL import Image, ImageChops
import numpy as np


def content_box(img, pad, thresh, min_col, min_row, margin=24):
    bg = Image.new('RGB', img.size, (255, 255, 255))
    mask = np.array(ImageChops.difference(img, bg).convert('L')
                    .point(lambda v: 255 if v > thresh else 0)) > 0
    h, w = mask.shape
    col, row = mask.sum(axis=0), mask.sum(axis=1)
    inner_c = [i for i in range(min(margin, w // 4), w - min(margin, w // 4)) if col[i] >= min_col]
    inner_r = [i for i in range(min(margin, h // 4), h - min(margin, h // 4)) if row[i] >= min_row]
    if not inner_c or not inner_r:
        return None
    left, right = inner_c[0], inner_c[-1] + 1
    top, bottom = inner_r[0], inner_r[-1] + 1
    return (max(0, left - pad), max(0, top - pad),
            min(w, right + pad), min(h, bottom + pad))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('src', type=Path)
    parser.add_argument('dst', type=Path)
    parser.add_argument('--pad', type=int, default=24, help='内容四周保留的像素（原图尺度）')
    parser.add_argument('--max-width', type=int, default=1800,
                        help='超过此宽度的图按比例缩小（300dpi 对应 6 英寸版面）')
    parser.add_argument('--thresh', type=int, default=20, help='与纯白差值超过此值算内容')
    parser.add_argument('--min-col', type=int, default=4, help='一列至少多少内容像素才算内容列')
    parser.add_argument('--min-row', type=int, default=2, help='一行至少多少内容像素才算内容行')
    args = parser.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    total = kept = 0
    for src in sorted(args.src.iterdir()):
        if src.suffix.lower() not in {'.png', '.jpg', '.jpeg'} or not src.is_file():
            continue
        dst = args.dst / src.name
        if dst.exists():
            continue
        img = Image.open(src).convert('RGB')
        box = content_box(img, args.pad, args.thresh, args.min_col, args.min_row)
        if box:
            cropped = img.crop(box)
        else:
            cropped = img
        if cropped.width > args.max_width:
            ratio = args.max_width / cropped.width
            cropped = cropped.resize((args.max_width, int(cropped.height * ratio)), Image.LANCZOS)
        cropped.save(dst, dpi=(300, 300))
        total += 1
        if box:
            kept += 1
        print(f'{src.name}: {img.size[0]}x{img.size[1]} -> {cropped.size[0]}x{cropped.size[1]}')
    print(f'{kept}/{total} cropped')


if __name__ == '__main__':
    main()
