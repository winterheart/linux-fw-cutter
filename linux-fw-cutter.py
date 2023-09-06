#!/usr/bin/python

# This file is part of Linux Firmware Cutter project
# SPDX-License-Identifier: GPL-3.0-or-later
# (c) 2022-2023 Azamat H. Hackimov <azamat.hackimov@gmail.com>

from enum import Enum
from pathlib import Path

import argparse
import logging
import lzma
import shutil
import sys
import yaml
import yaml.scanner

from marshmallow import Schema, fields, post_load, exceptions
from zstandard import ZstdCompressor


class CompressionType(Enum):
    """Enum class for compression methods"""
    NONE = "none"
    ZSTD = "zst"
    XZ = "xz"


class CustomFormatter(logging.Formatter):
    """Custom logger formatter"""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    fmt = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + fmt + reset,
        logging.INFO: grey + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
        logging.CRITICAL: bold_red + fmt + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def list_dir(directory, relative_directory):
    return set(sorted([file.relative_to(relative_directory).as_posix()
                       for file in Path(directory).rglob('*') if file.is_file()
                       and not file.relative_to(relative_directory).as_posix().startswith(".")]))


def relative_to(first: Path, second: Path):
    # This function is loosely equivalent to pathlib.Path.relative_to with walk_up from Python 3.12
    # There no some guards and fail checks, and we assume that first and second paths at least in
    # same directory
    num_common_parts = 0
    num_second_parts = len(second.parts)
    for first_part, second_part in zip(first.parts, second.parts):
        if first_part != second_part:
            break
        num_common_parts += 1
    up_parts = (num_second_parts - num_common_parts) * ("..", )

    path_parts = up_parts + first.parts[num_common_parts:]
    return Path(*path_parts)


class MetadataSchema(Schema):
    """Metadata entry schema validator"""
    format_version = fields.String(required=True)
    firmware_version = fields.String(required=True)

    @post_load
    def make_object(self, data, **kwargs):
        return Metadata(**data)


class LicenseSchema(Schema):
    """License entry schema validator"""
    name = fields.String(required=True)
    copyright = fields.String()
    info = fields.String()

    @post_load
    def make_object(self, data, **kwargs):
        return License(**data)


class FileSchema(Schema):
    """File entry schema validator"""
    name = fields.String(required=True)
    info = fields.String()
    source = fields.List(fields.String())
    version = fields.String()
    links = fields.List(fields.String())
    compress = fields.Boolean()

    @post_load
    def make_object(self, data, **kwargs):
        return File(**data)


class EntrySchema(Schema):
    """Entry schema validator"""
    name = fields.String(required=True)
    description = fields.String(required=True)
    category = fields.List(fields.String(required=True), required=True)
    vendor = fields.String(required=True)
    license = fields.Nested(LicenseSchema, required=True)
    info = fields.String(required=True)
    files = fields.List(fields.Nested(FileSchema), required=True)

    @post_load
    def make_object(self, data, **kwargs):
        return Entry(**data)


class WhenceSchema(Schema):
    """Whole file schema validator"""
    metadata = fields.Nested(MetadataSchema, required=True)
    entries = fields.List(fields.Nested(EntrySchema), required=True)


class File:
    """File class representation."""
    def __init__(self, name, info=None, source=None, version=None, links=None, compress=True):
        self.name = name
        self.info = info
        self.source = source
        self.version = version
        self.links = links
        self.compress = compress

    def __repr__(self):
        return f"<File(name={self.name}, " \
               f"info={self.info}, " \
               f"source={self.source}, " \
               f"version={self.version}, " \
               f"links={self.links}, " \
               f"compress={self.compress}" \
               ")>"

    def __str__(self):
        result = f"  - Name: {self.name}"
        if self.links is not None:
            result += "\n    Links:"
            for itm in self.links:
                result += f"\n      - {itm}"
        return result


class Metadata:
    """Metadata class representation."""
    def __init__(self, format_version, firmware_version):
        self.format_version = format_version
        self.firmware_version = firmware_version

    def __repr__(self):
        return f"<Metadata(format_version={self.format_version}, " \
               f"firmware_version={self.firmware_version})>"

    def __str__(self):
        return f"format_version: {self.format_version}\n" \
               f"firmware_version: {self.firmware_version}"


