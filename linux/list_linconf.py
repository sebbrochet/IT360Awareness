#!/usr/bin/env python

import re

class SortedDict(object):
    def __init__(self, d):
        self.d = d

class FakedList(object):
    def __init__(self, l):
        self.l= l

def GetSystemName(ssh):
    stdin, stdout, stderr = ssh.exec_command("hostname")

    result = "<UNKNOWN>"

    for line in stdout:
        result = line.strip()
        break

    return result

def GetOsType(ssh):
    result = []

    stdin, stdout, stderr = ssh.exec_command("cat /etc/issue")

    value = "<UNKNOWN>"

    for line in stdout:
        value = line.strip()
        break

    result.append(["Name", [value]])

    stdin, stdout, stderr = ssh.exec_command("cat /etc/debian_version")

    value = "<UNKNOWN>"

    for line in stdout:
        value = line.strip()
        break

    result.append(["Version", [value]])

    stdin, stdout, stderr = ssh.exec_command("uname -mrs")

    value = "<UNKNOWN>"

    for line in stdout:
        value = line.strip()
        break

    result.append(["Kernel", [value]])

    return result


def GetCPU(ssh):
    stdin, stdout, stderr = ssh.exec_command("cat /proc/cpuinfo")

    CPU_dict = {}
    result = {}
    nb_cpu = 0

    current_cpu = "NO_CPU"

    for line in stdout:
        try:
            key, value = re.split(":", line)
        except Exception, e:
            continue

        key = key.strip()
        value = value.strip()

        if key == "processor":
            current_cpu = "CPU%d" % int(value)
            nb_cpu += 1

        elif key == "vendor_id":
            result['%s_id' % current_cpu] = value
        elif key == "model name":
            result['%s_name' % current_cpu] = value
        elif key == "cpu family":
            result['%s_family' % current_cpu] = value
        elif key == "model":
            result['%s_model' % current_cpu] = value
        elif key == "stepping":
            result['%s_stepping' % current_cpu] = value
        elif key == "cpu MHz":
            result['%s_mhz' % current_cpu] = value
        elif key == "cache size":
            result['%s_cache' % current_cpu] = re.split(" ", value)[0]

    for cpu in range(nb_cpu):
        cpu_key = "CPU%d" % cpu
        CPU_dict[cpu_key] = [
            result["%s_name" % cpu_key],
            "%s Family %s Model %s Stepping %s @ %s MHz" % (result["%s_id" % cpu_key],
                                                            result["%s_family" % cpu_key],
                                                            result["%s_model" % cpu_key],
                                                            result["%s_stepping" % cpu_key],
                                                            result["%s_mhz" % cpu_key])
    ]

    return CPU_dict

def GetRAM(ssh):
    stdin, stdout, stderr = ssh.exec_command("cat /proc/meminfo")

    result = 0

    for line in stdout:
        try:
            key, value = re.split(":", line)
        except Exception, e:
            continue

        key = key.strip()
        value = value.strip()

        if key == "MemTotal":
            result = int(re.split(" ", value)[0])
            break

    return result

def GetInterfaces(ssh):
    stdin, stdout, stderr = ssh.exec_command("ifconfig")

    result = {}

    interface_line = True
    interface_name = "<UNKNOWN>"

    for line in stdout:
        line = line.strip()
        if interface_line:
            value_list = re.split("[' ']*", line)
            interface_name = value_list[0]
            right = " ".join(value_list[1:])

            result[interface_name] = []

            result[interface_name].append(right.strip())

            interface_line = False
        elif line:
            result[interface_name].append(line.strip())
        else:
            interface_line = True

    for key in result.keys():
        result[key] = result[key][:3]

    return result

def GetMounts(ssh):
    stdin, stdout, stderr = ssh.exec_command("mount")

    result = []

    for line in stdout:
        if line:
            result.append(line.strip())

    result.sort()

    return result

def GetLogicalDiskList(ssh):
    stdin, stdout, stderr = ssh.exec_command("cat /proc/partitions")

    result = []

    for line in stdout:
        line = line.strip()
        if line:
           value_list = re.split("[\t' ']*", line)

           filesystem = value_list[3].strip()

           if filesystem != "name":
              size = value_list[2].strip()
              result.append("%s - %s" % (filesystem, size))

    result.sort()

    return result

