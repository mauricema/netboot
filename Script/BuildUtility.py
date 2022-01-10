#!/usr/bin/env python
## @ BuildUtility.py
# Build bootloader main script
#
# Copyright (c) 2016 - 2021, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
##

##
# Import Modules
#
import os
import sys
import re
import ntpath
import subprocess
import urllib.request
from   distutils.version import LooseVersion


# Mimimum Toolchain Requirement
build_toolchains = {
    'python'    : '3.6.0',
    'nasm'      : '2.12.02',
    'iasl'      : '20160422',
    'openssl'   : '1.1.0g',
    'git'       : '2.20.0',
    'vs'        : '2015',
    'gcc'       : '7.3',
    'clang'     : '9.0.0'
}

def Fatal (msg):
    sys.stdout.flush()
    raise Exception (msg)


def download_url (url, save_path):
    urllib.request.urlretrieve (url, save_path)


def clone_repo (clone_dir, repo, branch):
    if not os.path.exists(clone_dir + '/.git'):
        print ('Cloning the repo ... %s' % repo)
        cmd = 'git clone %s %s' % (repo, clone_dir)
        ret = subprocess.call(cmd.split(' '))
        if ret:
            fatal ('Failed to clone repo to directory %s !' % clone_dir)
        print ('Done\n')
    else:
        print ('Update the repo ...')
        cmd = 'git fetch origin'
        ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
        if ret:
            fatal ('Failed to update repo in directory %s !' % clone_dir)
        print ('Done\n')

    print ('Checking out specified version ... %s' % branch)

    cmd = 'git checkout %s -f' % branch
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to check out specified branch !')
    print ('Done\n')

    cmd = 'git submodule init'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to init submodules !')
    print ('Done\n')

    cmd = 'git submodule update'
    ret = subprocess.call(cmd.split(' '), cwd=clone_dir)
    if ret:
        fatal ('Failed to update submodules !')
    print ('Done\n')


def apply_patch (cur_dir, patch_path, branch):
    print ('Applying patch ...')
    cmd = 'git checkout %s -f' % branch
    ret = subprocess.call(cmd.split(' '), cwd=cur_dir)
    if ret:
        fatal ('Failed to check out specified branch !')
    cmd = 'git am --abort'
    with open(os.devnull, 'w') as fnull:
        ret = subprocess.call(cmd.split(' '), cwd=cur_dir, stdout=fnull, stderr=subprocess.STDOUT)
    cmd = 'git am --keep-cr --whitespace=nowarn %s' % patch_path
    ret = subprocess.call(cmd.split(' '), cwd=cur_dir)
    if ret:
        Fatal ('Failed to apply patch !')
    print ('Done\n')


def check_files_exist (base_name_list, dir = '', ext = ''):
    for each in base_name_list:
        if not os.path.exists (os.path.join (dir, each + ext)):
            return False
    return True


def run_process (arg_list, print_cmd = False, capture_out = False):
    sys.stdout.flush()
    if os.name == 'nt' and os.path.splitext(arg_list[0])[1] == '' and \
       os.path.exists (arg_list[0] + '.exe'):
        arg_list[0] += '.exe'
    if print_cmd:
        print (' '.join(arg_list))

    exc    = None
    result = 0
    output = ''
    try:
        if capture_out:
            output = subprocess.check_output(arg_list).decode()
        else:
            result = subprocess.call (arg_list)
    except Exception as ex:
        result = 1
        exc    = ex

    if result:
        if not print_cmd:
            print ('Error in running process:\n  %s' % ' '.join(arg_list))
        if exc is None:
            sys.exit(1)
        else:
            raise exc

    return output


def is_valid_tool_version(cmd, current_version, optional=False):
    if 1:
        name_str = ntpath.basename(cmd).split('.')[0]
        name = re.sub(r'\d+', '', name_str)
        minimum_version = build_toolchains[name]
        valid = LooseVersion(current_version) >= LooseVersion(minimum_version)
    if 0: #except:
        print('Unexpected exception while checking %s tool version' % cmd)
        return False

    try:
        if os.name == 'posix':
            cmd = subprocess.check_output(['which', cmd], stderr=subprocess.STDOUT).decode().strip()
    except:
        pass

    print ('- %s: Version %s (>= %s) [%s]' % (cmd, current_version, minimum_version, \
           'PASS' if valid else 'RECOMMEND' if optional else 'FAIL'))
    return valid | optional


