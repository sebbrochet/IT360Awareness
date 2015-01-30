IT360Awareness
==============

Set of tools to detect/track changes on your IT infrastructure (Windows, linux, VMWare ESX, Active Directory, ...)

Tools are classed by OS/Category:

linux
* [ranlinconf](https://github.com/sebbrochet/ranlinconf): Track changes of the configuration of your linux servers
* [ranlinappconf](https://github.com/sebbrochet/ranlinappconf): Track changes of the files of your linux servers

network
* ranwinmac: Collect MAC addresses in your network for audit and filtering purposes

vmware:
* ranesxconf: Track changes of the configuration of your VMWare host servers (ESX and vCenter)

windows:
* [ranwinconf](https://github.com/sebbrochet/ranwinconf): Track changes of the configuration of your windows servers
* ranwinad: Track changes (groups, users, computers) in your Active Directory

misc:
* [ranlincmd](https://github.com/sebbrochet/ranlincmd) : Generic tool to track changes based on command output for your linux servers

list_* scripts, when available, are used by corresponding ran* scripts
They can also be used directly to display data on standard output.
Type name of script with no options in a shell to get help

