# luci-app-arcma

**Automatic Random changer MAC Address for OpenWrt**

> 本项目参考 [muink/luci-app-change-mac](https://github.com/muink/luci-app-change-mac) 和 [muink/rgmac](https://github.com/muink/rgmac)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OpenWrt ≥ 23.05](https://img.shields.io/badge/OpenWrt-%E2%89%A523.05-green.svg)](https://openwrt.org)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#零依赖设计)

---

## 目录

- [项目简介](#项目简介)
- [特性一览](#特性一览)
- [零依赖设计](#零依赖设计)
- [兼容性](#兼容性)
- [安装](#安装)
  - [安装前检查（必须）](#安装前检查必须)
  - [方式一：通过 OpenWrt Buildroot（本地包目录）编译【推荐】](#方式一通过-openwrt-buildroot本地包目录编译推荐)
  - [方式二：通过自定义 Feed 编译](#方式二通过自定义-feed-编译)
  - [方式三：安装已编译 ipk（路由器侧）](#方式三安装已编译-ipk路由器侧)
  - [方式四：开发调试直接部署（不走 opkg）](#方式四开发调试直接部署不走-opkg)
  - [安装后最小验证（建议执行）](#安装后最小验证建议执行)
  - [卸载与回滚](#卸载与回滚)
- [快速开始](#快速开始)
- [配置参考](#配置参考)
  - [UCI 配置文件结构](#uci-配置文件结构)
  - [global 节 — 全局设置](#global-节--全局设置)
  - [iface 节 — 按接口独立配置](#iface-节--按接口独立配置)
  - [配置示例](#配置示例)
- [arcma 命令行参考](#arcma-命令行参考)
  - [命令概览](#命令概览)
  - [apply — 应用 MAC](#apply--应用-mac)
  - [restore — 还原 MAC](#restore--还原-mac)
  - [show — 查看状态](#show--查看状态)
  - [list — 列出厂商](#list--列出厂商)
  - [gen — 生成 MAC（不应用）](#gen--生成-mac不应用)
- [内置 OUI 厂商数据库](#内置-oui-厂商数据库)
  - [router — 路由器](#router--路由器)
  - [wlan — 无线网卡](#wlan--无线网卡)
  - [eth — 有线网卡](#eth--有线网卡)
  - [console — 游戏主机](#console--游戏主机)
- [LuCI 界面说明](#luci-界面说明)
- [工作原理](#工作原理)
  - [MAC 生成算法](#mac-生成算法)
  - [原始 MAC 保护机制](#原始-mac-保护机制)
  - [触发机制](#触发机制)
  - [热插拔防抖](#热插拔防抖)
  - [Persist 模式](#persist-模式)
- [文件结构](#文件结构)
- [从源码编译](#从源码编译)
- [常见问题](#常见问题)
- [版本历史](#版本历史)
- [许可证](#许可证)

---

## 项目简介

`luci-app-arcma` 是一个 OpenWrt 上的 MAC 地址自动随机化工具。  
它在设备启动时和/或每次网络接口上线时（netifd `ifup` 热插拔事件），自动将所有或指定物理网络接口的 MAC 地址替换为随机值，从而防止设备被上游网络（ISP、Wi-Fi 热点等）通过固定 MAC 特征识别和追踪。

### 场景示例

| 场景 | 作用 |
|---|---|
| 运营商 PPPoE / DHCP 锁机 | 每次连接呈现不同 MAC，绕过 MAC 绑定限制 |
| 公共 Wi-Fi 追踪防护 | 防止热点记录设备 MAC 历史 |
| CGNAT / 流量溯源防护 | 使上游路由器无法通过 MAC 关联设备身份 |
| 测试/开发环境 | 快速模拟不同厂商设备接入网络 |
| 虚拟机 / 隔离容器网络 | 批量分配无冲突的随机 MAC |

---

## 特性一览

- **全量自动化**：一条配置 `device '*'` 自动枚举并处理路由器上全部物理接口，无需手动列举
- **双触发模式**：可分别或同时在开机（`boot`）和接口 `ifup` 热插拔事件时触发
- **热插拔防抖**：同一接口 10 秒内重复 `ifup` 事件只执行一次，防止接口抖动反复改 MAC
- **多种 MAC 类型**：
  - `local` — 本地管理地址（最大随机性，符合 IEEE 802.1Q 隐私地址规范）
  - `oui` — 从内置厂商数据库随机选取 OUI 前缀（伪装成真实设备）
  - `static` — 完全固定的指定 MAC（需配合 `-s` 参数）
- **顺序模式**：多接口时 NIC 字节递增，同一 OUI 前缀下的多个 MAC 形成逻辑连续性
- **按接口独立配置**：通过 `iface` 节对每块网卡单独指定模式、厂商、是否持久化
- **Persist 模式**：可选将随机 MAC 写入 `uci network.<iface>.macaddr` 跨重启持久保持
- **内置 OUI 数据**：4 类厂商共 35 家，每家提供 10 条真实 OUI 前缀，编译时打包，运行时零网络请求
- **零外部依赖**：核心脚本为纯 POSIX sh，仅使用 BusyBox、Linux sysfs 和 `ip-full`（OpenWrt 常见组件）
- **LuCI Web 界面**：完整的图形化配置界面，支持简体中文 / 繁体中文 / 英文
- **接口安全性**：`ip link set address` 失败时接口仍会被恢复 UP，不会导致断网

---

## 零依赖设计

arcma 完全基于 OpenWrt 基础镜像中固有的工具实现，无需额外安装任何软件包：

| 所需工具 | 来源 | 用途 |
|---|---|---|
| `sh` (ash) | BusyBox (base) | 脚本运行时 |
| `od` | BusyBox (base) | 从 `/dev/urandom` 读取随机字节 |
| `printf` `sed` `grep` `cut` `tr` `wc` | BusyBox (base) | 文本处理与 MAC 格式化 |
| `uci` | OpenWrt base | 读写 UCI 配置 |
| `logger` | BusyBox (base) | 写入系统日志 |
| `ip link` | `ip-full` | 应用 MAC 地址（自动 fallback 到 `ifconfig`） |
| `/dev/urandom` | Linux kernel | 密码学安全的随机熵源 |
| `/sys/class/net/` | Linux kernel sysfs | 接口枚举、当前 MAC 读取、出厂 MAC 读取 |



---

## 兼容性

| 系统 | 版本 | 状态 |
|---|---|---|
| OpenWrt | 23.05.x（稳定版） | ✅ 完全支持 |
| OpenWrt | 24.10.x（稳定版） | ✅ 完全支持 |
| OpenWrt | SNAPSHOT（开发版） | ✅ 完全支持 |
| OpenWrt | ≤ 21.02 | ⚠️ 未测试（缺少 `permaddr` sysfs 节点） |

**内核要求**：Linux ≥ 3.11（`/sys/class/net/<iface>/permaddr` 节点，用于读取出厂 MAC）。低于此版本时自动回退到快照机制保存原始 MAC。

---

## 安装

### 安装前检查（必须）

在路由器上先确认基础环境：

```bash
cat /etc/openwrt_release 2>/dev/null 
opkg update
opkg list-installed | grep -E '^luci-base|^rpcd|^ip-full' || true
```

若 `ip-full` 未安装：

```bash
opkg install ip-full
```

---

### 方式一：通过 OpenWrt Buildroot（本地包目录）编译【推荐】

适用于你本地已有 OpenWrt SDK 或完整源码树。

```bash
# 1) 进入 buildroot 根目录
cd /path/to/openwrt

# 2) 把本项目包目录链接到 package（注意是子目录 luci-app-arcma）
mkdir -p package/local
ln -sf luci-app-arcma package/local/luci-app-arcma

# 3) 更新 feeds（确保 luci feed 可用）
./scripts/feeds update -a
./scripts/feeds install -a

# 4) 选择包
make menuconfig
# LuCI -> Applications -> luci-app-arcma 设为 <*> 或 <M>

# 5) 编译单包
make package/luci-app-arcma/compile V=s
```

产物通常在：

```bash
bin/packages/*/*/luci-app-arcma_*.ipk
```

---

### 方式二：通过自定义 Feed 编译

如果你维护独立 feed，可用如下方式：

```bash
cd /path/to/openwrt

# 1) 在 feeds.conf.default 或 feeds.conf 添加（示例，显式指定 main 分支）
echo "src-git arcma https://github.com/newadev/luci-app-arcma.git;main" >> feeds.conf.default

# 2) 更新并安装该 feed 内包
./scripts/feeds update arcma
./scripts/feeds install -p arcma luci-app-arcma

# 3) 选择并编译
make menuconfig
make package/luci-app-arcma/compile V=s
```

> 本仓库采用 feed 根目录 + `luci-app-arcma/` 子目录结构，可被 `scripts/feeds` 正常索引。

---

### 方式三：安装已编译 ipk（路由器侧）

```bash
# 1) 上传 ipk
scp bin/packages/*/*/luci-app-arcma_*.ipk root@<router-ip>:/tmp/

# 2) 安装
ssh root@<router-ip>
opkg update
opkg install /tmp/luci-app-arcma_*.ipk
```

安装后立即检查：

```bash
which arcma
arcma --version
ls -l /etc/init.d/arcma /etc/hotplug.d/iface/20-arcma /usr/share/arcma/oui
/etc/init.d/arcma enabled; echo $?   # 返回 0 表示已启用
```

---

### 方式四：开发调试直接部署（不走 opkg）

仅建议开发阶段使用：

```bash
# 工作站执行：同步文件
rsync -av luci-app-arcma/root/ root@<router-ip>:/
rsync -av luci-app-arcma/htdocs/ root@<router-ip>:/

# 路由器执行：权限 + 启用
ssh root@<router-ip>
chmod +x /usr/sbin/arcma /etc/init.d/arcma /etc/hotplug.d/iface/20-arcma
/etc/init.d/arcma enable
/etc/init.d/arcma restart
```

若 LuCI 页面未更新，清理缓存：

```bash
rm -rf /tmp/luci-* /tmp/*cache*
/etc/init.d/uhttpd restart
```

---

### 安装后最小验证（建议执行）

```bash
# 1) 打开总开关
uci set arcma.global.enabled='1'
uci set arcma.global.trigger='both'
uci set arcma.global.mode='local'
uci commit arcma

# 2) 手动应用并查看
arcma uci-apply
arcma show

# 3) 查看日志确认执行链路
logread | grep arcma | tail -n 30
```

### 卸载与回滚

```bash
# opkg 安装的包
opkg remove luci-app-arcma

# 如需恢复 network 中持久化的 MAC（若启用过 persist）
uci show network | grep '\.macaddr='
# 按需删除对应项后提交
# uci delete network.<section>.macaddr
uci commit network
```

---

## 快速开始

### 1. 启用并立即生效（命令行）

```bash
# 启用全局 MAC 随机化，使用本地管理地址模式，双触发
uci set arcma.global.enabled='1'
uci set arcma.global.trigger='both'
uci set arcma.global.mode='local'
uci commit arcma

# 立即应用（不等重启）
arcma uci-apply
arcma show
```

### 2. 伪装成 Asus 路由器（OUI 模式）

```bash
uci set arcma.global.enabled='1'
uci set arcma.global.mode='oui'
uci set arcma.global.oui_type='router'
uci set arcma.global.oui_vendor='Asus'
uci commit arcma
arcma uci-apply
```

### 3. 针对单个接口配置

```bash
# 只对 wan 口的物理设备 eth0 做 MAC 随机化，伪装成 Intel 网卡
uci add arcma iface
uci set arcma.@iface[-1].enabled='1'
uci set arcma.@iface[-1].device='eth0'
uci set arcma.@iface[-1].mode='oui'
uci set arcma.@iface[-1].oui_type='eth'
uci set arcma.@iface[-1].oui_vendor='Intel'
uci commit arcma
arcma uci-apply eth0
```

### 4. 通过 LuCI 界面配置

登录 LuCI → **Network → Auto MAC Randomizer**，配置全局设置后点击「Apply Now」即可。

---

## 配置参考

### UCI 配置文件结构

配置文件位于 `/etc/config/arcma`，包含一个 `global` 命名节和任意数量的匿名 `iface` 节：

```
config arcma 'global'           ← 全局/默认设置
    option enabled '1'
    ...

config iface                    ← 按接口独立覆盖（可选，可多个）
    option device 'eth0'
    ...

config iface
    option device 'wlan0'
    ...
```

当不存在任何 `iface` 节，或所有 `iface` 节均 `enabled=0` 时，全局配置自动应用于所有物理接口。

---

### global 节 — 全局设置

| 选项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool (`0`/`1`) | `0` | 主开关。`0` 时 arcma 完全不工作 |
| `trigger` | enum | `both` | 触发时机（详见[触发机制](#触发机制)）：`boot` \| `ifup` \| `both` |
| `mode` | enum | `local` | MAC 生成模式：`local` \| `oui` \| `static` |
| `oui_type` | enum | `router` | OUI 类型（`mode=oui` 时生效）：`router` \| `wlan` \| `eth` \| `console` |
| `oui_vendor` | string | `Asus` | 厂商名（`mode=oui` 且 `oui_prefix` 为空时生效），参见[厂商列表](#内置-oui-厂商数据库) |
| `oui_prefix` | string | `` | 手动指定 OUI 前缀（格式 `XX:XX:XX`），非空时覆盖 `oui_vendor` 选择 |
| `sequence` | bool | `0` | 顺序模式（详见[顺序模式说明](#apply--应用-mac)） |
| `persist` | bool | `0` | 将随机 MAC 写入 `uci network.<iface>.macaddr` 持久化 |

#### `trigger` 选项详解

| 值 | 行为 |
|---|---|
| `boot` | 仅在 `init.d/arcma start`（开机 START=21）时执行一次 |
| `ifup` | 仅由 `hotplug.d/iface/20-arcma` 在每次 `ifup` 事件时触发，忽略开机顺序 |
| `both` | 开机执行一次，之后每次 `ifup` 也触发（推荐） |

---

### iface 节 — 按接口独立配置

每个 `config iface` 节覆盖特定物理接口的配置。存在至少一个有效（`enabled=1`）的 `iface` 节时，全局 fallback 不生效。

| 选项 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | bool | `1` | 此 iface 节是否生效 |
| `device` | string | *必填* | 物理接口名（如 `eth0`、`wlan0`），或 `*` 表示所有物理接口 |
| `mode` | enum | `local` | 此接口的 MAC 生成模式 |
| `oui_type` | enum | `router` | OUI 类型（`mode=oui` 时） |
| `oui_vendor` | string | — | 厂商名（`mode=oui` 且 `oui_prefix` 为空时） |
| `oui_prefix` | string | — | 手动 OUI 前缀，非空时覆盖 `oui_vendor` |
| `sequence` | bool | `0` | 顺序模式 |
| `persist` | bool | `0` | 持久化此接口的随机 MAC |

---

### 配置示例

#### 示例 1：全量本地随机，双触发（最简配置）

```
config arcma 'global'
    option enabled '1'
    option trigger 'both'
    option mode 'local'
    option persist '0'
```

效果：所有物理接口（`eth*`、`wlan*` 等有 `device` 硬件链接的接口）在开机和每次 `ifup` 时获得新的随机本地管理 MAC。

#### 示例 2：WAN 口伪装 Asus，其余接口保持随机

```
config arcma 'global'
    option enabled '1'
    option trigger 'both'

config iface
    option enabled '1'
    option device 'eth0'
    option mode 'oui'
    option oui_type 'router'
    option oui_vendor 'Asus'

config iface
    option enabled '1'
    option device 'wlan0'
    option mode 'local'

config iface
    option enabled '1'
    option device 'wlan1'
    option mode 'local'
```

#### 示例 3：持久化伪装，重启后 MAC 不变

```
config arcma 'global'
    option enabled '1'
    option trigger 'boot'
    option mode 'oui'
    option oui_type 'router'
    option oui_vendor 'Tp-Link'
    option persist '1'
```

首次开机生成随机 MAC 并写入 `uci network.wan.macaddr`，此后 netifd 负责维持该值。

#### 示例 4：多接口顺序模式（同 OUI 连续 NIC 字节）

```
config arcma 'global'
    option enabled '1'
    option trigger 'boot'

config iface
    option enabled '1'
    option device '*'
    option mode 'oui'
    option oui_type 'eth'
    option oui_vendor 'Intel'
    option sequence '1'
```

效果：假设枚举到 `eth0 eth1`，生成如 `A4:BB:6D:1A:2B:3C`、`A4:BB:6D:1A:2B:3D` 这样 NIC 字节递增的连续 MAC。

---

## arcma 命令行参考

### 命令概览

```
arcma <command> [options] [arguments]

命令:
  apply    [opts] [iface ...]   更改 MAC 地址
  restore  [iface ...]          还原原始 MAC
  show     [iface ...]          查看当前/原始 MAC 状态
  list     [type]               列出内置 OUI 类型和厂商
  gen      [opts]               生成 MAC（仅打印，不应用）
  uci-apply  [iface]            由 init.d / hotplug 调用，按 UCI 配置执行
  uci-restore [iface]           还原 UCI 配置覆盖的接口
  -V | --version                显示版本
  -h | --help | help            显示帮助
```

---

### apply — 应用 MAC

```
arcma apply [选项] [接口名 ...]
```

将随机 MAC（或指定 MAC）应用到一个或多个接口。未指定接口时，自动处理所有物理接口。

| 选项 | 说明 |
|---|---|
| `-m local` | 本地管理地址模式（默认）。bit1=1（locally-administered），bit0=0（unicast），其余 46 位完全随机 |
| `-m oui` | 从内置 OUI 数据库选取前缀，NIC 部分完全随机 |
| `-m static` | 固定 MAC，配合 `-s` 传入完整 6 字节 MAC |
| `-t <type>` | OUI 类型（`-m oui` 时生效）：`router` \| `wlan` \| `eth` \| `console`，默认 `router` |
| `-v <Vendor>` | 厂商名（`-m oui` 且未指定 `-s` 时必填），参见[厂商列表](#内置-oui-厂商数据库) |
| `-s <XX:XX:XX>` | 手动 OUI 前缀（`-m oui`）或完整 MAC（`-m static`） |
| `-e` | 顺序模式：在指定接口列表中，NIC 字节从随机基值开始递增 |
| `-p` | Persist：成功应用后将新 MAC 写入 `uci network.<iface>.macaddr` |

**使用示例：**

```bash
# 全量本地随机
arcma apply

# 只处理 eth0 和 eth1
arcma apply eth0 eth1

# 伪装成 Sony PlayStation（使用 console 类型）
arcma apply -m oui -t console -v Sony eth0

# 手动指定 OUI 前缀，在 wlan0/wlan1 上生成连续 MAC
arcma apply -m oui -s DC:A6:32 -e wlan0 wlan1

# 固定 MAC（用于测试）
arcma apply -m static -s AA:BB:CC:DD:EE:FF eth0

# 伪装 Intel 有线网卡并持久化
arcma apply -m oui -t eth -v Intel -p eth0
```

**顺序模式（`-e`）示意：**

```
不加 -e（Disorderly）:
  eth0  →  A4:BB:6D:72:1F:9A   (完全随机 NIC)
  eth1  →  A4:BB:6D:CE:3B:07   (完全随机 NIC)

加 -e（Sequence，共享随机基值后递增）:
  eth0  →  A4:BB:6D:2C:11:40
  eth1  →  A4:BB:6D:2C:11:41
  eth2  →  A4:BB:6D:2C:11:42
```

---

### restore — 还原 MAC

```
arcma restore [接口名 ...]
```

将接口 MAC 恢复到 arcma 首次运行前记录的值（优先使用内核 `/sys/class/net/<iface>/permaddr` 出厂 MAC，其次使用 `/tmp/arcma_orig/<iface>` 快照）。

```bash
# 还原所有接口
arcma restore

# 只还原 eth0
arcma restore eth0
```

> **注意**：`/tmp/arcma_orig/` 目录在重启后会丢失。若 `permaddr` 节点不可用且未在本次运行中生成快照，restore 将无法获取原始值。通过 `persist=0`（不持久化）可以避免此问题——只要重启，MAC 自然由 netifd 从硬件加载。

---

### show — 查看状态

```
arcma show [接口名 ...]
```

打印接口的当前 MAC、原始 MAC 和地址类型，未指定接口时显示所有物理接口。

**输出示例：**

```
Interface     Current MAC          Original MAC         Type
---------     -----------          ------------         ----
eth0          A4:BB:6D:2C:11:40    DC:11:22:33:44:55    global-unique
eth1          02:7F:A3:1E:9B:CC    DC:11:22:33:44:56    local-admin
wlan0         74:D0:2B:88:11:FE    74:D0:2B:12:34:56    global-unique
```

---

### list — 列出厂商

```
arcma list [type]
```

```bash
# 列出所有可用 OUI 类型
arcma list

# 列出 router 类型下的所有厂商名
arcma list router

# 其他类型
arcma list wlan
arcma list eth
arcma list console
```

---

### gen — 生成 MAC（不应用）

```
arcma gen [选项]
```

生成并打印一个 MAC 地址，不对任何接口执行操作。

```bash
# 生成随机本地管理 MAC
arcma gen

# 生成 Asus 路由器风格 MAC
arcma gen -m oui -t router -v Asus

# 生成任天堂游戏机风格 MAC
arcma gen -m oui -t console -v Nintendo

# 使用手动 OUI 前缀生成
arcma gen -m oui -s 74:D0:2B
```

---

## 内置 OUI 厂商数据库

数据库位于 `/usr/share/arcma/oui/`，采用 TAB 分隔的文本格式。  
每次调用时从该厂商的 OUI 列表中**随机**选取一条，再拼接随机 NIC 字节——即使同一厂商每次生成的 MAC 也不相同。

---

### router — 路由器

用于 WAN / LAN 接口，伪装成常见消费级路由器。

| 厂商名 | 代表型号 |
|---|---|
| `Asus` | RT-AX88U, RT-AC86U 系列 |
| `Tp-Link` | Archer AX73, TL-WDR 系列 |
| `Netgear` | Nighthawk RAX50, R7000 系列 |
| `Xiaomi` | AX3600, AX6000, Redmi AX6 |
| `Huawei` | WS5200, AX3 Pro 系列 |
| `D-Link` | DIR-X1860, DIR-2640 系列 |
| `Linksys` | EA8300, MR9600 系列 |
| `Ubnt` | UniFi AP, EdgeRouter 系列 |
| `Cisco` | RV340, CBS350 系列 |
| `Buffalo` | WXR-5950AX12 系列 |

---

### wlan — 无线网卡

用于 `wlan*` 接口，伪装成常见 Wi-Fi 芯片/网卡厂商。

| 厂商名 | 常见产品 |
|---|---|
| `Intel` | AX210, AX200, AC9260 系列 |
| `Apple` | MacBook / iPhone 内置 Wi-Fi |
| `Liteon` | 各品牌笔记本 OEM 无线网卡 |
| `AzureWave` | 各品牌笔记本 OEM 无线网卡 |
| `HonHai` | 富士康 OEM 无线网卡 |
| `Qualcomm` | IPQ Atheros 无线芯片模组 |
| `Broadcom` | BCM43xx 系列无线芯片 |
| `Realtek` | RTL8821CE, RTL8822CE 系列 |
| `MediaTek` | MT7921, MT7922 系列 |
| `Atheros` | AR9xxx, QCA 系列（老款） |

---

### eth — 有线网卡

用于有线以太网接口，伪装成常见 PC / 服务器网卡。

| 厂商名 | 常见产品 |
|---|---|
| `Intel` | I225-V, I219-V, X550 系列 |
| `Realtek` | RTL8111, RTL8125BG 系列 |
| `Dell` | Dell PowerEdge 服务器网卡 |
| `Broadcom` | BCM5xxx 服务器网卡 |
| `Marvell` | 88E1xxx Gigabit PHY |
| `HP` | HP ProLiant 服务器网卡 |
| `VMware` | VMware VMXNET3 虚拟网卡 |
| `Mellanox` | ConnectX-4/5/6 高速网卡 |
| `Aquantia` | AQtion 2.5G/5G 网卡 |
| `Chelsio` | T520/T580 服务器网卡 |

---

### console — 游戏主机

用于特殊伪装场景（部分网络对游戏机 MAC 有宽松策略）。

| 厂商名 | 设备 |
|---|---|
| `Sony` | PlayStation 4 / PlayStation 5 |
| `Nintendo` | Nintendo Switch, Wii U |
| `Microsoft` | Xbox One, Xbox Series X/S |
| `Apple` | Apple TV, iPad, iPhone |
| `Valve` | Steam Deck, Steam Link |

---

## LuCI 界面说明

访问路径：**LuCI → Network → Auto MAC Randomizer**

### 全局设置区

| 字段 | 说明 |
|---|---|
| Enable arcma | 主开关 |
| Trigger | 触发时机：Boot only / Interface up / Boot + Interface up |
| Default MAC mode | `Locally administered (random)` 或 `Vendor OUI prefix` |
| Default OUI type | 选择 router / wlan / eth / console |
| Vendor name | 根据选中的 OUI type 动态切换下拉列表 |
| Manual OUI prefix | 输入 `XX:XX:XX` 格式的自定义 OUI，优先级高于 Vendor name |
| Sequence mode | 勾选后多接口 NIC 字节递增 |
| Persist MAC | 勾选后将 MAC 写入 network UCI 持久化 |

### 按接口配置表

点击「Add」可新增行，每行独立配置一块网卡。  
`device` 列填 `*` 可一次性覆盖所有物理接口。  
不添加任何行时，全局设置自动应用于所有物理接口。

### 操作区

| 按钮 | 功能 |
|---|---|
| **Apply Now** | 保存 UCI 配置并立即执行 `arcma uci-apply` |
| **Restore Original** | 执行 `arcma uci-restore`，恢复所有接口的原始 MAC |
| **Show Status** | 执行 `arcma show`，在页面内联显示当前/原始 MAC 表格 |

操作结果实时显示在按钮下方的输出区。

---

## 工作原理

### MAC 生成算法

#### local 模式

```
byte[0] = (rand_byte & 0xFE) | 0x02   # bit0=0(unicast), bit1=1(locally-administered)
byte[1..5] = rand_bytes(5)             # 完全随机
```

生成示例：`02:7F:A3:1E:9B:CC`

符合 IEEE 802 私有/随机 MAC 规范，与 Android、iOS、Windows 11 的 Wi-Fi MAC 随机化实现一致。

#### oui 模式

```
OUI[0..2] = 从厂商数据库随机选取一条真实 OUI 前缀
NIC[3..5] = rand_bytes(3)              # 完全随机
MAC = OUI + NIC                        # bit0=0(unicast), bit1=0(globally-unique)
```

生成示例：`74:D0:2B:88:11:FE`（Asus OUI + 随机 NIC）

#### 随机熵来源

```sh
rand_hex() {
    # od 是 BusyBox 内建命令，/dev/urandom 是 CSPRNG
    od -An -N"${bytes}" -tx1 /dev/urandom | tr -d ' \n\t' | cut -c1-"${n}"
}
```

---

### 原始 MAC 保护机制

arcma 在**首次修改接口 MAC 之前**自动保存原始值，保存操作幂等：

```
优先级 1: /sys/class/net/<iface>/permaddr    (内核提供的出厂 MAC，不受软件修改影响)
优先级 2: /tmp/arcma_orig/<iface>            (快照文件，首次运行时写入当前 MAC)
```

`permaddr` 由内核驱动层维护，即使多次 `ip link set address` 也不会改变，这是 arcma 能在重启后可靠还原到出厂 MAC 的基础。

---

### 触发机制

```
开机流程:
  procd → init.d/arcma (START=21)
                         ↑
                  netifd START=20 已完成接口初始化
                  arcma 在 netifd 之后运行，确保 MAC 不被 netifd 覆盖

热插拔流程:
  netifd ifup → /etc/hotplug.d/iface/20-arcma
              → ACTION=ifup 检查通过
              → 读取 arcma.global.enabled / trigger
              → arcma uci-apply <device>
```

> **为何 START=21？** netifd 启动顺序为 20。旧版 `luci-app-change-mac` 使用 START=17，导致 netifd 启动后从 `network.<iface>.macaddr` 读取旧值并覆盖刚设好的随机 MAC。START=21 确保 arcma 永远是最后设置 MAC 的组件。

---

### 热插拔防抖

网络接口在某些驱动或场景下会短时间内多次触发 `ifup`（PPPoE 协商重连、桥接成员变化等）。arcma 使用基于锁文件的防抖机制：

```sh
LOCK="/tmp/arcma_lock_${DEV}"
if [ -f "${LOCK}" ]; then
    exit 0                          # 10 秒内再次触发，直接退出
fi
touch "${LOCK}"
( sleep 10; rm -f "${LOCK}" ) &     # 后台 10 秒后自动解锁
arcma uci-apply "${DEV}"
```

同一设备 10 秒窗口内无论触发多少次 `ifup`，只执行一次 MAC 更改。

---

### Persist 模式

| 模式 | 行为 | 适用场景 |
|---|---|---|
| `persist=0`（默认） | 每次触发都重新随机；仅在内存中保持，重启后由硬件 MAC 重置 | 最大隐私保护，每次开机 / 接口 UP 都换 MAC |
| `persist=1` | 将随机 MAC 写入 `uci network.<iface>.macaddr`；netifd 重启时使用该值 | 希望 MAC 稳定但不使用出厂值（如需要 DHCP 续租同一地址） |

写入逻辑通过正则转义安全处理 VLAN 接口名（如 `eth0.1`）：

```sh
dev_esc=$(printf '%s' "${dev}" | sed 's/[\[\]\^\$\.\*\+\?\{\}\(\)|\\]/\\&/g')
section=$(uci show network | grep -E "\.device='?${dev_esc}'?" | ...)
uci set "network.${section}.macaddr=${mac}"
uci commit network
```

---

## 文件结构

```
luci-app-arcma/
├── Makefile                                      # OpenWrt BuildRoot 包定义
│                                                 # LUCI_DEPENDS: +ip-full
├── htdocs/
│   └── luci-static/resources/view/
│       └── arcma.js                              # LuCI 前端（CBI form API，纯 JS）
├── po/
│   ├── templates/arcma.pot                       # 翻译模板（所有 msgid）
│   ├── zh-cn/arcma.po                            # 简体中文翻译
│   └── zh-tw/arcma.po                            # 繁体中文翻译
└── root/
    ├── etc/
    │   ├── config/
    │   │   └── arcma                             # UCI 默认配置（enabled=0）
    │   ├── hotplug.d/iface/
    │   │   └── 20-arcma                          # 热插拔触发脚本（含防抖锁）
    │   └── init.d/
    │       └── arcma                             # procd 服务脚本，START=21
    └── usr/
        ├── sbin/
        │   └── arcma                             # 核心程序（纯 POSIX sh）
        └── share/
            ├── arcma/oui/
            │   ├── router.txt                    # 路由器 OUI，10 厂商各 10 条
            │   ├── wlan.txt                      # Wi-Fi 网卡 OUI，10 厂商各 10 条
            │   ├── eth.txt                       # 有线网卡 OUI，10 厂商各 10 条
            │   └── console.txt                   # 游戏主机 OUI，5 厂商各 10 条
            ├── luci/menu.d/
            │   └── luci-app-arcma.json           # LuCI 菜单（Network 分组，order=12）
            └── rpcd/acl.d/
                └── luci-app-arcma.json           # rpcd ACL 权限声明
```

### OUI 数据文件格式

```
# 注释行以 # 开头，解析时忽略
# 格式：VendorName <TAB> OUI1 OUI2 ... （空格分隔，最多 10 条）
Asus    AC:22:0B 04:D9:F5 10:7B:44 2C:FD:A1 74:D0:2B 50:46:5D 90:E6:BA 08:60:6E 30:5A:3A F8:32:E4
```

如需添加自定义厂商：

```bash
# 追加一行（VendorName 与 OUI 列表之间必须用 TAB 分隔）
printf 'MyRouter\t11:22:33 44:55:66\n' >> /usr/share/arcma/oui/router.txt

# 验证
arcma list router
arcma gen -m oui -t router -v MyRouter
```

---

## 从源码编译

### 前提

- OpenWrt buildroot 已配置完成（`make menuconfig` 可正常使用）
- 已安装 `feeds/luci`（`./scripts/feeds install luci`）

### 步骤

```bash
# 1. 克隆仓库到 package 目录（或通过 feeds）
git clone https://github.com/newadev/luci-app-arcma.git \
    package/feeds/arcma/luci-app-arcma

# 2. 编译单包
make package/feeds/arcma/luci-app-arcma/compile -j$(nproc) V=s

# 3. 产物位置
ls bin/packages/*/arcma/luci-app-arcma_*.ipk
```

### 通过 Feed 集成

```bash
# feeds.conf.default 末尾追加
echo 'src-link arcma /path/to/luci-app-arcma/..' >> feeds.conf.default

./scripts/feeds update arcma
./scripts/feeds install luci-app-arcma
make menuconfig   # LuCI → Applications → luci-app-arcma
make -j$(nproc)
```

---

## 常见问题

**Q: apply 后 MAC 没变？**

检查 `arcma.global.enabled` 是否为 `1`；用 `arcma show` 确认接口名；部分 USB Wi-Fi 驱动不支持运行时修改 MAC（驱动层限制）。

---

**Q: 重启后 MAC 恢复出厂值了？**

正常行为（`persist=0`，默认）。若希望随机 MAC 跨重启保持，设置 `persist=1` 并确保 `trigger` 包含 `boot`。

---

**Q: hotplug 触发了但 MAC 没变？**

可能在 10 秒防抖窗口内触发（接口快速抖动时正常）。用 `logread | grep arcma` 查看日志确认。

---

**Q: 如何查看运行日志？**

```bash
logread | grep arcma
```

arcma 所有操作均通过 `logger -t arcma` 记录到 syslog。

---

**Q: persist=1 写入后如何完全恢复？**

```bash
# 删除 network 中的 macaddr 选项
uci delete network.wan.macaddr
uci commit network

# 立即恢复接口 MAC
arcma restore eth0

# 禁用 arcma 防止下次开机再随机
uci set arcma.global.enabled='0'
uci commit arcma
```

---

**Q: 能否为 VLAN 接口（如 eth0.1）配置？**

可以。arcma 内部对设备名进行正则转义，`.` 不会被当作元字符：

```bash
arcma apply -m local eth0.1
```

或在 UCI 中直接填写 `option device 'eth0.1'`。

---

**Q: 能否在 OpenWrt 21.02 上使用？**

可以运行，但 `/sys/class/net/<iface>/permaddr` 在极少数旧硬件上可能不存在。此时自动回退到运行时快照（重启后失效）。建议升级到 23.05+。

---

## 版本历史

### v1.0.0（2026-02-23）

**初始发布**

- 纯 POSIX sh 实现，零外部依赖（移除 bash / curl / getopt / rgmac）
- 支持 `local` / `oui` / `static` 三种 MAC 模式
- 内置 4 类 35 家厂商 OUI 数据库（每家 10 条真实 IEEE OUI）
- 双触发机制（boot + hotplug），`trigger` 选项三档可调
- 热插拔防抖（10 秒每设备锁文件）
- 按接口独立 UCI `iface` 节配置
- `persist` 模式将 MAC 写入 `uci network`，支持跨重启
- `sequence` 模式多接口 NIC 字节递增
- LuCI 图形界面（简体中文 / 繁体中文 / 英文），按接口 TableSection 配置
- `START=21`，确保在 netifd（START=20）之后运行
- 修复：`ip link set address` 失败时接口不再永久保持 DOWN 状态
- 修复：`cmd_show` 对 `N/A` 值进行算术运算导致 ash 崩溃
- 修复：`persist_to_uci` VLAN 接口名中 `.` 被当作正则元字符
- 修复：`uci_apply` 所有 `iface` 节禁用或 hotplug filter 无匹配时 global fallback 不触发
- 修复：LuCI `this.map` 未赋值导致 Apply Now / Restore 按钮静默失败
- 修复：LuCI 移除未使用的 `rpc` / `widgets` 模块引用



