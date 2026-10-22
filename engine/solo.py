"""Independent Monero daemon RPC mining path, based on published daemon RPC.

No XMRig code. GPU support is not implemented here.
"""
import hashlib
import json
import queue
import time
import urllib.request
from dataclasses import dataclass
from engine import Job, CpuWorkers, decode_hex, event

MAX_RPC=4*1024*1024

def read_varint(blob,offset):
    value=0
    for shift in range(0,70,7):
        if offset>=len(blob):raise ValueError('Truncated block header')
        byte=blob[offset];offset+=1
        if shift==63 and byte>1:raise ValueError('Block header varint overflow')
        value|=(byte&127)<<shift
        if not byte&128:return value,offset
    raise ValueError('Block header varint exceeds uint64')

def nonce_offset(blob):
    major,pos=read_varint(blob,0)
    _,pos=read_varint(blob,pos)
    _,pos=read_varint(blob,pos)
    if not 12<=major<=16:
        raise ValueError('Unsupported block version; only established RandomX v1 versions 12–16 are enabled')
    pos+=32
    if pos+4>len(blob):raise ValueError('Block header has no nonce')
    return pos

@dataclass(frozen=True)
class Template:
    job:Job
    block:bytes
    offset:int

    @classmethod
    def parse(cls,result):
        if not isinstance(result,dict) or result.get('status')!='OK' or result.get('untrusted',True):
            raise ValueError('Node must supply an OK, locally validated block template')
        hashing=decode_hex(result.get('blockhashing_blob'),'blockhashing_blob')
        block=decode_hex(result.get('blocktemplate_blob'),'blocktemplate_blob')
        if not 43<=len(hashing)<=512 or not 43<=len(block)<=MAX_RPC//2:
            raise ValueError('Unsupported block template size')
        offset=nonce_offset(hashing)
        if nonce_offset(block)!=offset or block[:offset+4]!=hashing[:offset+4]:
            raise ValueError('Hashing and submission block headers differ')
        # Current standard Monero pool jobs use offset 39. Refuse alternate
        # layouts until the worker candidate API supports them explicitly.
        if offset!=39:raise ValueError('Unsupported nonce offset')
        low=result.get('difficulty');high=result.get('difficulty_top64',0)
        if type(low)!=int or type(high)!=int or not 0<=low<2**64 or not 0<=high<2**64:
            raise ValueError('Invalid 128-bit node difficulty')
        difficulty=low+(high<<64)
        if difficulty<=0:raise ValueError('Zero node difficulty')
        seed=decode_hex(result.get('seed_hash'),'seed_hash',(32,))
        target=((1<<256)-1)//difficulty+1
        ident=hashlib.sha256(hashing+seed+str(difficulty).encode()).hexdigest()
        return cls(Job(ident,hashing,seed,target),block,offset)

    def submit_blob(self,nonce):
        return (self.block[:self.offset]+nonce.to_bytes(4,'little')+self.block[self.offset+4:]).hex()


class Rpc:
    def __init__(self,host,port,tls=False):
        self.url=('https' if tls else 'http')+'://'+host+':'+str(port)+'/json_rpc'
        # Local RPC must not be sent through a system HTTP proxy.
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(self,method,params):
        request=urllib.request.Request(self.url,data=json.dumps({'jsonrpc':'2.0','id':'xmr',
                                      'method':method,'params':params},allow_nan=False).encode(),
                                      headers={'Content-Type':'application/json','User-Agent':'XMR-Independent/0.2-dev'})
        with self.opener.open(request,timeout=10) as response:data=response.read(MAX_RPC+1)
        if len(data)>MAX_RPC:raise ValueError('Node RPC response exceeds size limit')
        reply=json.loads(data)
        if not isinstance(reply,dict) or reply.get('error'):
            raise ConnectionError('Node rejected RPC request: '+str(reply.get('error') if isinstance(reply,dict) else 'invalid reply'))
        result=reply.get('result')
        if not isinstance(result,dict):raise ValueError('Node RPC returned no result object')
        return result


def session(rx,host,port,wallet,threads,fast,stop_event,rpc=None,retain_context=False):
    if not wallet.startswith('4'):raise ValueError('Solo mining requires a standard mainnet address')
    rpc=rpc or Rpc(host,port)
    workers=None;template=None;accepted=rejected=0;last_report=time.monotonic();previous=0
    try:
        while not stop_event.is_set():
            incoming=Template.parse(rpc.call('get_block_template',{'wallet_address':wallet,'reserve_size':0}))
            if template is None or incoming.job!=template.job:
                if workers:workers.stop()
                workers=None
                event('preparing',percent=0)
                rx.prepare(incoming.job.seed,fast,stop_event.is_set)
                if stop_event.is_set():break
                template=incoming;workers=CpuWorkers(rx,threads);workers.start(template.job)
                previous=0;last_report=time.monotonic();event('job',job_id=template.job.id,mode='solo')
            until=time.monotonic()+1
            while not stop_event.is_set() and time.monotonic()<until:
                if not workers.errors.empty():raise workers.errors.get()
                try:nonce,digest=workers.shares.get(timeout=.1)
                except queue.Empty:continue
                if not template.job.accepts(digest):raise RuntimeError('Worker returned an invalid block candidate')
                result=rpc.call('submit_block',[template.submit_blob(nonce)])
                ok=result.get('status')=='OK'
                if ok:accepted+=1
                else:rejected+=1
                event('share',accepted=ok,total_accepted=accepted,total_rejected=rejected,share_type='block')
                # A successful block invalidates the current template. Stop
                # before polling again rather than submitting duplicate blocks.
                if ok:
                    workers.stop();workers=None;template=None;break
            if workers and time.monotonic()-last_report>=5:
                current=workers.hashes
                event('hashrate',cpu_hs=round((current-previous)/(time.monotonic()-last_report),2),accepted=accepted,rejected=rejected)
                previous=current;last_report=time.monotonic()
    finally:
        if workers:workers.stop()
        if not retain_context:rx.close()
        event('stopped',accepted=accepted,rejected=rejected)
