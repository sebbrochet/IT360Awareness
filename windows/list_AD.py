import active_directory
import argparse

def group_cmp(x, y):
    if x.cn < y.cn:
        return -1
    else:
        return 1

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

def generate_all_groups(target):
    sorted_group_list=[]

    for group in active_directory.search (objectClass='group'):
        sorted_group_list.append(group)

    sorted_group_list.sort(group_cmp)

    display_list = []

    for group in sorted_group_list:
      group_content = []
      try:
          sorted_group_content = []
          for member in group.member:
            sorted_group_content.append(member)
          sorted_group_content.sort(user_sort)

          for member in sorted_group_content:
            group_content.append("%s (%s / %s)" % (member.sAMAccountName, member.cn, member.mail))
      except Exception, e:
            pass
      display_list.append({ group.cn : group_content })

    output_list = []

    pretty_print(display_list, output_list)

    if target != "STDOUT":
        f = file(target, "w")
        f.write('\n'.join(output_list).encode('utf-8'))
        f.close()
    else:
        myprint('\n'.join(output_list))

def user_sort(x, y):
    if x.sAMAccountName < y.sAMAccountName:
        return -1
    elif x.sAMAccountName > y.sAMAccountName:
        return 1
    else:
        return 0

def generate_all_users(target):
    sorted_user_list = []
    for user in active_directory.search ("objectCategory='Person'", "objectClass='User'"):
        sorted_user_list.append(user)

    sorted_user_list.sort(user_sort)

    display_list = []
    for user in sorted_user_list:
        display_list.append("%s (%s / %s)" % (user.sAMAccountName, user.cn, user.mail))

    output_list = []

    pretty_print(display_list, output_list)

    if target != "STDOUT":
        f = file(target, "w")
        f.write('\n'.join(output_list).encode('utf-8'))
        f.close()
    else:
        myprint('\n'.join(output_list))

def computer_sort(x, y):
    if x.cn.lower() < y.cn.lower():
        return -1
    elif x.cn.lower() > y.cn.lower():
        return 1
    else:
        return 0

NB_DAYS = 3 * 31

def get_all_servers(pattern, nb_days_ago_when_changed_max = NB_DAYS):
    import datetime
    now = datetime.datetime.now()

    sorted_computer_list = []
    for computer in active_directory.search (pattern):
        when_changed = datetime.datetime(computer.whenChanged.year,
                                         computer.whenChanged.month,
                                         computer.whenChanged.day,
                                         computer.whenChanged.hour,
                                         computer.whenChanged.minute)

        if now - when_changed < datetime.timedelta(nb_days_ago_when_changed_max):
            sorted_computer_list.append(computer)

    sorted_computer_list.sort(computer_sort)

    return sorted_computer_list

def generate_all_servers(target):
    display_list = []

    sorted_computer_list = get_all_servers("objectClass='computer' AND operatingSystem='*Server*'")

    for computer in sorted_computer_list:
        display_list.append(computer.cn)
        #, computer.whenChanged))

    output_list = []

    pretty_print(display_list, output_list)

    if target != "STDOUT":
        f = file(target, "w")
        f.write('\n'.join(output_list).encode('utf-8'))
        f.close()
    else:
        myprint('\n'.join(output_list))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('param', type=str)
    parser.add_argument('output', type=str)
    args = parser.parse_args()

    param = args.param
    target = args.output

    if param == 'GROUPS':
        generate_all_groups(target)
    elif param == 'USERS':
        generate_all_users(target)
    elif param == 'SERVERS':
        generate_all_servers(target)
    else:
        print "param = 'GROUPS' | 'USERS' | 'SERVERS'"

if __name__ == '__main__':
    main()