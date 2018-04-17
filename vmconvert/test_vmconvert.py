# coding:utf8
from __future__ import print_function
import csv
import os
import sys
from vmconvert import usage, logger, VmwareVM
from vmconvert import download, convert, upload


def test_download():
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
        logger.debug(header)
        if header != csvformat:
            logger.critical("csv format error.")
            sys.exit(1)

    for vm_info in vm_list[1:2]:
        vm = VmwareVM(*vm_info)
        if download(vm):
            print("download test successfully.")


def test_convert():
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

        header = csv_reader[0]
        logger.debug(header)
        if header != csvformat:
            logger.critical("csv format error.")
            sys.exit(1)

    for vm_info in vm_list[1:2]:
        vm = VmwareVM(*vm_info)
        if convert(vm):
            print("convert test successfully.")


def test_upload():
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

        header = csv_reader[0]
        logger.debug(header)
        if header != csvformat:
            logger.critical("csv format error.")
            sys.exit(1)

    for vm_info in vm_list[1:2]:
        vm = VmwareVM(*vm_info)
        if upload(vm):
            print("upload test successfully.")
