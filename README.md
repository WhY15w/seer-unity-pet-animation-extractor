# Seer Unity Mesh Animation Extractor

一个快速验证想法的小脚本，提取 Unity Mesh 动画序列并导出为 PNG 或 GIF。

```bash
# 基础用法（画布自适应内容 + GIF）
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png

# 透明背景 + WebP 动态图
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png --transparent --webp

# 导出逐帧 PNG
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png --png

# 提取其他动画序列
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png -s attack --webp --transparent

# 固定画布尺寸（关闭自适应）
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png --width 800 --height 800

# 调大 scale 控制宠物像素尺寸
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png --scale 200

# 自适应画布留白
python unity_mesh_anim_extractor_json.py 4913.pet.json 4913._Atlas_.png --padding 40
```
