# coding:utf8
from __future__ import print_function
import logging
import re
import csv
import signal
import os
import sys
import subprocess as sp
from os import path


usage = """
Usage: python vmconvert.py vm.csv
"""


def init_log(level, filepath=None):
    """init instance of logging and return the instance, logger

    Args:
        level(logging.level): such as logging.DEBUG or logging.WARNING

    Returns:
        logger: instance of logging

    """
    logger = logging.getLogger("vmconvert")
    logger.setLevel(level)

    # format
    formatter = logging.Formatter("%(asctime)s-%(name)s-%(levelname)s-%(funcName)s:%(lineno)d  %(message)s")

    # init console handler and set level
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if filepath:
        fh = logging.FileHandler(filepath)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


logger = init_log(logging.DEBUG)


def diskusage(path_store, unit=None):
    """check disk usage of specify path

    Args:
        path_store(str): absolute path
        uint(str): the return value with unit, default unit is bytes

    Returns:
        free disk(int): capacity of the path

    """

    d = os.statvfs(path_store)
    freeDisk = d.f_bavail * d.f_frsize

    if unit == "KB":
        freeDisk = freeDisk / 1024
    elif unit == "MB":
        freeDisk = freeDisk / (1024 * 1024)
    elif unit == "GB":
        freeDisk = freeDisk / (1024 * 1024 * 1024)

    return freeDisk


def tryencode(field):
    """try parse the field with gbk of csv file

    Args:
        field(str): the field read from csv file

    Returns:
        field(str): field has decode
    """

    try:
        field = field.decode("gbk")
        return field
    except Exception as e:
        return field


def get_size(fname):
    """excute qemu-img info fname for get disk virtual size

    Args:
        fname: name of image has convert

    Returns:
        size_name(str): name of size, like 64MB or 500GB
        size(int): capacity of disk with unit GB
    """
    from sh import qemu_img
    from math import ceil
    # pattern for match size name
    pat_size_name = re.compile("virtual size: (\d+.+)\s\(")
    #  pattern for match size
    pat_size = re.compile("virtual size:.+\((\d+) bytes\)")
    cmd = "qemu-img info %s" % fname
    cmd = cmd.split()[1:]

    try:
        logger.info("excute command: %s" % cmd)
        proc = qemu_img(*cmd, _iter=True)
    except Exception as e:
        logger.critical("Excute command failed: %s " % cmd)
        logger.critical(e)
        return False

    # defind default value of size_name and size
    size_name = None
    size = None

    for line in proc:
        logger.info(line)
        find_size_name = pat_size_name.findall(line)
        find_size = pat_size.findall(line)
        if find_size_name:
            size_name = find_size_name[0]
        if find_size:
            size = find_size[0]
            if size.isdigit():
                mb = 1024 * 1024
                gb = mb * 1024.0
                size = int(size)
                if round(size / gb) == 0:
                    size = 1
                else:
                    size = ceil(size / gb)

    ret = not proc.exit_code
    if not ret:
        logger.critical("get size of vm image failed.")

    return size_name, size


