"""Use an already-enabled local Windows HTTP proxy without changing settings.

Only HTTP CONNECT to an explicit loopback proxy is auto-detected. Pool login
data is sent later, inside independently verified end-to-end pool TLS.
"""
import ipaddress
import socket
import sys
import time
from urllib.parse import urlsplit

def parse_local_proxy(value):
    if not isinstance(value,str) or len(value)>2048 or any(c in value for c in '\r\n'):
        return None
    if '=' in value:
        mappings=dict(part.strip().split('=',1) for part in value.split(';') if '=' in part)
        value=mappings.get('https',mappings.get('http',''))
    try:
        parsed=urlsplit(value.strip() if '://' in value else 'http://'+value.strip())
        if parsed.scheme!='http' or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
            return None
        host=parsed.hostname
        if host=='localhost':host='127.0.0.1'
        if not host or not ipaddress.ip_address(host).is_loopback:return None
        port=parsed.port
        if not port or not 1<=port<=65535:return None
        return host,port
    except (ValueError,TypeError):return None

def get_system_proxy():
    if sys.platform!='win32':return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
            enabled=winreg.QueryValueEx(key,'ProxyEnable')[0]
            if enabled!=1:return None
            return parse_local_proxy(winreg.QueryValueEx(key,'ProxyServer')[0])
    except OSError:return None

def open_connect_tunnel(proxy,host,port,timeout):
    if not host or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in host):
        raise ValueError('Invalid pool hostname for CONNECT')
    if not 1<=int(port)<=65535:raise ValueError('Invalid pool port')
    deadline=time.monotonic()+timeout
    raw=socket.create_connection(proxy,timeout=timeout)
    try:
        authority=f'{host}:{port}'
        raw.sendall(f'CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n\r\n'.encode('ascii'))
        header=bytearray()
        while not header.endswith(b'\r\n\r\n'):
            if len(header)>=8192:raise ConnectionError('Local proxy response header too large')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Local proxy CONNECT timed out')
            raw.settimeout(remaining)
            byte=raw.recv(1)
            if not byte:raise ConnectionError('Local proxy closed during CONNECT')
            header.extend(byte)
        status=bytes(header).split(b'\r\n',1)[0].split()
        if len(status)<2 or status[0] not in (b'HTTP/1.0',b'HTTP/1.1'):
            raise ConnectionError('Invalid local proxy CONNECT response')
        if status[1] in (b'403',b'407'):
            raise PermissionError('Local proxy denied CONNECT or requires authentication')
        if status[1]!=b'200':raise ConnectionError('Local proxy CONNECT failed: '+status[1].decode('ascii',errors='replace'))
        return raw
    except BaseException:
        raw.close()
        raise