def get_gcc_info ():
    toolchain = 'GCC5'
    cmd = 'gcc'
    try:
        ver = subprocess.check_output([cmd, '-dumpfullversion']).decode().strip()
    except:
        ver = ''
        pass
    valid = is_valid_tool_version(cmd, ver)
    return (toolchain if valid else None, None, None, ver)


def get_clang_info ():
    if os.name == 'posix':
        toolchain_path   = ''
    else:
        # On windows, still need visual studio to provide nmake build utility
        toolchain, toolchain_prefix, toolchain_path, toolchain_ver = get_visual_studio_info ()
        os.environ['CLANG_HOST_BIN'] =  os.path.join(toolchain_path, "bin\\Hostx64\\x64\\n")
        toolchain_path   = 'C:\\Program Files\\LLVM\\bin\\'
    toolchain        = 'CLANGPDB'
    toolchain_prefix = 'CLANG_BIN'
    cmd = os.path.join(toolchain_path, 'clang')
    try:
        ver_str = subprocess.check_output([cmd, '--version']).decode().strip()
        ver = re.search(r'version\s*([\d.]+)', ver_str).group(1)
    except:
        ver = ''
        pass
    valid = is_valid_tool_version(cmd, ver)
    return (toolchain if valid else None, toolchain_prefix, toolchain_path, ver)


def get_visual_studio_info (preference = ''):

    toolchain        = ''
    toolchain_prefix = ''
    toolchain_path   = ''
    toolchain_ver    = ''
    vs_ver_list      = ['2019', '2017']
    vs_ver_list_old  = ['2015', '2013']

    if preference:
        preference = preference.strip().lower()
        if not preference.startswith('vs'):
            print("Invalid vistual studio toolchain type '%s' !" % preference)
            return (None,None,None,None)
        vs_str = preference[2:]
        if vs_str in vs_ver_list:
            vs_ver_list     = [vs_str]
            vs_ver_list_old = []
        elif vs_str in vs_ver_list_old:
            vs_ver_list     = []
            vs_ver_list_old = [vs_str]
        else:
            print("Unsupported toolchain version '%s' !" % preference)
            return (None,None,None,None)

    # check new Visual Studio Community version first
    vswhere_path = "%s/Microsoft Visual Studio/Installer/vswhere.exe" % os.environ['ProgramFiles(x86)']
    if os.path.exists (vswhere_path):
        cmd = [vswhere_path, '-all', '-property', 'installationPath']
        lines = run_process (cmd, capture_out = True)
        vscommon_paths = []
        for each in lines.splitlines ():
            each = each.strip()
            if each and os.path.isdir(each):
                vscommon_paths.append(each)

        for vs_ver in vs_ver_list:
            for vscommon_path in vscommon_paths:
                vcver_file = vscommon_path + '\\VC\\Auxiliary\\Build\\Microsoft.VCToolsVersion.default.txt'
                if os.path.exists(vcver_file):
                    check_path = '\\Microsoft Visual Studio\\%s\\' % vs_ver
                    if check_path in vscommon_path:
                        toolchain_ver    = get_file_data (vcver_file, 'r').strip()
                        toolchain_prefix = 'VS%s_PREFIX' % (vs_ver)
                        toolchain_path   = vscommon_path + '\\VC\\Tools\\MSVC\\%s\\' % toolchain_ver
                        toolchain = 'VS%s' % (vs_ver)
                        break
            if toolchain:
                break

    if toolchain == '':
        vs_ver_dict = {
            '2015': 'VS140COMNTOOLS',
            '2013': 'VS120COMNTOOLS'
        }
        for vs_ver in vs_ver_list_old:
            vs_tool = vs_ver_dict[vs_ver]
            if vs_tool in os.environ:
                toolchain        ='VS%s%s' % (vs_ver, 'x86')
                toolchain_prefix = 'VS%s_PREFIX' % (vs_ver)
                toolchain_path   = os.path.join(os.environ[vs_tool], '..//..//')
                toolchain_ver    = vs_ver
                parts   = os.environ[vs_tool].split('\\')
                vs_node = 'Microsoft Visual Studio '
                for part in parts:
                    if part.startswith(vs_node):
                        toolchain_ver = part[len(vs_node):]
                break

    valid = is_valid_tool_version('vs', vs_ver)
    return (toolchain if valid else None, toolchain_prefix, toolchain_path, toolchain_ver)


def check_for_python():
    '''
    Verify Python executable is at required version
    '''
    os.environ['PYTHON_COMMAND'] = sys.executable
    cmd = os.environ['PYTHON_COMMAND']
    ver = subprocess.check_output([cmd, '--version']).decode().strip().split()[-1]
    try:
        ver = subprocess.check_output([cmd, '--version']).decode().strip().split()[-1]
    except:
        ver = ''
        pass
    return is_valid_tool_version(cmd, ver)


