#!/usr/bin/env python

class SortedDict(object):
    def __init__(self, d):
        self.d = d

class FakedList(object):
    def __init__(self, l):
        self.l= l

def GetSystemName(server, props):
    name = "<UNKNOWN>"

    hosts = server.get_hosts()

    if hosts:
        _, name = hosts.items()[0]

    return name

def GetModel(server, props):
    return props.hardware.systemInfo.model

def GetOsType(server, props):
    result = []

    result.append(["Name", [props.config.product.name]])
    result.append(["Version", [props.config.product.apiVersion]])
    result.append(["Build", [props.config.product.build]])

    return result

def GetCPU(server, props):
    result = {}

    for cpuPkg in props.hardware.cpuPkg:
        result["CPU%d" % cpuPkg.index] = cpuPkg.description

    result["Total nb cores"] = props.hardware.cpuInfo.numCpuCores

    return result

def GetRAM(server, props):
    return props.hardware.memorySize

def GetInterfaces(server, props):
    result = {}

    pnic_result = []
    pnic_key_to_name = {}

    for pnic in props.config.network.pnic:
        pnic_key_to_name[pnic.key] = pnic.device
        speed = "down"
        if hasattr(pnic, "linkSpeed"):
            if pnic.linkSpeed.duplex:
                duplex = "full-duplex"
            else:
                duplex = "half-duplex"

            speed = "%s %s" % (pnic.linkSpeed.speedMb, duplex)

        pnic_result.append("%s - %s - %s" % (pnic.device, speed, pnic.mac))

    pnic_result.sort()

    portgroup_result = []
    portgroup_key_to_name = {}

    for portgroup in props.config.network.portgroup:
        portgroup_key_to_name[portgroup.key] = portgroup.spec.name
        portgroup_result.append("%s - %s - VLAN %s" % (portgroup.spec.name, portgroup.spec.vswitchName, portgroup.spec.vlanId))

    portgroup_result.sort()

    vnic_result = []

    for vnic in props.config.network.vnic:
        vnic_result.append("%s - %s - %s - %s" % (vnic.device, vnic.spec.ip.ipAddress, vnic.spec.mac, vnic.portgroup))

    vnic_result.sort()

    vswitch_dict = {}

    for vswitch in props.config.network.vswitch:
        portgroup_list = []
        for portgroup in vswitch.portgroup:
            portgroup_list.append(portgroup_key_to_name.get(portgroup, "%s not found" % portgroup))
        portgroup_list.sort()
        pnic_list = []
        if hasattr(vswitch, "pnic"):
            for pnic in vswitch.pnic:
                pnic_list.append(pnic_key_to_name.get(pnic, "%s not found" % pnic))
            pnic_list.sort()
        vswitch_dict[vswitch.name] = { "NIC(%d)" % len(pnic_list) : pnic_list, "Portgroup (%d)" % len(portgroup_list) : portgroup_list }

    #props.config.network.dnsConfig.hostName

    return [
        ["NIC (%d)" % len(pnic_result),  pnic_result],
        ["VNIC (%d)" % len(vnic_result), vnic_result],
        ["Portgroup (%d)" % len(portgroup_result), portgroup_result],
        ["VSWITCH (%d)" % len(vswitch_dict), [SortedDict(vswitch_dict)]],
    ]

def GetDatastores(server, props):
    result = []

    for datastore in server.get_datastores().items():
        result.append("%s (%s)" % (datastore[1], datastore[0]))

    result.sort()

    return result

def GetHosts(server):
    result = []

    for host in server.get_hosts().items():
        result.append(host[1])

    result.sort()

    return result

def GetClusters(server):
    result = []

    for cluster in server.get_clusters().items():
        result.append(cluster[1])

    result.sort()

    return result

def GetDatacenters(server):
    result = []

    for datacenter in server.get_datacenters().items():
        result.append(datacenter[1])

    result.sort()

    return result

def GetVM(server):
    result = server.get_registered_vms()
    result.sort()
    return result

def GetResourcePools(server):
    result = []

    for resource_pool in server.get_resource_pools().items():
        result.append("%s (%s)" % (resource_pool[1], resource_pool[0]))

    result.sort()

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
    from pysphere import VIServer
    server = VIServer()

    try:
        server.connect(host, user, password)
    except Exception, e:
        print "Error while connecting to %s:" % host
        print "%s" % e
        return None, False

    server_type = server.get_server_type()

    result = {}

    if server_type == 'VMware vCenter Server':
        result["Hosts"] = GetHosts(server)
        result["Clusters"] = GetClusters(server)
        result["Datacenters"] = GetDatacenters(server)
        result["Datastores"] = GetDatastores(server, None)
        result["VM"] = GetVM(server)
        result["Resource Pools"] = GetResourcePools(server)
    else:
        hosts = server.get_hosts()

        if hosts:
            id, _ = hosts.items()[0]
            from pysphere import VIProperty
            props = VIProperty(server, id)

        result["Name"] = GetSystemName(server, props)
        result["OS"] = GetOsType(server, props)
        result["CPU"] = GetCPU(server, props)
        result["RAM"] = GetRAM(server, props)
        result["MODEL"] = GetModel(server, props)
        result["Interfaces"] = GetInterfaces(server, props)
        result["Datastores"] = GetDatastores(server, props)

    return server_type, result

def generate_host_config(host, target, user="", password="", RecordOnlyGoodConfig=False):
    server_type, host_config = GetHostConfig(host, user, password)

    output_list = []

    if host_config:
        if server_type == 'VMware vCenter Server':
            display_list = [
                { "Hosts" : host_config["Hosts"] },
                { "Clusters" : host_config["Clusters"] },
                { "Datacenters" : host_config["Datacenters"] },
                { "Datastores" : host_config["Datastores"] },
                { "VM" : host_config["VM"] },
                { "Resource Pools" : host_config["Resource Pools"] },
            ]
        else:
            display_list = [
                { "Name" : host_config["Name"] },
                { "Model" : host_config["MODEL"] },
                { "OS" : FakedList(host_config["OS"]) },
                { "CPU" : SortedDict(host_config["CPU"]) },
                { "RAM" : host_config["RAM"] },
                { "Interfaces" : host_config["Interfaces"] },
                { "Datastores" : host_config["Datastores"] },
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

    user = ""
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
