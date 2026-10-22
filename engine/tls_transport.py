"""Pool-specific verified TLS; no system trust changes or plaintext fallback.

Known pools use explicitly pinned self-signed certificates as their own trust
anchors. OpenSSL still checks the signature and validity dates. The exact leaf
SHA-256 must also match. Unknown hosts use normal CA and hostname validation.
Initial pin provenance is recorded in TLS-TRUST-POLICY.md; no runtime enrollment.
"""
import hashlib
import hmac
import socket
import ssl
import time
import selectors
import errno
import threading
from system_proxy import get_system_proxy,open_connect_tunnel

_dns_lock=threading.Lock()
_dns_pending={}

def _resolve_addresses(host,deadline):
    # Bound callers' DNS wait; share an outstanding lookup instead of creating
    # an unbounded number of abandoned resolver threads on repeated starts.
    with _dns_lock:
        record=_dns_pending.get(host)
        if record is None:
            if len(_dns_pending)>=16:
                raise OSError('DNS resolver busy; retry later')
            record={'done':threading.Event()}
            _dns_pending[host]=record
            def resolve():
                try:record['addresses']=socket.getaddrinfo(host,0,type=socket.SOCK_STREAM)
                except OSError as exc:record['error']=exc
                finally:
                    record['done'].set()
                    with _dns_lock:_dns_pending.pop(host,None)
            threading.Thread(target=resolve,daemon=True).start()
    if not record['done'].wait(max(0,min(3,deadline-time.monotonic()))):
        raise TimeoutError('DNS lookup timed out')
    if 'error' in record:raise record['error']
    addresses=[]
    for family,kind,proto,_,address in record['addresses']:
        item=(family,kind,proto,address)
        if item not in addresses:addresses.append(item)
    # Interleave families, so unreachable IPv6 cannot delay IPv4 or vice versa.
    v4=[a for a in addresses if a[0]==socket.AF_INET]
    v6=[a for a in addresses if a[0]==socket.AF_INET6]
    result=[]
    for i in range(max(len(v4),len(v6))):
        for group in (v6,v4):
            if i<len(group):result.append(group[i])
    if not result:raise OSError('DNS returned no usable addresses')
    return result[:4]

