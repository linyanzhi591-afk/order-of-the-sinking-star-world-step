# 发行验证 / Release validation

验证日期：2026-10-20。公开包不附带完整游戏程序、原版资源、存档、本机备份或旧 Git 历史。

Validation date: 2026-10-20. The public package includes no complete game executables, original assets, saves, local backups or old Git history.

本发行目录已完成隔离副本的首次安装、重复安装、状态检查、卸载和精确恢复；测试不修改实际游戏。隔离测试在调用作用域替换运行进程查询，发行安装器仍保留原有游戏运行保护。Python 语法、JSON 及 CMD 换行检查通过。

This release directory passed isolated first/repeated installation, status, uninstallation and exact-restoration checks without modifying the actual game. Process queries were mocked only within isolated test calls; the distributed installers retain their game-running guards. Python syntax, JSON and CMD line-ending checks passed.

相关原生回归：描边真实 x64 开关；俯视 125 组镜头、历史升级、Windows 映像加载；世界单步六组真实机器码测试。本次世界单步测试只在内存中剥离本机未完成网格层，再将已验证组合写入临时样本。

Related native regressions: real x64 highlight toggle; 125 camera orientations, upgrades and Windows image loading; six world-step machine-code test groups. For this run, the unfinished local grid layer was removed in memory and the verified world-step combination written only to a temporary sample.

上述测试不代表全关卡、实机画面、性能或实体手柄验收。适用范围及限制以 README 为准。

These checks do not constitute complete level, visual, performance or physical-controller acceptance. See README for scope and limitations.
