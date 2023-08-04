# WHENCE.yaml - database for linux-fw-cutter

This is part of linux-fw-cutter project. 

## WHENCE.yaml file

WHENCE.yaml file is YAML 1.2 compliant file with structured data about
firmware files. Particular file:

```yaml
# Metadata info
metadata:
  # Version supported by linux-fw-cutter.py
  format_version: "3"
  # Version of linux-firmware data
  firmware_version: "20230117"

# Entries with firmwares info
entries:
  - # Name of entry, usually the name of the module that loads firmware  
    name: rtl8xxxu
    # Description of entry
    description: Realtek 802.11n WLAN driver for RTL8XXX USB devices
    # List of categories where module resides
    category:
      - drivers/net/wireless
    # Vendor of firmware or device
    vendor: Realtek
    # License entry
    license:
      # Name of license file; May be "Redistributable" (if no license file)
      # or "Unknown" (if redistribution status is unknown)
      name: LICENCE.rtlwifi_firmware.txt
      # Optional: Copyright notice
      copyright: >
        Copyright (c) 2010, Realtek Semiconductor Corporation. All rights
        reserved.
      # Optional: Additional info for license information. If no license file,
      # add here cause for permission to distribute. Add
      # SPDX-License-Identifier (https://spdx.dev/ids/) if applicable
      info: Redistributable
    # Some descriptive information about firmware
    info: |
      rtl8723au taken from Realtek driver
      rtl8723A_WiFi_linux_v4.1.3_6044.20121224
      Firmware is embedded in the driver as data statements. This info has
      been extracted into a binary file.
    # List of firmware files
    files:
      - # Filename
        name: rtlwifi/rtl8723aufw_A.bin
        # Optional: version of firmware
        version: "35.7"
        # Optional: additional information about particular file
        info: Taken from old version
        # Optional: If there sources for firmware, add them as list here
        source:
          - rtlwifi/src/
      - name: rtlwifi/rtl8192eu_nic.bin
        # Optional: List of symlinks for being installed.
        # rtlwifi/rtl8192eefw.bin -> rtlwifi/rtl8723bs_nic.bin is means that in directory
        # rtlwifi will be created rtl8192eefw.bin that points to rtl8192eu_nic.bin
        # in that directory
        links:
          - rtlwifi/rtl8192eefw.bin
      - name: rtlwifi/rtl8723bs_nic.bin
```

After adding entry run `./linux-fw-cutter.py check` to verify correctness
of entry.

If firmware files comes with different licenses and/or different sources, add
them in separate entries (see `./linux-fw-cutter.py info -n ti_usb_3410_5052`
or `./linux-fw-cutter.py info -n cxgb3` as example).

## License

Copyright (c) 2022-2023 Azamat H. Hackimov <azamat.hackimov@gmail.com>

License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>

This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
