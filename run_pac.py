./gfw-pac.py -i gfwlist.txt \
                   -f gfw.pac \
                   -p "Socks 127.0.0.1:6080; DIRECT" \
                   --user-rule=custom-domains.txt \
                   --direct-rule=direct-domains.txt \
                   --localtld-rule=local-tlds.txt \