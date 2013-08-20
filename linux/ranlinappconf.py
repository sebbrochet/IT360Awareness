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

##def _manage_cvs_and_notification(server_name, filename):
##    try:
##        output = check_output(["cvs", "status", "%s" % filename])
##    except subprocess.CalledProcessError, e:
##        print "cvs status for %s has returned 1" % filename
##        return
##
##    if "Status: Unknown" in output:
##        print "Status unknown for %s" % filename
##        output = subprocess.check_call(["cvs", "add", "%s" % filename])
##
##        print "New file %s" % filename
##        modif = file(filename, "r").readlines()
##        body = ''.join(modif)
##        EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
##        EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")
##
##        if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
##            return
##
##        for email_to in EMAIL_TO.split(";"):
##            send_mail(EMAIL_FROM, email_to.strip(), "New server: %s" % server_name, body)
##    else:
##        try:
##            check_output(["cvs", "diff", "-u", "%s" % filename])
##        except subprocess.CalledProcessError, e:
##            print "Modifications detected for %s" % filename
##            modif = e.output.split('\r\n')[:]
##            body = '\n'.join(modif)
##            EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
##            EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")
##
##            if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
##                return
##
##            for email_to in EMAIL_TO.split(";"):
##                send_mail(EMAIL_FROM, email_to.strip(), "Changes detected for: %s" % server_name, body)
##        else:
##            pass
##
##    print "Commiting %s" % filename
##    subprocess.call(["cvs", "commit", "-m", "Update", "%s" % filename])

##def manage_svn_and_notification(server_name, filename):
##    try:
##        output = check_output(["svn", "status", "%s" % filename])
##    except WindowsError, e:
##        print "Please ensure svn.exe is in your PATH"
##        return
##
##    if "? " in output:
##        print "Status unknown for %s" % filename
##        try:
##            output = subprocess.check_call(["svn", "add", "%s" % filename])
##        except subprocess.CalledProcessError, e:
##            print "%s" % e
##    elif "M " in output:
##        output = check_output(["svn", "diff", "%s" % filename])
##        print "Modifications detected for %s" % filename
##        modif = output.split('\r\n')[4:]
##        body = '\n'.join(modif)
##        EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
##        EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")
##
##        if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
##            return
##
##        try:
##            send_mail(EMAIL_FROM, EMAIL_TO, "Changes detected for: %s" % server_name, body)
##        except Exception, e:
##            print "Sending mail has failed, please check value of MTA_SERVER in the configuration file."
##    else:
##        pass
##
##    print "Commiting %s" % filename
##    subprocess.call(["svn", "commit", "-m", "Update", "%s" % filename])

##def manage_vcs_and_notification(server_name, filename):
##    VCS = conf_get_IFP(config, "GENERAL", "VCS", "CVS")
##
##    if VCS == "CVS":
##        manage_cvs_and_notification(server_name, filename)
##    elif VCS == "SVN":
##        manage_svn_and_notification(server_name, filename)
##    else:
##        print "VCS %s is not supported" % VCS

cvs_added_cache = {}

def cvs_add_commit_IFN(short_filename):
    global cvs_added_cache

    added = False
    current_path = ''

    for sub_path in short_filename.split('/'):
        assert(sub_path)

        if not current_path:
            current_path = sub_path
        else:
            current_path = "%s/%s" % (current_path, sub_path)

        #print "Currentpath = %s" % current_path

        if current_path in cvs_added_cache:
            #print "In cache : %s" % current_path
            continue

        try:
            #print "Checking status for %s" % current_path
            output = check_output(["cvs", "-Q", "status", "-l", "%s" % current_path])
            #output = check_output(["cvs", "status", "-l", "%s" % current_path])
        except subprocess.CalledProcessError, e:
            print "cvs status for %s has returned 1" % current_path

            try:
                output = subprocess.check_call(["cvs", "add", "-ko", "%s" % current_path])
                added = True

                print "Commiting %s" % current_path
                subprocess.call(["cvs", "commit", "-m", "Update", "%s" % current_path])

                cvs_added_cache[current_path] = True
            except subprocess.CalledProcessError, e:
                print "Error: %s" % e

            continue

        if "Status: Unknown" in output:
            print "Status unknown for %s" % current_path
            output = subprocess.check_call(["cvs", "add", "-ko", "%s" % current_path])
            added = True

            print "Commiting %s" % current_path
            subprocess.call(["cvs", "commit", "-m", "Update", "%s" % current_path])

        cvs_added_cache[current_path] = True

    return added