class License:
    """License class representation"""
    def __init__(self, name, copyright=None, info=None):
        self.name = name
        self.copyright = copyright
        self.info = info

    def __repr__(self):
        return f"<License(name={self.name}, " \
               f"copyright={self.copyright}, " \
               f"info={self.info})>"

    def __str__(self):
        result = f"  Name: {self.name}"
        if self.copyright is not None:
            result += f"\n  Copyright: {self.copyright}"
        if self.info is not None:
            result += f"\n  Info: {self.info}"
        return result


class Entry:
    """
    Entry class representation.
    """
    def __init__(self, name, description, category, vendor, license, info, files):
        self.name = name
        self.description = description
        self.category = category
        self.vendor = vendor
        self.license = license
        self.info = info
        self.files = files
        self.size = 0

    def __repr__(self):
        return f"<Entry (name={self.name}, description={self.description}, " \
               f"category={self.category}, vendor={self.vendor}, license={self.license}, " \
               f"info={self.info}, files={self.files})>"

    def __str__(self):
        return "Entry: {self.name}\n" \
               "Description: {self.description}\n" \
               "Categories:\n{categories}\n" \
               "Vendor: {self.vendor}\n" \
               "License:\n{self.license}\n" \
               "Info:\n{self.info}\n" \
               "Size: {self.size:,} bytes\n" \
               "Files:\n{files}\n" \
               "--------\n" \
            .format(
                self=self,
                categories="\n".join(f"  - {itm}" for itm in self.category),
                files="\n".join(f"{itm}" for itm in self.files),
            )


