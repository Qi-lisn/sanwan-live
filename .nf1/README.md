# 三万大肥鱼 · 前臂无补绘基线 & 静态残留清理 V0.1

## DSH V0.4 的新结论
- 原位置前臂足迹主要属于背景，前臂补绘不应继续使用。
- `forearm_fill_v01.png` ~ `forearm_fill_v04.png` 均停止用于正式模型。
- DSH 提供的 `forearm_repaint_mask_v6.png` 是微小轮廓接缝参考，**不是需要补成衣服的区域**。

## 本次交付
1. `torso_base_no_floating_fingers_v01.png`：1152×1495 RGBA，取原 `torso_base_with_shoulder.png`，只清理画面左下悬空手指候选区域。清理范围 x=340..429, y=843..890，**实际删除 1,369 个不透明像素**，其他原始像素不变。保留已通过的肩部 V4.1。
2. `forearm_fill_DISABLED.png`：同尺寸透明占位层；表明前臂区域不再填色，而非新的有色补绘。
3. `floating_finger_removal_mask.png`：本轮实际删除像素的二值蒙版（非创作素材）。
4. `qa_before_after_fingertips.png`：底图清理前/后棋盘背景对比，左前右后。
5. `dsh_baseline_no_fill_motion.png`：DSH 原始无补绘 0/-25/-40/-60° 测试截图（供对照）。
6. `dsh_seam_mask_v6_reference.png`：DSH V6 接缝参考蒙版，未自动应用。
7. `DSH_PROMPT.md`：下一步测试指令。

## 当前状态
- 本包**仅解决底图下方悬空手指的一部分残留**，不声称整条手臂可以绑定或通过美术验收。
- 原底图在袖口处还有可能存在静态手部/袖管残影，需 DSH 核验并按实际层级清除；不得用整片紫色补绘覆盖背景。
- 不修改正在运行的直播系统、OBS、TTS、弹幕或正式立绘。
- 肩部 V4.1 保留不动；本次只交付候选清理底图与测试素材。