TRUSTED_CERTIFICATES = {'pool.hashvault.pro': {'provider': 'HashVault', 'sha256': '420c7850e09b7c0bdcf748a7da9eb3647daf8515718f36d9ccfdd6b9ff834b14', 'pem': '-----BEGIN CERTIFICATE-----\nMIIDnTCCAoWgAwIBAgIUZSdIViQBrjXpqX8EcIteqr3N8WMwDQYJKoZIhvcNAQEL\nBQAwXTELMAkGA1UEBhMCSVQxEjAQBgNVBAgMCUhhc2hWYXVsdDESMBAGA1UEBwwJ\nSGFzaFZhdWx0MRIwEAYDVQQKDAlIYXNoVmF1bHQxEjAQBgNVBAMMCUhhc2hWYXVs\ndDAgFw0xOTA5MjYxNTA5MzNaGA8yMTE5MDkwMjE1MDkzM1owXTELMAkGA1UEBhMC\nSVQxEjAQBgNVBAgMCUhhc2hWYXVsdDESMBAGA1UEBwwJSGFzaFZhdWx0MRIwEAYD\nVQQKDAlIYXNoVmF1bHQxEjAQBgNVBAMMCUhhc2hWYXVsdDCCASIwDQYJKoZIhvcN\nAQEBBQADggEPADCCAQoCggEBAPdYGskWIPiPF+zfcFxp2aX92uARRTVEAyQZfH52\njaeTagT4wTdnqNCF5HbQpAOIzjYwegD6FZfR1Oz+OMrF0LhohZjJ5zY0XeFRtR7j\nvyNXX+6QptyVxoc2seI6mU0o+TdgTrQXRk2yIUkwPK0G4i9BPVe5AJCoipTh1RW9\nL7NV5zxzsSOyydMaJewwMsQOLHiECHPzSKnofdc2QddmRN3/3um3ZX0FLpe2a/nv\n+mW8LPohiwd4BRkeZsQnQTwCrGDl2w5Rzjnqux5veH6PnqgfemvZ0DmFdGkCBDqz\nTzXHsiOa6vbUMtPJNd8ewbSMX9cRrfs/5c8r7w4UsFtaCiECAwEAAaNTMFEwHQYD\nVR0OBBYEFCcwkaEhQo7M94Jsx+hawdlvd+iGMB8GA1UdIwQYMBaAFCcwkaEhQo7M\n94Jsx+hawdlvd+iGMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEB\nAEhglGcCCPmppJIFrFkoE4vEtOCerON4VfpmuZQNEx9kTTahx6NUDinlagCE6udw\nEscv5qyCfprgTDdMi691HEIUZfwyK13B+YRTFSoSLh1crYrJTQjD++UXwXkiXhWe\nh/5v8rdkZIuaLnv2S+wmxFQxyTXe9pv/lUud5HUpm+AuHRcx48XrU9SicLyXHaPP\npxdo8WFMvG4/RT+E/0bqebdXT2XNxNvCXrX2RYM8pCW0CbZvmCCWTtJahUJCv+p1\nOoY+OCfv4gli8FzGsPgqvFnv9Vr3RI3fsNb+XihGaTYL0pLOYjKikHU0gKfbQXrZ\n8odFWSSuhDskPiJD7CHT9T8=\n-----END CERTIFICATE-----\n'}, 'gulf.moneroocean.stream': {'provider': 'MoneroOcean', 'sha256': '239daadd5c7d0ac097376c7871f787738826eef1c024729eff870e473b970855', 'pem': '-----BEGIN CERTIFICATE-----\nMIIDiTCCAnGgAwIBAgIJAOnIBoZRmS1uMA0GCSqGSIb3DQEBCwUAMFoxCzAJBgNV\nBAYTAklUMQ0wCwYDVQQIDARQb29sMQ8wDQYDVQQHDAZEYWVtb24xFDASBgNVBAoM\nC01pbmluZyBQb29sMRUwEwYDVQQDDAxtaW5pbmcucHJveHkwIBcNMTcwOTAzMTQz\nNzM3WhgPMjExNzA4MTAxNDM3MzdaMFoxCzAJBgNVBAYTAklUMQ0wCwYDVQQIDARQ\nb29sMQ8wDQYDVQQHDAZEYWVtb24xFDASBgNVBAoMC01pbmluZyBQb29sMRUwEwYD\nVQQDDAxtaW5pbmcucHJveHkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIB\nAQCwyJ4cZN53p3aGaUtZPdTKIS5rAYUsYJJGiXLdrOL9b7UcbF7DD6iYJhS7nBbr\nFYizbPURbJOSzTYOfnAb74gOgKd8gkWHljUlF1cZcuC9Em90Hp26bKX1yomiKymx\n0AfHL5UsZfZBtI+f36Kb8pmyq8dNhJZMe5uCVKhIijGoGUzyssgdmnR0sd/Vqr/4\nuiKfB9WAXGgEdMBpmqjY5JZGPuibZSKfyRvkY1PWpMDXBfgm4KuwezoUqQrIL1Ye\nTgdyU3sH4uN9MjGDsJdrEavAmm6RKRns4CR9ppC/Rzmc6dWofY1FVAt8OHw75DBY\nqZwFlNo8P1K/DfPp56sFt9+3AgMBAAGjUDBOMB0GA1UdDgQWBBT//S4D8Tf3XV3Z\nRNzibSrx5hD4lDAfBgNVHSMEGDAWgBT//S4D8Tf3XV3ZRNzibSrx5hD4lDAMBgNV\nHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAp4aWNRSm0rjOkzkEEmxDRkJCe\nNltw9covQBfTH0C47akmdEHcJQ+NuvBhyuvpANPbVcRrP3hPrzOSVTTHxwVdX2tq\n12YaCT2jRue6nLmW8xxnd32iYpIIX4nLaygr4L/ttmb3istyOpdGmvtqgphqYRhn\nuon8vRLxMyrBd8nCyHjlt+bloIfA030h+zm1bWbBELsBBenCt/hkYfL8ZrH6GYZH\nC2QOgmjdkOY52VnHo5QE/FSTaJR1Cq61Aydn71Vd1KH7VX+jMcIlKDEdXLIu//ob\ndgE40Oolo3a4vOpc7JGdOHuEYnA+fkda/Bc4FHOJZ8QU9LuMJU1iLMgLwKEb\n-----END CERTIFICATE-----\n'}}

