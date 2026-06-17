#!/bin/bash
# 统信 UOS / Deepin / 麒麟 公文字体安装脚本
# 用法: sudo bash utils/setup_fonts.sh
# 说明: 从当前目录的 fonts/ 子目录安装字体到系统目录
# 注意: 本脚本为 Linux 环境设计（项目运行于 Windows + python-docx，
#       字体嵌入由 python-docx 内部处理，无需系统安装字体）。
#       此脚本仅用于部署到信创 Linux 系统时使用。

set -e

FONT_SRC="$(cd "$(dirname "$0")/../fonts" && pwd)"
FONT_DST="/usr/share/fonts/truetype/gov-doc"

if [ ! -d "$FONT_SRC" ]; then
    echo "请先将字体文件放入项目根目录下的 fonts/ 文件夹，再运行此脚本。"
    echo ""
    echo "需要的字体："
    echo "  - 方正小标宋简体.TTF"
    echo "  - 仿宋_GB2312.TTF"
    echo "  - 黑体.TTF"
    echo "  - 楷体_GB2312.TTF"
    exit 1
fi

echo "安装公文字体到 $FONT_DST ..."
sudo mkdir -p "$FONT_DST"
sudo cp -v "$FONT_SRC"/*.TTF "$FONT_SRC"/*.ttf "$FONT_DST"/ 2>/dev/null || true

echo "更新字体缓存..."
sudo fc-cache -fv "$FONT_DST"

echo ""
echo "验证安装："
fc-list :lang=zh | grep -E "方正|仿宋|黑体|楷体" || echo "  （字体未出现在 fc-list 中，请检查文件名是否匹配）"

echo ""
echo "完成。请重启 OpenCode 使字体生效。"