def GetInstalledProgs(ssh):
    stdin, stdout, stderr = ssh.exec_command("dpkg --list")

    result = {}

    applications_found = False

    for line in stdout:
        if line.startswith("ii"):
            applications_found = True

            value_list = re.split("[' ']*", line)

            name = value_list[1]
            version = value_list[2]

            #description = "".join(value_list[3:])

            result[name] = version

    if not applications_found:
        stdin, stdout, stderr = ssh.exec_command("rpm -qa")

    for line in stdout:
        result[line.strip()] = "n/a"

    return result

def GetLocale(ssh):
    stdin, stdout, stderr = ssh.exec_command("locale")

    result = {}

    for line in stdout:
        line = line.strip()

        if line:
           value_list = re.split("=", line)

           if value_list:
                key = value_list[0].strip()
                value = ''

                if len(value_list) > 1:
                    value = ''.join(value_list[1:])

                result[key] = value

    return result

def pretty_print_dict(d, output_list, left, sort = False):
    if sort:
        for key in iter(sorted(d.keys())):
            output_list.append("%s%s" % (left * ' ', key))
            pretty_print(d[key], output_list, left+3)
    else:
        for key in d.keys():
            output_list.append("%s%s" % (left * ' ', key))
            pretty_print(d[key], output_list, left+3)

def pretty_print_list(l, output_list, left):
    for item in l:
        if item.__class__ is list:
            pretty_print(item, output_list, left+3)
        else:
            pretty_print(item, output_list, left)

def pretty_print(v, output_list, left=0):
    if v.__class__ is SortedDict:
        pretty_print_dict(v.d, output_list, left, sort = True)
    elif v.__class__ is dict:
        pretty_print_dict(v, output_list, left)
    elif v.__class__ is FakedList:
        pretty_print_list(v.l, output_list, left-3)
    elif v.__class__ is list:
        pretty_print_list(v, output_list, left)
    else:
        output_list.append("%s%s" % (left * ' ', v))

def myprint(unicodeobj):
    #print unicodeobj.encode('utf-8')
    print unicodeobj

def GetHostConfig(host, user, password):
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(host, username=user, password=password)
    except Exception, e:
      print "Error: %s" % e
      return False

    result = {}

    result["Name"] = GetSystemName(ssh)
    result["OS"] = GetOsType(ssh)
    result["CPU"] = GetCPU(ssh)
    result["RAM"] = GetRAM(ssh)
    result["Interfaces"] = GetInterfaces(ssh)
    result["Disks"] = GetLogicalDiskList(ssh)
    result["Mounts"] = GetMounts(ssh)
    result["Locale"] = GetLocale(ssh)
    result["Applications"] = GetInstalledProgs(ssh)

    return result

def generate_host_config(host, target, user="", password="", RecordOnlyGoodConfig=False):
    host_config = GetHostConfig(host, user, password)

    output_list = []

    if host_config:
        display_list = [
            { "Name" : host_config["Name"] },
            { "OS" : FakedList(host_config["OS"]) },
            { "CPU" : host_config["CPU"] },
            { "RAM" : host_config["RAM"] },
            { "Interfaces" : SortedDict(host_config["Interfaces"]) },
            { "Disks" : host_config["Disks"] },
            { "Mounts" : host_config["Mounts"] },
            { "Locale" : SortedDict(host_config["Locale"]) },
            { "Applications" : SortedDict(host_config["Applications"]) },
        ]

        pretty_print(display_list, output_list)
    else:
        output_list.append("Error: check if:")
        output_list.append("host %s answers ping" % host)
        output_list.append("Used account has enough (admin) rights")

    if target != "<stdout>":
        if host_config or not RecordOnlyGoodConfig:
            f = file(target, "w")
            #f.write('\n'.join(output_list).encode('utf-8'))
            f.write('\n'.join(output_list))
            f.close()
    else:
        myprint('\n'.join(output_list))

    return host_config or not RecordOnlyGoodConfig

def main():
    import sys

    user = "root"
    password = ""

    if len(sys.argv) == 2:
        host = sys.argv[1]
    elif len(sys.argv) == 3:
        host = sys.argv[1]
        user = sys.argv[2]
    elif len(sys.argv) == 4:
        host = sys.argv[1]
        user = sys.argv[2]
        password = sys.argv[3]
    else:
        print "Usage: %s host [user] [pass]" % sys.argv[0]
        return

    target = "<stdout>"

    generate_host_config(host, target, user, password)

if __name__ == '__main__':
    main()