def context_for(host):
    host=host.lower().rstrip('.')
    policy=TRUSTED_CERTIFICATES.get(host)
    if policy:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # The exact leaf pin binds this certificate to this allowlisted DNS
        # host, even though the historical certificate has no DNS SAN.
        context.check_hostname=False
        context.verify_mode=ssl.CERT_REQUIRED
        context.load_verify_locations(cadata=policy['pem'])
    else:
        context=ssl.create_default_context()
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    return context,policy

def _open_tls_once(host,port,timeout=10):
    host=host.lower().rstrip('.')
    context,policy=context_for(host)
    raw=socket.create_connection((host,port),timeout=timeout)
    secure=None
    try:
        secure=context.wrap_socket(raw,server_hostname=host)
        if policy:
            actual=hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
            if not hmac.compare_digest(actual,policy['sha256']):
                raise ssl.SSLCertVerificationError('Pool certificate fingerprint changed; refusing connection')
        if secure.version() not in ('TLSv1.2','TLSv1.3'):
            raise ssl.SSLError('Unsupported TLS protocol')
        return secure
    except BaseException:
        if secure is not None:secure.close()
        else:raw.close()
        raise

def _candidate_ports(host,port):
    if host=='gulf.moneroocean.stream' and port in (20001,20128,443):
        return list(dict.fromkeys([port,443,20128,20001]))
    return [port]

def _open_proxy_tls(host,ports,proxy,deadline,progress):
    context,policy=context_for(host)
    errors=[]
    for candidate in ports:
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        raw=secure=None
        try:
            attempt_deadline=min(deadline,time.monotonic()+4)
            progress('PROXY',host=host,port=candidate,proxy_host=proxy[0],proxy_port=proxy[1],route='system_proxy')
            raw=open_connect_tunnel(proxy,host,candidate,attempt_deadline-time.monotonic())
            remaining=attempt_deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Proxy TLS deadline reached')
            raw.settimeout(remaining)
            progress('TLS',host=host,port=candidate,address=host,route='system_proxy')
            secure=context.wrap_socket(raw,server_hostname=host)
            if policy:
                actual=hashlib.sha256(secure.getpeercert(binary_form=True)).hexdigest()
                if not hmac.compare_digest(actual,policy['sha256']):
                    raise ssl.SSLCertVerificationError('Pool certificate fingerprint changed; refusing connection')
            if secure.version() not in ('TLSv1.2','TLSv1.3'):raise ssl.SSLError('Unsupported TLS protocol')
            # The TCP peer is the local proxy. Preserve the actual selected
            # mining port separately so the GUI never treats 7890 as a pool.
            secure.xmr_pool_port=candidate
            secure.xmr_pool_address=host
            secure.xmr_route='system_proxy'
            return secure
        except (ssl.SSLCertVerificationError,PermissionError):
            if secure is not None:secure.close()
            elif raw is not None:raw.close()
            raise
        except OSError as exc:
            errors.append(f'{candidate}:{type(exc).__name__}')
            if secure is not None:secure.close()
            elif raw is not None:raw.close()
    raise ConnectionError(f'{host}: 系统本地代理加密连接失败 / Verified TLS through enabled local proxy failed [{", ".join(errors)}]')