class VmwareVM(object):
    """the class contain info of vm,include vmrelease,exsiip,exsiuser,exsipass,vmname,etc.

    Attributes:
        vmrelease: os distribution like, centos, ubuntum etc.
        exsiip: exsi ip.
        exsiuser: exsi username.
        exsipass: exsi password.
        vmname: name of specify vm.
        down_name: name of vm after download.
        convert_name: name of vm after convert.
    """

    def __init__(self, vmrelease, exsiip, exsiuser, exsipass, vmname):
        self.vmrelease = vmrelease
        self.exsiip = exsiip
        self.exsiuser = exsiuser
        self.exsipass = exsipass
        self.vmname = vmname
        self.down_name = "%s-disk1" % vmname
        self.convert_name = self.down_name + "-sda"

    def writepass(self):
        """write password in file name .esxpasswd
        """

        with open(".esxpasswd", "w") as wf:
            wf.write(self.exsipass)

    def image_download(self):
        """download the vmdk file to local system

        Returns:
            bool: True is success, or False for failed
        """
        from sh import virt_v2v_copy_to_local
        logger.debug("try write exsi password in .esxpasswd")
        self.writepass()
        logger.debug("write exsi password successfully")
        cmd = "virt-v2v-copy-to-local -v -ic esx://%s@%s?no_verify=1 --password-file .esxpasswd %s"
        cmd = cmd % (self.exsiuser, self.exsiip, self.vmname)
        cmd_args = cmd.split()[1:]
        stderrfilename = self.vmname + ".output"

        try:
            logger.debug("excute command: %s" % cmd)
            logger.debug("download vm: %s" % self.vmname)
            proc = virt_v2v_copy_to_local(*cmd_args, _iter=True, _err=stderrfilename)
            logger.info("image download process start.")
        except Exception as e:
            logger.critical("download image failed.")
            logger.critical("excute command faild: %s " % cmd)
            logger.critical(e)
            return False

        msg = "\nimage downloading\nvmdk:%s\nexsi:%s " % (self.vmname, self.exsiip)
        logger.info(msg)
        for line in proc:
            logger.debug(line)
            length = VmwareVM.getLength(stderrfilename)
            if length:
                msg = "VMDK size length: %s " % length
                logger.debug(msg)
                # get capacity of current path
                sysdisk = diskusage("./")

                # what meaning of this ? , clear all content
                with open(stderrfilename, "w") as wf:
                    wf.truncate()

                if length * 1.5 > sysdisk:
                    logger.critical("current capacity of current disk: %s" % sysdisk)
                    logger.critical("have no enough disk space for convert")
                    logger.critical("try to kill the process and delete the vmdk")
                    proc.process.signal(signal.SIGINT)
                    if VmwareVM.remove(self.down_name):
                        logger.warning("remove failed vmdk file success.")
                    else:
                        logger.warning("remove failed vmdk file failed.")

                    return False

        msg = "return code of the command: %s" % proc.exit_code
        logger.debug(msg)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
                logger.info("Download completed")
            open(".vm/" + self.vmname + ".download", "a").close()
        else:
            msg = "Download faild for some reasone, excute the command manually for review: %s " % cmd
            logger.info(msg)

        return ret

    def virt_v2v_convert(self, out="./"):
        """"convert the vm to raw format with virt-v2v

        Args:
            out(str): path for output, default ./

        Returns:
            bool: True is success, or False for failed"""
        from sh import sh
        vm = self.down_name
        cmd = "export LIBGUESTFS_BACKEND=direct; virt-v2v -v -i disk %s -of raw -o local -os %s "
        cmd = cmd % (vm, out)

        try:
            logger.info("excute command: %s" % cmd)
            logger.info("convert vm: %s" % self.vmname)
            proc = sh("-c", cmd, _iter=True)
            logger.info("virt-v2v convert command start.")
        except Exception as e:
            logger.critical("convert image failed.")
            logger.critical("excute command failed: %s " % cmd)
            logger.critical(e)
            return False

        for line in proc:
            logger.debug(line)

        # 0 mean success
        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
            logger.info("convert completed.....")
            open(".vm/" + self.vmname + ".convert", "a").close()
            logger.debug("try remove the original vmdk file")
            # remove orignal vmdk file
            if VmwareVM.remove(vm):
                logger.info("remove orignal vmdk file success.")
            else:
                logger.warning("remove orignal vmdk file failed.")
        return ret

    def qemu_convert(self, out="./"):
        """"convert the vm to raw format with qemu-img

        Args:
            out(str): path for output, default ./

        Returns:
            bool: True is success, or False for failed"""
        from sh import qemu_img
        vm = self.down_name
        cmd = "qemu-img convert -O qcow2 %s %s%s-raw"
        cmd = cmd % (vm, out, self.convert_name)
        cmd_args = cmd.split()[1:]

        try:
            logger.info("excute command: %s" % cmd)
            logger.info("convert vm: %s" % self.vmname)
            proc = qemu_img(*cmd_args, _iter=True)
            logger.info("qemu-img convert command start.")
        except Exception as e:
            logger.critical("convert image failed.")
            logger.critical("excute command failed: %s " % cmd)
            logger.critical(e)
            return False

        for line in proc:
            logger.info(line)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
            logger.info("convert completed.....")
            open(".vm/" + self.vmname + ".convert", "a").close()
            logger.info("Remove the original vmdk file")
            # remove orignal vmdk file
            if VmwareVM.remove(vm):
                logger.info("remove orignal vmdk file success.")
            else:
                logger.warning("remove orignal vmdk file failed.")
        return ret

    def convert(self):
        """convert image

        Returns:
            bool: True is success, or False for failed"""
        if "ubuntu" in self.vmrelease.lower() or "debian" in self.vmrelease.lower():
            return self.qemu_convert()
        else:
            return self.virt_v2v_convert()

    def upload(self):
        """upload converted image to openstack
        Returns:
            bool: True is success, or False for failed"""
        from sh import sh
        size_name, size = get_size(self.convert_name)
        # if not all True
        if not all([size_name, size]):
            return False

        openrc_path = os.path.abspath(os.path.curdir)
        source_cmd = "source " + os.path.join(openrc_path, "openrc")

        # logger.debug("use glancn command to upload image.")
        cmd = source_cmd + ";glance image-create --name %s --min-disk %s --disk-format raw --container-format bare --file %s --progress"
        # pass vmname, min-disk, file path
        cmd = cmd % (self.vmname + "-" + size_name, int(size), self.convert_name)

        try:
            logger.info("excute command: %s" % cmd)
            logger.info("convert vm: %s" % self.vmname)
            proc = sh("-c", cmd, _iter=True)
            logger.info("glance upload command start.")
        except Exception as e:
            logger.critical("upload image failed.")
            logger.critical("excute command failed: %s " % cmd)
            logger.critical(e)
            return False

        for line in proc:
            logger.debug(line)

        ret = not proc.exit_code

        if ret:
            if not os.path.exists(".vm"):
                os.mkdir(".vm")
            logger.info("upload completed.....")
            open(".vm/" + self.vmname + ".upload", "a").close()
            logger.info("Remove the converted image  file")
            # remove orignal vmdk file
            if VmwareVM.remove(self.convert_name):
                logger.warning("remove converted image file success.")
            else:
                logger.warning("remove converted image file failed.")
        return ret

    @staticmethod
    def getLength(fname):
        """get the vm disk size"""
        lengthre = re.compile(r"Content-Length: (\d+)")
        length = None
        with open(fname) as rf:
            retline = rf.read()
            length = lengthre.findall(retline)
            if len(length) > 0:
                length = int(length[0])

        return length

    @staticmethod
    def remove(fname):
        """remove the vm file

        Args:
            fname(str): file name for remove

        Retrun:
            Bool value: if remove success return True, or False
        """
        if path.isfile(fname):
            try:
                os.remove(fname)
                return True
            except Exception as e:
                logger.critical("remove the file: %s error." % fname)
                logger.critical(e)
                return False
        else:
            msg = "not a file: %s" % fname
            logger.critical(msg)
            return False

    @staticmethod
    def checkRecord(vmname, method):
        """check the vm is downloaded or upload or something

        Args:
            vmname(str): the name of vm
            method(str): the method of whole process, like convert,download,upload

        Returns:
            Bool: if exists return True else return False
        """
        fpath = ".vm/" + vmname + "." + method
        ret = os.path.exists(fpath)

        return ret


