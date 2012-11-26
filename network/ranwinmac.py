#!/usr/bin/env python

import ctypes
import socket
import struct
import ConfigParser
import subprocess

config = None

def conf_get_IFP_boolean(config, section, option, default):
    if config.has_option(section, option):
        return config.getboolean(section, option)
    else:
        return default

def conf_get_IFP(config, section, option, default):
    if config.has_option(section, option):
        return config.get(section, option)
    else:
        return default

def conf_get_IFP_int(config, section, option, default):
    if config.has_option(section, option):
        return config.getint(section, option)
    else:
        return default

def get_macaddress(host):
    """ Returns the MAC address of a network host, requires >= WIN2K. """

    # Check for api availability
    try:
        SendARP = ctypes.windll.Iphlpapi.SendARP
    except:
        raise NotImplementedError('Usage only on Windows 2000 and above')

    # Doesn't work with loopbacks, but let's try and help.
    if host == '127.0.0.1' or host.lower() == 'localhost':
        host = socket.gethostname()

    # gethostbyname blocks, so use it wisely.
    try:
        inetaddr = ctypes.windll.wsock32.inet_addr(host)
        if inetaddr in (0, -1):
            raise Exception
    except:
        hostip = socket.gethostbyname(host)
        inetaddr = ctypes.windll.wsock32.inet_addr(hostip)

    buffer = ctypes.c_buffer(6)
    addlen = ctypes.c_ulong(ctypes.sizeof(buffer))
    if SendARP(inetaddr, 0, ctypes.byref(buffer), ctypes.byref(addlen)) != 0:
        raise WindowsError('Retreival of mac address(%s) - failed' % host)

    # Convert binary data into a string.
    macaddr = ''
    for intval in struct.unpack('BBBBBB', buffer):
        if intval > 15:
            replacestr = '0x'
        else:
            replacestr = 'x'
        macaddr = ''.join([macaddr, hex(intval).replace(replacestr, '')])

    return macaddr.upper()

def send_mail(who, to, subject, body):
    MTA_SERVER = conf_get_IFP(config, "GENERAL", "MTA_SERVER", "")

    if not MTA_SERVER:
        print "Mail not sent because no MTA_SERVER has been defined."
        return

    import smtplib

    # Import the email modules we'll need
    from email.mime.text import MIMEText
    msg = MIMEText(body)

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = who
    msg['To'] = to

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(MTA_SERVER)
    s.sendmail(who, [to], msg.as_string())
    s.quit()

STDOUT = -2

def manage_cvs_and_notification(server_name, filename):
    try:
        output = subprocess.check_output("cvs status %s" % filename)
    except subprocess.CalledProcessError, e:
        print "%s" % e
        return

    if "Status: Unknown" in output:
        print "Status unknown for %s" % filename
        output = subprocess.check_call("cvs add %s" % filename)
    else:
        try:
            subprocess.check_output("cvs diff -u %s" % filename)
        except subprocess.CalledProcessError, e:
            print "Modifications detected for %s" % filename
            modif = e.output.split('\r\n')[7:]
            body = '\n'.join(modif)
            EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
            EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

            if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
                return

            try:
                send_mail(EMAIL_FROM, EMAIL_TO, "Changes detected for: %s" % server_name, body)
            except Exception, e:
                print "Sending mail has failed, please check value of MTA_SERVER in the configuration file."
        else:
            pass

    print "Commiting %s" % filename
    subprocess.call("cvs commit -M Update %s" % filename)

def manage_svn_and_notification(server_name, filename):
    try:
        output = subprocess.check_output("svn status %s" % filename)
    except WindowsError, e:
        print "Please ensure svn.exe is in your PATH"
        return

    if "? " in output:
        print "Status unknown for %s" % filename
        try:
            output = subprocess.check_call("svn add %s" % filename)
        except subprocess.CalledProcessError, e:
            print "%s" % e
    elif "M " in output:
        output = subprocess.check_output("svn diff %s" % filename)
        print "Modifications detected for %s" % filename
        modif = output.split('\r\n')[4:]
        body = '\n'.join(modif)
        EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
        EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

        if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
            return

        send_mail(EMAIL_FROM, EMAIL_TO, "Changes detected for: %s" % server_name, body)
    else:
        pass

    print "Commiting %s" % filename
    subprocess.call("svn commit -m Update %s" % filename)

