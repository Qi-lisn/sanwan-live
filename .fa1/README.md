# 三万大肥鱼 V0.5 前臂补绘候选 V0.1

**交付状态：候选版；程序化几何检查通过，未通过美术与关节运动验收。**

## 文件

- `forearm_fill_v01.png`：前臂原位置有色候选补绘层；1152×1495 RGBA 透明 PNG，坐标与 DSH V0.5 输入完全一致。
- `torso_base_preview_merged.png`：叠加于原始 `torso_base_with_shoulder.png` 的全画布合成预览。
- `forearm_before_after.png`：前臂补绘区局部检查图。
- `qa_report.json`：程序化 QA；覆盖范围、外溢、坐标与既有底图保真。
- `DSH_PROMPT.md`：可直接发送给 DSH 的验收提示词。

## 输入约束

输入来自 `sanwan-forearm-repaint-input.zip`。原图冻结、肩部 V4.1 冻结。只处理 `forearm_repaint_mask.png` 指定区域，硬蒙版共 **4,894 px**，bbox (404,684)-(482,850)（右下边界不含）。其他部位不改，左侧应保留的背景不填色。

## 实际制作方法与限制

本候选通过原始已确认外套区域的布料颜色/纹理重采样与方向性明暗调整制作，并非人工完整结构重绘。没有新增鱼形标识、反光条、袖口罗纹；没有重新绘制原脸、头发、肩带、鱼玩偶或双腿。

**重要：蒙版下端有结构性疑点。** 检查发现 y=830..849，补绘窄带与现有躯干轮廓有约 48–62 px 距离。即便严格填满蒙版，抬手后可能出现一片悬空的紫色布料，不宜仅凭覆盖率判定完成。若确认为不合理，必须先让 DSH 只修复蒙版下段的结构定义，再进行精细补绘，不能靠模糊延长衣料掩盖。

## 接入

```python
from PIL import Image
base=Image.open('torso_base_with_shoulder.png').convert('RGBA')
fill=Image.open('forearm_fill_v01.png').convert('RGBA')
base.alpha_composite(fill)
base.save('torso_with_forearm.png')
```

不要缩放、裁剪、居中；本次不修改直播代码、已通过的肩部素材、Live2D 绑定。

## DSH 重点验收

1. 实际合成 0° / -25° / -40° / -60°，查看是否仍存在断裂、悬空布片、幽灵袖子。
2. 检查顶部 y≈684–700 的水平接缝、下端 y≈820–850 的衣摆归属及腰侧过渡。
3. 蒙版内部空洞、蒙版外溢与美术连续性必须分别评判。
4. 只要下端悬空，即使覆盖率 100%，也应美术 FAIL，并给出具体最小蒙版修订方案。
