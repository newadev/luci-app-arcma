# SPDX-License-Identifier: MIT
# Copyright (C) 2026 arcma contributors

include $(TOPDIR)/rules.mk

PKG_LICENSE:=MIT
PKG_MAINTAINER:=arcma contributors

LUCI_TITLE:=LuCI for ARCMA
LUCI_DEPENDS:=+ip-full
LUCI_PKGARCH:=all

PKG_VERSION:=1.0.0
PKG_RELEASE:=1

include $(TOPDIR)/feeds/luci/luci.mk

define Package/$(PKG_NAME)/conffiles
/etc/config/arcma
endef

define Package/$(PKG_NAME)/postinst
#!/bin/sh
[ -n "$$IPKG_INSTROOT" ] && exit 0
chmod +x /usr/sbin/arcma
chmod +x /etc/init.d/arcma
chmod +x /etc/hotplug.d/iface/20-arcma
/etc/init.d/arcma enable
exit 0
endef

define Package/$(PKG_NAME)/prerm
#!/bin/sh
[ -n "$$IPKG_INSTROOT" ] && exit 0
/etc/init.d/arcma stop 2>/dev/null
/etc/init.d/arcma disable 2>/dev/null
exit 0
endef

# call BuildPackage - OpenWrt buildroot signature
