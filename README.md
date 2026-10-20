# 世界暂停与单步 / World Step

> 因作者目前仍然在打一阶段，目前只确保能在一阶段可使用。
> 该 mod 可能会因游戏更新而失效（26/10/20 可用，2026-10-20）。
> 本项目的 mod 均由 AI 生成。
>
> The author is currently still playing Stage 1; usability is only assured for Stage 1 at present.
> Game updates may break this mod (working as of 2026-10-20).
> All mods in this project are AI-generated.

中文为默认说明语言；English follows each corresponding section.

## 说明 / Description

适用游戏：**Order of the Sinking Star**，Steam Build **26006400**。发行版本：**0.1.3-test**。

Target: **Order of the Sinking Star**, Steam Build **26006400**. Release version: **0.1.3-test**.

N 暂停／恢复世界；M 立即推进一次 33 毫秒原生逻辑更新。按住 M 满 99 毫秒后开始连发，之后约每 33 毫秒一步；松开保持暂停。在正常运行时按 M 也会进入单步暂停。N 长按不重复，N/M 同时按下优先单步；失焦不响应，切回仍按住的键需松开重按。

N pauses/resumes the world; M immediately advances one 33 ms native logic update. Holding M starts repetition after 99 ms, then advances roughly every 33 ms; releasing keeps the world paused. M also enters step-pause from normal running. Holding N does not repeat, simultaneous N/M prioritizes stepping, and unfocused input is ignored. Release held keys after returning to the game.

## 安装 / Installation

Windows x64、Python 3（64 位），无需第三方 Python 包或日常安装用编译器。 / Windows x64 and 64-bit Python 3; no third-party Python packages or compiler needed for installation.

1. 解压完整发行包到独立文件夹，保留全部文件，不要直接覆盖游戏目录。 / Extract the complete release into its own folder; keep all files and do not extract over the game directory.
2. 正常退出游戏，双击 `install.cmd`，确认成功后再从 Steam 启动游戏。 / Exit the game normally, run `install.cmd`, confirm success, then launch through Steam.
3. 默认路径如下；游戏在其他位置时，打开终端进入本 mod 文件夹，使用下面的安装命令。 / The default path is below. For another location, open a terminal in this mod folder and use the command below.

```text
D:\Program Files (x86)\Steam\steamapps\common\Order of the Sinking Star
```

```powershell
python -X utf8 patch.py install --game-dir "你的游戏目录 / your game directory"
```


## 使用 / Usage

按 N 暂停／恢复，M 单步或长按连续推进。编辑 config.json 的 pause_key / step_key 后重新安装；支持 A–Z、0–9、F1–F12，不能相同，O/P/Q 已保留。 / Use N to pause/resume and M to step or repeat. Edit pause_key / step_key in config.json and reinstall to rebind. Supports A–Z, 0–9, F1–F12; keys must differ, and O/P/Q are reserved.

状态检查（自定义路径时同样追加对应的路径参数）： / Check status (also pass the custom path option if applicable):

```powershell
python -X utf8 patch.py status
```

## 卸载 / Uninstallation

正常退出游戏，双击 `restore.cmd`。自定义路径时，在下面的命令后追加安装时使用的路径参数。请保留安装目录及其生成的备份；不要用其他版本的整个 exe 覆盖组合安装。

Exit the game and run `restore.cmd`. For a custom game location, append the same path option used during installation. Keep the mod folder and generated backups. Do not overwrite combined installations with another version's complete executable.

```powershell
python -X utf8 patch.py restore
```

## 兼容与安装顺序 / Compatibility and order

必须最后安装；升级、改键或卸载其他程序 mod 前先卸载本 mod。严格支持的基础包括原版、仅奔跑，以及奔跑＋俯视 v0.1.9＋描边 P 的默认组合；粒子减量独立。不能把已验证默认组合推广到任意子组合、版本或改键状态，未知完整哈希会拒绝安装。

Install last; remove this mod before upgrading, rebinding or removing other executable mods. Verified bases include the original game, toggle-run alone, and the default toggle-run + camera v0.1.9 + highlight P combination; particle reduction is independent. Validation does not cover arbitrary subsets, versions or rebound combinations. Unknown complete hashes are rejected.

## 实现与验证边界 / Implementation and validation

每显示帧最多一步，低帧率会降低推进速度，不补跑积压。一次 33 毫秒更新不等于移动一格或一次机关动作。音乐、纯渲染特效、界面动画及独立真实时间计时器不保证冻结。补丁不直接读写存档，但游戏仍可能自行保存。

At most one step runs per display frame; low frame rates slow repetition and missed steps do not accumulate. A 33 ms update is not one tile movement or puzzle action. Music, rendering-only effects, UI animations and independent real-time timers may continue. The mod does not access saves directly, but the game can still save.

已有真实 x64 钩子、时间累计、暂停 300 帧、不同帧率连步、99/33 毫秒边界、旧版升级及完整撤销检查。保留实验版版本号；敌人、机关、菜单、切关、撤销及存档流程仍需完整实机验收。

Existing checks cover real x64 hooks, time accumulation, 300 paused frames, repetition at different frame rates, 99/33 ms boundaries, upgrades and exact restoration. The experimental version label is retained; enemies, mechanisms, menus, transitions, undo and save workflows still need full gameplay validation.

## 更新与故障反馈 / Updates and troubleshooting

游戏更新或 Steam 验证文件可能移除补丁。遇到版本不符、未知修改或损坏备份时，不要跳过哈希检查。请在本仓库 Issues 提供游戏 Build ID、mod 版本、安装顺序、已安装 mod、操作步骤和完整错误信息；不要上传存档或完整游戏文件。

Game updates or Steam file verification may remove the patch. Do not bypass hash checks for unsupported versions, unknown modifications or damaged backups. Report the game Build ID, mod version, installation order, installed mods, reproduction steps and full errors in this repository's Issues. Do not upload saves or complete game files.

## 源码与署名 / Source and credits

仓库提供安装器、必要载荷及开发源码。日常安装使用已生成并校验的载荷；修改原生载荷后须重新构建并同步哈希。既有开发测试可能依赖本地合法游戏样本及同级 mod 工作区，不能视为下载后即能独立运行的通用测试。

The repository includes installers, required payloads and development sources. Normal installation uses generated, verified payloads; native payload changes require rebuilding and updating hashes. Existing developer tests may require local legitimate game samples and sibling mod workspaces; they are not universally standalone tests.

本项目是非官方 AI 生成 mod，与游戏开发商、发行商及 Steam 无隶属关系。游戏及其资源属于原权利人。

This is an unofficial AI-generated mod, unaffiliated with the game's developer, publisher or Steam. The game and its assets belong to their respective rights holders.