def cvs_diff(short_filename):
    modified = False
    change = ""

    try:
        check_output(["cvs", "diff", "-ko", "-u", "%s" % short_filename])
    except subprocess.CalledProcessError, e:
        print "Modifications detected for %s" % short_filename
        modif = e.output.split('\r\n')[:]
        modified = True
        change = '\n'.join(modif)
    else:
        pass

    return modified, change

def create_change(app_name, body):
    local_dir = "@changes"
    mkdir_IFN(local_dir)

    local_change_filename = "%s/%s.txt" % (local_dir, app_name)

    f = file(local_change_filename, 'w')
    f.write(body)
    f.close()

    cvs_add_commit_IFN(local_change_filename)

    modified, change = cvs_diff(local_change_filename)
    if modified:
        subprocess.call(["cvs", "commit", "-m", "Update", "%s" % local_change_filename])

def manage_cvs_and_notification(app_name, file_short_list):
    change_lines_list= []

    for short_filename in file_short_list:
        added = cvs_add_commit_IFN(short_filename)
        if added:
            change = "New file %s" % short_filename
            change_lines_list.append([change])

        modified, change = cvs_diff(short_filename)
        if modified:
            change_lines_list.append([change])

            print "Commiting %s" % short_filename
            subprocess.call(["cvs", "commit", "-m", "Update", "%s" % short_filename])

    if change_lines_list:
        EMAIL_FROM = conf_get_IFP(config, "GENERAL", "EMAIL_FROM", "")
        EMAIL_TO = conf_get_IFP(config, "GENERAL", "EMAIL_TO", "")

        if not '@' in EMAIL_FROM or not '@' in EMAIL_TO:
            return

        index = 1
        body_lines = []

        for change_lines in change_lines_list:
            body_lines.append(80 * '-')
            body_lines.append("Change %d" % index)
            body_lines.append(80 * '-')
            body_lines.extend(change_lines)
            index += 1

        body = '\n'.join(body_lines)

        create_change(app_name, body)

        for email_to in EMAIL_TO.split(";"):
            send_mail(EMAIL_FROM, email_to.strip(), "%d changes detected for: %s" % (len(change_lines_list), app_name), body)

def manage_vcs_and_notification(app_name, file_list, root_cwd):
    file_short_list = []

    start = len(root_cwd)+1

    for filename in file_list:
        file_short_list.append(filename[start:])

    VCS = conf_get_IFP(config, "GENERAL", "VCS", "CVS")

    if VCS == "CVS":
        manage_cvs_and_notification(app_name, file_short_list)
    elif VCS == "SVN":
        manage_svn_and_notification(app_name, file_short_list)
    else:
        print "VCS %s is not supported" % VCS

server_auth = {}

def generate_server_auth(filename):
    global server_auth

    f = file(filename, "r")
    lines = f.read().split('\n')
    for line in lines:
        if line.startswith('#'):
            continue
        value_list = line.split(',')
        server_name = ""
        user = ""
        password = ""
        if len(value_list) >= 1:
            server_name = value_list[0].strip()
        if len(value_list) >= 2:
            user = value_list[1].strip()
        if len(value_list) >= 3:
            password = value_list[2].strip()

	if server_name:
            server_auth[server_name] = (user, password)

    return True

def load_app_list_dict(filename):
    import yaml

    app_list_dict = None

    f = file(filename, "r")
    try:
        app_list_dict = yaml.load(f)
    except Exception, e:
        print "Error while interpreting application list configuration: %s" % filename
        print "Exception: %s" % e

    f.close()

    return app_list_dict

def sftp_walk(sftp, remotepath, pattern):
    from stat import S_ISDIR, S_ISLNK
    import os

    filter = pattern['filter']
    recursive = pattern['recursive']
    folder_type = pattern['folder_type']
    file_type = pattern['file_type']
    dir_filter = pattern['dir_filter']
    minus_dir_filter = pattern['minus_dir_filter']
    minus_filter = pattern['minus_filter']

    path = remotepath
    files = []
    folders = []
    try:
        for f in sftp.listdir_attr(remotepath):
            if not S_ISLNK(f.st_mode):
                if S_ISDIR(f.st_mode) and (folder_type or recursive):
                    short_folder = os.path.basename(f.filename)
                    if file_in_filter(short_folder, dir_filter) and not file_in_filter(short_folder, minus_dir_filter) \
                       and not short_folder.upper() == "CVS":
                        folders.append(f.filename)
                elif not S_ISDIR(f.st_mode) and file_type:
                    short_filename = os.path.basename(f.filename)
                    if file_in_filter(short_filename, filter) and not file_in_filter(short_filename, minus_filter):
                        files.append(f.filename)
        #print (path,folders,files)
        yield path, folders, files

        if recursive:
            for folder in folders:
                new_path = os.path.join(remotepath, folder)
                for x in sftp_walk(sftp, new_path, pattern):
                    yield x

    except IOError, e:
        print "Error while walking %s (%s)" % (remotepath, e)

