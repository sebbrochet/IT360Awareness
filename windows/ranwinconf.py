import subprocess
import ConfigParser

config = None

import codecs
codecs.register(lambda name: name == 'cp65001' and codecs.lookup('utf-8') or None)

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

from list_winconf import generate_host_config

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
        print "cvs status for %s has returned 1" % filename
        return

    if "Status: Unknown" in output:
        print "Status unknown for %s" % filename
        output = subprocess.check_call("cvs add %s" % filename)

        print "New file %s" % filename
        modif = file(filename, "r").readlines()
        body = ''.join(modif)
        EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
        EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

        if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
            return

        send_mail(EMAIL_FROM, EMAIL_TO, "New server: %s" % server_name, body)
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

            send_mail(EMAIL_FROM, EMAIL_TO, "Changes detected for: %s" % server_name, body)
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

            print "New file %s" % filename
            modif = file(filename, "r").readlines()
            body = ''.join(modif)
            EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
            EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

            if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
                return

            send_mail(EMAIL_FROM, EMAIL_TO, "New server: %s" % server_name, body)

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

        try:
            send_mail(EMAIL_FROM, EMAIL_TO, "Changes detected for: %s" % server_name, body)
        except Exception, e:
            print "Sending mail has failed, please check value of MTA_SERVER in the configuration file."
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

def thread_work(server_name):
    import pythoncom
    pythoncom.CoInitialize()

    import datetime
    start = datetime.datetime.now()

    user = conf_get_IFP(config, "GENERAL", "USER", "")
    password = conf_get_IFP(config, "GENERAL", "PASSWORD", "")

    record_only_good_config =  conf_get_IFP_boolean(config, "GENERAL", "RECORD_ONLY_GOOD_CONFIG", False)

    generate_host_config(server_name, "%s.txt" % server_name, user, password, record_only_good_config)

    end = datetime.datetime.now()
    duration = end - start

    return "%s, %s, %s, %s" % (server_name, start, end, duration)

def winconf_multi(method, nb_jobs):
    from list_AD import get_all_servers

    pattern = conf_get_IFP(config, "GENERAL", "PATTERN", "operatingSystem='*Server*'")

    print "Retrieving server list from AD based on pattern: %s" % pattern

    server_list = get_all_servers("objectClass='computer' AND %s" % pattern)

    server_name_list = [ computer.cn for computer in server_list]
    #server_name_list = server_name_list[:1]

    print "%d servers were retrieved" % len(server_name_list)

    # Thread avec lib threadtool
    import threadpool
    pool = threadpool.ThreadPool(nb_jobs)

    def thread_callback(request, result):
        print result

    requests = threadpool.makeRequests(thread_work, server_name_list, callback=thread_callback)

    for req in requests:
        pool.putRequest(req)

    pool.wait()

    for server_name in server_name_list:
        manage_vcs_and_notification(server_name, "%s.txt" % server_name)

def do_benchmark(method):
    import datetime

    f = file("benchmark2_%d_servers_method_%d.txt" % (len(SVR_LIST), method), "w")

    for nb_jobs in [15, 18, 20, 23, 25, 30]:
        start = datetime.datetime.now()

        winconf_multi(method, nb_jobs)

        end = datetime.datetime.now()
        duration = end - start

        f.write("NB_JOBS: %d - METHOD: %d - %s\n" % (nb_jobs, method, duration))
        f.flush()

    f.close()

DEFAULT_CONFIGURATION = """
# This is the default configuration file
# Please edit it and update values with your environment
[GENERAL]
# /!\ IMPORTANT /!\
# Update parameters below with your environment
# Then change NO_GO to false to let ranwinconf use configuration file
NO_GO = true

EMAIL_FROM = ranwinconf@yourdomain.com
EMAIL_TO = winadmin@yourdomain.com
MTA_SERVER = youremailserver.com

# Put NB_JOBS=0 for automatic settings
NB_JOBS = 20
METHOD = 2

# Set user and password below if account that execute program has not enough admin rights
#USER = account_name
#PASSWORD = = account_password

# Versionning and Configuration System: CVS or SVN
VCS = CVS

# Pattern to filter computer in the domain
PATTERN = operatingSystem='*Server*'
"""

def create_default_configuration_file(filename):
    f = file(filename, "w")
    f.write(DEFAULT_CONFIGURATION)
    f.close()

def main():
    global config

    import os

    ranwinconf_directory = r"%s/%s" % (os.environ["APPDATA"], "ranwinconf")

    if not os.path.exists(ranwinconf_directory):
        os.makedirs(ranwinconf_directory)

    filename = r"%s/%s" % (ranwinconf_directory, "ranwinconf.ini")

    if not os.path.exists(filename):
        create_default_configuration_file(filename)

    config = ConfigParser.ConfigParser()
    config.read(filename)

    no_go = conf_get_IFP_boolean(config, "GENERAL", "NO_GO", False)

    if no_go:
        print "Please update NO_GO parameter in configuration file: %s" % filename
        return 0

    NB_JOBS = conf_get_IFP_int(config, "GENERAL", "NB_JOBS", 0)

    if NB_JOBS == 0:
        NB_JOBS = 4

    METHOD = conf_get_IFP_int(config, "GENERAL", "METHOD", 2)

    if not METHOD in [2, 3]:
        METHOD = 2

    import datetime
    start = datetime.datetime.now()

    winconf_multi(METHOD, NB_JOBS)

    end = datetime.datetime.now()
    duration = end - start

    print "Duration : %s" % duration

if __name__ == '__main__':
    main()