class WhenceLoader:
    """Main class for loading everything."""
    def __init__(self, whence_file="WHENCE.yaml"):
        """Load WHENCE.yaml file and initialize object"""
        self.supported_version = "3"
        try:
            loaded = yaml.safe_load(Path(whence_file).read_text())
            schema = WhenceSchema()
            self.whence_content = schema.load(loaded)
            if self.whence_content["metadata"].format_version != self.supported_version:
                logger.error("Format version of WHENCE-file mismatch: "
                             f"'{self.supported_version}' expected, "
                             f"'{self.whence_content['metadata'].format_version}' actual.")
                sys.exit(1)
        except FileNotFoundError as e:
            logger.error(f"WHENCE-file '{whence_file}' not found: {e}!")
            sys.exit(1)
        except yaml.scanner.ScannerError as e:
            logger.error(f"Format of WHENCE-file is incorrect: {e}!")
            sys.exit(1)
        except exceptions.ValidationError as e:
            logger.error(f"Schema of WHENCE-file is incorrect: {e}!")
            sys.exit(1)

    def _install(self, source: Path, file: File, destination: Path, compress: CompressionType):
        """Install requested file"""
        sourcepath = source / file.name
        if not sourcepath.exists():
            logger.error(f"Source file {source} does not exists")
            return

        fullpath = destination / file.name
        if file.compress:
            fullpath = fullpath.with_suffix(fullpath.suffix + "." + compress.value)
        fullpath.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        if fullpath.exists() and fullpath.is_file():
            logger.warning(f"Target file {fullpath} exists, overwriting")
            fullpath.unlink()

        if fullpath.is_dir():
            return
        logger.info(f"Copying {file.name} to {fullpath}")
        try:
            if file.compress:
                match compress:
                    case CompressionType.XZ:
                        with open(sourcepath, "rb") as source_fd:
                            with lzma.open(fullpath, "wb", check=lzma.CHECK_CRC32) as dest_fd:
                                shutil.copyfileobj(source_fd, dest_fd)
                    case CompressionType.ZSTD:
                        with open(sourcepath, "rb") as source_fd:
                            with open(fullpath, "wb") as dest_fd:
                                compressor = ZstdCompressor(write_content_size=True,
                                                            write_checksum=True)
                                compressor.copy_stream(source_fd, dest_fd,
                                                       size=sourcepath.stat().st_size)
                    case CompressionType.NONE:
                        shutil.copyfile(sourcepath, fullpath)
            else:
                shutil.copyfile(sourcepath, fullpath)

        except shutil.SameFileError:
            pass

    def _install_symlink(self, destination: Path, source: File, link: Path,
                         compress: CompressionType):
        """Install requested symlink"""
        source_name = Path(source.name)
        # Don't resolve it, pathlib will follow symlinks
        linkpath = Path(destination) / Path(link)
        if source.compress:
            source_name = source_name.with_suffix(source_name.suffix + "." + compress.value)
            linkpath = linkpath.with_suffix(linkpath.suffix + "." + compress.value)
        parentpath = linkpath.parent
        # Create parentpath early since targetpath may require existing path
        parentpath.mkdir(mode=0o755, parents=True, exist_ok=True)

        sourcepath = Path(destination) / source_name
        if not sourcepath.exists():
            logger.error(f"Source file {sourcepath} does not exists")
            return

        if linkpath.exists():
            logger.warning(f"Target link {linkpath} exists, overwriting")
            linkpath.unlink()

        local_file = relative_to(source_name, Path(link).parent)
        logger.info(f"Making link {linkpath} to {local_file}")
        linkpath.symlink_to(local_file)

    def check(self, args):
        """Check WHENCE.yaml content, compare file lists with actual files in repo"""
        # Ignorable files
        known_paths = [".asc", "check_whence.py", "configure", "copy-firmware.sh", "Dockerfile",
                       "firmware-install.py", "ChangeLog", "Makefile", "NOTICE.txt",
                       "README.md", "WHENCE", "WHENCE.yaml"]
        # Ignorable license names
        known_licenses = ["Redistributable", "Unknown"]
        # Get content (files, sources, licenses)
        entries = self.list()
        # Get all filenames from files section
        # N.B.: Don't include directories ("/" at end of path)
        whence_files = set(itm.name for itm in entries for itm in itm.files if itm.name[-1] != "/")
        # Append licenses files
        whence_files.update(set(
            itm.license.name for itm in entries if itm.license.name not in known_licenses
        ))
        # Append source entries from files section (only regular files)
        # If source points to directory, all files recursively
        # from that directory will be added
        for itm in set(
                itm for itm in list(
                    itm.source for itm in entries for itm in itm.files if itm.source is not None)
                for itm in itm):
            full_path = Path(args.source) / Path(itm)
            if full_path.is_dir():
                whence_files.update(list_dir(full_path, args.source))
            else:
                whence_files.add(itm)

        ret = 0
        if not Path(args.source).is_dir():
            logger.error(f"'{args.source}' is not a directory")
            return 1
        output = list_dir(args.source, args.source)

        for name in output.difference(whence_files):
            if name.endswith(tuple(known_paths)):
                continue
            logger.error(f"'{name}' not listed in WHENCE.yaml")
            ret = 1

        for name in whence_files.difference(output):
            logger.error(f"'{name}' listed in WHENCE.yaml does not exist")
            ret = 1

        return ret

    def get(self, name):
        """
        Returns info about particular entry_name or empty list if no such entry
        """
        return list(filter(lambda d: d.name == name, self.whence_content["entries"]))

    def list(self, names=None, vendors=None, categories=None, files=None, licenses=None):
        """Return list of entries that matches provided filters"""
        return list(
            filter(lambda d: (
                    (names is None or d.name in names) and
                    (vendors is None or d.vendor in vendors) and
                    (licenses is None or d.license.name in licenses) and
                    (files is None or any(
                        map(lambda each: each in (itm.name for itm in d.files), files))
                     ) and
                    (categories is None or any(map(lambda each: each in d.category, categories)))
            ), self.whence_content["entries"]))

    def install(self, source: Path, destination: Path, names=None, vendors=None, categories=None,
                files=None, licenses=None, compress=CompressionType.NONE):
        """Install files from filtered query list"""
        entries = self.list(names=names, vendors=vendors, categories=categories, files=files,
                            licenses=licenses)

        for entry in entries:
            for file in entry.files:
                self._install(source, file, destination, compress)
                if file.links is not None:
                    for link in file.links:
                        self._install_symlink(destination, file, link, compress)


