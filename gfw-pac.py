#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import math
import socket
import struct
import pkgutil
import urllib.parse
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from argparse import ArgumentParser
import base64

gfwlist_url = "https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt"

# from https://github.com/Leask/Flora_Pac


def ip2long(ip):
    packedIP = socket.inet_aton(ip)
    return struct.unpack("!L", packedIP)[0]


# from https://github.com/Leask/Flora_Pac


def fetch_ip_data():
    # fetch data from apnic
    print("Fetching data from apnic.net, it might take a few minutes, please wait...")
    url = r"http://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
    # url=r'http://flora/delegated-apnic-latest' #debug
    data = urllib.request.urlopen(url).read().decode("utf-8")

    cnregex = re.compile(
        r"apnic\|cn\|ipv4\|[0-9\.]+\|[0-9]+\|[0-9]+\|a.*", re.IGNORECASE
    )
    cndata = cnregex.findall(data)

    results = []
    prev_net = ""

    for item in cndata:
        unit_items = item.split("|")
        starting_ip = unit_items[3]
        num_ip = int(unit_items[4])

        imask = 0xFFFFFFFF ^ (num_ip - 1)
        # convert to string
        imask = hex(imask)[2:]
        mask = [0] * 4
        mask[0] = imask[0:2]
        mask[1] = imask[2:4]
        mask[2] = "0"  # imask[4:6]
        mask[3] = "0"  # imask[6:8]

        # convert str to int
        mask = [int(i, 16) for i in mask]
        mask = "%d.%d.%d.%d" % tuple(mask)

        # mask in *nix format
        mask2 = 32 - int(math.log(num_ip, 2))

        ip = starting_ip.split(".")
        ip[2] = "0"
        ip[3] = "0"
        starting_ip = ".".join(ip)
        if starting_ip != prev_net:
            results.append((ip2long(starting_ip), ip2long(mask), mask2))
            prev_net = starting_ip

    results.insert(0, (ip2long("127.0.0.1"), ip2long("255.0.0.0"), 0))
    results.insert(1, (ip2long("10.0.0.0"), ip2long("255.0.0.0"), 0))
    results.insert(2, (ip2long("172.16.0.0"), ip2long("255.240.0.0"), 0))
    results.insert(3, (ip2long("192.168.0.0"), ip2long("255.255.0.0"), 0))

    def ip(item):
        return item[0]

    results = sorted(results, key=ip)
    return results


def decode_gfwlist(content):
    # decode base64 if have to
    try:
        if "." in content:
            raise Exception()
        return base64.b64decode(content).decode("utf-8")
    except:
        return content


def get_hostname(something):
    try:
        # quite enough for GFW
        if not something.startswith("http:"):
            something = "http://" + something
        r = urllib.parse.urlparse(something)
        return r.hostname
    except Exception as e:
        logging.error(e)
        return None


def add_domain_to_set(s, something):
    hostname = get_hostname(something)
    if hostname is not None:
        s.add(hostname)


def combine_lists(content, user_rule=None):
    gfwlist = content.splitlines(False)
    if user_rule:
        gfwlist.extend(user_rule.splitlines(False))
    return gfwlist


def parse_gfwlist(gfwlist):
    domains = set()
    for line in gfwlist:
        if line.find(".*") >= 0:
            continue
        elif line.find("*") >= 0:
            line = line.replace("*", "/")
        if line.startswith("||"):
            line = line.lstrip("||")
        elif line.startswith("|"):
            line = line.lstrip("|")
        elif line.startswith("."):
            line = line.lstrip(".")
        if line.startswith("!"):
            continue
        elif line.startswith("["):
            continue
        elif line.startswith("@"):
            # ignore white list
            continue
        add_domain_to_set(domains, line)
    return domains


