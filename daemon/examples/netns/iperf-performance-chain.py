#!/usr/bin/python

# Copyright (c)2013 the Boeing Company.
# See the LICENSE file included in this distribution.

# This script creates a CORE session, that will connect n nodes together
# in a chain, with static routes between nodes
#    number of nodes / number of hops
#            2            0
#            3            1
#            4            2
#            n          n - 2
#
# Use core-cleanup to clean up after this script as the session is left running.
#

import datetime
import optparse
import sys

from core import constants
from core.misc import ipaddress, nodeutils, nodemaps
from core.netns import nodes

# node list (count from 1)
from core.session import Session

n = [None]


def main():
    usagestr = "usage: %prog [-h] [options] [args]"
    parser = optparse.OptionParser(usage=usagestr)
    parser.set_defaults(numnodes=5)

    parser.add_option("-n", "--numnodes", dest="numnodes", type=int,
                      help="number of nodes")

    def usage(msg=None, err=0):
        sys.stdout.write("\n")
        if msg:
            sys.stdout.write(msg + "\n\n")
        parser.print_help()
        sys.exit(err)

    # parse command line options
    (options, args) = parser.parse_args()

    if options.numnodes < 1:
        usage("invalid number of nodes: %s" % options.numnodes)

    if options.numnodes >= 255:
        usage("invalid number of nodes: %s" % options.numnodes)

    for a in args:
        sys.stderr.write("ignoring command line argument: '%s'\n" % a)

    start = datetime.datetime.now()

    session = Session(1, persistent=True)
    if 'server' in globals():
        server.addsession(session)
    print "creating %d nodes" % options.numnodes
    left = None
    prefix = None
    for i in xrange(1, options.numnodes + 1):
        tmp = session.add_object(cls=nodes.CoreNode, name="n%d" % i, objid=i)
        if left:
            tmp.newnetif(left, ["%s/%s" % (prefix.addr(2), prefix.prefixlen)])

        # limit: i < 255
        prefix = ipaddress.Ipv4Prefix("10.83.%d.0/24" % i)
        right = session.add_object(cls=nodes.PtpNet)
        tmp.newnetif(right, ["%s/%s" % (prefix.addr(1), prefix.prefixlen)])
        tmp.cmd([constants.SYSCTL_BIN, "net.ipv4.icmp_echo_ignore_broadcasts=0"])
        tmp.cmd([constants.SYSCTL_BIN, "net.ipv4.conf.all.forwarding=1"])
        tmp.cmd([constants.SYSCTL_BIN, "net.ipv4.conf.default.rp_filter=0"])
        tmp.setposition(x=100 * i, y=150)
        n.append(tmp)
        left = right

    prefixes = map(lambda (x): ipaddress.Ipv4Prefix("10.83.%d.0/24" % x),
                   xrange(1, options.numnodes + 1))

    # set up static routing in the chain
    for i in xrange(1, options.numnodes + 1):
        for j in xrange(1, options.numnodes + 1):
            if j < i - 1:
                gw = prefixes[i - 2].addr(1)
            elif j > i:
                if i > len(prefixes) - 1:
                    continue
                gw = prefixes[i - 1].addr(2)
            else:
                continue
            net = prefixes[j - 1]
            n[i].cmd([constants.IP_BIN, "route", "add", str(net), "via", str(gw)])

    print "elapsed time: %s" % (datetime.datetime.now() - start)


if __name__ == "__main__" or __name__ == "__builtin__":
    # configure nodes to use
    node_map = nodemaps.NODES
    nodeutils.set_node_map(node_map)

    main()
