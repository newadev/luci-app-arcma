# luci-app-arcma

**ARCMA** 是一个用于 OpenWrt / ImmortalWrt 的 LuCI 应用，用来在启动或接口上线时自动更改网络接口 MAC 地址。

它提供 LuCI 图形界面、命令行工具、init.d 启动任务和 hotplug 触发器，支持本地管理随机 MAC、厂商 OUI 伪装和固定 MAC 三种模式。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](luci-app-arcma/LICENSE)
[![OpenWrt/ImmortalWrt >= 24.10](https://img.shields.io/badge/OpenWrt%2FImmortalWrt-%3E%3D24.10-green.svg)](https://openwrt.org)

## 特性

- LuCI 菜单入口统一为 **Network -> ARCMA**。
- 支持启动时、接口上线时，或两者同时触发。
- 支持 `local`、`oui`、`static` 三种 MAC 模式。
- 内置 Router / WLAN / Ethernet / Console OUI 数据库。
- 支持按物理接口覆盖全局配置。
- 自动保存原始 MAC 到 `/etc/arcma/orig/`，便于恢复。
- hotplug 使用 `/tmp` 原子锁做短时间防抖，避免频繁 ifup 重复执行。
- 可选将随机后的 MAC 写入 `uci network.<iface>.macaddr`。

## 目录结构

```text
README.md
luci-app-arcma/
  Makefile
  htdocs/luci-static/resources/view/arcma.js
  root/etc/config/arcma
  root/etc/init.d/arcma
  root/etc/hotplug.d/iface/20-arcma
  root/usr/sbin/arcma
  root/usr/share/arcma/oui/*.txt
  root/usr/share/luci/menu.d/luci-app-arcma.json
  root/usr/share/rpcd/acl.d/luci-app-arcma.json
  po/
```

## 依赖

- OpenWrt / ImmortalWrt 24.10 或更新版本。
- `ip-full`，由包依赖自动选择。
- BusyBox `sh`、`hexdump`、`uci`、`logger` 等基础工具。

## 编译安装

### 通过 feed 编译

在 OpenWrt 源码根目录的 `feeds.conf.default` 中加入：

```bash
src-git arcma https://github.com/newadev/luci-app-arcma.git;main
```

然后执行：

```bash
./scripts/feeds update arcma
./scripts/feeds install -p arcma luci-app-arcma
make menuconfig
make package/feeds/arcma/luci-app-arcma/compile V=s
```

在 `menuconfig` 中选择：

```text
LuCI -> Applications -> luci-app-arcma
```

### 直接克隆到 package

```bash
git clone https://github.com/newadev/luci-app-arcma.git package/arcma
./scripts/feeds update -a
./scripts/feeds install -a
make menuconfig
make package/arcma/luci-app-arcma/compile V=s
```

## LuCI 使用

安装后进入：

```text
Network -> ARCMA
```

常用流程：

1. 勾选 `Enable ARCMA`。
2. 选择触发方式：`Boot only`、`Interface up (hotplug)` 或 `Boot + Interface up`。
3. 选择默认 MAC 模式。
4. 需要单独控制某个物理接口时，在 `Per-interface Override` 添加一行。
5. 点击 `Apply Now` 立即保存并应用。

## CLI 使用

查看状态：

```bash
arcma show
```

生成一个本地管理随机 MAC，不应用到接口：

```bash
arcma gen
```

生成一个厂商 OUI MAC：

```bash
arcma gen -m oui -t router -v Asus
```

按 UCI 配置应用：

```bash
uci set arcma.global.enabled='1'
uci set arcma.global.trigger='both'
uci set arcma.global.mode='local'
uci commit arcma
arcma uci-apply
```

恢复原始 MAC：

```bash
arcma restore
```

只对指定物理接口应用：

```bash
arcma apply eth0
```

使用厂商 OUI：

```bash
arcma apply -m oui -t router -v Asus eth0
```

使用固定 MAC：

```bash
arcma apply -m static -s 02:11:22:33:44:55 eth0
```

## UCI 配置示例

全局本地随机：

```text
config arcma 'global'
	option enabled '1'
	option trigger 'both'
	option mode 'local'
	option sequence '0'
	option persist '0'
```

全局厂商 OUI：

```text
config arcma 'global'
	option enabled '1'
	option trigger 'both'
	option mode 'oui'
	option oui_type 'router'
	option oui_vendor 'Asus'
	option sequence '0'
	option persist '0'
```

指定接口固定 MAC：

```text
config iface
	option enabled '1'
	option device 'eth0'
	option mode 'static'
	option static_mac '02:11:22:33:44:55'
	option persist '0'
```

## 触发方式

- `boot`：只在 init.d 启动时执行。
- `ifup`：只在接口上线 hotplug 事件中执行。
- `both`：启动和接口上线都执行。

hotplug 会优先使用环境变量 `DEVICE`。如果不存在，则从 `network.<INTERFACE>.device` 或 `network.<INTERFACE>.ifname` 推导物理设备名。

## 注意事项

- 修改 MAC 会短暂 down/up 目标接口，可能导致连接瞬断。
- `persist=1` 会写入 `/etc/config/network` 并提交 UCI 配置，适合希望重启后保持同一 MAC 的场景。
- DSA/bridge 场景请优先对 `br-lan` 这类 network device 做持久化；桥成员端口（例如 `eth1`、`lan1`）运行时可以改 MAC，但不一定有对应的 UCI device 段可写。
- 默认配置不会自动启用，需要在 LuCI 或 UCI 中设置 `arcma.global.enabled='1'`。
- 如果从旧版本升级，建议检查 `/etc/config/arcma` 中是否残留旧的 `config iface 'default'` 段；该段可能覆盖全局设置。

## 排障

LuCI 按钮没有反应：

```bash
/etc/init.d/rpcd restart
rm -rf /tmp/luci-*
```

查看脚本是否可执行：

```bash
ls -l /usr/sbin/arcma /etc/init.d/arcma /etc/hotplug.d/iface/20-arcma
```

查看当前配置：

```bash
uci show arcma
```

查看 LuCI `Apply Now` / `Restore Original` 后台执行日志：

```bash
cat /tmp/arcma/last.log
```

查看可用 OUI 类型和厂商：

```bash
arcma list
arcma list router
```

手动测试但不修改接口：

```bash
arcma gen
arcma gen -m static -s 02:11:22:33:44:55
```

## 许可证

MIT License。详见 [luci-app-arcma/LICENSE](luci-app-arcma/LICENSE)。