def open_tls_socket(host,port,timeout=10,on_progress=None):
    host=host.lower().rstrip('.')
    def progress(stage,**values):
        if on_progress:on_progress(stage,**values)
    progress('DNS',host=host)
    ports=_candidate_ports(host,port)
    deadline=time.monotonic()+max(0.1,min(float(timeout),8))
    proxy=None if host in ('localhost','127.0.0.1','::1') else get_system_proxy()
    if proxy:return _open_proxy_tls(host,ports,proxy,time.monotonic()+max(.1,min(float(timeout),12)),progress)
    try:addresses=_resolve_addresses(host,deadline)
    except OSError as exc:
        raise ConnectionError(f'{host}: DNS 解析失败 / DNS resolution failed: {exc}') from exc
    ips=list(dict.fromkeys(address[3][0] for address in addresses))
    progress('TCP',host=host,addresses=ips,ports=ports)
    context,policy=context_for(host)
    active={};winner=None;errors=[]
    with selectors.DefaultSelector() as selector:
        try:
            # Race only this pool's explicit TLS ports and DNS answers. Never
            # race another pool or send login data before certificate checks.
            for candidate in ports:
                for family,kind,proto,address in addresses:
                    raw=socket.socket(family,kind,proto)
                    try:
                        raw.setblocking(False)
                        target=(address[0],candidate)+address[2:]
                        code=raw.connect_ex(target)
                        if code not in (0,errno.EINPROGRESS,errno.EWOULDBLOCK,errno.EALREADY,10035,10036,10037):
                            raise OSError(code,'TCP connect failed')
                        active[raw]=(candidate,'TCP')
                        selector.register(raw,selectors.EVENT_WRITE)
                    except OSError as exc:
                        raw.close();errors.append(f'{candidate}/TCP:{type(exc).__name__}')
            while active and time.monotonic()<deadline:
                for key,_ in selector.select(max(0,deadline-time.monotonic())):
                    conn=key.fileobj
                    candidate,stage=active[conn]
                    try:
                        if stage=='TCP':
                            code=conn.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
                            if code:raise OSError(code,'TCP connect failed')
                            progress('TLS',host=host,port=candidate,address=conn.getpeername()[0])
                            selector.unregister(conn);active.pop(conn)
                            raw=conn
                            try:conn=context.wrap_socket(raw,server_hostname=host,do_handshake_on_connect=False)
                            except BaseException:
                                raw.close();raise
                            active[conn]=(candidate,'TLS')
                            stage='TLS'
                            selector.register(conn,selectors.EVENT_READ|selectors.EVENT_WRITE)
                        try:conn.do_handshake()
                        except ssl.SSLWantReadError:
                            selector.modify(conn,selectors.EVENT_READ);continue
                        except ssl.SSLWantWriteError:
                            selector.modify(conn,selectors.EVENT_WRITE);continue
                        if policy:
                            actual=hashlib.sha256(conn.getpeercert(binary_form=True)).hexdigest()
                            if not hmac.compare_digest(actual,policy['sha256']):
                                raise ssl.SSLCertVerificationError('Pool certificate fingerprint changed; refusing connection')
                        if conn.version() not in ('TLSv1.2','TLSv1.3'):
                            raise ssl.SSLError('Unsupported TLS protocol')
                        selector.unregister(conn);active.pop(conn)
                        conn.setblocking(True);conn.settimeout(timeout)
                        winner=conn
                        return winner
                    except ssl.SSLCertVerificationError:
                        # Fail closed; never accept another certificate as a
                        # workaround for a trust failure.
                        raise
                    except OSError as exc:
                        errors.append(f'{candidate}/{stage}:{type(exc).__name__}')
                        if conn in active:
                            selector.unregister(conn);active.pop(conn)
                        conn.close()
            errors.extend(f'{candidate}/{stage}:Timeout' for candidate,stage in active.values())
        finally:
            for conn in active:conn.close()
    details=', '.join(dict.fromkeys(errors))
    raise ConnectionError(f'{host} ({", ".join(ips)}): 加密连接失败 / Verified TLS unavailable [{details}]. 请重试或选择其他矿池 / Retry or select another pool.')