if __name__ == "__main__":
    logger = logging.getLogger("firmware-install")

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setFormatter(CustomFormatter())

    logger.addHandler(ch)

    def do_check(args):
        """Method for checking WHENCE.yaml."""
        content = WhenceLoader(args.whence)
        sys.exit(content.check(args))

    def do_info(args):
        """Method for querying info about entries."""
        content = WhenceLoader(args.whence)
        if not args.terse:
            print(f"format_version: {content.whence_content['metadata'].format_version}\n"
                  f"firmware_version: {content.whence_content['metadata'].firmware_version}\n")
        for entry in content.list(
                names=args.names,
                vendors=args.vendors,
                licenses=args.licenses,
                files=args.files,
                categories=args.categories
        ):
            if args.terse:
                print(entry.name)
            else:
                try:
                    entry.size = sum(
                        (args.source / Path(itm.name)).stat().st_size for itm in entry.files
                    )
                except FileNotFoundError as e:
                    logger.debug(f"Error calculation file size: {e}!")
                print(entry)
        sys.exit(0)

    def do_install(args):
        """Method for installing files."""
        content = WhenceLoader(args.whence)
        destination = Path(args.destination).resolve()
        destination.mkdir(exist_ok=True)
        try:
            source = Path(args.source).resolve(strict=True)
        except FileNotFoundError:
            logger.error(f"{args.source} does not exists!")
            return
        content.install(
            source,
            destination,
            names=args.names,
            vendors=args.vendors,
            licenses=args.licenses,
            files=args.files,
            categories=args.categories,
            compress=CompressionType(args.compress)
        )

    def do_list(args):
        """Method for listing entries."""
        content = WhenceLoader(args.whence)
        entries = content.list()

        if args.licenses:
            licenses = sorted(set(itm.license.name for itm in entries))
            print("\n".join(licenses))
        elif args.vendors:
            vendors = sorted(set(itm.vendor for itm in entries))
            print("\n".join(vendors))
        elif args.categories:
            categories = sorted(set(itm for itm in entries for itm in itm.category))
            print("\n".join(categories))
        elif args.files:
            files = sorted(set(itm.name for itm in entries for itm in itm.files))
            print("\n".join(files))
        else:
            # Default - list names
            names = sorted(set(itm.name for itm in entries))
            print("\n".join(names))

    # Main
    parser = argparse.ArgumentParser(
        prog="firmware-install.py",
        description="Query info and installs firmware files"
    )
    parser.set_defaults(func=lambda arg: parser.print_help())
    parser.add_argument("-V", "--verbose",
                        help="Specify verbose level (DEBUG, INFO, WARNING, ERROR or CRITICAL, "
                             "default is WARNING)", default="WARNING")
    subparsers = parser.add_subparsers(title="Commands", description="valid subcommands")
    parser_check = subparsers.add_parser("check", help="Check WHENCE.yaml content and files")
    parser_info = subparsers.add_parser("info",
                                        help="Get info about entries that comply filtered query")
    parser_install = subparsers.add_parser("install",
                                           help="Install firmware files that comply filtered query")
    parser_list = subparsers.add_parser("list", help="List all unique entries for provided query")

    parser_check.set_defaults(func=do_check)
    parser_info.set_defaults(func=do_info)
    parser_install.set_defaults(func=do_install)
    parser_list.set_defaults(func=do_list)

    parser_check.add_argument("-w", "--whence",
                              help="Specify custom WHENCE.yaml file (default is WHENCE.yaml)",
                              default="WHENCE.yaml")

    group_list = parser_list.add_mutually_exclusive_group()
    group_list.add_argument("-n", "--names", action="store_true",
                            help="Get all unique entry names")
    group_list.add_argument("-v", "--vendors", action="store_true",
                            help="Get all unique vendor names")
    group_list.add_argument("-c", "--categories", action="store_true",
                            help="Get all unique category names")
    group_list.add_argument("-l", "--licenses", action="store_true",
                            help="Get all unique license names")
    group_list.add_argument("-f", "--files", action="store_true",
                            help="Get all installable files")
    parser_list.add_argument("-w", "--whence",
                             help="Specify custom WHENCE.yaml file (default is WHENCE.yaml)",
                             default="WHENCE.yaml")

    for i in [parser_info, parser_install]:
        i.add_argument("-n", "--names", nargs="+", help="Query filter with entry names")
        i.add_argument("-v", "--vendors", nargs="+", help="Query filter with vendor names")
        i.add_argument("-c", "--categories", nargs="+", help="Query filter with categories")
        i.add_argument("-l", "--licenses", nargs="+", help="Query filter with licenses")
        i.add_argument("-f", "--files", nargs="+", help="Query filter with files")
        i.add_argument("-w", "--whence",
                       help="Specify custom WHENCE.yaml file (default is WHENCE.yaml)",
                       default="WHENCE.yaml")
    for i in [parser_check, parser_info, parser_install]:
        i.add_argument("-s", "--source",
                       help="Source directory of linux-firmware package (default is current "
                            "directory",
                       default=".")
    parser_info.add_argument("-t", "--terse", action="store_true", help="Terse mode",
                             default=False)

    parser_install.add_argument("-d", "--destination",
                                help="Destination directory (default is /lib/firmware)",
                                default="/lib/firmware")
    parser_install.add_argument("-C", "--compress",
                                help="Compression algorithm (none, zst, xz, default is none)",
                                default="none")

    arguments = parser.parse_args()
    logger.setLevel(arguments.verbose)
    ch.setLevel(arguments.verbose)

    arguments.func(arguments)
