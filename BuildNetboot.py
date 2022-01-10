#!/usr/bin/env python
## @ BuildNetBoot.py
# Build netboot UEFI payload main script
#
# Copyright (c) 2021, Intel Corporation. All rights reserved.<BR>
#  SPDX-License-Identifier: BSD-2-Clause-Patent

##
# Import Modules
#
import os
import sys

tool_dir = os.path.join(os.path.dirname (os.path.realpath(__file__)), 'Script')
sys.dont_write_bytecode = True
sys.path.append (tool_dir)

import re
import glob
import errno
import shutil
import argparse
import subprocess
import multiprocessing
from   ctypes import *
from   BuildUtility import *


def rebuild_basetools ():

    edk_dir  = '.'
    exe_list = 'GenFfs  GenFv  GenFw  GenSec  LzmaCompress  TianoCompress  VfrCompile'.split()
    ret = 0

    if os.name == 'posix':
        if not check_files_exist (exe_list, os.path.join(edk_dir, 'BaseTools', 'Source', 'C', 'bin')):
            ret = run_process (['make', '-C', 'BaseTools'])

    elif os.name == 'nt':

        if not check_files_exist (exe_list, os.path.join(edk_dir, 'BaseTools', 'Bin', 'Win32'), '.exe'):
            print ("Could not find pre-built BaseTools binaries, try to rebuild BaseTools ...")
            ret = run_process (['BaseTools/toolsetup.bat', 'forcerebuild'])

    if ret:
        print ("Build BaseTools failed, please check required build environment and utilities !")
        sys.exit(1)


def create_conf (workspace = '.'):
    # create conf and build folder if not exist
    if not os.path.exists(os.path.join(workspace, 'Conf')):
        os.makedirs(os.path.join(workspace, 'Conf'))
    for name in ['target', 'tools_def', 'build_rule']:
        txt_file = os.path.join(workspace, 'Conf/%s.txt' % name)
        if not os.path.exists(txt_file):
            shutil.copy (
                os.path.join(workspace, 'BaseTools/Conf/%s.template' % name),
                os.path.join(workspace, 'Conf/%s.txt' % name))


def prep_env (edk2_dir, toolchain_preferred = ''):
    # Verify toolchains first
    verify_toolchains(toolchain_preferred)

    os.environ['WORKSPACE'] = edk2_dir
    # Update Environment vars
    if os.name == 'nt':
        os.environ['PATH'] = os.environ['PATH'] + ';' + os.path.join(edk2_dir, 'BaseTools', 'Bin', 'Win32')
        os.environ['PATH'] = os.environ['PATH'] + ';' + os.path.join(edk2_dir, 'BaseTools', 'BinWrappers', 'WindowsLike')
        os.environ['PYTHONPATH'] = os.path.join(edk2_dir, 'BaseTools', 'Source', 'Python')
        os.environ['WINSDK_PATH_FOR_RC_EXE'] = r'C:\Program Files (x86)\Windows Kits\8.1\bin\x86'
    else:
        os.environ['PATH'] = os.environ['PATH'] + ':' + os.path.join(edk2_dir, 'BaseTools', 'BinWrappers', 'PosixLike')
    os.environ['EDK_TOOLS_PATH'] = os.path.join(edk2_dir, 'BaseTools')
    os.environ['BASE_TOOLS_PATH'] = os.path.join(edk2_dir, 'BaseTools')
    os.environ['CONF_PATH'] = os.path.join(os.environ['WORKSPACE'], 'Conf')
    create_conf ()

    # Check if BaseTools has been compiled
    rebuild_basetools ()


def main():

    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(help='command')
    edk2_dir = os.getcwd() + '/Edk2'
    branch = 'edk2-stable202102'


    def cmd_build_dsc(args):
        if not os.path.exists (edk2_dir):
            clone_repo (edk2_dir, 'http://github.com/tianocore/edk2.git', branch)
        else:
            netboot_inf = 'UefiPayloadPkg/NetBoot/NetBoot.inf'
            if os.path.exists(netboot_inf):
                os.remove (netboot_inf)
            apply_patch (edk2_dir, '../Patch/0001-Enable-iPXE-in-UEFI-Payload.patch', branch)

        os.chdir (edk2_dir)

        # prepare environment
        prep_env (edk2_dir, args.toolchain)

        # download netboot image
        netboot_path = os.path.join('UefiPayloadPkg', 'NetBoot', 'X64', 'NetBoot.efi')
        if not os.path.exists(os.path.dirname(netboot_path)):
            os.makedirs (os.path.dirname(netboot_path))
        if not os.path.exists(netboot_path):
            download_url ('https://boot.netboot.xyz/ipxe/netboot.xyz.efi', 'UefiPayloadPkg/NetBoot/X64/NetBoot.efi')

        cmd_args = [
            "build" if os.name == 'posix' else "build.bat",
            "--platform", 'UefiPayloadPkg/UefiPayloadPkg.dsc',
            "-b",         'RELEASE' if args.release else 'DEBUG',
            "--arch",     'X64',
            "--tagname",  os.environ['TOOL_CHAIN'],
            "-n",         str(multiprocessing.cpu_count()),
            ]

        run_process (cmd_args)

    buildp = sp.add_parser('build', help='build UEFI NetBoot payload')
    buildp.add_argument('-r',  '--release', action='store_true', help='Release build')
    buildp.add_argument('-t',  '--toolchain', dest='toolchain', type=str, default='', help='Perferred toolchain name')
    buildp.set_defaults(func=cmd_build_dsc)

    args = ap.parse_args()
    if len(args.__dict__) <= 1:
        # No arguments or subcommands were given.
        ap.print_help()
        ap.exit()

    args.func(args)

if __name__ == '__main__':
    main()
