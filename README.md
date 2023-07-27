# gfw-pac

科学上网。通过 gfwlist 和中国 IP 地址生成 PAC(Proxy auto-config) 文件。对存在于 gfwlist 的域名和解析出的 IP 在国外的域名使用代理。

## 特性
* 速度快，优先按域名匹配，再按解析后的 IP 匹配
* 可自定义需要代理的域名
* 可自定义本地开发 TLD 域名，例如 .test
* 可自定义不需要代理的域名
* 如果访问的域名不在列表里，但是 IP 在国外，也返回代理服务器
* 从 apnic 下载的 IP 分配文件
* gfwlist 从 <https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt> 下载

## 用法
    custom-domains.txt 自定义使用代理的域名文件，文件里每行一个域名
    direct-domains.txt 自定义不使用代理的域名文件，文件里每行一个域名
    local-tlds.txt 自定义不使用代理的顶级域，文件里每行一个域名，必须带前导圆点（例如 .test）