def file_in_filter(filename, filter):
    # shortcut
    if filter == '*' or filter == '.*?':
        return True
    else:
        import re
        return re.match(filter, filename)

def get_all(ssh, sftp, remotepath, localpath, pattern):
    local_dir = "%s/%s" % (localpath, remotepath)
    mkdir_IFN(local_dir)

    local_file_list = []

    filter = pattern['filter']
    recursive = pattern['recursive']
    folder_type = pattern['folder_type']
    file_type = pattern['file_type']
    dir_filter = pattern['dir_filter']
    minus_dir_filter = pattern['minus_dir_filter']
    minus_filter = pattern['minus_filter']

    import os

    for walker in sftp_walk(sftp, remotepath, pattern):
        if folder_type:
           ls_command = "ls -lA --full-time %s" % walker[0]
           stdin, stdout, stderr = ssh.exec_command(ls_command)
           local_dir = "%s%s" % (localpath, walker[0])
           mkdir_IFN(local_dir)
           local_dirfilename = "%s/%s" % (local_dir, '_DIR_')
           f = file(local_dirfilename, 'w')
           f.write("%s\n" % ls_command)
           for line in stdout:
               if line.startswith('total '):
                   continue
               if line.startswith('-'):
                   filename = line.split(' ')[-1].strip()
                   if file_in_filter(filename, filter) and not file_in_filter(filename, minus_filter):
                       f.write(line)
               elif line.startswith('d'):
                   short_folder = line.split(' ')[-1].strip()
                   if file_in_filter(short_folder, dir_filter) and not file_in_filter(short_folder, minus_dir_filter):
                       f.write(line)
               else:
                   f.write(line)

           f.close()
           local_file_list.append(local_dirfilename)

        for filename in walker[2]:
            local_dir = "%s%s" % (localpath, walker[0])
            mkdir_IFN(local_dir)

            remote_finame = os.path.join(walker[0], filename)
            local_filename = "%s%s" % (localpath, remote_finame)

            try:
                sftp.get(remote_finame, local_filename)
                local_file_list.append(local_filename)
            except IOError, e:
                print "Error while getting %s (%s) " % (remote_finame, e)

    return local_file_list

def refresh_pattern(localpath, server_name, pattern):
    user = password = ""

    if server_name in server_auth:
        user, password = server_auth[server_name]
    else:
        print "No credentials found for server %s" % server_name

    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(server_name, username=user, password=password)
    except Exception, e:
      print "Error on [%s]: %s" % (server_name, e)
      return False

    sftp = ssh.open_sftp()

    remotepath = pattern['dir']

    local_file_list = get_all(ssh, sftp, remotepath, localpath, pattern)

    return local_file_list

def mkdir_IFN(localpath):
    import os

    try:
        os.makedirs(localpath)
    except:
        pass

def mkdir_IFN_chdir(localpath):
    import os

    mkdir_IFN(localpath)

    os.chdir(localpath)

DEFAULT_PATTERN = {
    'dir'           : '',
    'dir_filter'    : ".*?",
    'minus_dir_filter': "$^",

    'filter'        : '.*?',
    'minus_filter'  : '$^',

    'recursive'     : True,
    'folder_type'   : True,
    'file_type'     : True,
}