def manage_vcs_and_notification(server_name, filename):
    VCS = conf_get_IFP(config, "GENERAL", "VCS", "CVS")

    if VCS == "CVS":
        manage_cvs_and_notification(server_name, filename)
    elif VCS == "SVN":
        manage_svn_and_notification(server_name, filename)
    else:
        print "VCS %s is not supported" % VCS

def generate_ipv4_range(start, end):
    start_list = start.split('.')
    end_list = end.split('.')

    assert(len(start_list) == len(end_list))
    assert(len(start_list) == 4)

    ip_range = []

    is0 = int(start_list[0])
    is1 = int(start_list[1])
    is2 = int(start_list[2])
    is3 = int(start_list[3])

    ie0= int(end_list[0])
    ie1 = int(end_list[1])
    ie2 = int(end_list[2])
    ie3 = int(end_list[3])

    while ((is0 << 24) + (is1 << 16) + (is2 << 8) + is3 <= (ie0 << 24) + (ie1 << 16) + (ie2 << 8) + ie3):
        ip = '%d.%d.%d.%d' % (is0, is1, is2, is3)
        ip_range.append(ip)

        is3 = (is3 + 1) % 256

        if is3 == 0:
            is2 = (is2 + 1) % 256

            if is2 == 0:
                is1 = (is1 + 1) % 256

                if is1 == 0:
                    is0 = (is0 + 1) % 256

    return ip_range

mac_vendor_dict = {}

def load_mac_vendor_list_IFP():
    global mac_vendor_dict

    import os

    filename = "mac_vendor_short_list.txt"

    if os.path.exists(filename):
        f = file(filename, "r")
        lines = f.read().split('\n')
        for line in lines:
            value_list = line.split('=')
            if len(value_list) == 2:
                mac = value_list[0].strip()
                mac_arg_list = mac.split('-')
                mac = "".join(mac_arg_list)
                vendor = value_list[1].strip()
                mac_vendor_dict[mac] = vendor
        f.close

mac_reference_dict = {}

def load_mac_reference_IFP():
    global mac_reference_dict

    import os

    filename =  conf_get_IFP(config, "GENERAL", "WHITELIST", "")
    seperator = conf_get_IFP(config, "GENERAL", "SEPARATOR", ";")

    if os.path.exists(filename):
        f = file(filename, "r")
        lines = f.read().split('\n')
        for line in lines:
            value_list = line.split(seperator)
            if len(value_list) == 2:
                mac = value_list[0].strip()
                reference = value_list[1].strip()
                mac_reference_dict[mac] = reference
        f.close

def thread_work(ip):
    for i in range(3):
        try:
            mac = get_macaddress(ip)

            try:
                hostname = socket.gethostbyaddr(ip)[0]
                vendor = mac_vendor_dict.get(mac[:6], "UNKNOWN")
                hostname = "%s - <%s>" % (hostname, vendor)
            except socket.herror, e:
                vendor = mac_vendor_dict.get(mac[:6], "UNKNOWN")
                hostname = "<%s>" % vendor

            return (mac, hostname, ip)
        except WindowsError, e:
            pass

    return None

def collect_macinfo(start, end):
    import socket

    result = []

    nb_jobs = conf_get_IFP_int(config, "GENERAL", "NB_JOBS", 50)

    ip_range = generate_ipv4_range(start, end)

    # Thread avec lib threadtool
    import threadpool
    pool = threadpool.ThreadPool(nb_jobs)
    macinfo_list = []

    def thread_callback(request, result):
        if result:
            print "%s, %s, %s" % (result[2], result[0], result[1])
            macinfo_list.append(result)

    requests = threadpool.makeRequests(thread_work, ip_range, callback=thread_callback)

    for req in requests:
        pool.putRequest(req)

    pool.wait()

    return macinfo_list

def load_reference_dict_IFP(reference_dict, filename):
    import os

    if os.path.exists(filename):
        f = file(filename, "r")
        lines = f.read().split('\n')
        for line in lines:
            value_list = line.split(',')
            if len(value_list) >= 2:
                mac = value_list[0].strip()
                hostname = ",".join(value_list[1:]).strip()
                reference_dict[mac] = hostname
        f.close

