# Live2D 素材工程（V0.1 粗分层）

本目录用于 Live2D 模型制作，**不参与直播运行**。直播仍然使用 `live/` 下的 PNG 图层与 WebM 动作。

## 状态

**粗分层（rough extraction）**：图层由单张母版按多边形掩码抽取，位置与母版完全一致，
但**没有任何遮挡补绘**，也**没有做关节分段**。不能直接绑定，不能当正式 PSD。

## 目录

```
layers_v01/
├── 00_reference/   母版、分区对照图、OpenRaster 工程（.ora）
├── 20_body/        remainder（躯干/外套/裙/背包主体）
├── 30_arm_right/   抱玩偶的手、右前臂衣袖
├── 40_plush/       海豹玩偶（仅正面）
├── 50_arm_left/    画面左臂整条袖子、张开的手
├── 60_backpack/    背包挂件
└── 70_face/        头部（含五官与前发，未拆）
```

`manifest_v01.csv` 记录每个图层的画布、包围盒、像素数与状态。

## 二进制文件策略

`layers_v01/` 下的 PNG/ORA 有 17MB，**不进普通 Git 历史**（已加入 `.gitignore`）。
需要版本化时用 Git LFS 或独立素材仓：

```bash
git lfs track "live2d/layers_v01/**/*.png" "live2d/layers_v01/**/*.ora"
```

## 左右命名

包里 `screen_left` / `screen_right` 指**画面方向**，不是角色解剖方向。
`screen_left` = 观众看到的左边 = 角色自己的右手。

## 下一步

1. 按 `docs/live2d-layer-audit-v01.md` 的缺失清单补绘
2. 拆分头部（眼/嘴/眉/前发/后发/耳机）
3. 手臂分上臂/前臂/手，补肩肘遮挡
4. 补绘完成后重新导出 PSD（真分层，不是 PNG 叠放）
5. 进 Cubism Editor 绑网格、参数、物理，导出 `.moc3`