def reduce_domains(domains):
    # reduce 'www.google.com' to 'google.com'
    # remove invalid domains
    with open("./tld.txt", "r") as f:
        tld_content = f.read()
    tlds = set(tld_content.splitlines(False))
    new_domains = set()
    for domain in domains:
        domain_parts = domain.split(".")
        last_root_domain = None
        for i in range(0, len(domain_parts)):
            root_domain = ".".join(domain_parts[len(domain_parts) - i - 1 :])
            if i == 0:
                if not tlds.__contains__(root_domain):
                    # root_domain is not a valid tld
                    break
            last_root_domain = root_domain
            if tlds.__contains__(root_domain):
                continue
            else:
                break
        if last_root_domain is not None:
            new_domains.add(last_root_domain)

    uni_domains = set()
    for domain in new_domains:
        domain_parts = domain.split(".")
        for i in range(0, len(domain_parts) - 1):
            root_domain = ".".join(domain_parts[len(domain_parts) - i - 1 :])
            if domains.__contains__(root_domain):
                break
        else:
            uni_domains.add(domain)
    return uni_domains


def generate_pac_fast(domains, direct_domains, cnips, local_tlds):
    # render the pac file
    with open("./pac-template", "r") as f:
        proxy_content = f.read()
    domains_dict = {}
    for domain in domains:
        domains_dict[domain] = 1
    proxy_content = proxy_content.replace(
        "__DOMAINS__", json.dumps(domains_dict, indent=2, sort_keys=True)
    )

    direct_domains_dict = {}
    for domain in direct_domains:
        direct_domains_dict[domain] = 1
    proxy_content = proxy_content.replace(
        "__DIRECT_DOMAINS__", json.dumps(direct_domains_dict, indent=2, sort_keys=True)
    )

    proxy_content = proxy_content.replace(
        "__CN_IPS__", json.dumps(cnips, indent=2, sort_keys=False)
    )

    tlds_dict = {}
    for domain in local_tlds:
        tlds_dict[domain] = 1
    proxy_content = proxy_content.replace(
        "__LOCAL_TLDS__", json.dumps(tlds_dict, indent=2, sort_keys=True)
    )

    return proxy_content


def generate_pac_precise(rules, proxy):
    def grep_rule(rule):
        if rule:
            if rule.startswith("!"):
                return None
            if rule.startswith("["):
                return None
            return rule
        return None

    # render the pac file
    proxy_content = pkgutil.get_data("gfwlist2pac", "./abp.js")
    rules = list(filter(grep_rule, rules))
    proxy_content = proxy_content.replace("__RULES__", json.dumps(rules, indent=2))
    return proxy_content


def main():
    user_rule = None
    direct_rule = None
    localtld_rule = None
    print("Downloading gfwlist from %s" % gfwlist_url)
    content = urllib.request.urlopen(gfwlist_url, timeout=10).read().decode("utf-8")

    userrule_parts = urllib.parse.urlsplit("./custom-domains.txt")
    if not userrule_parts.scheme or not userrule_parts.netloc:
        # It's not an URL, deal it as local file
        with open("./custom-domains.txt", "r") as f:
            user_rule = f.read()
    else:
        # Yeah, it's an URL, try to download it
        print("Downloading user rules file from %s" % "./custom-domains.txt")
        user_rule = (
            urllib.request.urlopen("./custom-domains.txt", timeout=10)
            .read()
            .decode("utf-8")
        )

    directrule_parts = urllib.parse.urlsplit("./direct-domains.txt")
    if not directrule_parts.scheme or not directrule_parts.netloc:
        # It's not an URL, deal it as local file
        with open("./direct-domains.txt", "r") as f:
            direct_rule = f.read()
    direct_rule = direct_rule.splitlines(False)

    tldrule_parts = urllib.parse.urlsplit("./local-tlds.txt")
    if not tldrule_parts.scheme or not tldrule_parts.netloc:
        # It's not an URL, deal it as local file
        with open("./local-tlds.txt", "r") as f:
            localtld_rule = f.read()
    localtld_rule = localtld_rule.splitlines(False)

    cnips = fetch_ip_data()

    content = decode_gfwlist(content)
    gfwlist = combine_lists(content, user_rule)

    domains = parse_gfwlist(gfwlist)
    # domains = reduce_domains(domains)
    pac_content = generate_pac_fast(domains, direct_rule, cnips, localtld_rule)

    with open("./gfw.pac", "w") as f:
        f.write(pac_content)
    print("build OK!")


if __name__ == "__main__":
    main()