def appconf_multi(application_pattern):
    import os

    filename = conf_get_IFP(config, "GENERAL", "SERVER_LIST", "")
    filename = os.path.expanduser(filename)

    if not os.path.exists(filename):
        print "server list file not found: %s" % filename
        return

    generate_server_auth(filename)

    filename = conf_get_IFP(config, "GENERAL", "APP_LIST", "")
    filename = os.path.expanduser(filename)

    if not os.path.exists(filename):
        print "application list file not found: %s" % filename
        return

    app_list_dict = load_app_list_dict(filename)

    if not app_list_dict:
        return

    for app_name, server_conf_list in app_list_dict.iteritems():
        if not file_in_filter(app_name, application_pattern):
            continue

        root_cwd = os.getcwd()

        print "Checking application: %s" % app_name
        mkdir_IFN_chdir(app_name)

        app_file_list = []

        for server_conf_dict in server_conf_list:
            for server_name, pattern_list in server_conf_dict.iteritems():
                cwd = os.getcwd()

                print "Checking server: %s" % server_name
                mkdir_IFN_chdir(server_name)

                server_file_list = []

                for pattern in pattern_list:
                    cur_pattern = DEFAULT_PATTERN.copy()

                    if 'dir' in pattern:
                        cur_pattern['dir'] = pattern['dir']
                    if 'dir_filter' in pattern:
                        cur_pattern['dir_filter'] = pattern['dir_filter']
                    if 'minus_dir_filter' in pattern:
                        cur_pattern['minus_dir_filter'] = pattern['minus_dir_filter']

                    if 'filter' in pattern:
                        cur_pattern['filter'] = pattern['filter']
                    if 'minus_filter' in pattern:
                        cur_pattern['minus_filter'] = pattern['minus_filter']

                    if 'recursive' in pattern:
                        cur_pattern['recursive'] = pattern['recursive']
                    if 'file_type' in pattern:
                        cur_pattern['file_type'] = pattern['file_type']
                    if 'folder_type' in pattern:
                        cur_pattern['folder_type'] = pattern['folder_type']

                    dir = cur_pattern['dir']
                    filter = cur_pattern['filter']

                    print "Refreshing pattern for %s/%s" % (dir, filter)

                    pattern_file_list = refresh_pattern(os.getcwd(), server_name, cur_pattern)
                    server_file_list.extend(pattern_file_list)

                app_file_list.extend(server_file_list)
                os.chdir(cwd)

        os.chdir(root_cwd)

        app_file_list_unique = list(set(app_file_list))

        manage_vcs_and_notification(app_name, app_file_list_unique, root_cwd)

DEFAULT_CONFIGURATION = \
"""# This is the default configuration file
# Please edit it and update values with your environment
[GENERAL]
# /!\ IMPORTANT /!\
# Update parameters below with your environment
# Then change NO_GO to false to let ranlinconf use configuration file
NO_GO = true

EMAIL_FROM = ranlinappconf@yourdomain.com
EMAIL_TO = linadmin@yourdomain.com
MTA_SERVER = youremailserver.com

# Versionning and Configuration System: CVS or SVN
VCS = CVS

# Location of the file with the list of servers to analyse
# LINE FORMAT:
# server_name, [login], [password]
SERVER_LIST = ~/.server_list.txt

# Location of the file with the list of applications to monitor
# Format is YAML to describe a mapping between application names and the servers they are composed of
# For each server, the corresponding files are defined
# Sample:
# www.mysite.com:
#    - srv_lin05: ['/etc/httpd/*', '/home/products/*']
# www.anothersite.com:
#    - srv_lin06: ['/etc/httpd/*', '/home/products/*'] # web server 1
#    - srv_lin07: ['/etc/httpd/*', '/home/products/*'] # web server 2
APP_LIST = ~/.app_list.yaml
"""

def create_default_configuration_file(filename):
    f = file(filename, "w")
    f.write(DEFAULT_CONFIGURATION)
    f.close()

def main():
    global config

    import os

    filename = r"%s/%s" % (os.environ["HOME"], ".ranlinappconf")

    if not os.path.exists(filename):
        create_default_configuration_file(filename)

    config = ConfigParser.ConfigParser()
    config.read(filename)

    no_go = conf_get_IFP_boolean(config, "GENERAL", "NO_GO", False)

    if no_go:
        print "Please update NO_GO parameter in configuration file: %s" % filename
        return 0

    application_pattern = '*'

    import sys

    if len(sys.argv) == 2:
        application_pattern = sys.argv[1]
    else:
        print "Usage: %s pattern" % sys.argv[0]
        print "Examples: %s '*' to refresh all applications" % sys.argv[0]
        print "or %s 'www.mysite.com' to refresh only www.mysite.com application" % sys.argv[0]
        print "or %s '^.*\.(com|fr)$' to refresh only .com or .fr applications" % sys.argv[0]
        return

    import datetime
    start = datetime.datetime.now()

    appconf_multi(application_pattern)

    end = datetime.datetime.now()
    duration = end - start

    print "Duration : %s" % duration

if __name__ == '__main__':
    main()
