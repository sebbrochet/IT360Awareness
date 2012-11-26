import argparse
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

def pretty_print_dict(d, output_list, left):
    for key in d.keys():
        output_list.append("%s%s" % (left * ' ', key))
        pretty_print(d[key], output_list, left+3)

def pretty_print_list(l, output_list, left):
    for item in l:
        pretty_print(item, output_list, left)

def pretty_print(v, output_list, left=0):
    if v.__class__ is dict:
        pretty_print_dict(v, output_list, left)
    elif v.__class__ is list:
        pretty_print_list(v, output_list, left)
    else:
        output_list.append("%s%s" % (left * ' ', v))

def myprint(unicodeobj):
    print unicodeobj.encode('utf-8')

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
    except WindowsError, e:
        print "Please ensure cvs.exe is in your PATH"
        return
    except subprocess.CalledProcessError, e:
        print "cvs status for %s has returned 1" % filename
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
    VCS = conf_get_IFP(config, "GENERAL", "VCS", "CVS").upper()

    if VCS == "CVS":
        manage_cvs_and_notification(server_name, filename)
    elif VCS == "SVN":
        manage_svn_and_notification(server_name, filename)
    else:
        print "VCS %s is not supported" % VCS

DEFAULT_CONFIGURATION = """
# This is the default configuration file
# Please edit it and update values with your environment
[GENERAL]
# /!\ IMPORTANT /!\
# Update parameters below with your environment
# Then change NO_GO to false to let ranwinad use configuration file
NO_GO = true

EMAIL_FROM = ranwinad@yourdomain.com
EMAIL_TO = winadmin@yourdomain.com
MTA_SERVER = youremailserver.com

# Versionning and Configuration System: CVS or SVN
VCS = CVS

RANWINAD_DEBUG = true
CVS_COMMIT_COMMENT = MAJ
"""

def create_default_configuration_file(filename):
    f = file(filename, "w")
    f.write(DEFAULT_CONFIGURATION)
    f.close()

def main():
    global config

    import os

    ranwinad_directory = r"%s/%s" % (os.environ["APPDATA"], "ranwinad")

    if not os.path.exists(ranwinad_directory):
        os.makedirs(ranwinad_directory)

    filename = r"%s/%s" % (ranwinad_directory, "ranwinad.ini")

    if not os.path.exists(filename):
        create_default_configuration_file(filename)

    config = ConfigParser.ConfigParser()
    config.read(filename)

    no_go = conf_get_IFP_boolean(config, "GENERAL", "NO_GO", False)

    if no_go:
        print "Please update NO_GO parameter in configuration file: %s" % filename
        return 0

    from list_AD import generate_all_servers, generate_all_users, generate_all_groups

    generate_all_servers('all_servers.txt')
    manage_vcs_and_notification("SERVERS", 'all_servers.txt')

    generate_all_users('all_users.txt')
    manage_vcs_and_notification("USERS", 'all_users.txt')

    generate_all_groups('all_groups.txt')
    manage_vcs_and_notification("GROUPS", 'all_groups.txt')

if __name__ == '__main__':
    main()
