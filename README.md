# Linux Firmware Cutter

Linux Firmware Cutter - utility that aims to help Linux distribution
maintainers and users separate large linux-firmware tarball into viable
logical parts.

## Problem

As for 2023, linux-firmware project grows over 820 Mb of raw data. Many files
are not required for average user's installation, for example, i915 video cards
does not require AMD GPU firmwares and vice versa. But, `i915` firmwares takes
over 25 Mb and `amdgpu` - over 65 Mb of unpacked data. Some cases go worse:
`iwlwifi` (Intel Wireless Wi-Fi) takes over 240 Mb!

Maintainers of Linux distribution may split large linux-firmware package into
subpackages, but which files belong to a group of supported hardware?
linux-firmware provides WHENCE file, where described all needed info about
grouping and installation instructions. Main problem is that WHENCE file is
non-structured, so with every release maintainer should recheck content all of
subpackages.

So here comes `linux-fw-cutter`. It uses a structured `WHENCE.yaml` file that allows
query, list, check and install desired subset of files.

## Usage

```
usage: linux-fw-cutter [-h] [-V VERBOSE] {check,info,install,list} ...

Query info and installs firmware files

options:
  -h, --help            show this help message and exit
  -V VERBOSE, --verbose VERBOSE
                        Specify verbose level (DEBUG, INFO, WARNING, ERROR or
                        CRITICAL, default is WARNING)

Commands:
  valid subcommands

  {check,info,install,list}
    check               Check WHENCE.yaml content and files
    info                Get info about entries that comply filtered query
    install             Install firmware files that comply filtered query
    list                List all unique entries for provided query
```

Query and installation subcommands support queries that filter requested
data. You can filter them for names (`-n`), vendors (`-v`), categories (`-c`),
and licenses (`-l`).

Here are some quick examples.

Let's say we need query info about `rtl8192cu` entry:

```
# linux-fw-cutter info -V -n rtl8192cu
Entry: rtl8192cu
Description: Realtek 802.11n WLAN driver for RTL8192CU
Categories:
  - drivers/net/wireless 
Vendor: Realtek
License:
  Name: LICENCE.rtlwifi_firmware.txt
  Copyright: Copyright (c) 2010, Realtek Semiconductor Corporation. All rights reserved.

  Info: Redistributable
Info:
From Vendor's rtl8188C_8192C_usb_linux_v4.0.1_6911.20130308 driver
All files extracted from driver/hal/rtl8192c/usb/Hal8192CUHWImg.c
Relevant variables (CONFIG_BT_COEXISTENCE not set):
- rtlwifi/rtl8192cufw_A.bin: Rtl8192CUFwUMCACutImgArray
- rtlwifi/rtl8192cufw_B.bin: Rtl8192CUFwUMCBCutImgArray
- rtlwifi/rtl8192cufw_TMSC.bin: Rtl8192CUFwTSMCImgArray

Size: 64,362 bytes
Files:
  - rtlwifi/rtl8192cufw.bin
  - rtlwifi/rtl8192cufw_A.bin
  - rtlwifi/rtl8192cufw_B.bin
  - rtlwifi/rtl8192cufw_TMSC.bin
Links:
None
--------
```

List all available licenses:
```
# linux-fw-cutter list --license
GPL-2
GPL-3
LICENCE.Abilis
LICENCE.IntcSST2
LICENCE.Marvell
LICENCE.NXP
LICENCE.Netronome
LICENCE.OLPC
LICENCE.adsp_sst
LICENCE.agere
LICENCE.atheros_firmware
LICENCE.broadcom_bcm43xx
LICENCE.ca0132
LICENCE.cadence
LICENCE.cavium
LICENCE.cavium_liquidio
LICENCE.chelsio_firmware
LICENCE.cnm
LICENCE.cw1200
LICENCE.cypress
LICENCE.e100
LICENCE.ene_firmware
LICENCE.fw_sst_0f28
LICENCE.go7007
LICENCE.ibt_firmware
LICENCE.it913x
LICENCE.iwlwifi_firmware
LICENCE.kaweth
LICENCE.mediatek
LICENCE.microchip
LICENCE.moxa
LICENCE.myri10ge_firmware
LICENCE.nvidia
LICENCE.open-ath9k-htc-firmware
LICENCE.phanfw
LICENCE.qat_firmware
LICENCE.qla1280
LICENCE.qla2xxx
LICENCE.r8a779x_usb3
LICENCE.ralink-firmware.txt
LICENCE.ralink_a_mediatek_company_firmware
LICENCE.rockchip
LICENCE.rtlwifi_firmware.txt
LICENCE.siano
LICENCE.ti-connectivity
LICENCE.ti-keystone
LICENCE.ti-tspa
LICENCE.ueagle-atm4-firmware
LICENCE.via_vt6656
LICENCE.wl1251
LICENCE.xc4000
LICENCE.xc5000
LICENCE.xc5000c
LICENSE.Lontium
LICENSE.QualcommAtheros_ar3k
LICENSE.QualcommAtheros_ath10k
LICENSE.amd-sev
LICENSE.amd-ucode
LICENSE.amdgpu
LICENSE.amlogic_vdec
LICENSE.amphion_vpu
LICENSE.atmel
LICENSE.cirrus
LICENSE.dib0700
LICENSE.hfi1_firmware
LICENSE.i915
LICENSE.ice
LICENSE.ice_enhanced
LICENSE.ipu3_firmware
LICENSE.nxp_mc_firmware
LICENSE.qcom
LICENSE.radeon
LICENSE.sdma_firmware
Redistributable
Unknown
wfx/LICENCE.wf200
```

Install only open-source firmwares:

```
# linux-fw-cutter install -l GPL-2,GPL-3
```

## License

Copyright (c) 2022-2023 Azamat H. Hackimov <azamat.hackimov@gmail.com>

License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>

This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.