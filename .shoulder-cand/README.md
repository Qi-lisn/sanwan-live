# 三万大肥鱼 V0.4 肩部补绘候选文件（未通过验收）

文件说明：
1. shoulder_fill.png — 1152×1495 RGBA，有色肩部局部填充候选层，叠加到现有 torso_base.png。
2. torso_base_preview_merged.png — torso_base + shoulder_fill 的合成预览。
3. README.md — 本说明。
4. DSH_test_prompt.txt — 交给 DSH 的测试要求。

重要：当前素材并非可直接绑定的正式肩部底图；虽然 shoulder_fill_mask.png 标记的 18,534 个像素均有颜色层覆盖，但合成预览仍存在显著的透明空洞，且生成内容与原画在纹理、边缘上的连续性未得到验证。因此不能称作已经完成补绘或通过 60° 抬臂测试。

测试时沿用原工程的 shoulder_fill_mask.png、torso_base.png 和独立手臂图层，逐个检查 0/12/25/40/60 度，不要直接覆盖正式素材或合并主分支。