def download(vm):
    """download vm image

    Args:
        vm(class): the instance of VmwareVM

    Returns:
        Bool: True for success and False for failed
    """
    if vm.checkRecord(vm.vmname, "download"):
        logger.info("downloaded before")
        return True
    return vm.image_download()


def convert(vm):
    """convert vm image

    Args:
        vm(class): the instance of VmwareVM

    Returns:
        Bool: True for success and False for failed
    """
    if vm.checkRecord(vm.vmname, "convert"):
        logger.info("converted before")
        return True
    return vm.convert()


def upload(vm):
    """upload vm image

    Args:
        vm(class): the instance of VmwareVM

    Returns:
        Bool: True for success and False for failed
    """
    if vm.checkRecord(vm.vmname, "upload"):
        logger.info("upload before")
        return True
    return vm.upload()


def init_env():
    """init env variable
        source openrc
        export LIBGUESTFS_BACKEND=direct
    """
    global logger
    openrc_path = os.path.abspath(os.path.curdir)
    ret_code = sp.call("export LIBGUESTFS_BACKEND=direct", shell=True)
    if ret_code:
        logger.critical("run command: export LIBGUESTFS_BACKEND=direct failed")
        sys.exit(1)
    cmd = "source " + os.path.join(openrc_path, "openrc")
    ret_code = sp.call(cmd, shell=True)
    if ret_code:
        logger.critical("run command: source openrc failed")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print("please sepecify csv file after the script.")
        print(usage)
        sys.exit(1)

    vm_list = []
    csvformat = ['vmrelease', 'exsiip', 'exsiuser', 'exsipass', 'vmname']

    with open(csv_file) as rf:
        csv_reader = csv.reader(rf)
        for line in csv_reader:
            vm_list.append(line)

        header = vm_list[0]
        logger.debug("header: %s " % header)
        logger.debug("format: %s " % csvformat)
        if header != csvformat:
            logger.critical("csv format error.")
            sys.exit(1)

    for vm_info in vm_list[1:]:
        vm_info = [tryencode(info) for info in vm_info]
        vm = VmwareVM(*vm_info)
        if download(vm) and convert(vm) and upload(vm):
            logger.info("vm: %s convert successfully." % vm.vmname)
        else:
            logger.info("vm: %s convert failed." % vm.vmname)
            continue


if __name__ == '__main__':
    main()
