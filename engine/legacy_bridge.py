"""Original UI configuration/log adapter for the independent CPU engine.

Development only. GPU must fail explicitly until an independent GPU backend is
implemented. No fallback to XMRig and no pretending that GPU work was started.
"""
import argparse
import json
import os
from pathlib import Path
import threading
import time
from dataclasses import dataclass
import engine
import solo

@dataclass(frozen=True)
class Config:
    host:str
    port:int
    wallet:str
    threads:int
    tls:bool
    daemon:bool
    cuda:bool=False

    @classmethod
    def parse(cls,value):
        if not isinstance(value,dict):raise ValueError('Configuration must be an object')
        if value.get('opencl',{}).get('enabled'):
            raise ValueError('Independent AMD OpenCL backend is not implemented; no fallback engine will be used')
        cuda=bool(value.get('cuda',{}).get('enabled'))
        cpu=value.get('cpu',{})
        if not cpu.get('enabled') and not cuda:raise ValueError('Enable CPU or CUDA mining')
        pools=value.get('pools')
        if not isinstance(pools,list) or len(pools)!=1:raise ValueError('Exactly one active pool/node is required')
        pool=pools[0];endpoint=pool.get('url','')
        import re
        if not re.fullmatch(r'[A-Za-z0-9.-]+:[0-9]{1,5}',endpoint):raise ValueError('Expected host:port')
        host,port=endpoint.rsplit(':',1);port=int(port)
        if not 1<=port<=65535:raise ValueError('Invalid port')
        if not pool.get('tls') and host.lower() not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Remote mining requires verified TLS; no plaintext fallback is permitted')
        wallet=pool.get('user','')
        if not re.fullmatch(r'[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{95}',wallet):raise ValueError('Invalid payout address')
        assignment=cpu.get('rx/0',cpu.get('rx'))
        if cpu.get('enabled'):
            if not isinstance(assignment,list) or not 1<=len(assignment)<=(os.cpu_count() or 1):raise ValueError('Invalid CPU thread assignment')
            threads=len(assignment)
        else:threads=0
        if cuda and pool.get('daemon'):raise ValueError('CUDA solo mode has not been validated')
        return cls(host,port,wallet,threads,bool(pool.get('tls')),bool(pool.get('daemon')),cuda)


def original_ui_event(kind,**values):
    global SESSION_ACCEPTED,SESSION_REJECTED,CURRENT_ENDPOINT
    if kind=='tls_verified' and values.get('host') and values.get('port'):
        CURRENT_ENDPOINT=f'{values["host"]}:{values["port"]}'
    if kind in ('share','stopped'):
        SESSION_ACCEPTED=values.get('total_accepted',values.get('accepted',SESSION_ACCEPTED))
        SESSION_REJECTED=values.get('total_rejected',values.get('rejected',SESSION_REJECTED))
    if kind=='job':print('new job from '+CURRENT_ENDPOINT,flush=True)
    elif kind=='hashrate':
        rate=values['cpu_hs']
        print(f'backend-rate cpu {rate} H/s',flush=True)
        gpu=values.get('gpu_hs',0)
        print(f'backend-rate cuda {gpu} H/s',flush=True)
        # A rolling ~10-second estimate, emitted every second. Keep the
        # existing window label; refresh cadence is independent of averaging.
        print(f'speed 10s/60s/15m {round(rate+gpu,2)} n/a n/a H/s',flush=True)
    elif kind=='share':
        if values.get('accepted'):
            print(f'accepted ({ACCEPTED_BASE+values["total_accepted"]}/{REJECTED_BASE+values["total_rejected"]})',flush=True)
        else:print('share rejected: '+str(values.get('error','node/pool rejected')),flush=True)
    else:print('XMR | '+json.dumps({'event':kind,**values},ensure_ascii=False),flush=True)

CURRENT_ENDPOINT=''
ACCEPTED_BASE=REJECTED_BASE=0
SESSION_ACCEPTED=SESSION_REJECTED=0

def run(path,stop_event,factory=None):
    global CURRENT_ENDPOINT,ACCEPTED_BASE,REJECTED_BASE,SESSION_ACCEPTED,SESSION_REJECTED
    ACCEPTED_BASE=REJECTED_BASE=SESSION_ACCEPTED=SESSION_REJECTED=0
    previous_engine_event,previous_solo_event=engine.event,solo.event
    engine.event=original_ui_event;solo.event=original_ui_event
    config=None;miner=None;thread=None;failures=[]
    # Preserve the same immutable dataset across address/pool changes, so the
    # one-minute author window does not repeatedly rebuild two GiB of data.
    shared_rx=engine.RandomX() if factory is None else None
    shared_gpu=None
    if factory is None:
        def factory(c):
            nonlocal shared_gpu
            m=engine.Miner(shared_rx,c.threads,True)
            if c.cuda:
                from cuda_backend import CudaBackend,HybridWorkers
                if shared_gpu is None:shared_gpu=CudaBackend()
                m.worker_factory=lambda rx,count:HybridWorkers(rx,count,shared_gpu)
                if not c.threads and c.host=='gulf.moneroocean.stream':m.login_difficulty=1000
            m.retain_context=True;m.report_interval=1
            return m
    last_bytes=None
    try:
        while not stop_event.is_set():
            # Read full JSON before touching running work. A partial write is
            # retried, and a malformed configuration never silently changes a wallet.
            data=path.read_bytes()
            if data!=last_bytes:
                try:incoming=Config.parse(json.loads(data))
                except json.JSONDecodeError:
                    stop_event.wait(.1);continue
                if incoming!=config:
                    if miner:miner.stop()
                    if thread:thread.join()
                    if failures:raise failures[0]
                    if miner:
                        ACCEPTED_BASE+=SESSION_ACCEPTED;REJECTED_BASE+=SESSION_REJECTED
                    SESSION_ACCEPTED=SESSION_REJECTED=0
                    config=incoming;CURRENT_ENDPOINT=f'{config.host}:{config.port}'
                    miner=factory(config)
                    def work(m=miner,c=config):
                        try:
                            if c.daemon:solo.session(m.rx,c.host,c.port,c.wallet,c.threads,True,m.stop_event,
                                                   solo.Rpc(c.host,c.port,c.tls),retain_context=True)
                            else:m.session(c.host,c.port,c.wallet,c.tls)
                        except InterruptedError:pass
                        except BaseException as exc:failures.append(exc)
                    thread=threading.Thread(target=work,name='XMR-session');thread.start()
                    print('XMR | configuration applied; old session fully stopped before restart',flush=True)
                last_bytes=data
            if failures:raise failures[0]
            if thread and not thread.is_alive():break
            stop_event.wait(.1)
    finally:
        if miner:miner.stop()
        if thread:thread.join()
        if shared_gpu:shared_gpu.close()
        if shared_rx:shared_rx.close()
        engine.event,solo.event=previous_engine_event,previous_solo_event


if __name__=='__main__':
    import sys
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);args=parser.parse_args()
    try:run(args.config,threading.Event())
    except KeyboardInterrupt:pass
    except Exception as exc:
        print('XMR ERROR | '+str(exc),flush=True);raise SystemExit(1)
