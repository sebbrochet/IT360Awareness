#!/usr/bin/env python

import subprocess
import ConfigParser

def check_output(*popenargs, **kwargs):
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        error = subprocess.CalledProcessError(retcode, cmd)
        error.output = output
        raise error
    return output

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
        output = check_output(["cvs", "status", "%s" % filename])
    except subprocess.CalledProcessError, e:
        print "cvs status for %s has returned 1" % filename
        return

    if "Status: Unknown" in output:
        print "Status unknown for %s" % filename
        output = subprocess.check_call(["cvs", "add", "%s" % filename])
    else:
        try:
            check_output(["cvs", "diff", "-u", "%s" % filename])
        except subprocess.CalledProcessError, e:
            print "Modifications detected for %s" % filename
            modif = e.output.split('\r\n')[:]
            body = '\n'.join(modif)
            EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
            EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

            if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
                return

            for email_to in EMAIL_TO.split(";"):
                send_mail(EMAIL_FROM, email_to.strip(), "Changes detected for: %s" % server_name, body)
        else:
            pass

    print "Commiting %s" % filename
    subprocess.call(["cvs", "commit", "-m", "Update", "%s" % filename])

def manage_svn_and_notification(server_name, filename):
    try:
        output = check_output(["svn", "status", "%s" % filename])
    except WindowsError, e:
        print "Please ensure svn.exe is in your PATH"
        return

    if "? " in output:
        print "Status unknown for %s" % filename
        try:
            output = subprocess.check_call(["svn", "add", "%s" % filename])
        except subprocess.CalledProcessError, e:
            print "%s" % e
    elif "M " in output:
        output = check_output(["svn", "diff", "%s" % filename])
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
    subprocess.call(["svn", "commit", "-m", "Update", "%s" % filename])

def manage_vcs_and_notification(server_name, filename):
    VCS = conf_get_IFP(config, "GENERAL", "VCS", "CVS")

    if VCS == "CVS":
        manage_cvs_and_notification(server_name, filename)
    elif VCS == "SVN":
        manage_svn_and_notification(server_name, filename)
    else:
        print "VCS %s is not supported" % VCS

def linconf_multi():
    import os

    filename = conf_get_IFP(config, "GENERAL", "SERVER_LIST", "")
    filename = os.path.expanduser(filename)

    if not os.path.exists(filename):
        print "server list file not found: %s" % filename
        return

    server_list = []

    f = file(filename, "r")
    lines = f.read().split('\n')
    for line in lines:
        value_list = line.split(',')
        server_name = ""
        login = ""
        password = ""
        if len(value_list) >= 1:
            server_name = value_list[0].strip()
        if len(value_list) >= 2:
            login = value_list[1].strip()
        if len(value_list) >= 3:
            password = value_list[2].strip()

	if server_name:
            server_list.append((server_name, login, password))

    print "%d servers were retrieved" % len(server_list)

    from list_linconf import generate_host_config

    record_only_good_config =  conf_get_IFP_boolean(config, "GENERAL", "RECORD_ONLY_GOOD_CONFIG", False)

    for value in server_list:
        server_name, login, password = value
        target = "%s.txt" % server_name
        result = generate_host_config(server_name, target, login, password, record_only_good_config)
        if result:
            manage_vcs_and_notification(server_name, target)

DEFAULT_CONFIGURATION = \
"""# This is the default configuration file
# Please edit it and update values with your environment
[GENERAL]
# /!\ IMPORTANT /!\
# Update parameters below with your environment
# Then change NO_GO to false to let ranlinconf use configuration file
NO_GO = true

EMAIL_FROM = ranlinconf@yourdomain.com
EMAIL_TO = linadmin@yourdomain.com
MTA_SERVER = youremailserver.com

# Versionning and Configuration System: CVS or SVN
VCS = CVS

# Location of the file with the list of servers to analyse
# LINE FORMAT:
# server_name, [login], [password]
SERVER_LIST = ~/.server_list.txt
"""

def create_default_configuration_file(filename):
    f = file(filename, "w")
    f.write(DEFAULT_CONFIGURATION)
    f.close()

def main():
    global config

    import os

    filename = r"%s/%s" % (os.environ["HOME"], ".ranlinconf")

    if not os.path.exists(filename):
        create_default_configuration_file(filename)

    config = ConfigParser.ConfigParser()
    config.read(filename)

    no_go = conf_get_IFP_boolean(config, "GENERAL", "NO_GO", False)

    if no_go:
        print "Please update NO_GO parameter in configuration file: %s" % filename
        return 0

    import datetime
    start = datetime.datetime.now()

    linconf_multi()

    end = datetime.datetime.now()
    duration = end - start

    print "Duration : %s" % duration

if __name__ == '__main__':
    main()