def update_reference_dict(macinfo_list, reference_dict):
    for macinfo in macinfo_list:
        mac = macinfo[0]
        hostname = macinfo[1]

        if not mac in reference_dict:
            reference_dict[mac] = hostname
        elif mac in reference_dict:
            vendor = reference_dict[mac]
            if vendor == "<UNKNOWN>":
                vendor = mac_vendor_dict.get(mac[:6], "UNKNOWN")
                hostname = "<%s>" % vendor
                reference_dict[mac] = hostname

def update_reference_dict_with_whitelist(reference_dict):
    for key in reference_dict.keys():
        if key in mac_reference_dict:
            reference_dict[key] = "[%s]" % mac_reference_dict[key]

def write_reference_dict(reference_dict, filename):
    result_print = []

    for key in reference_dict.iterkeys():
        result_print.append("%s, %s" % (key, reference_dict[key]))

    result_print.sort()

    f = file(filename, "w")
    f.write('\n'.join(result_print))
    f.close()

def update_mac_file(start, end):
    filename = "%s_%s_%s.csv" % ("mac", start.replace('.', '-'), end.replace('.', '-'))

    reference_dict = {}

    load_reference_dict_IFP(reference_dict, filename)

    macinfo_list = collect_macinfo(start, end)

    update_reference_dict(macinfo_list, reference_dict)

    update_reference_dict_with_whitelist(reference_dict)

    write_reference_dict(reference_dict, filename)

    manage_vcs_and_notification("%s-%s" % (start, end), filename)

DEFAULT_CONFIGURATION = """
# This is the default configuration file
# Please edit it and update values with your environment
[GENERAL]
# /!\ IMPORTANT /!\
# Update parameters below with your environment
# Then change NO_GO to false to let ranwinmac use configuration file
NO_GO = true

EMAIL_FROM = ranwinmac@yourdomain.com
EMAIL_TO = winadmin@yourdomain.com
MTA_SERVER = youremailserver.com

# Put NB_JOBS=0 for automatic settings
NB_JOBS = 50

# Versionning and Configuration System: CVS or SVN
VCS = CVS

# Whitelist file - Format is CSV
# ex:
# 001B78A94EF5;MyServer1
# 001B78A94EF6;MyServer2
WHITELIST = reference.csv
SEPARATOR = ;

[IP_RANGE]
# Put here the list of IP v4 ranges to scan for MAC addresses
#NB_RANGE = 2
#RANGE1 = 172.16.0.1, 172.16.1.0
#RANGE2 = 192.168.0.0, 192.168.0.100
#...
"""

def create_default_configuration_file(filename):
    f = file(filename, "w")
    f.write(DEFAULT_CONFIGURATION)
    f.close()

def main():
    global config

    import os

    ranwinmac_directory = r"%s/%s" % (os.environ["APPDATA"], "ranwinmac")

    if not os.path.exists(ranwinmac_directory):
        os.makedirs(ranwinmac_directory)

    filename = r"%s/%s" % (ranwinmac_directory, "ranwinmac.ini")

    if not os.path.exists(filename):
        create_default_configuration_file(filename)

    config = ConfigParser.ConfigParser()
    config.read(filename)

    no_go = conf_get_IFP_boolean(config, "GENERAL", "NO_GO", False)

    if no_go:
        print "Please update NO_GO parameter in configuration file: %s" % filename
        return 0

    load_mac_reference_IFP()
    load_mac_vendor_list_IFP()

    nb_range = conf_get_IFP_int(config, "IP_RANGE", "NB_RANGE", 0)

    if nb_range < 0:
        print "ERROR: NB_RANGE should be > 0"
        return

    ip_range_list = []

    for i in range(nb_range):
        ip_range_index = "RANGE%d" % (i+1)
        ip_range = conf_get_IFP(config, "IP_RANGE", ip_range_index, "")

        if ip_range:
            ip_range_arg_list = ip_range.split(',')
            if len(ip_range_arg_list) != 2:
                print "ERROR: %s is incorrect, please check syntax." % ip_range_index
                return
            start = ip_range_arg_list[0].strip()
            end = ip_range_arg_list[1].strip()

            ip_range_list.append((start, end))

    for ip_range in ip_range_list:
        update_mac_file(ip_range[0], ip_range[1])

if __name__ == '__main__':
    main()