def check_for_openssl():
    '''
    Verify OpenSSL executable is available
    '''
    cmd = get_openssl_path ()
    try:
        ver = subprocess.check_output([cmd, 'version']).decode().strip().split()[1]
    except:
        print('ERROR: OpenSSL not available. Please set OPENSSL_PATH.')
        ver = ''
        pass
    return is_valid_tool_version(cmd, ver)


def check_for_nasm():
    '''
    Verify NASM executable is available
    '''
    if os.name == 'nt' and 'NASM_PREFIX' not in os.environ:
        os.environ['NASM_PREFIX'] = "C:\\Nasm\\"

    cmd = os.path.join(os.environ.get('NASM_PREFIX', ''), 'nasm')
    try:
        ver_str = subprocess.check_output([cmd, '-v']).decode().strip()
        ver = re.search(r'version\s*([\d.]+)', ver_str).group(1)
    except:
        print('ERROR: NASM not available. Please set NASM_PREFIX.')
        ver = ''
        pass
    return is_valid_tool_version(cmd, ver)


def check_for_iasl():
    '''
    Verify iasl executable is available
    '''
    if os.name == 'nt' and 'IASL_PREFIX' not in os.environ:
        os.environ['IASL_PREFIX'] = "C:\\ASL\\"

    cmd = os.path.join(os.environ.get('IASL_PREFIX', ''), 'iasl')
    try:
        ver_str = subprocess.check_output([cmd, '-v']).decode().strip()
        ver = re.search(r'version\s*([\d.]+)', ver_str).group(1)
    except:
        print('ERROR: iasl not available. Please set IASL_PREFIX.')
        ver = ''
        pass
    return is_valid_tool_version(cmd, ver)


def check_for_git():
    '''
    Verify Git executable is available
    '''
    cmd = 'git'
    try:
        ver_str = subprocess.check_output([cmd, '--version']).decode().strip()
        ver = re.search(r'version\s*([\d.]+)', ver_str).group(1)
    except:
        print('ERROR: Git not found. Please install Git or check if Git is in the PATH environment variable.')
        ver = ''
        pass
    return is_valid_tool_version(cmd, ver, True)


def check_for_toolchain(toolchain_preferred):
    toolchain = None
    if toolchain_preferred.startswith('clang'):
        toolchain, toolchain_prefix, toolchain_path, toolchain_ver = get_clang_info ()
    elif sys.platform == 'darwin':
        toolchain, toolchain_prefix, toolchain_path, toolchain_ver = get_clang_info ()
        toolchain, toolchain_prefix, toolchain_path = 'XCODE5', None, None
    elif os.name == 'posix':
        toolchain, toolchain_prefix, toolchain_path, toolchain_ver = get_gcc_info ()
    elif os.name == 'nt':
        toolchain, toolchain_prefix, toolchain_path, toolchain_ver = get_visual_studio_info (toolchain_preferred)

    if not toolchain:
        return False

    os.environ['TOOL_CHAIN'] = toolchain
    if toolchain_prefix:
        os.environ[toolchain_prefix] = toolchain_path
    return True


def verify_toolchains(toolchain_preferred):
    print('Checking Toolchain Versions...')

    valid  = check_for_python()
    valid &= check_for_openssl()
    valid &= check_for_nasm()
    valid &= check_for_iasl()
    valid &= check_for_git()
    valid &= check_for_toolchain(toolchain_preferred)

    if valid != True:
        print('...Failed! Please check toolchain versions!')
        sys.exit(-1)
    print('...Done!\n')


def get_openssl_path ():
    if os.name == 'nt':
        if 'OPENSSL_PATH' not in os.environ:
            openssl_dir = "C:\\Openssl\\bin\\"
            if os.path.exists (openssl_dir):
                os.environ['OPENSSL_PATH'] = openssl_dir
            else:
                os.environ['OPENSSL_PATH'] = "C:\\Openssl\\"
                if 'OPENSSL_CONF' not in os.environ:
                    openssl_cfg = "C:\\Openssl\\openssl.cfg"
                    if os.path.exists(openssl_cfg):
                        os.environ['OPENSSL_CONF'] = openssl_cfg
        openssl = os.path.join(os.environ.get ('OPENSSL_PATH', ''), 'openssl.exe')
    else:
        # Get openssl path for Linux cases
        import shutil
        openssl = shutil.which('openssl')

    return openssl


def get_file_data (file, mode = 'rb'):
    return open(file, mode).read()
