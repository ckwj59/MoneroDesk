"""XMR desktop interface with the bundled XMRig runtime bridge."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
if sys.platform == "win32":
    import winreg
else:
    winreg = None
if not getattr(sys,'frozen',False):
    sys.path.insert(0,str(Path(__file__).resolve().parent))
from portable_support import IS_WINDOWS, NO_WINDOW, engine_name, cuda_files, linux_hardware, validate_native_manifest, LinuxMinerJob
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from datetime import datetime
import math
import urllib.error
import psutil
from Crypto.Hash import keccak

BASE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
DATA = BASE / 'data'
BENEFICIARY = '48Rd53h2a9aT1wYnMF6VtVZab189WPVR5jgVf6UedT4iRiLNX91MoA5GydXdu5oMVeSZZCv1H86wKR91V6bBZXCu4LpLusv'
ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
POOL_PRESETS = [
    {'name':'HashVault', 'endpoint':'pool.hashvault.pro:443', 'tls':True, 'fee':'0.9',
     'source':'https://hashvault.pro/monero/ports'},
    {'name':'MoneroOcean', 'endpoint':'gulf.moneroocean.stream:20001', 'tls':True, 'fee':'0',
     'source':'https://moneroocean.stream'},
]
PUBLIC_NODES = [
    {'name':'Seth for Privacy', 'endpoint':'node.sethforprivacy.com:443', 'tls':True,
     'source':'https://sethforprivacy.com/about/'},
    {'name':'Cake Wallet', 'endpoint':'xmr-node.cakewallet.com:18081', 'tls':False,
     'source':'https://github.com/cake-tech/upptime-monerocom'},
    {'name':'HashVault', 'endpoint':'nodes.hashvault.pro:18081', 'tls':False,
     'source':'https://hashvault.pro/monero'},
]
TEXT = {
 'zh': {'title':'门罗币工作台', 'tag':'本地 CPU 挖矿 · 公开费用 · 手动控制', 'setup':'挖矿设置', 'device':'本机设备', 'logs':'运行日志',
 'wallet':'主收款地址', 'mode':'挖矿方式', 'solo':'本地节点独立挖矿', 'pool':'矿池（费用由矿池决定）', 'endpoint':'节点 / 矿池地址', 'threads':'CPU 挖矿线程',
 'tls':'矿池 TLS（端口需支持）', 'share':'向指定地址分配 1% 挖矿时间（可取消）', 'start':'开始挖矿', 'stop':'停止', 'refresh':'重新检测设备',
 'idle':'未启动', 'stopped':'已停止', 'checking':'正在检查本地节点…', 'running':'正在运行', 'hash':'实时算力', 'accepted':'有效份额 / 区块', 'uptime':'本次运行',
 'fee':'开发者捐赠 0%  ·  本地独挖矿池费 0%', 'note':'独挖只有找到区块才有奖励，普通笔记本可能长期没有收入。挖矿仍需消耗电力。',
 'split':'每 100 分钟分配 1 分钟给指定地址，非币数精确分账；独挖仅找到区块才有奖励。矿池模式两个地址分别达到付款门槛才到账。',
 'owner':'指定分成地址（完整公开）', 'opt':'优化：自动指令集、AES/JIT、缓存感知线程、已有大页权限；不修改系统权限或加载 MSR 驱动。',
 'cpu':'处理器', 'cores':'物理 / 逻辑核心', 'ram':'可用 / 总内存', 'cache':'L3 缓存', 'power':'供电', 'gpu':'显示设备（此版本使用 CPU）', 'recommend':'建议起始线程',
 'ac':'已接电', 'battery':'电池供电', 'unknown':'无法读取', 'save':'修改设置后需停止再启动。设置保存在 data 文件夹；不要填写助记词或私钥。',
 'consent':'我理解电力开销、无收益保证及当前分成设置', 'warn':'请检查', 'ready':'设备已就绪', 'exit':'退出会停止本程序启动的矿工。', 'no_temp':'温度：当前接口不提供读数，请自行查看硬件监控工具。'},
 'en': {'title':'Monero Desk', 'tag':'Local CPU mining · Visible fees · Manual control', 'setup':'Mining', 'device':'Hardware', 'logs':'Activity',
 'wallet':'Main payout address', 'mode':'Mining mode', 'solo':'Solo via local node', 'pool':'Pool (operator fees may apply)', 'endpoint':'Node / pool endpoint', 'threads':'CPU mining threads',
 'tls':'Pool TLS (port must support TLS)', 'share':'Allocate 1% of runtime to the specified address (optional)', 'start':'Start mining', 'stop':'Stop', 'refresh':'Refresh hardware',
 'idle':'Idle', 'stopped':'Stopped', 'checking':'Checking local node…', 'running':'Running', 'hash':'Hashrate', 'accepted':'Accepted shares / blocks', 'uptime':'Session time',
 'fee':'Developer donation 0%  ·  Local solo pool fee 0%', 'note':'Solo rewards require finding a block. A laptop may earn nothing for a long time. Electricity still costs money.',
 'split':'Allocate 1 minute per 100 minutes, not an exact coin split. Solo rewards require finding a block. Pools pay each address separately after its payout threshold.',
 'owner':'Specified beneficiary (fully visible)', 'opt':'Optimizations: automatic ISA, AES/JIT, cache-aware threads and existing huge-page permissions. No privilege changes or MSR drivers.',
 'cpu':'CPU', 'cores':'Physical / logical cores', 'ram':'Available / total RAM', 'cache':'L3 cache', 'power':'Power', 'gpu':'Display adapters (this build mines on CPU)', 'recommend':'Suggested starting threads',
 'ac':'Plugged in', 'battery':'On battery', 'unknown':'Unavailable', 'save':'Stop and restart to apply changes. Settings stay in data. Never enter a seed phrase or private key.',
 'consent':'I understand electricity costs, uncertain rewards and the current allocation', 'warn':'Check settings', 'ready':'Hardware ready', 'exit':'Exiting stops the miner started by this app.', 'no_temp':'Temperature: unavailable through this interface. Use your hardware monitor.'}
}
TEXT['zh'].update(nodes='备用公开节点', remote='远程节点独立挖矿', check_all='检测全部', check_one='检测选中',
                  use_node='使用选中节点', copy_node='复制地址', node_name='提供者', node_addr='地址',
                  node_height='区块高度', latency='延迟', node_status='状态 / 最近检测',
                  untested='未检测', probing='检测中', online='主网已同步', failed='连接失败', copied='已复制',
                  node_help='公开节点可用于 GUI Wallet。也可选择远程独挖，开始前会检查挖矿 RPC 权限；连得通不代表允许挖矿。远程节点不会加速本地区块链同步，也不是矿池。',
                  node_privacy='检测只查询节点状态，不发送钱包地址。点击开始远程挖矿后才向选中节点提交公开收款地址。HTTP 节点未加密；可优先使用 HTTPS。第三方服务可能随时离线。',
                  tls='TLS 加密连接（建议保持勾选）', checking='正在检查节点…')
TEXT['en'].update(nodes='Public backup nodes', remote='Solo via remote node', check_all='Test all', check_one='Test selected',
                  use_node='Use selected node', copy_node='Copy endpoint', node_name='Provider', node_addr='Endpoint',
                  node_height='Height', latency='Latency', node_status='Status / last checked',
                  untested='Not tested', probing='Testing', online='Mainnet synced', failed='Connection failed', copied='Copied',
                  node_help='Use these nodes in GUI Wallet or select remote solo mode. Mining RPC permission is checked before start; reachability does not imply mining permission. These are not pools and do not speed up local blockchain sync.',
                  node_privacy='Tests only query status, without a wallet address. Starting remote mining sends the public payout address to the selected node. HTTP is unencrypted; prefer HTTPS when available. Availability may change.',
                  tls='Remote TLS (port must support TLS)', checking='Checking node…')
TEXT['zh'].update(earnings='价格与收益', price='XMR 参考价格', price_refresh='刷新价格', wallet_refresh='读取钱包',
                 balance='当前钱包余额', unlocked='已解锁可用', mined='钱包历史独挖区块奖励', valuation='余额参考价值',
                 unknown_money='未读取', wallet_rpc='本机钱包 RPC', rpc_user='RPC 用户名（可选）', rpc_password='RPC 密码（不保存）',
                 money_help='独挖奖励直接到钱包，没有矿池提现门槛；区块奖励通常需约 60 个区块解锁，转出仍有网络手续费。矿池付款门槛由矿池决定，可在矿池实况页查询已接入的账户接口。',
                 wallet_help='自动读取需已运行的本机 monero-wallet-rpc（节点 RPC 不是钱包 RPC），只查询账户 0 的主地址。仅输入 RPC 登录信息，不输入助记词、私钥或钱包解密密码；GUI Wallet 打开本身不会提供此接口。',
                 money_note='区块奖励合计来自钱包历史，包含其他矿工产生的奖励，不能视为本程序收入；矿池付款不算独挖奖励。余额可能包含普通转入。价格仅作参考，非兑换报价；钱包扫描未完成时数据可能不完整。',
                 last_update='更新时间', scan_height='钱包扫描高度', mode_now='当前选择的挖矿方式')
TEXT['en'].update(earnings='Price & earnings', price='XMR reference price', price_refresh='Refresh price', wallet_refresh='Read wallet',
                 balance='Current wallet balance', unlocked='Unlocked / spendable', mined='Historical solo block rewards', valuation='Reference balance value',
                 unknown_money='Not read', wallet_rpc='Local wallet RPC', rpc_user='RPC username (optional)', rpc_password='RPC password (not saved)',
                 money_help='Solo rewards go directly to the wallet, with no pool withdrawal threshold. Block rewards normally unlock after about 60 blocks; sending still costs a network fee. Pool payout thresholds are operator-defined. Supported account APIs are available on the Live pool data tab.',
                 wallet_help='Requires an existing local monero-wallet-rpc (not node RPC). Reads only account 0 primary address. Enter RPC credentials only, never a seed, private key or wallet decryption password. GUI Wallet alone does not expose this interface.',
                 money_note='Historical block rewards include other miners, not just this app. Pool deposits are not solo block rewards. Balance may include ordinary deposits. Prices are indicative, not exchange quotes; incomplete wallet scans may omit funds.',
                 last_update='Last updated', scan_height='Wallet scan height', mode_now='Selected mining mode')


# Display currency follows the selected interface language; ISO codes avoid ambiguous symbols.
LANGUAGE_CURRENCIES={'zh':'cny','en':'gbp','es':'eur','fr':'eur','de':'eur','pt':'eur','ru':'rub','ar':'sar','hi':'inr','ja':'jpy','ko':'krw','it':'eur','tr':'try','id':'idr','vi':'vnd','th':'thb','pl':'pln','nl':'eur','uk':'uah','bn':'bdt'}
PRICE_CURRENCIES=tuple(sorted(set(LANGUAGE_CURRENCIES.values())|{'usd'}))


def sync_owned_desktop_shortcuts(title,description):
    """Localize existing links to this exact packaged app; never touch other targets."""
    if not IS_WINDOWS or not getattr(sys,'frozen',False): return
    script=r"""
$ErrorActionPreference='Stop'
$shell=New-Object -ComObject WScript.Shell
$desktop=$shell.SpecialFolders.Item('Desktop')
$target=[IO.Path]::GetFullPath($env:MONERODESK_LINK_TARGET)
$name=$env:MONERODESK_LINK_TITLE
foreach($char in [IO.Path]::GetInvalidFileNameChars()) { $name=$name.Replace([string]$char,'_') }
$name=$name.Trim()
if([string]::IsNullOrWhiteSpace($name)) { exit 0 }
$destination=Join-Path $desktop ($name+'.lnk')
foreach($file in Get-ChildItem -LiteralPath $desktop -Filter '*.lnk' -File) {
    $link=$shell.CreateShortcut($file.FullName)
    if(-not [string]::Equals($link.TargetPath,$target,[StringComparison]::OrdinalIgnoreCase)) { continue }
    $link.Description=$env:MONERODESK_LINK_DESCRIPTION
    $link.Save()
    if([string]::Equals($file.FullName,$destination,[StringComparison]::OrdinalIgnoreCase)) { continue }
    if(-not (Test-Path -LiteralPath $destination)) { Rename-Item -LiteralPath $file.FullName -NewName ($name+'.lnk') }
}
"""
    env=dict(os.environ,MONERODESK_LINK_TARGET=str(Path(sys.executable).resolve()),MONERODESK_LINK_TITLE=title,MONERODESK_LINK_DESCRIPTION=description)
    try:
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,timeout=15,creationflags=0x08000000)
    except (OSError,subprocess.TimeoutExpired): pass


def fetch_price():
    url = 'https://api.coingecko.com/api/v3/simple/price?ids=monero&vs_currencies='+','.join(PRICE_CURRENCIES)+'&include_last_updated_at=true'
    req = urllib.request.Request(url,headers={'User-Agent':'MoneroDesk/2.8','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=8) as response:
        raw = json.loads(response.read(65536))['monero']
    quote={}
    for currency in PRICE_CURRENCIES:
        value=raw.get(currency)
        if not isinstance(value,bool) and value is not None:
            try:
                if math.isfinite(float(value)) and float(value)>0: quote[currency]=value
            except (ValueError,TypeError): pass
    if 'usd' not in quote: raise ValueError('Invalid market price')
    timestamp = int(raw.get('last_updated_at',0))
    if timestamp<=0 or timestamp>time.time()+300 or time.time()-timestamp>3600:
        raise ValueError('行情数据已过期 / Market data is stale')
    return {**quote,'last_updated_at':timestamp,'source':'CoinGecko'}


def wallet_call(endpoint, method, params, user='', password=''):
    if method not in ('get_address','get_balance','get_height','get_transfers'):
        raise ValueError('Read-only RPC methods only')
    if not re.fullmatch(r'(127\.0\.0\.1|localhost):\d{1,5}',endpoint) or not 1<=int(endpoint.rsplit(':',1)[1])<=65535:
        raise ValueError('钱包接口仅允许本机 / Wallet RPC must use loopback')
    url = 'http://'+endpoint+'/json_rpc'
    handlers = [urllib.request.ProxyHandler({})]
    if user:
        manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None,url,user,password)
        handlers.append(urllib.request.HTTPDigestAuthHandler(manager))
    payload = {'jsonrpc':'2.0','id':'read-only','method':method,'params':params}
    request = urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(*handlers).open(request,timeout=8) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:
        raise ValueError('钱包历史太大，无法完整读取 / Wallet history response too large')
    reply = json.loads(raw)
    if 'error' in reply or 'result' not in reply:
        raise ValueError(str(reply.get('error','Invalid wallet response')))
    return reply['result']


def fetch_wallet(endpoint, expected, user='', password=''):
    if not valid_wallet(expected):
        raise ValueError('先填写有效收款地址 / Enter the payout address first')
    def call(method, params):
        return wallet_call(endpoint,method,params,user,password)
    address = call('get_address',{'account_index':0,'address_index':[0]}).get('address')
    if address != expected:
        raise ValueError('钱包账户 0 主地址与收款地址不一致，未读取余额。 / Wallet primary address does not match payout address.')
    balance = call('get_balance',{'account_index':0,'address_indices':[0]})
    height = call('get_height',{})['height']
    transfers = call('get_transfers',{'in':True,'account_index':0,'subaddr_indices':[0],
                                    'out':False,'pending':False,'failed':False,'pool':False})
    blocks = [entry for entry in transfers.get('in',[]) if entry.get('type') == 'block' and entry.get('address') == address]
    if balance.get('multisig_import_needed'):
        raise ValueError('钱包余额需要额外同步，不能可靠读取 / Wallet balance needs multisig import')
    total = int(balance['balance'])
    unlocked = int(balance['unlocked_balance'])
    if total<0 or not 0<=unlocked<=total:
        raise ValueError('Invalid wallet amounts')
    return {'address':address,'balance':total,'unlocked':unlocked,'mined':sum(int(e['amount']) for e in blocks),
            'blocks':len(blocks),'height':int(height),'blocks_to_unlock':int(balance.get('blocks_to_unlock',0)),
            'checked':time.strftime('%Y-%m-%d %H:%M:%S')}


def xmr_amount(atomic):
    return f'{Decimal(atomic)/Decimal(10**12):.12f} XMR'


TEXT['zh'].update(stats='区块与统计', blocks='最近区块', sessions='挖矿历史', chain_refresh='刷新节点区块',
                 estimate='理论收益试算', input_hash='本机算力 H/s（可手填）', pool_hash='矿池总算力 H/s（选填）',
                 pool_fee='矿池费 %（手填）', calculate='计算预估', chain_hint='查询选中节点最近 20 个区块，不代表这些区块由你挖到。矿池模式使用备用页的节点查询链上数据。',
                 estimated_hint='预估采用当前难度、最近区块平均奖励及持续在线假设；不扣电费，不是已到账收入。独挖可能长期为零。矿池算力和费率是手填值，未向矿池核实。',
                 history_hint='仅记录本程序完整结束的挖矿会话；“已接受结果”不是已到账币数。钱包实际奖励请查看“价格与收益”。',
                 network='全网算力估计', network_share='本机占全网', your_pool_share='本机占矿池', pool_network_share='矿池占全网',
                 results='已接受结果', duration='运行秒数', daily='理论每日', monthly='理论每 30 天', lifetime='记录累计运行')
TEXT['en'].update(stats='Blocks & statistics', blocks='Recent blocks', sessions='Mining history', chain_refresh='Refresh chain data',
                 estimate='Expected yield', input_hash='Your hashrate H/s (editable)', pool_hash='Pool hashrate H/s (optional)',
                 pool_fee='Pool fee % (manual)', calculate='Calculate estimate', chain_hint='Queries the latest 20 blocks from the selected node. These are not necessarily your blocks. Pool mode uses the selected backup RPC for chain data.',
                 estimated_hint='Uses current difficulty, recent mean block reward and continuous uptime. Excludes electricity; this is not earned income. Solo payouts may remain zero. Pool rate/fee are manually entered and unverified.',
                 history_hint='Records completed sessions from this app only. Accepted results are not received coins. See Price & earnings for wallet rewards.',
                 network='Estimated network hashrate', network_share='Your network share', your_pool_share='Your pool share', pool_network_share='Pool network share',
                 results='Accepted results', duration='Seconds', daily='Expected / day', monthly='Expected / 30 days', lifetime='Recorded total runtime')


def fetch_chain(endpoint, tls):
    info = node_rpc(endpoint,tls)
    if info.get('status')!='OK' or not info.get('mainnet',info.get('nettype')=='mainnet'):
        raise ValueError('Not an OK mainnet node')
    height = int(info['height'])
    if height<1:
        raise ValueError('Empty chain')
    reply = node_rpc(endpoint,tls,{'jsonrpc':'2.0','id':'headers','method':'get_block_headers_range',
                                 'params':{'start_height':max(0,height-20),'end_height':height-1,'fill_pow_hash':False}})
    headers = reply.get('result',{}).get('headers',[])
    if reply.get('error') or not headers:
        raise ValueError('Node did not return block headers')
    difficulty = int(info.get('wide_difficulty','0x0'),16) if info.get('wide_difficulty') else int(info['difficulty'])
    target = int(info['target'])
    reward = sum(Decimal(int(h['reward'])) for h in headers)/Decimal(len(headers))/Decimal(10**12)
    if difficulty<=0 or target<=0 or reward<=0:
        raise ValueError('Invalid network parameters')
    return {'endpoint':endpoint,'height':height,'difficulty':difficulty,'target':target,
            'reward':str(reward),'headers':headers,'checked':time.strftime('%Y-%m-%d %H:%M:%S'),
            'synchronized':bool(info.get('synchronized'))}


def estimate_yield(hashes, chain, allocation=False, pool_rate=None, pool_fee=0):
    hashes,fee = Decimal(str(hashes)),Decimal(str(pool_fee))
    if not hashes.is_finite() or hashes<=0 or not fee.is_finite() or not 0<=fee<=100:
        raise ValueError('算力必须为正数，费率为 0–100 / Positive hashrate and fee 0–100 required')
    difficulty = Decimal(chain['difficulty'])
    network = difficulty/Decimal(chain['target'])
    factor = Decimal('0.99') if allocation else Decimal(1)
    daily = hashes*Decimal(86400)/difficulty*Decimal(chain['reward'])*factor*(1-fee/100)
    result = {'network':network,'network_share':hashes/network*100,'daily':daily,'monthly':daily*30,
              'days_per_block':difficulty/hashes/Decimal(86400),'pool_share':None,'pool_network':None}
    if pool_rate is not None:
        rate = Decimal(str(pool_rate))
        if not rate.is_finite() or rate<=0 or hashes>rate:
            raise ValueError('矿池总算力应不小于本机算力 / Pool rate must be at least your rate')
        result.update(pool_share=hashes/rate*100,pool_network=rate/network*100)
    return result


TEXT['zh'].update(pool_live='矿池实况', pool_query='查询矿池', pool_scope='结算方式',
                 pool_notice='当前支持 HashVault 官方 API。查询会向 HashVault 发送此公开收款地址；不会切换挖矿目标，也不需要私钥。',
                 pool_address='查询收款地址', pool_hint='占比采用同一窗口的矿池侧算力，不代表 PPLNS 最终分账比例。钱包余额和付款记录合并该地址的矿池结算方式。API 可能延迟。',
                 pool_payments='最近付款记录', pool_empty='该地址未见挖矿历史，或数据尚未更新。未在此矿池挖过不会产生收益。')
TEXT['en'].update(pool_live='Live pool data', pool_query='Query pool', pool_scope='Accounting mode',
                 pool_notice='Supports the official HashVault API. Clicking Query sends this public address to HashVault; it does not switch mining targets or require private keys.',
                 pool_address='Address to query', pool_hint='Share uses pool-side hashrates over the same window, not final PPLNS reward weights. Wallet balances and payments combine accounting modes. API data may lag.',
                 pool_payments='Recent payments', pool_empty='No mining history is visible for this address, or data has not updated. Querying alone does not earn coins.')


def pool_json(path):
    # Fixed HTTPS provider; no arbitrary API URLs or credentials.
    request = urllib.request.Request('https://api.hashvault.pro/v3/monero/'+path,
                                     headers={'User-Agent':'MoneroDesk/2.4','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=10) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:
        raise ValueError('Pool response too large')
    return json.loads(raw)


def parse_pool_data(public, wallet, payments, address, scope):
    units = Decimal(str(public['config']['sigDivisor']))
    if units != 10**12:
        raise ValueError('Unexpected XMR units')
    pool = public['pool_statistics'][scope]
    miner = wallet.get(scope,{}) if wallet else {}
    revenue = wallet.get('revenue',{}) if wallet else {}
    # Average 1h numerator and denominator, or current/current if missing.
    average = 'avg1hashRate' in pool and 'avg1hashRate' in miner
    field = 'avg1hashRate' if average else 'hashRate'
    def number(source,key):
        value = source.get(key)
        if value is None or isinstance(value,bool):
            return None
        value = Decimal(str(value))
        if not value.is_finite() or value<0:
            raise ValueError('Invalid pool statistic: '+key)
        return value
    pool_hash = number(pool,field)
    your_hash = number(miner,field)
    share = your_hash/pool_hash*100 if your_hash is not None and pool_hash and pool_hash>0 else None
    network = public.get('network_statistics',{})
    difficulty = number(network,'difficulty')
    target = number(public['config'],'coinDiffTarget')
    network_hash = difficulty/target if difficulty and target else None
    pool_network = pool_hash/network_hash*100 if pool_hash is not None and network_hash else None
    amounts = {key:number(revenue,key) for key in ('confirmedBalance','totalPaid','dailyCredited','payoutThreshold')}
    pending = revenue.get('unconfirmedBalance')
    pending_atomic = None
    if isinstance(pending,dict) and all(isinstance(pending.get(k),dict) and 'total' in pending[k] for k in ('collective','solo')):
        pending_atomic = sum(number(pending[k],'total') for k in ('collective','solo'))
    parsed_payments = []
    if isinstance(payments,list):
        for payment in payments[:25]:
            # Explicitly discard transaction keys and unrelated response fields.
            amount = number(payment,'amount')
            fee = number(payment,'paidFee')
            parsed_payments.append({'time':datetime.fromtimestamp(int(payment['ts'])).strftime('%Y-%m-%d %H:%M:%S'),
                                    'amount':str(amount/units) if amount is not None else None,
                                    'fee':str(fee/units) if fee is not None else None,'txid':str(payment.get('txnHash',''))})
    found = wallet is not None and any((number(miner,'totalHashes') or 0,amounts['totalPaid'] or 0,amounts['confirmedBalance'] or 0))
    return {'provider':'HashVault','address':address,'scope':scope,'checked':time.strftime('%Y-%m-%d %H:%M:%S'),
            'pool_hash':pool_hash,'your_hash':your_hash,'window':'1h' if average else 'current','share':share,
            'pool_network':pool_network,'confirmed':amounts['confirmedBalance']/units if amounts['confirmedBalance'] is not None else None,
            'pending':pending_atomic/units if pending_atomic is not None else None,
            'paid':amounts['totalPaid']/units if amounts['totalPaid'] is not None else None,
            'daily':amounts['dailyCredited']/units if amounts['dailyCredited'] is not None else None,
            'threshold':amounts['payoutThreshold']/units if amounts['payoutThreshold'] is not None else None,
            'fee':number(public['config'],'pplns_fee') if scope=='collective' else None,
            'valid':number(miner,'validShares'),'invalid':number(miner,'invalidShares'),
            'history_found':bool(found),'payments':parsed_payments}


def fetch_pool_data(address, scope):
    if not valid_wallet(address) or scope not in ('collective','solo'):
        raise ValueError('Invalid XMR address or pool mode')
    paths = ['pool/stats','wallet/'+address+'/stats?workers=false&chart=false','wallet/'+address+'/payments']
    results = []
    errors = []
    def read(path):
        try:
            return pool_json(path),None
        except Exception as exc:
            # Do not echo a wallet-bearing request URL or the raw response.
            return None,type(exc).__name__
    with ThreadPoolExecutor(max_workers=3) as executor:
        for value,error in executor.map(read,paths):
            results.append(value)
            errors.append(error)
    if results[0] is None:
        raise ValueError('矿池公共 API 不可用 / Pool API unavailable: '+str(errors[0]))
    result = parse_pool_data(*results,address,scope)
    result['errors'] = {key:error for key,error in zip(('pool','wallet','payments'),errors) if error}
    return result


LANGUAGES = {'中文':'zh','English':'en','Español':'es','Français':'fr','Deutsch':'de','Português':'pt','Русский':'ru','العربية':'ar','हिन्दी':'hi','日本語':'ja','한국어':'ko','Italiano':'it','Türkçe':'tr','Bahasa Indonesia':'id','Tiếng Việt':'vi','ไทย':'th','Polski':'pl','Nederlands':'nl','Українська':'uk','বাংলা':'bn'}

FLAG_COUNTRIES = dict(zip(LANGUAGES.values(),['cn','gb','es','fr','de','pt','ru','sa','in','jp','kr','it','tr','id','vn','th','pl','nl','ua','bd']))

def system_language_name(locale_name=None):
    if locale_name is None:
        try:
            buffer=ctypes.create_unicode_buffer(85)
            ui_language=ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if not ctypes.windll.kernel32.LCIDToLocaleName(ui_language,buffer,len(buffer),0):
                raise OSError('Locale unavailable')
            locale_name=buffer.value
        except (OSError,AttributeError):
            import locale
            locale_name=locale.getlocale()[0] or 'en'
    code=locale_name.replace('_','-').split('-')[0].lower()
    return next((name for name,value in LANGUAGES.items() if value==code),'English')

UI_EN = dict(all_cpu='All CPU: {n} threads', recommended_cpu='Recommended: {n} threads', cpu_detected='Detected device: {cpu} · {physical} physical cores / {logical} logical threads · recommendation considers physical cores and L3 cache.', all_warning='All threads do not guarantee 100% usage or best hashrate.', select_pool='Select mining pool', pool_details='{provider} · pool fee {fee}% · TLS · payout network fees separate.', pool_support='Live account data follows the selected pool. Opening this tab sends the public query address to that provider. No private keys are needed.', loading='Loading…', unavailable='Unavailable', pool_rate_live='Pool-side hashrate', your_share='Your pool share', network_pool='Pool network share', confirmed_due='Confirmed unpaid', pending_money='Pending', paid_total='Total paid', credited_daily='Daily credited', threshold_live='Account payout threshold', fee_live='Pool fee', shares_live='Valid / invalid shares', remaining_live='Remaining to threshold', payout_timing='Reaching the threshold does not guarantee immediate payment.', partial_api='Partial API errors', query_only='Query only; current mining target is different.', query_prompt='Enter a payout address and click Query.', invalid_address='Enter a valid mainnet XMR address.', unsupported_pool='No supported pool selected. Choose HashVault or MoneroOcean on the Mining page.', scope_info='collective = PPLNS; solo = pool solo', not_provided='Not provided', manual_value='manual input', solo_pool_na='Pool share: N/A (solo)', block_wait='Expected block wait: {n} days', allocation_label='Runtime allocation: {n}%', chain_first='Refresh chain data first.', unsynced='Node is not synchronized.', hash_first='Enter your hashrate or run the miner first.', running_mode='Running mode', blocks_unlock='Blocks to unlock', language_map='World language map', map_note='Language selection · schematic world map; languages are used across multiple regions.', time_heading='Time', amount_heading='XMR (API amount)', fee_heading='XMR fee', transaction_heading='Transaction hash', height_heading='Height', reward_heading='XMR reward', hash_heading='Block hash', mo_basis='MoneroOcean raw/pay hashrates use different bases; share and network share are unavailable until matching units are verified. Account threshold and daily credit are unavailable through this endpoint.', selected_provider='Selected pool', api_failed='Pool API unavailable', failure='Failed', price_failed='Price not updated', wallet_failed='Wallet not read', detected_refresh='Re-detect hardware', cpu_mode='CPU mode', custom_cpu='Custom threads')
UI_ZH = dict(zip(UI_EN, ['全部 CPU：{n} 线程','推荐：{n} 线程','检测设备：{cpu} · {physical} 物理核心 / {logical} 逻辑线程 · 推荐值结合物理核心及 L3 缓存计算。','全部线程不保证持续 100% 占用或最高算力。','一键选择矿池','{provider} · 矿池费 {fee}% · TLS · 付款网络费另计。','实况跟随主页所选矿池。打开此页会向该矿池发送公开查询地址，无需私钥。','正在读取…','未提供','矿池侧算力','你的矿池算力占比','矿池占全网','已确认未支付','待确认','累计已付','每日入账','账户付款门槛','矿池费','有效 / 无效份额','距付款门槛','达到门槛不保证立即支付。','部分接口读取失败','仅查询；当前正在挖矿的目标不同。','填写收款地址并点击查询。','请填写有效的主网门罗币地址。','尚未选择支持的矿池，请在主页选择 HashVault 或 MoneroOcean。','collective = PPLNS；solo = 矿池独挖','未填写','手工输入','矿池占比：不适用（独挖）','理论平均等待：{n} 天','挖矿时间分配：{n}%','请先刷新节点区块。','节点尚未同步。','请填写本机算力或先运行矿工。','正在运行的模式','待解锁区块数','世界语言地图','语言选择 · 示意地图；一种语言可用于多个地区。','时间','XMR（接口金额）','XMR 手续费','交易哈希','高度','XMR 区块奖励','区块哈希','MoneroOcean 原始与支付算力口径不同，尚未验证相同单位，暂不计算占比。该接口不提供账户付款门槛及每日入账。','所选矿池','矿池接口不可用','读取失败','价格未更新','钱包未读取','重新检测硬件','CPU 模式','自定义线程']))
TEXT['en'].update(UI_EN)
TEXT['zh'].update(UI_ZH)

TEXT['en'].update(cpu_percent='CPU thread allocation (%)',cpu_allocation='{percent}% → {used} / {logical} threads',
    system_language='Follow system language',pool_offline='Cannot connect to the selected pool API. Check the network or retry later.',
    switch_pool='Switch pool and continue mining',switching='Connecting to new pool…',switched='New pool job received',switch_failed='Pool switch timed out; previous pool restored',start_first='Start mining before switching a running miner.',
    energy='Power & electricity',power_refresh='Read power sensors',power_now='CPU package power (sensor)',power_measured='Recorded CPU energy (kWh)',power_estimated='Estimated whole-device energy (kWh)',manual_watts='Whole-device watts (manual estimate)',tariff='Electricity price per kWh (optional)',energy_cost='Estimated electricity cost',energy_unknown='No compatible power sensor is available. Plugged-in Windows devices do not normally expose wall-socket power.',energy_note='CPU energy covers the CPU package only, not the whole computer. Missing samples are excluded. Whole-device energy uses your manually entered watts while this miner runs; 1 kWh = 1000 W × 1 hour. Values exclude earlier sessions before this feature. Use a wall meter for billed electricity.',energy_sampled='Measured duration: {seconds} seconds',power_source='Sensor source',energy_invalid='Enter positive watts and a nonnegative electricity price.',energy_manual_source='Manual whole-device estimate')
TEXT['zh'].update(cpu_percent='CPU 线程分配比例（%）',cpu_allocation='{percent}% → {used} / {logical} 线程',system_language='跟随本机系统语言',pool_offline='无法连接所选矿池的查询接口，请检查网络或稍后重试。',switch_pool='切换矿池并继续挖矿',switching='正在连接新矿池…',switched='已收到新矿池任务，切换成功',switch_failed='切换超时，已恢复原矿池',start_first='请先启动矿工，再进行运行中切换。',energy='功率与用电',power_refresh='读取功率传感器',power_now='CPU 封装功率（传感器）',power_measured='累计实测 CPU 用电（度）',power_estimated='累计估算整机用电（度）',manual_watts='整机功率瓦数（手动估算）',tariff='每度电单价（可选）',energy_cost='估算电费',energy_unknown='当前没有可用功率传感器。接电源时 Windows 通常不能直接读取插座功率。',energy_note='CPU 用电只含处理器，不代表整机；缺失采样不计入。整机估算使用你手填的瓦数，按本程序挖矿时间累计；1 度电 = 1000 瓦运行 1 小时。本功能上线前的运行时间不追算。实际电费以插座电表为准。',energy_sampled='有效实测时间：{seconds} 秒',power_source='传感器来源',energy_invalid='请填写正数瓦数及非负电价。',energy_manual_source='手动估算整机')

def read_power_sensor():
    if not IS_WINDOWS:
        return {"watts":None,"source":"","scope":"whole","time":time.monotonic(),"request_status":"unavailable"}
    # Read existing monitoring providers only. Never install a driver or alter privileges.
    command="""$ErrorActionPreference='SilentlyContinue'; $meters=@(); $whole=@(); $meterStatus='ok'; try { $whole=@(Get-CimInstance -Namespace root/cimv2/power -ClassName Win32_PowerMeter -ErrorAction Stop) } catch { if($_.Exception.StatusCode -eq 2){$meterStatus='access_denied'}else{$meterStatus='unavailable'} }; foreach($meter in $whole) { $system=@(Get-CimAssociatedInstance -InputObject $meter -ResultClassName Win32_ComputerSystem -ErrorAction SilentlyContinue); $meters+=@{system_associated=($system.Count -gt 0);reading=$meter.CurrentReading;unit_modifier=$meter.UnitModifier;base_units=$meter.BaseUnits;meter_type=$meter.MeterType;id=$meter.DeviceID} }; $cpu=$null; foreach($ns in @('root/LibreHardwareMonitor','root/OpenHardwareMonitor')) { $sensor=Get-CimInstance -Namespace $ns -ClassName Sensor -ErrorAction SilentlyContinue | Where-Object { $_.SensorType -eq 'Power' -and $_.Name -eq 'CPU Package' } | Select-Object -First 1; if($sensor) { $cpu=@{watts=[double]$sensor.Value;source=$ns;scope='cpu'}; break } }; @{meters=$meters;cpu=$cpu;meter_status=$meterStatus} | ConvertTo-Json -Depth 4 -Compress"""
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,timeout=12,creationflags=NO_WINDOW)
    if result.returncode: raise ValueError('Power sensor unavailable')
    value=json.loads(result.stdout.decode('utf-8-sig'))
    for meter in value.get('meters',[]):
        watts=valid_whole_meter(meter)
        if watts is not None:
            return {'watts':watts,'source':'Win32_PowerMeter:'+str(meter.get('id','')),'scope':'whole','time':time.monotonic(),'request_status':'ok'}
    cpu=value.get('cpu') or {}
    watts=cpu.get('watts')
    if watts is not None and (not math.isfinite(float(watts)) or not 0<float(watts)<=2000):
        watts=None
    return {'watts':float(watts) if watts is not None else None,'source':str(cpu.get('source','')),'scope':'cpu','time':time.monotonic(),'request_status':value.get('meter_status','unavailable')}


def integrate_power(previous,current):
    if previous is None or current is None or previous.get('watts') is None or current.get('watts') is None or previous.get('source')!=current.get('source') or previous.get('scope')!=current.get('scope'):
        return 0.0,0.0
    seconds=current['time']-previous['time']
    if not 0<seconds<=30:
        return 0.0,0.0
    return (previous['watts']+current['watts'])/2*seconds/3600000,seconds


TEXT['en'].update(pool_paused='The pool temporarily suspended this public IP. Automatic reconnect has stopped. Wait for the pool cooldown; this does not remove the pool restriction.',pool_cooldown='This pool is cooling down. Retry after {minutes} minute(s).',pool_paused_restored='The new pool suspended this IP. The previous pool configuration was restored.',whole_power='Whole-computer power (hardware meter)',whole_energy='Recorded whole-computer energy (kWh)',whole_time='Whole-computer measured duration: {seconds} seconds',whole_unavailable='No verified whole-computer watt reading is available. A zero reading with missing units/capabilities is not treated as zero consumption. CPU power is separate. An external electricity meter is needed if the hardware cannot report whole-computer power.',whole_cost='Measured whole-computer electricity cost')
TEXT['zh'].update(pool_paused='矿池临时暂停了当前公网 IP，已停止自动重连。请等待矿池冷却，本程序不能解除矿池限制。',pool_cooldown='该矿池正在冷却，请在 {minutes} 分钟后重试。',pool_paused_restored='新矿池暂停了当前 IP，已恢复原矿池连接配置。',whole_power='整机实时功率（硬件电表）',whole_energy='累计实测整机用电（度）',whole_time='整机有效实测时长：{seconds} 秒',whole_unavailable='目前没有经过验证的整机瓦数。缺少单位和能力信息的零读数不代表零耗电。CPU 功率单独显示；硬件无法提供整机功率时，需使用外接电表读取实际用电。',whole_cost='实测整机电费')

def cooldown_key(endpoint):
    return endpoint.lower().strip().rsplit(':',1)[0]

def valid_whole_meter(value):
    if not isinstance(value,dict) or not value.get('system_associated') or value.get('unit_modifier') is None or value.get('base_units') is None or value.get('meter_type')!=0:
        return None
    try:
        modifier=int(value['unit_modifier'])
        if not -6<=modifier<=6: return None
        watts=float(value['reading'])*10**modifier
        return watts if math.isfinite(watts) and 0<watts<=10000 else None
    except (TypeError,ValueError,OverflowError):
        return None


TEXT['en'].update(automatic_power_note='Whole-computer power is detected automatically and integrated into kWh while this app is open. No manual watt input is used. Only valid hardware-meter samples count. If the computer cannot report whole-system power, actual electricity use is unavailable.',connecting_pool='Connecting to mining pool…',reconnecting_pool='Mining connection lost; reconnecting…',waiting_shares='Pool job received; waiting for accepted shares',accepted_live='Mining: accepted shares received',connection_help='Check the Activity tab for the actual connection error. Pool API statistics and the mining connection are separate services.')
TEXT['zh'].update(automatic_power_note='自动检测整机功率，程序打开期间累计有效采样的用电度数，无需手填瓦数。只计算硬件电表的有效读数；本机无法提供整机功率时，实际耗电显示未提供。',connecting_pool='正在连接矿池…',reconnecting_pool='挖矿连接已断开，正在重连…',waiting_shares='已收到矿池任务，等待有效份额',accepted_live='正在挖矿：已收到有效份额',connection_help='运行日志会显示实际连接错误。矿池统计接口与挖矿连接是两个不同的服务。')
TEXT['en'].update(share='Allocate minute 20:00–20:59 of every 100 runtime minutes to the specified address (optional)',split='Every 100 accumulated runtime minutes: main address for 99 minutes, specified address from 20:00 up to 21:00 for 1 minute (1%). This allocates mining time, not an exact coin transfer. Each pool address has its own payout threshold. A new schedule starts at zero on this upgrade; pauses do not advance it, and restarts resume the saved runtime.')
TEXT['zh'].update(share='每累计运行100分钟，从第20分钟起分配1分钟给指定地址（可取消）',split='每累计运行100分钟：主地址99分钟，指定地址在20:00至21:00之间挖1分钟，时间占比1%。这是分配挖矿时间，并非精确币数转账；矿池各地址分别达到门槛后付款。本次升级从新周期0分钟开始，停止时暂停计时，重启后续计。')

def allocation_active(seconds,enabled=True):
    return bool(enabled and 1200 <= seconds % 6000 < 1260)

TEXT['zh'].update(share='每100分钟，仅第20:00至21:00这1分钟分配给作者（可取消）',owner='作者收款地址（完整公开）',split='首次启动累计运行到20:00立即给作者挖1分钟，21:00切回主地址。之后在120:00–121:00、220:00–221:00依次重复，即每100分钟给作者1分钟（1%），其余时间给主地址。停止时暂停计时，正常重启继续累计。切换会重连矿池，可能延迟或失败；这是时间分配，不是自动转账或到账保证。',author_role='作者地址',main_role='主收款地址',author_timer='累计运行 {elapsed}；当前计划：{role}；距下次切换 {seconds} 秒。',same_author='主地址与作者地址相同：定时分配不会改变实际收款账户。')
TEXT['en'].update(share='Every 100 minutes, allocate only 20:00–21:00 to the author (optional)',owner='Author payout address (fully visible)',split='At the first 20:00 of accumulated runtime, mine for the author for 1 minute; return to the main address at 21:00. Repeat at 120:00–121:00, 220:00–221:00, and so on: 1 author minute per 100 minutes (1%). Pauses stop the clock; normal restarts resume it. Account switches reconnect to the pool and may be delayed or fail. This is time allocation, not a transfer or guaranteed payout.',author_role='author address',main_role='main address',author_timer='Runtime {elapsed}; scheduled recipient: {role}; next switch in {seconds} seconds.',same_author='Main and author addresses are identical: scheduled allocation does not change the actual payout account.')
TEXT['zh'].update(pool_support='实况按实际运行的矿池和主收款地址查询。运行中选择新矿池会先停止旧矿工，确认退出，再自动启动新矿工。旧统计会清空，连接成功需收到新矿池任务；接口请求失败会单独显示。',switching='旧矿工已停止，正在启动新矿池…',switch_failed='新矿池未在时限内收到任务，已停止；请检查日志后重试。')
TEXT['en'].update(pool_support='Live data follows the actual running pool and main payout address. Selecting a pool while mining stops the old miner, waits for exit, then starts a new miner automatically. Old statistics are cleared. A new pool job confirms connection; API failures are shown separately.',switching='Old miner stopped; starting new pool…',switch_failed='The new pool did not supply a job in time. Mining stopped; check Activity before retrying.')
TEXT['zh'].update(power_refresh='向系统请求功率读数',power_request_loading='正在向 Windows 整机电表接口发送读取请求…',power_request_ok='读取成功：系统已返回有效整机瓦数。',power_request_denied='系统拒绝访问功率接口；本程序未自动提升权限。',power_request_invalid='读取请求已完成，但系统接口没有提供有效的整机瓦数。',power_request_failed='本次读取请求未完成，将稍后自动重试。')
TEXT['en'].update(power_refresh='Request power reading from Windows',power_request_loading='Requesting a reading from the Windows whole-computer meter…',power_request_ok='Reading succeeded: valid whole-computer watts received.',power_request_denied='Windows denied access to the power interface. This app has not elevated privileges.',power_request_invalid='The reading request completed, but no valid whole-computer watts were provided.',power_request_failed='The reading request did not complete. It will be retried later.')

TEXT['zh'].update(details='使用说明与注意事项',allocation_summary='作者时间：20:00–21:00、120:00–121:00… 每100分钟1分钟（1%）；其余给主地址。',pool_selection_note='运行中选矿池将自动停止旧矿工并启动新配置；实况跟随实际运行目标。',pool_payment_note='收益以矿池确认的有效份额和付款门槛为准；本机算力不等于已到账收益。')
TEXT['en'].update(details='Usage notes',allocation_summary='Author window: 20:00–21:00, 120:00–121:00… One minute per 100 minutes (1%); main address otherwise.',pool_selection_note='Selecting a pool while mining stops the old miner and starts the new configuration. Live data follows the running target.',pool_payment_note='Earnings depend on pool-accepted shares and payout thresholds. Local hashrate is not a credited balance.')
TEXT['zh'].update({'pool_overview': '多个矿池收益', 'refresh_pools': '刷新全部矿池', 'overview_note': '按主收款地址查询各矿池；不同矿池余额分别结算，不能合并提现。已确认累计收益＝累计已支付＋已确认未支付，不含待确认金额。', 'pool_earned': '已确认累计收益', 'pool_value': '未支付参考价值', 'pool_minimum': '矿池允许的最低付款额', 'payout_adjust': '调整自动付款金额', 'payout_use_min': '使用矿池最低值', 'payout_save': '保存到矿池并核验', 'payout_note': '这是自动付款门槛，不是立即提现。达到门槛后由矿池安排支付；最低门槛可能产生更高的相对手续费。', 'payout_target': '设置目标', 'payout_input': '自动付款门槛（XMR）', 'payout_saved': '已重新读取，矿池门槛与提交值一致。', 'payout_failed': '未能确认修改成功，请刷新或到矿池官网核对。', 'payout_invalid': '请输入不低于矿池最低值的有效 XMR 金额（最多12位小数）。', 'payout_unavailable': '矿池未返回有效政策或账户门槛，暂不能直接修改。', 'payout_website': '打开矿池官方设置', 'payout_fee': '预计单次付款手续费', 'payout_fee_unknown': '付款手续费：接口未提供有效公式，请在矿池官网核对。', 'overview_address': '汇总收款地址', 'payout_verifying': '正在提交并重新读取矿池设置…', 'overview_partial': '部分数据不可用；未提供不代表零余额。', 'wallet_section': '本机钱包（可选）'})
TEXT['en'].update({'pool_overview': 'Multiple pool earnings', 'refresh_pools': 'Refresh all pools', 'overview_note': 'Queries each pool for the main payout address. Pools settle separately; balances cannot be combined for payout. Total confirmed earnings = total paid + confirmed unpaid, excluding pending amounts.', 'pool_earned': 'Total confirmed earnings', 'pool_value': 'Unpaid reference value', 'pool_minimum': 'Pool minimum payout', 'payout_adjust': 'Adjust automatic payout amount', 'payout_use_min': 'Use pool minimum', 'payout_save': 'Save to pool and verify', 'payout_note': 'This sets an automatic payout threshold, not an immediate withdrawal. The pool schedules payment after the threshold is reached. Lower thresholds may have higher relative fees.', 'payout_target': 'Settings target', 'payout_input': 'Automatic payout threshold (XMR)', 'payout_saved': 'Read-back confirmed: the pool threshold matches the submitted value.', 'payout_failed': 'The update could not be verified. Refresh or check the official pool website.', 'payout_invalid': 'Enter a valid XMR amount at or above the pool minimum, with at most 12 decimal places.', 'payout_unavailable': 'Valid pool policy or account threshold was not returned. Direct changes are unavailable.', 'payout_website': 'Open official pool settings', 'payout_fee': 'Estimated fee per payment', 'payout_fee_unknown': 'Payment fee: no valid formula returned. Check the official pool website.', 'overview_address': 'Overview payout address', 'payout_verifying': 'Submitting and reading back pool settings…', 'overview_partial': 'Some data is unavailable. Missing data does not mean zero balance.', 'wallet_section': 'Local wallet (optional)'})
TEXT['zh']['mo_basis']='MoneroOcean 原始与支付算力口径不同，暂不计算占比；账户付款门槛单独读取。'
TEXT['en']['mo_basis']='MoneroOcean raw and pay hashrates use different bases; shares are withheld. Account payout settings are queried separately.'
LOCALE_DIR = Path(getattr(sys,'_MEIPASS',BASE))/'locales'
for language_code in LANGUAGES.values():
    if language_code not in TEXT:
        try:
            TEXT[language_code] = json.loads((LOCALE_DIR/(language_code+'.json')).read_text(encoding='utf-8'))
        except (OSError,ValueError):
            TEXT[language_code] = dict(TEXT['en'])

TEXT['en'].update(tls_connected='TLS verified · logging in',preparing_dataset='Connected · preparing RandomX memory')
TEXT['zh'].update(tls_connected='TLS 加密已验证 · 正在登录矿池',preparing_dataset='已连接矿池 · 正在准备 RandomX 内存')

for _locale in TEXT.values():
    _locale['title']='XMR'

def check_pool_transport(endpoint,tls):
    if not tls:
        raise ValueError('必须启用 TLS 加密连接。 / Verified TLS is required for pool mining.')
    import re
    if not re.fullmatch(r'[A-Za-z0-9.-]+:[0-9]{1,5}',endpoint) or not 1<=int(endpoint.rsplit(':',1)[1])<=65535:
        raise ValueError('地址格式应为 host:port / Expected host:port')
    # The engine performs the verified TLS handshake once, with same-pool
    # encrypted endpoint retries. Do not block startup on a duplicate handshake.


# XMR_TLS_TRANSPORT_LABELS
TEXT['en']['transport_tls']='TLS / pinned certificate verified'
TEXT['zh']['transport_tls']='TLS / 固定证书校验'

# XMR_CONNECTION_UI_V2
TEXT['zh']['engine_failed']='启动或运行失败，请查看运行日志；连接超时可手动选择其他矿池'
TEXT['en']['engine_failed']='Start/run failed; see Activity. For a timeout, retry or select another pool.'

def detected_threads(device,profile,current=1):
    if profile.startswith('percent:'):
        percent=max(1,min(100,float(profile.split(':',1)[1])))
        return max(1,min(device['logical'],int(device['logical']*percent/100)))
    if profile=='all':
        return device['logical']
    if profile=='recommended':
        return device['recommended']
    if profile=='half':
        return max(1,device['logical']//2)
    return max(1,min(device['logical'],current))

def recommend_threads(physical,logical,l3_bytes):
    """Choose a cache-aware starting point while allowing some SMT workers.

    Capping strictly at physical cores left measured RandomX throughput lower
    on the 16-core/32-thread 8940HX; using every SMT thread was also slower.
    Start with cache-supported physical workers plus half the SMT siblings.
    This remains a starting point, not a guarantee for thermally constrained CPUs.
    """
    physical=max(1,int(physical));logical=max(1,int(logical))
    cache_limit=(int(l3_bytes)//(2*1024**2)) if l3_bytes else physical
    primary=min(physical,cache_limit)
    smt_extra=max(0,logical-physical)//2
    return max(1,min(logical,primary+smt_extra))

def provider_for(endpoint):
    if endpoint.lower() in ('gulf.moneroocean.stream:20001','gulf.moneroocean.stream:20128','gulf.moneroocean.stream:443'):
        return 'MoneroOcean'
    return next((pool['name'] for pool in POOL_PRESETS if pool['endpoint'].lower()==endpoint.strip().lower()),None)


def mo_json(path):
    req=urllib.request.Request('https://api.moneroocean.stream/'+path,headers={'User-Agent':'MoneroDesk/2.6','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:
        raw=response.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:
        raise ValueError('Pool response too large')
    result=json.loads(raw)
    if isinstance(result,dict) and result.get('error'):
        raise ValueError('Pool API error')
    return result

def parse_mo_data(public,wallet,payments,config,address):
    def number(obj,key):
        value=obj.get(key) if isinstance(obj,dict) else None
        if value is None or isinstance(value,bool):
            return None
        value=Decimal(str(value))
        if not value.is_finite() or value<0:
            raise ValueError('Invalid pool statistic')
        return value
    units=number(config,'sigDivisor')
    if units is not None and units!=10**12:
        raise ValueError('Unexpected XMR units')
    units=Decimal(10**12)
    due,paid=number(wallet,'amtDue'),number(wallet,'amtPaid')
    result={'provider':'MoneroOcean','scope':'collective','address':address,'checked':time.strftime('%Y-%m-%d %H:%M:%S'),
        'pool_hash':number(public.get('pool_statistics',{}),'hashRate'),'your_hash':number(wallet,'hash'),'window':'API raw',
        'share':None,'pool_network':None,'confirmed':due/units if due is not None else None,'paid':paid/units if paid is not None else None,
        'pending':None,'daily':None,'threshold':None,'fee':number(config,'pplns_fee'),'valid':number(wallet,'validShares'),
        'invalid':number(wallet,'invalidShares'),'history_found':bool((number(wallet,'totalHashes') or 0) or due or paid),'payments':[]}
    if isinstance(payments,list):
        for payment in payments[:25]:
            amount=number(payment,'amount')
            result['payments'].append({'time':datetime.fromtimestamp(int(payment['ts'])).strftime('%Y-%m-%d %H:%M:%S'),
                'amount':str(amount/units) if amount is not None else None,'fee':None,'txid':str(payment.get('txnHash',''))})
    return result

def _fetch_selected_pool_stats(provider,address,scope):
    if provider=='HashVault':
        return fetch_pool_data(address,scope)
    if provider!='MoneroOcean' or not valid_wallet(address) or scope!='collective':
        raise ValueError('Unsupported pool, address or accounting mode')
    paths=['pool/stats','miner/'+address+'/stats','miner/'+address+'/payments','config']
    def read(path):
        try:
            return mo_json(path),None
        except Exception as exc:
            return None,type(exc).__name__
    with ThreadPoolExecutor(max_workers=4) as executor:
        values=list(executor.map(read,paths))
    if values[0][0] is None:
        raise ValueError('Pool API unavailable: '+str(values[0][1]))
    result=parse_mo_data(values[0][0],values[1][0],values[2][0],values[3][0],address)
    result['errors']={key:error for key,(_,error) in zip(('pool','wallet','payments','config'),values) if error}
    return result



def payout_decimal(value, positive=False):
    if value is None or isinstance(value,bool): return None
    try:
        number=Decimal(str(value))
        return number if number.is_finite() and (number>0 if positive else number>=0) else None
    except Exception: return None


def fetch_payout_settings(provider,address):
    if not valid_wallet(address): raise ValueError('Invalid XMR address')
    if provider=='HashVault':
        public=pool_json('pool/stats')
        account=pool_json('wallet/'+address+'/private/threshold')
        config=public.get('config',{})
        units=payout_decimal(config.get('sigDivisor'),True)
        if units!=10**12: raise ValueError('Unexpected XMR units')
        minimum=payout_decimal(config.get('payout',{}).get('minimum'),True)
        threshold=payout_decimal(account.get('threshold'),True)
        return dict(minimum=minimum/units if minimum else None,threshold=threshold/units if threshold else None,policy=None)
    if provider!='MoneroOcean': raise ValueError('Unsupported pool')
    config=mo_json('config'); account=mo_json('user/'+address)
    policy=config.get('payout_policy') or config.get('payoutPolicy') or {}
    minimum=payout_decimal(policy.get('minimumThreshold'),True)
    default=payout_decimal(policy.get('defaultThreshold'),True)
    denomination=payout_decimal(policy.get('denomination'),True)
    raw=payout_decimal(account.get('payout_threshold'))
    # Match the official frontend: >1 uses atomic units, <=1 uses XMR.
    threshold=(raw/Decimal(10**12) if raw>1 else raw) if raw else default
    return dict(minimum=minimum,threshold=threshold,policy=policy if minimum and default and denomination else None)


def fetch_selected_pool(provider,address,scope):
    with ThreadPoolExecutor(max_workers=2) as executor:
        stats=executor.submit(_fetch_selected_pool_stats,provider,address,scope)
        settings=executor.submit(fetch_payout_settings,provider,address)
        result=stats.result()
        try:
            payout=settings.result()
            result['minimum']=payout['minimum']; result['payout_policy']=payout['policy']
            if payout['threshold'] is not None: result['threshold']=payout['threshold']
        except Exception as exc:
            result.setdefault('errors',{})['payout']=type(exc).__name__
    return result


def payout_fee_estimate(value,policy):
    if not isinstance(policy,dict): return None
    formula=policy.get('feeFormula') or {}
    minimum=payout_decimal(policy.get('minimumThreshold'),True)
    maximum=payout_decimal(formula.get('maxFee'))
    zero=payout_decimal(formula.get('zeroFeeThreshold'),True)
    if minimum is None or maximum is None or zero is None: return None
    if zero<=minimum: return Decimal(0) if value>=zero else maximum
    return min(maximum,max(Decimal(0),maximum-(value-minimum)*maximum/(zero-minimum)))


def set_payout_threshold(provider,address,value):
    # Re-read current provider policy before writing. No wallet transfer or private key.
    settings=fetch_payout_settings(provider,address)
    minimum=settings.get('minimum')
    value=payout_decimal(value,True)
    if value is None or minimum is None or settings.get('threshold') is None or value<minimum or value*10**12!=(value*10**12).to_integral_value():
        raise ValueError('Invalid or unavailable payout threshold')
    if provider=='MoneroOcean':
        if not settings.get('policy'): raise ValueError('Payout policy unavailable')
        url='https://api.moneroocean.stream/user/updateThreshold'
        payload={'username':address,'threshold':float(value)}
    elif provider=='HashVault':
        url='https://api.hashvault.pro/v3/monero/wallet/'+address+'/private/threshold'
        payload={'threshold':int(value*10**12)}
    else: raise ValueError('Unsupported pool')
    request=urllib.request.Request(url,data=json.dumps(payload).encode('utf8'),headers={'Content-Type':'application/json','Accept':'application/json','User-Agent':'MoneroDesk/2.7'},method='POST')
    with urllib.request.urlopen(request,timeout=15) as response:
        result=json.loads(response.read(65536))
    if not isinstance(result,dict) or result.get('error') or result.get('success') is False:
        raise ValueError('Pool rejected threshold change')
    # Never claim success from HTTP 200 alone.
    verified=fetch_payout_settings(provider,address)
    if verified.get('threshold')!=value: raise ValueError('Threshold read-back mismatch')
    return verified


def valid_wallet(address):
    if len(address) != 95:
        return False
    try:
        raw = b''
        for start in range(0, 95, 11):
            part = address[start:start + 11]
            number = 0
            for char in part:
                number = number * 58 + ALPHABET.index(char)
            raw += number.to_bytes(8 if len(part) == 11 else 5, 'big')
        return raw[0] in (18, 42) and keccak.new(digest_bits=256, data=raw[:-4]).digest()[:4] == raw[-4:]
    except (ValueError, OverflowError):
        return False


def hardware():
    result = {'cpu':os.environ.get('PROCESSOR_IDENTIFIER', 'CPU'), 'physical':psutil.cpu_count(logical=False) or 1,
              'logical':psutil.cpu_count() or 1, 'l3':0, 'gpu':[]}
    try:
        if not IS_WINDOWS: raise OSError("Use native Linux hardware probe")
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            result['cpu'] = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        # SYSTEM_LOGICAL_PROCESSOR_INFORMATION has a pointer-sized mask,
        # a DWORD relationship, alignment, then a 16-byte union (x64).
        size = ctypes.c_ulong()
        ctypes.windll.kernel32.GetLogicalProcessorInformation(None, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if ctypes.windll.kernel32.GetLogicalProcessorInformation(buffer, ctypes.byref(size)):
            stride = 32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 24
            relation_offset = ctypes.sizeof(ctypes.c_void_p)
            union_offset = 16 if stride == 32 else 8
            for pos in range(0, size.value, stride):
                raw = buffer.raw[pos:pos+stride]
                if int.from_bytes(raw[relation_offset:relation_offset+4], 'little') == 2 and raw[union_offset] == 3:
                    result['l3'] += int.from_bytes(raw[union_offset+4:union_offset+8], 'little')
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Video') as video:
            for i in range(winreg.QueryInfoKey(video)[0]):
                try:
                    with winreg.OpenKey(video, winreg.EnumKey(video, i) + r'\0000') as key:
                        name = winreg.QueryValueEx(key, 'DriverDesc')[0]
                        if name not in result['gpu']:
                            result['gpu'].append(name)
                except OSError:
                    pass
    except OSError:
        pass
    if not IS_WINDOWS: result=linux_hardware(result)
    mem = psutil.virtual_memory()
    result.update(total=mem.total, available=mem.available)
    result['recommended'] = recommend_threads(result['physical'],result['logical'],result['l3'])
    return result



def parse_backend_rate(line):
    match=re.search(r'backend-rate (cpu|cuda|opencl) (n/a|[0-9]+(?:\.[0-9]+)?) H/s',line)
    if not match: return None
    return match[1],None if match[2]=='n/a' else float(match[2])

def verify_gpu_bundle(engine):
    manifest=json.loads((engine/'gpu-manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest.get('files',{}).items():
        file=engine/name
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
            raise ValueError('GPU plugin missing or damaged: '+name)
    if not manifest.get('files') or any(name not in manifest['files'] for name in cuda_files()):
        raise ValueError('GPU plugin manifest is incomplete')


TEXT['zh']['gpu_efficiency']='GPU 效率提示：门罗币 RandomX 更适合 CPU。CPU 与 GPU 同时挖矿可能因共享功耗、散热和内存带宽而降低 CPU 算力，总算力也可能下降。请比较稳定运行后的总算力与功耗，再决定是否开启 GPU。'
TEXT['en']['gpu_efficiency']='GPU efficiency: Monero RandomX favors CPUs. Running CPU and GPU together may reduce CPU hashrate through shared power, cooling and memory bandwidth; total hashrate can also fall. Compare steady total hashrate and power before enabling the GPU.'
TEXT['en'].update(cpu_rate='CPU hashrate (10s)',gpu_rate='GPU hashrate (10s)',backend_off='Disabled',gpu_enable='Enable GPU mining')
TEXT['zh'].update(cpu_rate='CPU 算力（10 秒）',gpu_rate='GPU 算力（10 秒）',backend_off='未启用',gpu_enable='启用 GPU 挖矿')
TEXT['en'].update(cpu_enable='Enable CPU mining',gpu_backend='GPU backend',gpu_help='Enable CPU and GPU separately. Backend labels match their actual device. Both share this pool, wallet and allocation schedule. Apply changes by stopping and restarting. GPU startup/errors appear in Activity.',gpu_invalid='Invalid GPU backend.',gpu_no_backend='Enable CPU or select a GPU backend.',gpu='Display adapters',tag='CPU + GPU mining · Visible fees · Manual control')
TEXT['zh'].update(cpu_enable='启用 CPU 挖矿',gpu_backend='GPU 挖矿后端',gpu_help='✓ 表示已启用。CPU、GPU 可独立开关，共用当前矿池、钱包和分成计划；修改后停止再启动。显卡启动结果和错误见运行日志。',gpu_invalid='GPU 后端无效。',gpu_no_backend='请启用 CPU 或选择 GPU 后端。',gpu='显示设备',tag='CPU + GPU 挖矿 · 公开费用 · 手动控制')

def make_config(mode, endpoint, wallet, threads, tls, gpu_backend="off", cpu_enabled=True):
    solo = mode in ('solo', 'remote')
    return {'autosave':False, 'watch':False, 'background':False, 'colors':False, 'print-time':10,
            'donate-level':0, 'donate-over-proxy':0, 'http':{'enabled':False},
            'randomx':{'mode':'auto', 'numa':True, 'rdmsr':False, 'wrmsr':False},
            'cpu':{'enabled':cpu_enabled, 'huge-pages':True, 'hw-aes':None, 'priority':1, 'yield':True,
                   'asm':True, 'rx':[-1]*threads, 'rx/0':[-1]*threads},
            'opencl':{'enabled':gpu_backend=='AMD OpenCL','cache':True,'platform':'AMD'},
            'cuda':{'enabled':gpu_backend=='NVIDIA CUDA','loader':str(BASE/'engine'/cuda_files()[0]),'nvml':True},
            # No credentials on disk: the engine uses its non-secret default "x".
            'pools':[{'coin':'monero', 'url':endpoint, 'user':wallet, 'daemon':solo,
                      'tls':bool(tls and mode != 'solo'), 'keepalive':not solo, 'daemon-poll-interval':1000}]}


def node_rpc(endpoint, tls=False, payload=None):
    if not re.fullmatch(r'[A-Za-z0-9.-]+:\d{1,5}', endpoint) or not 1<=int(endpoint.rsplit(':',1)[1])<=65535:
        raise ValueError('Invalid host:port')
    local = endpoint.split(':')[0] in ('127.0.0.1','localhost')
    url = ('https://' if tls else 'http://')+endpoint+('/json_rpc' if payload else '/get_info')
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                                 headers={'Content-Type':'application/json','User-Agent':'MoneroDesk/2.1'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if local else urllib.request.build_opener()
    with opener.open(req, timeout=7) as response:
        raw = response.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:
        raise ValueError('Node response too large')
    return json.loads(raw)


def check_public_node(node):
    begin = time.monotonic()
    info = node_rpc(node['endpoint'],node['tls'])
    if info.get('status') != 'OK' or not info.get('mainnet',info.get('nettype') == 'mainnet'):
        raise ValueError('Not an OK mainnet RPC node')
    if not info.get('synchronized') or info.get('busy_syncing') or info.get('offline'):
        raise ValueError('Node is not synchronized')
    return {'height':int(info['height']), 'ms':int((time.monotonic()-begin)*1000), 'checked':time.strftime('%H:%M:%S')}


def check_remote_mining(endpoint, tls, wallet):
    check_public_node({'endpoint':endpoint,'tls':tls})
    reply = node_rpc(endpoint,tls,{'jsonrpc':'2.0','id':'mining-check','method':'getblocktemplate',
                                'params':{'wallet_address':wallet,'reserve_size':8}})
    result = reply.get('result',{})
    if reply.get('error') or result.get('status') != 'OK' or not result.get('blocktemplate_blob'):
        raise ValueError('此节点不允许独挖 RPC，请换节点或使用本地节点。 / Mining RPC unavailable: '+str(reply.get('error',result.get('status','unsupported'))))


def check_local_node(endpoint):
    if not re.fullmatch(r'(127\.0\.0\.1|localhost):\d{1,5}', endpoint):
        raise ValueError('本地模式仅接受 127.0.0.1:端口 / Local mode requires 127.0.0.1:port')
    req = urllib.request.Request('http://' + endpoint + '/get_info', data=b'{}', headers={'Content-Type':'application/json'})
    # Do not forward local node calls through system HTTP proxies.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as response:
        info = json.load(response)
    if info.get('status') != 'OK' or not info.get('mainnet', info.get('nettype') == 'mainnet'):
        raise ValueError('需要主网节点 / A mainnet node is required')
    if info.get('offline') or not info.get('synchronized') or info.get('busy_syncing'):
        raise ValueError('节点尚未同步，请先在 GUI Wallet 启动并完成同步。 / Sync your local node first.')
    return info


class MinerJob:
    """Windows kills the owned miner if the UI process exits unexpectedly."""
    def __init__(self, process):
        class Limits(ctypes.Structure):
            _fields_ = [('process_time',ctypes.c_longlong),('job_time',ctypes.c_longlong),('flags',wintypes.DWORD),
                        ('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),('active',wintypes.DWORD),
                        ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(name,ctypes.c_ulonglong) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic',Limits),('io',IO),('process_mem',ctypes.c_size_t),('job_mem',ctypes.c_size_t),
                        ('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p,wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE,wintypes.HANDLE]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel = kernel
        self.handle = kernel.CreateJobObjectW(None,None)
        settings = Extended()
        settings.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not kernel.SetInformationJobObject(self.handle,9,ctypes.byref(settings),ctypes.sizeof(settings)) or not kernel.AssignProcessToJobObject(self.handle,wintypes.HANDLE(int(process._handle))):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error,'Cannot bind miner lifetime to application')

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


# XMR_LIVE_REPORTING_V1
for _locale in TEXT.values():
    for _rate_key in ('cpu_rate','gpu_rate'):
        if _rate_key in _locale:_locale[_rate_key]=_locale[_rate_key].replace('10','1')
TEXT['en'].update(connecting_dns='Resolving pool address',connecting_tcp='Connecting to pool TCP port',connecting_tls='Checking encrypted TLS connection',connection_retry='Connection timed out; retrying once')
TEXT['zh'].update(connecting_dns='正在解析矿池地址',connecting_tcp='正在连接矿池 TCP 端口',connecting_tls='正在建立并校验 TLS 加密连接',connection_retry='连接超时，正在重试一次')
TEXT['zh'].update(cpu_rate='CPU 算力（每秒刷新）',gpu_rate='GPU 算力（每秒刷新）')
TEXT['en'].update(cpu_rate='CPU hashrate (1s refresh)',gpu_rate='GPU hashrate (1s refresh)')
TEXT['zh'].update(reconnecting='连接中断，等待自动重连',connection_warning='保活回复延迟，正在检查矿池数据')
TEXT['en'].update(reconnecting='Disconnected; automatic reconnect pending',connection_warning='Keepalive reply delayed; monitoring pool traffic')
TEXT['zh']['connecting_proxy']='正在通过已启用的系统本地代理连接矿池'
TEXT['en']['connecting_proxy']='Connecting through enabled local system proxy'

class App:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.job = None
        self.events = queue.Queue()
        self.elapsed = 0.0
        self.total = 0.0
        self.allocation_elapsed = 0.0
        self.last = None
        self.lastsave = 0
        self.loglines = []
        self.phase = False
        self.checking = False
        self.generation = 0
        self.lang = tk.StringVar(value=system_language_name())
        self.language_manual = False
        self.wallet = tk.StringVar()
        self.mode = tk.StringVar(value='pool')
        self.node = tk.StringVar(value='127.0.0.1:18081')
        self.remote = tk.StringVar(value=PUBLIC_NODES[0]['endpoint'])
        self.node_checks = {}
        self.probing = set()
        self.market = None
        self.wallet_snapshot = None
        self.money_busy = set()
        self.money_error = ''
        self.wallet_endpoint = tk.StringVar(value='127.0.0.1:18082')
        self.rpc_user = tk.StringVar()
        self.rpc_password = tk.StringVar()
        self.chain = None
        self.chain_busy = False
        self.chain_message = ''
        self.stats_hash = tk.StringVar()
        self.pool_rate = tk.StringVar()
        self.pool_fee = tk.StringVar(value='0')
        self.chain_endpoint = tk.StringVar(value=PUBLIC_NODES[0]['endpoint'])
        self.chain_tls = tk.BooleanVar(value=True)
        self.stats_result = ''
        self.last_hps = 0.0
        self.session_history = []
        self.session_started = None
        self.pool_query_address = tk.StringVar()
        self.pool_query_scope = tk.StringVar(value='collective')
        self.pool_snapshot = None
        self.overview_results={}
        self.overview_busy=False
        self.overview_request=0
        self.overview_address=""
        self.overview_checked=0
        self.payout_dialog=None
        self.pool_query_busy = False
        self.pool_request_id = 0
        self.pool_query_error = ''
        self.pool = tk.StringVar()
        self.endpoint = tk.StringVar(value=self.node.get())
        self.cpu_profile = 'percent:100'
        self.cpu_percent=tk.IntVar(value=100)
        self.cpu_allocation=tk.StringVar()
        self.pool_cooldowns={}
        self.energy_whole_kwh=0.0
        self.energy_whole_seconds=0.0
        self.pending_pool=None
        self.switch_message=''
        self.manual_watts=tk.StringVar()
        self.electric_tariff=tk.StringVar()
        self.energy_cpu_kwh=0.0
        self.energy_estimated_kwh=0.0
        self.energy_measured_seconds=0.0
        self.power_sample=None
        self.power_previous=None
        self.power_busy=False
        self.last_power_poll=0.0
        self.cpu_enabled = tk.BooleanVar(value=True)
        self.gpu_backend = tk.StringVar(value="NVIDIA CUDA")
        self.gpu_enabled = tk.BooleanVar(value=False)
        self.threads = tk.IntVar(value=1)
        self.tls = tk.BooleanVar(value=True)
        self.share = tk.BooleanVar(value=True)
        self.consent = tk.BooleanVar(value=False)
        self.cpu_hashrate = tk.StringVar(value='— H/s')
        self.gpu_hashrate = tk.StringVar(value='— H/s')
        self.backend_rates = {}
        self.hashrate = tk.StringVar(value='— H/s')
        self.accepted = tk.StringVar(value='0')
        self.runtime = tk.StringVar(value='00:00:00')
        self.statekey = 'idle'
        self.device = hardware()
        # This user explicitly prefers the maximum detected logical thread
        # count. The cache-aware recommendation remains visible in Hardware.
        self.threads.set(self.device['logical'])
        try:
            saved = json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
            for name in ('wallet', 'mode', 'node', 'remote', 'pool', 'tls', 'share', 'threads', 'gpu_backend', 'cpu_enabled'):
                if name in saved:
                    getattr(self, name).set(saved[name])
            self.gpu_enabled.set(bool(saved.get('gpu_enabled',saved.get('gpu_backend','off')!='off')))
            if self.gpu_backend.get()=='off': self.gpu_backend.set('NVIDIA CUDA')
            if saved.get('mining_default_version')!=2:
                self.mode.set('pool')
                self.tls.set(True)
            self.language_manual=bool(saved.get('language_manual',False))
            if self.language_manual and saved.get('lang') in LANGUAGES:
                self.lang.set(saved['lang'])
            self.total = max(0, float(saved.get('total', 0)))
            if saved.get('allocation_policy')=='100min-minute20-v2':
                value=float(saved.get('allocation_elapsed',0))
                self.allocation_elapsed=value if math.isfinite(value) and value>=0 else 0.0
            else:
                self.share.set(True)
            self.last_hps = max(0,float(saved.get('last_hps',0)))
            if self.last_hps and math.isfinite(self.last_hps):
                self.stats_hash.set(str(self.last_hps))
            if self.mode.get() not in ('solo', 'pool', 'remote'):
                self.mode.set('pool')
            self.threads.set(max(1, min(self.device['logical'], self.threads.get())))
            self.cpu_profile=saved.get('cpu_profile','all' if self.threads.get()==self.device['logical'] else 'custom')
            if self.cpu_profile=='all': self.cpu_profile='percent:100'
            if self.cpu_profile=='half': self.cpu_profile='percent:50'
            self.cpu_percent.set(int(float(self.cpu_profile.split(':')[1])) if self.cpu_profile.startswith('percent:') else max(1,min(100,round(self.threads.get()/self.device['logical']*100))))
            self.manual_watts.set(str(saved.get('manual_watts','')))
            self.electric_tariff.set(str(saved.get('electric_tariff','')))
            self.pool_cooldowns={key:float(value) for key,value in saved.get('pool_cooldowns',{}).items() if isinstance(key,str) and isinstance(value,(int,float)) and time.time()<value<=time.time()+3600}
            for field in ('energy_cpu_kwh','energy_estimated_kwh','energy_measured_seconds','energy_whole_kwh','energy_whole_seconds'):
                value=float(saved.get(field,0))
                if math.isfinite(value) and value>=0: setattr(self,field,value)
            self.threads.set(detected_threads(self.device,self.cpu_profile,self.threads.get()))
        except (OSError, ValueError, TypeError, tk.TclError):
            pass
        try:
            lines = (DATA/'sessions.jsonl').read_text(encoding='utf-8').splitlines()[-100:]
            self.session_history = [json.loads(line) for line in lines]
        except (OSError,ValueError):
            pass
        if not self.pool.get().strip():
            self.pool.set(POOL_PRESETS[0]['endpoint'])
            if self.mode.get()=='pool':
                self.tls.set(True)
        # XMR_TLS_ONLY_MIGRATION: upgrade the previous explicit plaintext experiment.
        if self.pool.get()=='gulf.moneroocean.stream:10001':
            self.pool.set('gulf.moneroocean.stream:20001')
            self.tls.set(True)
        self.endpoint.set(self.endpoint_var().get())
        self.pool_query_address.set(self.wallet.get())
        if self.cooldown_remaining(self.endpoint.get()): self.switch_message='pool_paused'
        self.threads.trace_add('write',self.on_threads_changed)
        self.endpoint.trace_add('write',lambda *args:self.invalidate_pool())
        self.mode.trace_add('write',lambda *args:self.invalidate_pool())
        self.pool_query_address.trace_add('write',lambda *args:self.invalidate_pool())
        root.geometry('1180x820')
        root.minsize(960, 700)
        root.configure(bg='#0c1425')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.build()
        self.sync_desktop_language()
        root.after(500, self.tick)

    def t(self, key):
        return TEXT[LANGUAGES.get(self.lang.get(),'en')].get(key,TEXT['en'].get(key,key))

    def display_currency(self):
        return LANGUAGE_CURRENCIES.get(LANGUAGES.get(self.lang.get(),'en'),'usd')

    def fiat_value(self,xmr,include_usd=False):
        currency=self.display_currency()
        quote=self.market or {}
        rate=payout_decimal(quote.get(currency),True)
        text=currency.upper()+' '+(f'{Decimal(str(xmr))*rate:,.2f}' if rate is not None else self.t('unavailable'))
        if include_usd and currency!='usd':
            usd=payout_decimal(quote.get('usd'),True)
            if usd is not None: text+=f' / USD {Decimal(str(xmr))*usd:,.2f}'
        return text

    def error_text(self,text):
        text=str(text)
        if ' / ' in text:
            text=text.split(' / ',1)[0 if self.lang.get()=='中文' else 1]
        return text

    def label(self, parent, text='', size=10, fg='#acbad1', **kwargs):
        return tk.Label(parent, text=text, bg='#141f33', fg=fg, font=('Microsoft YaHei UI',size), **kwargs)

    def build(self, event=None):
        selected_page=getattr(self,'page_index',0)
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.t('title'))
        try:
            self.root.iconbitmap(str(Path(getattr(sys,'_MEIPASS',BASE))/'app.ico'))
        except tk.TclError:
            pass
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.',font=('Microsoft YaHei UI',10),background='#141f33',foreground='#d9e5f2')
        style.configure('Workspace.TNotebook',background='#0c1425',borderwidth=0,tabmargins=0)
        style.layout('Workspace.TNotebook.Tab',[])
        style.configure('TEntry',fieldbackground='#101c2e',foreground='#e9f2fb',bordercolor='#2b4058',lightcolor='#2b4058',darkcolor='#2b4058',padding=8)
        style.map('TEntry',bordercolor=[('focus','#4bcbb0')])
        style.configure('TCombobox',fieldbackground='#101c2e',background='#203148',foreground='#e9f2fb',arrowcolor='#9db2c9',padding=6,borderwidth=1)
        style.map('TCombobox',fieldbackground=[('readonly','#101c2e')],foreground=[('readonly','#e9f2fb')],selectbackground=[('readonly','#21423e')],selectforeground=[('readonly','#e9f2fb')])
        style.configure('TSpinbox',fieldbackground='#101c2e',background='#203148',foreground='#e9f2fb',arrowcolor='#9db2c9',padding=6)
        style.configure('TButton',background='#22364c',foreground='#e7f0fa',borderwidth=0,padding=(14,9),focusthickness=0)
        style.map('TButton',background=[('active','#2f4861'),('pressed','#365974'),('disabled','#18273a')],foreground=[('disabled','#60788f')])
        style.configure('Accent.TButton',background='#58d8b1',foreground='#082a24',font=('Microsoft YaHei UI',10,'bold'),padding=(24,11))
        style.map('Accent.TButton',background=[('active','#80e9c7'),('disabled','#24473f')],foreground=[('disabled','#7d9f95')])
        style.configure('Stop.TButton',background='#3d2834',foreground='#f3bacb',padding=(20,11))
        style.map('Stop.TButton',background=[('active','#583445')])
        style.configure('TMenubutton',background='#1a2b40',foreground='#e9f2fb',borderwidth=0,padding=(12,7))
        style.configure('Treeview',background='#121f31',fieldbackground='#121f31',foreground='#dbe6f4',rowheight=34,borderwidth=0)
        style.map('Treeview',background=[('selected','#234d49')],foreground=[('selected','#a4f1d8')])
        style.configure('Treeview.Heading',background='#203148',foreground='#a7bdd2',padding=(10,10),font=('Microsoft YaHei UI',9,'bold'),borderwidth=0)
        style.configure('Vertical.TScrollbar',background='#2a4058',troughcolor='#101b2c',arrowcolor='#8da5bd',borderwidth=0,arrowsize=12)
        top=tk.Frame(self.root,bg='#0c1425')
        top.pack(fill='x',padx=24,pady=(18,14))
        try:
            self.brand_icon=tk.PhotoImage(file=str(Path(getattr(sys,'_MEIPASS',BASE))/'app.png')).subsample(6,6)
            tk.Label(top,image=self.brand_icon,bg='#0c1425').pack(side='left',padx=(0,12))
        except tk.TclError:
            pass
        brand=tk.Frame(top,bg='#0c1425'); brand.pack(side='left')
        tk.Label(brand,text=self.t('title'),bg='#0c1425',fg='#f1f6ff',font=('Microsoft YaHei UI',18,'bold')).pack(anchor='w')
        tk.Label(brand,text=self.t('tag'),bg='#0c1425',fg='#7890a9',font=('Microsoft YaHei UI',9)).pack(anchor='w',pady=(3,0))
        self.flag_images={}
        flag_dir=Path(getattr(sys,'_MEIPASS',BASE))/'flags'
        for code,country in FLAG_COUNTRIES.items():
            try:
                self.flag_images[code]=tk.PhotoImage(file=str(flag_dir/(country+'.png'))).subsample(2,2)
            except tk.TclError:
                pass
        language=ttk.Menubutton(top,text=self.lang.get(),image=self.flag_images.get(LANGUAGES.get(self.lang.get()),''),compound='right')
        language.pack(side='right')
        menu=tk.Menu(language,tearoff=False,bg='#17283d',fg='#dce9f6',activebackground='#28554f',activeforeground='#a4f1d8',bd=0)
        language.configure(menu=menu)
        for name,code in LANGUAGES.items():
            menu.add_command(label=name,image=self.flag_images.get(code,''),compound='right',command=lambda value=name:self.choose_language(value))
        menu.add_separator()
        menu.add_command(label=self.t('system_language'),command=lambda:self.choose_language(None))
        cards=tk.Frame(self.root,bg='#0c1425')
        cards.pack(fill='x',padx=24,pady=(0,18))
        for column,(key,var) in enumerate([('hash',self.hashrate),('cpu_rate',self.cpu_hashrate),('gpu_rate',self.gpu_hashrate),('accepted',self.accepted),('uptime',self.runtime)]):
            cards.columnconfigure(column,weight=1,uniform='metrics')
            box=tk.Frame(cards,bg='#141f33',padx=18,pady=14,highlightthickness=1,highlightbackground='#22354b')
            box.grid(row=0,column=column,sticky='ew',padx=(0,10 if column<4 else 0))
            self.label(box,self.t(key),fg='#8ea5bd',size=9).pack(anchor='w')
            tk.Label(box,textvariable=var,bg='#141f33',fg='#69dfbd' if column==0 else '#edf4fc',font=('Microsoft YaHei UI',19,'bold')).pack(anchor='w',pady=(5,0))
        workspace=tk.Frame(self.root,bg='#0c1425')
        workspace.pack(fill='both',expand=True,padx=24)
        navigation=tk.Frame(workspace,bg='#101c2d',width=164)
        navigation.pack(side='left',fill='y')
        navigation.pack_propagate(False)
        book=ttk.Notebook(workspace,style='Workspace.TNotebook')
        book.pack(side='left',fill='both',expand=True,padx=(14,0))
        self.ui_book=book
        self.nav_buttons=[]
        setup_outer = tk.Frame(book,bg='#141f33')
        setup_canvas = tk.Canvas(setup_outer,bg='#141f33',highlightthickness=0)
        setup_scroll = ttk.Scrollbar(setup_outer,orient='vertical',command=setup_canvas.yview)
        setup_canvas.configure(yscrollcommand=setup_scroll.set)
        setup_scroll.pack(side='right',fill='y')
        setup_canvas.pack(side='left',fill='both',expand=True)
        setup = tk.Frame(setup_canvas,bg='#141f33',padx=18,pady=14)
        setup_item = setup_canvas.create_window((0,0),window=setup,anchor='nw')
        setup.bind('<Configure>',lambda event:setup_canvas.configure(scrollregion=setup_canvas.bbox('all')))
        setup_canvas.bind('<Configure>',lambda event:setup_canvas.itemconfigure(setup_item,width=event.width))
        energy_page=tk.Frame(book,bg='#141f33',padx=18,pady=14)
        devices = tk.Frame(book, bg='#141f33', padx=20, pady=14)
        logs = tk.Frame(book, bg='#141f33', padx=12, pady=12)
        nodes = tk.Frame(book, bg='#141f33', padx=18, pady=14)
        earnings_outer = tk.Frame(book,bg='#141f33')
        earnings_canvas = tk.Canvas(earnings_outer,bg='#141f33',highlightthickness=0)
        earnings_scroll = ttk.Scrollbar(earnings_outer,orient='vertical',command=earnings_canvas.yview)
        earnings_canvas.configure(yscrollcommand=earnings_scroll.set)
        earnings_scroll.pack(side='right',fill='y')
        earnings_canvas.pack(side='left',fill='both',expand=True)
        earnings = tk.Frame(earnings_canvas,bg='#141f33',padx=18,pady=14)
        earnings_item = earnings_canvas.create_window((0,0),window=earnings,anchor='nw')
        earnings.bind('<Configure>',lambda event:earnings_canvas.configure(scrollregion=earnings_canvas.bbox('all')))
        earnings_canvas.bind('<Configure>',lambda event:earnings_canvas.itemconfigure(earnings_item,width=event.width))
        stats_outer = tk.Frame(book,bg='#141f33')
        stats_canvas = tk.Canvas(stats_outer,bg='#141f33',highlightthickness=0)
        stats_scroll = ttk.Scrollbar(stats_outer,orient='vertical',command=stats_canvas.yview)
        stats_canvas.configure(yscrollcommand=stats_scroll.set)
        stats_scroll.pack(side='right',fill='y')
        stats_canvas.pack(side='left',fill='both',expand=True)
        stats_frame = tk.Frame(stats_canvas,bg='#141f33',padx=18,pady=14)
        stats_item = stats_canvas.create_window((0,0),window=stats_frame,anchor='nw')
        stats_frame.bind('<Configure>',lambda event:stats_canvas.configure(scrollregion=stats_canvas.bbox('all')))
        stats_canvas.bind('<Configure>',lambda event:stats_canvas.itemconfigure(stats_item,width=event.width))
        def scroll_page(event):
            canvas = earnings_canvas if book.select()==str(earnings_outer) else stats_canvas if book.select()==str(stats_outer) else pool_canvas if book.select()==str(pool_live) else setup_canvas if book.select()==str(setup_outer) else None
            if canvas:
                canvas.yview_scroll(-int(event.delta/120),'units')
        self.root.bind('<MouseWheel>',scroll_page)
        pool_live = tk.Frame(book,bg='#141f33')
        pool_canvas = tk.Canvas(pool_live,bg='#141f33',highlightthickness=0)
        pool_scroll = ttk.Scrollbar(pool_live,orient='vertical',command=pool_canvas.yview)
        pool_canvas.configure(yscrollcommand=pool_scroll.set)
        pool_scroll.pack(side='right',fill='y')
        pool_canvas.pack(side='left',fill='both',expand=True)
        pool_body = tk.Frame(pool_canvas,bg='#141f33',padx=18,pady=14)
        pool_item = pool_canvas.create_window((0,0),window=pool_body,anchor='nw')
        pool_body.bind('<Configure>',lambda event:pool_canvas.configure(scrollregion=pool_canvas.bbox('all')))
        pool_canvas.bind('<Configure>',lambda event:pool_canvas.itemconfigure(pool_item,width=event.width))
        for frame, key in [(setup_outer,'setup'),(pool_live,'pool_live'),(stats_outer,'stats'),(earnings_outer,'earnings'),(nodes,'nodes'),(devices,'device'),(energy_page,'energy'),(logs,'logs')]:
            book.add(frame, text=self.t(key))
            index=len(self.nav_buttons)
            button=tk.Button(navigation,text=self.t(key),command=lambda value=index:self.navigate_page(value),anchor='w',justify='left',wraplength=136,bg='#101c2d',fg='#91a7bf',activebackground='#21374b',activeforeground='#e8f3ff',relief='flat',bd=0,padx=16,pady=13,font=('Microsoft YaHei UI',10),cursor='hand2',highlightthickness=0)
            button.pack(fill='x',padx=6,pady=(4,0))
            self.nav_buttons.append(button)

        setup.columnconfigure(1,weight=1)
        self.label(setup,self.t('wallet')).grid(row=0,column=0,sticky='w',pady=6)
        ttk.Entry(setup,textvariable=self.wallet).grid(row=0,column=1,columnspan=2,sticky='ew',padx=(12,0))
        self.label(setup,self.t('mode')).grid(row=1,column=0,sticky='w',pady=6)
        self.modebox = ttk.Combobox(setup,values=[self.t('solo'),self.t('pool'),self.t('remote')],state='readonly')
        self.modebox.current(('solo','pool','remote').index(self.mode.get()))
        self.modebox.grid(row=1,column=1,columnspan=2,sticky='ew',padx=(12,0))
        self.modebox.bind('<<ComboboxSelected>>',self.change_mode)
        self.label(setup,self.t('endpoint')).grid(row=2,column=0,sticky='w',pady=6)
        ttk.Entry(setup,textvariable=self.endpoint).grid(row=2,column=1,columnspan=2,sticky='ew',padx=(12,0))
        self.label(setup,self.t('threads')).grid(row=3,column=0,sticky='w',pady=6)
        ttk.Spinbox(setup,from_=1,to=self.device['logical'],textvariable=self.threads,width=6).grid(row=3,column=1,sticky='w',padx=12)
        tk.Checkbutton(setup,text=self.t('tls'),variable=self.tls,bg='#141f33',fg='#cedcf0',selectcolor='#263854',activebackground='#141f33',activeforeground='white').grid(row=3,column=2,sticky='e')
        cpu_buttons = tk.Frame(setup,bg='#141f33')
        cpu_buttons.grid(row=4,column=0,columnspan=3,sticky='ew')
        self.label(cpu_buttons,self.t('cpu_percent')).pack(side='left')
        percent_box=ttk.Spinbox(cpu_buttons,from_=1,to=100,textvariable=self.cpu_percent,width=5,command=self.apply_cpu_percent)
        percent_box.pack(side='left',padx=8)
        percent_box.bind('<Return>',lambda event:self.apply_cpu_percent())
        percent_box.bind('<FocusOut>',lambda event:self.apply_cpu_percent())
        for percent in (25,50,75,100):
            ttk.Button(cpu_buttons,text=f'{percent}%',width=5,command=lambda value=percent:self.set_cpu_profile('percent:'+str(value))).pack(side='left',padx=3)
        self.label(setup,'',textvariable=self.cpu_allocation,size=9).grid(row=16,column=0,columnspan=3,sticky='w')
        self.update_cpu_allocation()
        gpu_controls=tk.Frame(setup,bg='#141f33')
        gpu_controls.grid(row=19,column=0,columnspan=3,sticky='ew',pady=8)
        self.backend_toggle(gpu_controls,self.cpu_enabled,'cpu_enable')
        self.backend_toggle(gpu_controls,self.gpu_enabled,'gpu_enable')
        self.label(gpu_controls,self.t('gpu_backend')).pack(side='left',padx=8)
        ttk.Combobox(gpu_controls,textvariable=self.gpu_backend,values=['NVIDIA CUDA','AMD OpenCL'],state='readonly',width=18).pack(side='left')
        self.label(setup,self.t('gpu_help'),size=9,wraplength=930,justify='left').grid(row=20,column=0,columnspan=3,sticky='w',pady=4)
        self.label(setup,self.t('gpu_efficiency'),fg='#e5be7c',size=9,wraplength=930,justify='left').grid(row=21,column=0,columnspan=3,sticky='w',pady=(4,10))
        presets = tk.Frame(setup,bg='#141f33')
        presets.grid(row=5,column=0,columnspan=3,sticky='ew',pady=8)
        self.label(presets,self.t('select_pool')).pack(side='left')
        choices=[f"{pool['name']} | {pool['fee']}% | "+self.t('transport_tls') for pool in POOL_PRESETS]
        picker=ttk.Combobox(presets,values=choices,state='readonly',width=29)
        picker.pack(side='left',padx=12)
        selected=next((i for i,pool in enumerate(POOL_PRESETS) if pool['endpoint']==self.pool.get()),None)
        if selected is not None:
            picker.current(selected)
        picker.bind('<<ComboboxSelected>>',lambda event:self.select_pool(picker.current()))
        pool=next((pool for pool in POOL_PRESETS if pool['endpoint']==self.endpoint.get() and self.mode.get()=='pool'),None)
        detail=(self.t('pool_details').format(provider=pool['name'],fee=pool['fee'])+'\n' if pool else '')+self.t('pool_selection_note')
        self.label(setup,detail,wraplength=930,justify='left',fg='#70dbbc',size=9).grid(row=6,column=0,columnspan=3,sticky='w')
        ttk.Button(presets,text=self.t('switch_pool'),command=self.switch_running_pool).pack(side='left',padx=8)
        self.switch_label=self.label(setup,self.t(self.switch_message) if self.switch_message else '',fg='#70dbbc',size=9)
        self.switch_label.grid(row=17,column=0,columnspan=3,sticky='w')
        self.author_label=self.label(setup,'',wraplength=930,justify='left',size=9,fg='#70dbbc')
        self.author_label.grid(row=18,column=0,columnspan=3,sticky='w',pady=6)
        self.update_author_label()
        self.label(setup,self.t('cpu_detected').format(**self.device),wraplength=930,justify='left',size=9).grid(row=15,column=0,columnspan=3,sticky='w',pady=8)
        self.label(setup,self.t('fee'),fg='#70dbbc',size=11).grid(row=7,column=0,columnspan=3,sticky='w',pady=(12,4))
        self.label(setup,self.t('note') if self.mode.get()!='pool' else self.t('pool_payment_note'),wraplength=930,justify='left',fg='#e5be7c').grid(row=8,column=0,columnspan=3,sticky='w')
        sharebutton = tk.Checkbutton(setup,text=self.t('share'),variable=self.share,bg='#141f33',fg='#eef4ff',selectcolor='#263854',activebackground='#141f33',activeforeground='white')
        sharebutton.grid(row=9,column=0,columnspan=3,sticky='w',pady=(12,2))
        self.label(setup,self.t('allocation_summary'),wraplength=930,justify='left',size=9).grid(row=10,column=0,columnspan=3,sticky='w',pady=(2,8))
        self.label(setup,self.t('owner'),size=9).grid(row=11,column=0,columnspan=3,sticky='w',pady=(8,2))
        address = ttk.Entry(setup)
        address.insert(0,BENEFICIARY)
        address.configure(state='readonly')
        address.grid(row=12,column=0,columnspan=3,sticky='ew')
        self.render_help(setup)
        tk.Checkbutton(setup,text=self.t('consent'),variable=self.consent,bg='#141f33',fg='#eef4ff',selectcolor='#263854',activebackground='#141f33',activeforeground='white').grid(row=14,column=0,columnspan=3,sticky='w')
        self.render_energy(energy_page)
        self.render_hardware(devices)
        self.render_nodes(nodes)
        self.render_earnings(earnings)
        self.render_stats(stats_frame)
        if self.chain and self.stats_hash.get().strip():
            self.calculate_stats()
        self.render_pool_live(pool_body)
        book.bind('<<NotebookTabChanged>>',lambda event:(self.sync_navigation(),self.on_pool_tab(book,pool_live),self.on_earnings_tab()))
        ttk.Button(devices,text=self.t('refresh'),command=self.refresh_hardware).pack(anchor='w',pady=12)
        scrollbar = ttk.Scrollbar(logs)
        scrollbar.pack(side='right',fill='y')
        self.log = tk.Text(logs,bg='#0c1425',fg='#b6c9e5',font=('Consolas',10),relief='flat',wrap='word',yscrollcommand=scrollbar.set)
        self.log.pack(fill='both',expand=True)
        scrollbar.configure(command=self.log.yview)
        self.log.insert('end','\n'.join(self.loglines))
        self.log.configure(state='disabled')
        footer = tk.Frame(self.root,bg='#0c1425')
        footer.pack(side='bottom',fill='x',padx=24,pady=12,before=workspace)
        self.startbutton = ttk.Button(footer,text=self.t('start'),command=self.start,style='Accent.TButton')
        self.startbutton.pack(side='left')
        if self.proc or self.checking:
            self.startbutton.configure(state='disabled')
        ttk.Button(footer,text=self.t('stop'),command=self.stop,style='Stop.TButton').pack(side='left',padx=10)
        self.status = tk.Label(footer,text=self.t(self.statekey),bg='#12332f',fg='#7cddbd',font=('Microsoft YaHei UI',9),padx=12,pady=9,wraplength=590,justify='left')
        self.status.pack(side='right',padx=(16,0))
        tk.Label(self.root,text=self.t('save'),bg='#0c1425',fg='#8eabc9',font=('Microsoft YaHei UI',9)).pack(side='bottom',anchor='w',padx=24,pady=(0,4),before=workspace)

        book.select(min(selected_page,len(self.nav_buttons)-1))
        self.sync_navigation()
        self.root.after_idle(self.responsive_wrap)
        self.root.after(150,self.responsive_wrap)
        self.root.bind('<Configure>',self.on_ui_resize)

    def navigate_page(self,index):
        self.ui_book.select(index)
        self.sync_navigation()

    def sync_navigation(self):
        try:
            self.page_index=self.ui_book.index(self.ui_book.select())
            for index,button in enumerate(self.nav_buttons):
                active=index==self.page_index
                button.configure(bg='#1b3f3c' if active else '#101c2d',fg='#8ce8cb' if active else '#91a7bf',font=('Microsoft YaHei UI',10,'bold' if active else 'normal'))
        except tk.TclError:
            pass

    def on_ui_resize(self,event):
        if event.widget!=self.root: return
        pending=getattr(self,'resize_job',None)
        if pending:
            try: self.root.after_cancel(pending)
            except tk.TclError: pass
        self.resize_job=self.root.after(100,self.responsive_wrap)

    def responsive_wrap(self):
        self.resize_job=None
        def visit(widget):
            for child in widget.winfo_children():
                if isinstance(child,tk.Label):
                    try:
                        if float(str(child.cget('wraplength')))>0:
                            child.configure(wraplength=max(220,min(1050,child.master.winfo_width()-40)))
                    except (ValueError,tk.TclError): pass
                visit(child)
        try:
            visit(self.root)
            self.status.configure(wraplength=max(260,self.root.winfo_width()-530))
        except tk.TclError:
            pass

    def render_help(self,parent):
        area=tk.Frame(parent,bg='#141f33')
        area.grid(row=13,column=0,columnspan=3,sticky='ew',pady=10)
        body=tk.Frame(area,bg='#101c2d',padx=14,pady=12)
        for key in ('split','opt','exit'):
            tk.Label(body,text=self.t(key),wraplength=850,justify='left',anchor='w',bg='#101c2d',fg='#91a7bf',font=('Microsoft YaHei UI',9)).pack(fill='x',pady=4)
        def toggle():
            if body.winfo_manager():
                body.pack_forget()
                button.configure(text='＋ '+self.t('details'))
            else:
                body.pack(fill='x',pady=(8,0))
                button.configure(text='− '+self.t('details'))
                self.root.after_idle(self.responsive_wrap)
        button=ttk.Button(area,text='＋ '+self.t('details'),command=toggle)
        button.pack(anchor='w')

    def render_hardware(self, parent):
        d = self.device
        battery = psutil.sensors_battery()
        power = self.t('unknown') if battery is None else self.t('ac' if battery.power_plugged else 'battery')+f' · {battery.percent:.0f}%'
        rows = [('cpu',d['cpu']),('cores',f"{d['physical']} / {d['logical']}"),
                ('ram',f"{d['available']/1024**3:.1f} / {d['total']/1024**3:.1f} GB"),
                ('cache',f"{d['l3']/1024**2:.1f} MB" if d['l3'] else self.t('unknown')),('power',power),
                ('gpu',', '.join(d['gpu']) or self.t('unknown')),('recommend',str(d['recommended']))]
        for key,value in rows:
            line = tk.Frame(parent,bg='#141f33')
            line.pack(fill='x',pady=8)
            self.label(line,self.t(key),fg='#8eabc9').pack(anchor='w')
            self.label(line,value,size=12,fg='#e8f0ff',wraplength=900,justify='left').pack(anchor='w')
        self.label(parent,self.t('no_temp'),wraplength=900,justify='left',size=9).pack(anchor='w',pady=6)

    def refresh_hardware(self):
        self.device = hardware()
        self.threads.set(detected_threads(self.device,self.cpu_profile,self.threads.get()))
        self.build()

    def render_pool_live(self, parent):
        self.pool_provider_label=self.label(parent,(self.selected_pool() or '—')+' · '+self.t('pool_support'),wraplength=930,justify='left',fg='#e5be7c',size=9)
        self.pool_provider_label.pack(anchor='w')
        controls = tk.Frame(parent,bg='#141f33')
        controls.pack(fill='x',pady=10)
        self.label(controls,self.t('pool_address'),size=9).pack(anchor='w')
        ttk.Entry(controls,textvariable=self.pool_query_address).pack(fill='x',pady=(2,8))
        buttons = tk.Frame(controls,bg='#141f33')
        buttons.pack(fill='x')
        ttk.Combobox(buttons,textvariable=self.pool_query_scope,values=['collective','solo'] if self.selected_pool()=='HashVault' else ['collective'],state='readonly',width=14).pack(side='left')
        self.label(buttons,self.t('scope_info'),size=9).pack(side='left',padx=10)
        ttk.Button(buttons,text=self.t('pool_query'),command=self.query_pool).pack(side='right')
        ttk.Button(parent,text=self.t('payout_adjust'),command=self.open_payout_dialog).pack(anchor='w',pady=6)
        self.pool_summary = self.label(parent,'',wraplength=930,justify='left',fg='#70dbbc',size=10)
        self.pool_summary.pack(anchor='w',pady=6)
        self.label(parent,self.t('pool_hint'),wraplength=930,justify='left',size=9).pack(anchor='w',pady=4)
        self.label(parent,self.t('pool_payments'),fg='#eef4ff',size=11).pack(anchor='w',pady=(6,4))
        self.payments_tree = ttk.Treeview(parent,columns=('time','amount','fee','txid'),show='headings',height=4)
        for key,title,width in [('time',self.t('time_heading'),190),('amount',self.t('amount_heading'),160),('fee',self.t('fee_heading'),140),('txid',self.t('transaction_heading'),400)]:
            self.payments_tree.heading(key,text=title)
            self.payments_tree.column(key,width=width,minwidth=60)
        self.payments_tree.pack(fill='x')
        self.update_pool_view()

    def update_pool_view(self):
        self.pool_provider_label.configure(text=(self.selected_pool() or '—')+' · '+self.t('pool_support'))
        self.payments_tree.delete(*self.payments_tree.get_children())
        result = self.pool_snapshot
        lines = []
        if self.pool_query_busy:
            lines.append(self.t('loading'))
        if self.pool_query_error:
            lines.append(self.t(self.pool_query_error) if self.pool_query_error in UI_EN else self.t('pool_offline'))
        if result and result['provider']!=self.selected_pool():
            result=None
        if result:
            if result['provider']=='MoneroOcean':
                lines.append(self.t('mo_basis'))
            def fmt(value,suffix='',digits=8):
                return self.t('unavailable') if value is None else f'{value:,.{digits}f}'+suffix
            lines.append(f"{result['provider']} / {result['scope']} · {result['checked']} · {result['address']}")
            lines.append(self.t('pool_rate_live')+' ('+result['window']+'): '+fmt(result['your_hash'],' H/s',2)+' / '+fmt(result['pool_hash'],' H/s',2))
            lines.append(self.t('your_share')+': '+fmt(result['share'],'%')+' · '+self.t('network_pool')+': '+fmt(result['pool_network'],'%',4))
            lines.append(self.t('confirmed_due')+': '+fmt(result['confirmed'],' XMR')+' · '+self.t('pending_money')+': '+fmt(result['pending'],' XMR'))
            lines.append(self.t('paid_total')+': '+fmt(result['paid'],' XMR')+' · '+self.t('credited_daily')+': '+fmt(result['daily'],' XMR'))
            lines.append(self.t('threshold_live')+': '+fmt(result['threshold'],' XMR')+' · '+self.t('fee_live')+': '+fmt(result['fee'],'%',2))
            lines.append(self.t('pool_minimum')+': '+fmt(result.get('minimum'),' XMR'))
            lines.append(self.t('shares_live')+': '+fmt(result['valid'],digits=0)+' / '+fmt(result['invalid'],digits=0))
            if result['confirmed'] is not None and result['threshold'] is not None:
                lines.append(self.t('remaining_live')+': '+fmt(max(Decimal(0),result['threshold']-result['confirmed']),' XMR')+self.t('payout_timing'))
            if not result['history_found'] and not result.get('errors',{}).get('wallet') and result.get('valid') is not None:
                lines.append(self.t('pool_empty'))
            if result.get('errors'):
                lines.append(self.t('partial_api')+': '+str(result['errors']))
            for payment in result['payments']:
                self.payments_tree.insert('','end',values=(payment['time'],payment['amount'] or '—',payment['fee'] or '—',payment['txid']))
            active = self.run if self.proc else {'mode':self.mode.get(),'endpoint':self.endpoint.get()}
            if not self.proc or active['mode']!='pool' or provider_for(active['endpoint'])!=result['provider']:
                lines.append(self.t('query_only'))
        elif not self.pool_query_busy and not self.pool_query_error:
            lines.append(self.t('query_prompt'))
        self.pool_summary.configure(text='\n'.join(lines))

    def query_pool(self):
        if self.proc or self.checking:
            self.pool_query_address.set(self.pool_account_address())
        provider=self.selected_pool()
        if not provider:
            self.pool_request_id+=1
            self.pool_query_busy=False
            self.pool_snapshot=None
            self.pool_query_error='unsupported_pool'
            self.update_pool_view()
            return
        self.pool_request_id+=1
        request_id=self.pool_request_id
        address,scope = self.pool_query_address.get().strip(),self.pool_query_scope.get()
        if provider=='MoneroOcean':
            scope='collective'
            self.pool_query_scope.set(scope)
        if not valid_wallet(address):
            self.pool_query_busy=False
            self.pool_snapshot=None
            self.pool_query_error = 'invalid_address'
            self.update_pool_view()
            return
        self.pool_query_busy = True
        self.pool_query_error = ''
        self.pool_snapshot = None
        self.update_pool_view()
        def query():
            try:
                self.events.put(('pool_live',(request_id,provider,address,scope,fetch_selected_pool(provider,address,scope),None)))
            except Exception as exc:
                self.events.put(('pool_live',(request_id,provider,address,scope,None,type(exc).__name__+': '+('Pool API unavailable' if isinstance(exc,urllib.error.HTTPError) else str(exc)))))
        threading.Thread(target=query,daemon=True).start()

    def render_stats(self, parent):
        self.label(parent,self.t('chain_hint'),wraplength=930,justify='left',size=9).pack(anchor='w')
        row = tk.Frame(parent,bg='#141f33')
        row.pack(fill='x',pady=8)
        chooser = ttk.Combobox(row,textvariable=self.chain_endpoint,values=['127.0.0.1:18081']+[n['endpoint'] for n in PUBLIC_NODES],width=38)
        chooser.pack(side='left')
        def select(event):
            self.chain_tls.set(any(n['endpoint']==self.chain_endpoint.get() and n['tls'] for n in PUBLIC_NODES))
        chooser.bind('<<ComboboxSelected>>',select)
        tk.Checkbutton(row,text='TLS',variable=self.chain_tls,bg='#141f33',fg='white',selectcolor='#263854').pack(side='left',padx=10)
        ttk.Button(row,text=self.t('chain_refresh'),command=self.refresh_chain).pack(side='left')
        fields = tk.Frame(parent,bg='#141f33')
        fields.pack(fill='x',pady=6)
        for col,key,var in [(0,'input_hash',self.stats_hash),(1,'pool_hash',self.pool_rate),(2,'pool_fee',self.pool_fee)]:
            self.label(fields,self.t(key),size=9).grid(row=0,column=col,sticky='w')
            ttk.Entry(fields,textvariable=var,width=25).grid(row=1,column=col,sticky='ew',padx=(0,12))
            fields.columnconfigure(col,weight=1)
        ttk.Button(parent,text=self.t('calculate'),command=self.calculate_stats).pack(anchor='w',pady=6)
        self.stats_label = self.label(parent,self.stats_result,wraplength=930,justify='left',fg='#70dbbc',size=11)
        self.stats_label.pack(anchor='w',pady=6)
        self.chain_meta = self.label(parent,self.chain_message,wraplength=930,justify='left',size=9)
        self.chain_meta.pack(anchor='w')
        self.label(parent,self.t('estimated_hint'),wraplength=930,justify='left',size=9,fg='#e5be7c').pack(anchor='w',pady=6)
        self.label(parent,self.t('blocks'),fg='#eef4ff',size=12).pack(anchor='w',pady=(8,4))
        self.blocks_tree = ttk.Treeview(parent,columns=('height','time','reward','hash'),show='headings',height=5)
        for key,title,width in [('height',self.t('height_heading'),100),('time',self.t('time_heading'),180),('reward',self.t('reward_heading'),150),('hash',self.t('hash_heading'),450)]:
            self.blocks_tree.heading(key,text=title)
            self.blocks_tree.column(key,width=width,minwidth=70)
        self.blocks_tree.pack(fill='x')
        self.label(parent,self.t('sessions'),fg='#eef4ff',size=12).pack(anchor='w',pady=(12,4))
        self.history_tree = ttk.Treeview(parent,columns=('time','mode','seconds','results','hps'),show='headings',height=5)
        for key,title,width in [('time',self.t('time_heading'),200),('mode',self.t('mode'),180),('seconds',self.t('duration'),100),('results',self.t('results'),120),('hps','H/s',130)]:
            self.history_tree.heading(key,text=title)
            self.history_tree.column(key,width=width,minwidth=60)
        self.history_tree.pack(fill='x')
        self.label(parent,self.t('history_hint'),wraplength=930,justify='left',size=9).pack(anchor='w',pady=6)
        self.populate_stats_tables()

    def populate_stats_tables(self):
        self.blocks_tree.delete(*self.blocks_tree.get_children())
        if self.chain:
            for header in sorted(self.chain['headers'],key=lambda h:h['height'],reverse=True):
                stamp = datetime.fromtimestamp(header['timestamp']).strftime('%m-%d %H:%M:%S')
                self.blocks_tree.insert('','end',values=(header['height'],stamp,xmr_amount(header['reward']).replace(' XMR',''),header['hash']))
        self.history_tree.delete(*self.history_tree.get_children())
        for session in reversed(self.session_history[-100:]):
            self.history_tree.insert('','end',values=(session['started'],self.t(session['mode']),session['seconds'],session['accepted'],session['hps']))

    def refresh_chain(self):
        if self.chain_busy:
            return
        endpoint,tls = self.chain_endpoint.get().strip(),self.chain_tls.get()
        self.chain_busy = True
        self.chain_meta.configure(text=self.t('loading'))
        def fetch():
            try:
                self.events.put(('chain',(fetch_chain(endpoint,tls),None)))
            except Exception as exc:
                self.events.put(('chain',(None,str(exc))))
        threading.Thread(target=fetch,daemon=True).start()

    def calculate_stats(self):
        try:
            if not self.chain:
                raise ValueError(self.t('chain_first'))
            if not self.chain.get('synchronized'):
                raise ValueError(self.t('unsynced'))
            if self.proc and self.last_hps>0:
                self.stats_hash.set(str(self.last_hps))
            if not self.stats_hash.get().strip():
                raise ValueError(self.t('hash_first'))
            mode = self.run['mode'] if self.proc else self.mode.get()
            allocation = self.run['share'] if self.proc else self.share.get()
            fee = self.pool_fee.get() if mode=='pool' else 0
            pool_rate = self.pool_rate.get().strip() if mode=='pool' else ''
            result = estimate_yield(self.stats_hash.get(),self.chain,allocation,pool_rate or None,fee)
            rate = f"{result['network']/Decimal(10**9):.3f} GH/s"
            lines = [self.t('network')+': '+rate+' · '+self.t('network_share')+f": {result['network_share']:.8f}%"]
            if mode=='pool':
                lines.append(self.t('your_pool_share')+(': '+f"{result['pool_share']:.8f}%" if result['pool_share'] is not None else ': '+self.t('not_provided')))
                if result['pool_network'] is not None:
                    lines.append(self.t('pool_network_share')+f": {result['pool_network']:.5f}% ("+self.t('manual_value')+")")
            else:
                lines.append(self.t('solo_pool_na'))
                lines.append(self.t('block_wait').format(n=f"{result['days_per_block']:.1f}"))
            for key in ('daily','monthly'):
                value = result[key]
                line = self.t(key)+f': {value:.8f} XMR'
                if self.market:
                    line += ' ≈ '+self.fiat_value(value)
                lines.append(line)
            lines.append(self.t('allocation_label').format(n='1' if allocation else '0'))
            self.stats_result = '\n'.join(lines)
            self.stats_label.configure(text=self.stats_result)
        except Exception as exc:
            self.stats_label.configure(text=self.error_text(exc))

    def render_earnings(self, parent):
        self.money_mode = self.label(parent,'',fg='#70dbbc',size=12)
        self.money_mode.pack(anchor='w')
        self.label(parent,self.t('money_help'),wraplength=930,justify='left',fg='#e5be7c',size=9).pack(anchor='w',pady=(6,10))
        grid = tk.Frame(parent,bg='#141f33')
        grid.pack(fill='x')
        grid.columnconfigure(1,weight=1)
        self.money_labels = {}
        for row,key in enumerate(('price',)):
            self.label(grid,self.t(key)).grid(row=row,column=0,sticky='w',pady=5)
            value = self.label(grid,self.t('unknown_money'),fg='#eef4ff',size=12)
            value.grid(row=row,column=1,sticky='w',padx=20)
            self.money_labels[key] = value
        self.money_meta = self.label(parent,'',size=9,wraplength=930,justify='left')
        self.money_meta.pack(anchor='w',pady=6)
        ttk.Button(parent,text=self.t('price_refresh'),command=lambda:self.refresh_money('price')).pack(anchor='w',pady=(2,10))
        self.render_pool_overview(parent)
        self.label(parent,self.t('wallet_section'),size=12,fg='#eef4ff').pack(anchor='w',pady=(20,8))
        wallet_grid=tk.Frame(parent,bg='#141f33'); wallet_grid.pack(fill='x')
        for row,key in enumerate(('mined','balance','unlocked','valuation')):
            self.label(wallet_grid,self.t(key),size=9).grid(row=row,column=0,sticky='w',pady=4)
            value=self.label(wallet_grid,self.t('unknown_money'),size=10,fg='#eef4ff')
            value.grid(row=row,column=1,sticky='w',padx=20); self.money_labels[key]=value
        rpc = tk.Frame(parent,bg='#141f33')
        rpc.pack(fill='x')
        for col,(key,var) in enumerate((('wallet_rpc',self.wallet_endpoint),('rpc_user',self.rpc_user),('rpc_password',self.rpc_password))):
            self.label(rpc,self.t(key),size=9).grid(row=0,column=col,sticky='w')
            ttk.Entry(rpc,textvariable=var,width=24,show='*' if key=='rpc_password' else '').grid(row=1,column=col,sticky='ew',padx=(0,10))
            rpc.columnconfigure(col,weight=1)
        ttk.Button(parent,text=self.t('wallet_refresh'),command=lambda:self.refresh_money('wallet')).pack(anchor='w',pady=10)
        self.label(parent,self.t('wallet_help'),wraplength=930,justify='left',size=9).pack(anchor='w')
        self.label(parent,self.t('money_note'),wraplength=930,justify='left',size=9).pack(anchor='w',pady=8)
        self.update_money()

    def render_pool_overview(self,parent):
        self.label(parent,self.t('pool_overview'),size=13,fg='#eef4ff').pack(anchor='w',pady=(12,6))
        self.label(parent,self.t('overview_note'),wraplength=930,justify='left',size=9).pack(anchor='w')
        bar=tk.Frame(parent,bg='#141f33'); bar.pack(fill='x',pady=8)
        ttk.Button(bar,text=self.t('refresh_pools'),command=self.refresh_pool_overview).pack(side='left')
        self.overview_meta=self.label(bar,'',size=9); self.overview_meta.pack(side='left',padx=12)
        self.overview_widgets={}
        for provider in ('HashVault','MoneroOcean'):
            card=tk.Frame(parent,bg='#101c2d',padx=14,pady=12,highlightthickness=1,highlightbackground='#24374b'); card.pack(fill='x',pady=5)
            self.label(card,provider,fg='#70dbbc',size=12).pack(anchor='w')
            value=self.label(card,'',wraplength=900,justify='left',size=10)
            value.configure(bg='#101c2d')
            value.pack(anchor='w',fill='x',pady=4)
            card.bind('<Configure>',lambda event,label=value:label.configure(wraplength=max(220,event.width-30)))
            self.overview_widgets[provider]=value
        self.update_pool_overview()

    def on_earnings_tab(self):
        if self.page_index==3:
            self.update_pool_overview()
            if not self.market and 'price' not in self.money_busy: self.refresh_money('price')
            if valid_wallet(self.pool_account_address()) and not self.overview_busy and (self.overview_address!=self.pool_account_address() or time.monotonic()-self.overview_checked>60): self.refresh_pool_overview()

    def refresh_pool_overview(self):
        if self.overview_busy: return
        address=self.pool_account_address()
        if not valid_wallet(address):
            messagebox.showerror(self.t('pool_overview'),self.t('invalid_address')); return
        self.overview_request+=1; request=self.overview_request
        self.overview_busy=True
        if address!=self.overview_address: self.overview_results={}
        self.update_pool_overview()
        def fetch():
            def read(provider):
                try: return provider,fetch_selected_pool(provider,address,'collective')
                except Exception as exc: return provider,{'error':type(exc).__name__}
            with ThreadPoolExecutor(max_workers=2) as executor:
                values=dict(executor.map(read,('HashVault','MoneroOcean')))
            self.events.put(('pool_overview',(request,address,values)))
        threading.Thread(target=fetch,daemon=True).start()

    def update_pool_overview(self):
        if not hasattr(self,'overview_widgets'): return
        address=self.pool_account_address()
        current=self.overview_address==address
        self.overview_meta.configure(text=self.t('loading') if self.overview_busy else self.t('overview_address')+': '+address[:10]+'…'+address[-8:])
        def amount(value):
            if value is None: return self.t('unavailable')
            text=f'{value:.8f} XMR'
            if self.market: text+=' ≈ '+self.fiat_value(value)
            return text
        for provider,label in self.overview_widgets.items():
            result=self.overview_results.get(provider) if current else None
            if not result:
                label.configure(text=self.t('loading') if self.overview_busy else self.t('unknown_money')); continue
            if result.get('error'):
                label.configure(text=self.t('api_failed')+' · '+result['error']); continue
            confirmed,paid,pending=(result.get(key) for key in ('confirmed','paid','pending'))
            earned=confirmed+paid if confirmed is not None and paid is not None else None
            lines=[self.t('pool_earned')+': '+amount(earned),
                   self.t('confirmed_due')+': '+amount(confirmed)+'   ·   '+self.t('pending_money')+': '+amount(pending),
                   self.t('paid_total')+': '+amount(paid),
                   self.t('threshold_live')+': '+amount(result.get('threshold'))+'   ·   '+self.t('pool_minimum')+': '+amount(result.get('minimum'))]
            if confirmed is not None and result.get('threshold') is not None:
                lines.append(self.t('remaining_live')+': '+amount(max(Decimal(0),result['threshold']-confirmed)))
            lines.append(self.t('payout_timing')+' · '+result['checked'])
            if result.get('errors'): lines.append(self.t('overview_partial')+' '+str(result['errors']))
            label.configure(text='\n'.join(lines))

    def open_payout_dialog(self):
        provider=self.selected_pool(); address=self.pool_account_address() if self.proc or self.checking else self.pool_query_address.get().strip()
        if provider not in ('HashVault','MoneroOcean') or not valid_wallet(address):
            messagebox.showerror(self.t('payout_adjust'),self.t('invalid_address')); return
        existing=self.payout_dialog
        if existing and existing.winfo_exists(): existing.lift(); return
        dialog=tk.Toplevel(self.root); self.payout_dialog=dialog
        dialog.title(self.t('payout_adjust')); dialog.geometry('680x520'); dialog.minsize(600,460); dialog.configure(bg='#141f33'); dialog.transient(self.root)
        token=object(); self.payout_token=token
        self.payout_context=(provider,address)
        self.payout_settings=None; self.payout_busy=False
        self.payout_value=tk.StringVar()
        self.label(dialog,self.t('payout_target')+': '+provider,size=12,fg='#70dbbc').pack(anchor='w',padx=20,pady=(18,4))
        self.label(dialog,address,wraplength=620,justify='left',size=9).pack(anchor='w',padx=20)
        self.label(dialog,self.t('payout_note'),wraplength=620,justify='left',fg='#e5be7c',size=9).pack(anchor='w',padx=20,pady=10)
        self.payout_info=self.label(dialog,self.t('loading'),wraplength=620,justify='left',size=10); self.payout_info.pack(anchor='w',padx=20,pady=6)
        self.label(dialog,self.t('payout_input'),size=10).pack(anchor='w',padx=20)
        ttk.Entry(dialog,textvariable=self.payout_value).pack(fill='x',padx=20,pady=6)
        self.payout_fee_label=self.label(dialog,'',wraplength=620,justify='left',size=9); self.payout_fee_label.pack(anchor='w',padx=20,pady=6)
        controls=tk.Frame(dialog,bg='#141f33');controls.pack(fill='x',padx=20,pady=10)
        self.payout_min_button=ttk.Button(controls,text=self.t('payout_use_min'),command=self.use_minimum_payout,state='disabled'); self.payout_min_button.pack(side='left')
        self.payout_save_button=ttk.Button(controls,text=self.t('payout_save'),command=self.save_payout_threshold,state='disabled'); self.payout_save_button.pack(side='left',padx=10)
        self.payout_status=self.label(dialog,'',wraplength=620,justify='left',fg='#70dbbc',size=9); self.payout_status.pack(anchor='w',padx=20)
        def website():
            import webbrowser
            webbrowser.open('https://hashvault.pro/monero/dashboard?wallet='+address if provider=='HashVault' else 'https://moneroocean.stream/#/wallet/'+address)
        ttk.Button(dialog,text=self.t('payout_website'),command=website).pack(anchor='w',padx=20,pady=8)
        self.payout_value.trace_add('write',lambda *args:self.update_payout_fee())
        def fetch():
            try: result,error=fetch_payout_settings(provider,address),None
            except Exception as exc: result,error=None,type(exc).__name__
            self.events.put(('payout_settings',(token,provider,address,result,error)))
        threading.Thread(target=fetch,daemon=True).start()

    def payout_dialog_matches(self,token,provider,address):
        return token is getattr(self,'payout_token',None) and self.payout_dialog and self.payout_dialog.winfo_exists() and self.payout_context==(provider,address)

    def receive_payout_settings(self,token,provider,address,result,error):
        if not self.payout_dialog_matches(token,provider,address): return
        self.payout_settings=result
        if error or not result or result.get('minimum') is None or result.get('threshold') is None:
            self.payout_info.configure(text=self.t('payout_unavailable')+(' · '+error if error else '')); return
        self.payout_info.configure(text=self.t('threshold_live')+f": {result['threshold']:.8f} XMR\n"+self.t('pool_minimum')+f": {result['minimum']:.8f} XMR")
        self.payout_value.set(str(result['threshold']))
        self.payout_min_button.configure(state='normal');self.payout_save_button.configure(state='normal')
        self.update_payout_fee()

    def use_minimum_payout(self):
        if self.payout_settings and not self.payout_busy: self.payout_value.set(str(self.payout_settings['minimum']))

    def update_payout_fee(self):
        if not self.payout_dialog or not self.payout_dialog.winfo_exists(): return
        value=payout_decimal(self.payout_value.get(),True)
        policy=(self.payout_settings or {}).get('policy')
        fee=payout_fee_estimate(value,policy) if value else None
        self.payout_fee_label.configure(text=self.t('payout_fee')+f': {fee:.8f} XMR' if fee is not None else self.t('payout_fee_unknown'))

    def save_payout_threshold(self):
        if self.payout_busy: return
        value=payout_decimal(self.payout_value.get(),True); settings=self.payout_settings or {}
        if value is None or settings.get('minimum') is None or value<settings['minimum'] or value*10**12!=(value*10**12).to_integral_value():
            self.payout_status.configure(text=self.t('payout_invalid'));return
        provider,address=self.payout_context; token=self.payout_token
        self.payout_busy=True; self.payout_save_button.configure(state='disabled');self.payout_min_button.configure(state='disabled')
        self.payout_status.configure(text=self.t('payout_verifying'))
        def submit():
            try: result,error=set_payout_threshold(provider,address,value),None
            except Exception as exc: result,error=None,type(exc).__name__
            self.events.put(('payout_saved',(token,provider,address,result,error)))
        threading.Thread(target=submit,daemon=True).start()

    def receive_payout_saved(self,token,provider,address,result,error):
        # Completion invalidates both views, even if the user closed the dialog.
        if result:
            self.overview_checked=0
            if self.pool_snapshot and self.pool_snapshot['provider']==provider and self.pool_snapshot['address']==address:
                self.pool_snapshot['threshold']=result['threshold'];self.pool_snapshot['minimum']=result['minimum'];self.update_pool_view()
            for snapshot in (self.overview_results.get(provider),):
                if snapshot and snapshot.get('address')==address: snapshot.update(threshold=result['threshold'],minimum=result['minimum'])
            self.update_pool_overview()
        if not self.payout_dialog_matches(token,provider,address): return
        self.payout_busy=False
        if result: self.receive_payout_settings(token,provider,address,result,None)
        else:
            self.payout_save_button.configure(state='normal');self.payout_min_button.configure(state='normal')
        self.payout_status.configure(text=self.t('payout_saved') if result else self.t('payout_failed')+(' · '+error if error else ''))

    def update_money(self):
        actual_mode = self.run['mode'] if self.proc else self.mode.get()
        heading = self.t('running_mode') if self.proc else self.t('mode_now')
        self.money_mode.configure(text=heading+'：'+self.t({'solo':'solo','remote':'remote','pool':'pool'}[actual_mode]))
        for label in self.money_labels.values():
            label.configure(text=self.t('unknown_money'))
        meta = []
        quote = self.market
        snapshot = self.wallet_snapshot
        if quote:
            self.money_labels['price'].configure(text=self.fiat_value(1,include_usd=True))
            stamp = datetime.fromtimestamp(quote['last_updated_at']).strftime('%Y-%m-%d %H:%M:%S')
            meta.append('CoinGecko · '+self.t('last_update')+' '+stamp)
        if snapshot and snapshot['address'] == self.wallet.get().strip():
            for key in ('mined','balance','unlocked'):
                self.money_labels[key].configure(text=xmr_amount(snapshot[key]))
            meta.append(self.t('scan_height')+f" {snapshot['height']} · "+self.t('last_update')+' '+snapshot['checked'])
            meta.append(self.t('blocks_unlock')+': '+str(snapshot['blocks_to_unlock']))
            if quote:
                value = Decimal(snapshot['balance'])/Decimal(10**12)
                self.money_labels['valuation'].configure(text='≈ '+self.fiat_value(value,include_usd=True))
        if self.money_busy:
            meta.append(self.t('loading'))
        if self.money_error:
            meta.append(self.money_error)
        self.money_meta.configure(text='\n'.join(meta))
        self.update_pool_overview()

    def refresh_money(self, kind):
        if kind in self.money_busy:
            return
        args = (self.wallet_endpoint.get().strip(),self.wallet.get().strip(),self.rpc_user.get(),self.rpc_password.get())
        self.money_busy.add(kind)
        self.money_error = ''
        self.update_money()
        def fetch():
            try:
                result = fetch_price() if kind=='price' else fetch_wallet(*args)
                self.events.put(('money',(kind,result,None)))
            except Exception as exc:
                self.events.put(('money',(kind,None,str(exc))))
        threading.Thread(target=fetch,daemon=True).start()

    def endpoint_var(self):
        return {'solo':self.node,'pool':self.pool,'remote':self.remote}[self.mode.get()]

    def render_nodes(self, parent):
        self.label(parent,self.t('node_help'),wraplength=930,justify='left',fg='#e5be7c').pack(anchor='w',pady=(0,12))
        self.node_tree = ttk.Treeview(parent,columns=('provider','endpoint','tls','height','latency','status'),show='headings',height=7,selectmode='browse')
        for name,title,width in [('provider',self.t('node_name'),135),('endpoint',self.t('node_addr'),280),('tls','TLS',55),
                                 ('height',self.t('node_height'),90),('latency',self.t('latency'),80),('status',self.t('node_status'),170)]:
            self.node_tree.heading(name,text=title)
            self.node_tree.column(name,width=width,minwidth=45)
        self.node_tree.pack(fill='x')
        for i,node in enumerate(PUBLIC_NODES):
            self.node_tree.insert('','end',iid=str(i))
        self.update_node_rows()
        self.node_tree.selection_set('0')
        buttons = tk.Frame(parent,bg='#141f33')
        buttons.pack(fill='x',pady=14)
        for key,command in [('check_all',lambda:self.test_nodes(range(len(PUBLIC_NODES)))),
                            ('check_one',lambda:self.test_nodes([self.selected_node()])),
                            ('copy_node',self.copy_node),('use_node',self.use_node)]:
            ttk.Button(buttons,text=self.t(key),command=command).pack(side='left',padx=(0,10))
        self.label(parent,self.t('node_privacy'),wraplength=930,justify='left').pack(anchor='w',pady=8)

    def selected_node(self):
        selected = self.node_tree.selection()
        return int(selected[0]) if selected else 0

    def update_node_rows(self):
        for i,node in enumerate(PUBLIC_NODES):
            result = self.node_checks.get(i,{})
            key = 'probing' if i in self.probing else ('failed' if 'error' in result else ('online' if result else 'untested'))
            status = self.t(key)+' '+result.get('checked','')
            self.node_tree.item(str(i),values=(node['name'],node['endpoint'],'✓' if node['tls'] else '—',
                                              result.get('height','—'),str(result['ms'])+' ms' if 'ms' in result else '—',status))

    def test_nodes(self, indexes):
        indexes = [i for i in indexes if i not in self.probing]
        self.probing.update(indexes)
        self.update_node_rows()
        def test(i):
            try:
                result = check_public_node(PUBLIC_NODES[i])
            except Exception as exc:
                result = {'error':str(exc),'checked':time.strftime('%H:%M:%S')}
            self.events.put(('node_result',(i,result)))
        def batch():
            with ThreadPoolExecutor(max_workers=3) as executor:
                list(executor.map(test,indexes))
        threading.Thread(target=batch,daemon=True).start()

    def copy_node(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(PUBLIC_NODES[self.selected_node()]['endpoint'])
        self.append(self.t('copied')+' | '+PUBLIC_NODES[self.selected_node()]['endpoint'])

    def use_node(self):
        self.endpoint_var().set(self.endpoint.get())
        node = PUBLIC_NODES[self.selected_node()]
        self.mode.set('remote')
        self.remote.set(node['endpoint'])
        self.endpoint.set(node['endpoint'])
        self.tls.set(node['tls'])
        self.build()


    def selected_pool(self):
        active=self.run if (self.proc or self.checking) else {'mode':self.mode.get(),'endpoint':self.endpoint.get()}
        return provider_for(active['endpoint']) if active['mode']=='pool' else None

    def pool_account_address(self):
        return self.run['wallet'] if (self.proc or self.checking) else self.wallet.get().strip()

    def invalidate_pool(self):
        self.pool_request_id+=1
        self.pool_snapshot=None
        self.pool_query_busy=False
        self.pool_query_error=''

    def on_pool_tab(self,book,tab):
        if book.select()==str(tab):
            self.pool_query_address.set(self.pool_account_address())
            if not self.pool_query_busy:
                self.query_pool()

    def set_cpu_profile(self,profile):
        self.cpu_profile=profile
        if profile.startswith('percent:'): self.cpu_percent.set(int(profile.split(':')[1]))
        self.threads.set(detected_threads(self.device,profile,self.threads.get()))
        self.update_cpu_allocation()

    def on_threads_changed(self,*args):
        try:
            if self.threads.get()!=detected_threads(self.device,self.cpu_profile,self.threads.get()):
                self.cpu_profile='custom'
        except tk.TclError:
            self.cpu_profile='custom'
        self.update_cpu_allocation()


    def update_author_label(self):
        if not hasattr(self,'author_label'): return
        enabled=self.run['share'] if self.proc else self.share.get()
        if not enabled:
            self.author_label.configure(text=self.t('allocation_label').format(n='0'))
            return
        clock=self.allocation_elapsed
        phase=allocation_active(clock)
        position=clock%6000
        seconds=1260-position if phase else (1200-position if position<1200 else 7200-position)
        text=self.t('author_timer').format(elapsed=f'{int(clock)//60}:{int(clock)%60:02d}',role=self.t('author_role' if phase else 'main_role'),seconds=max(0,math.ceil(seconds)))
        main=self.run['wallet'] if self.proc else self.wallet.get().strip()
        if main==BENEFICIARY:
            text+='\n'+self.t('same_author')
        self.author_label.configure(text=text)

    def update_cpu_allocation(self):
        try:
            used=self.threads.get()
            percent=self.cpu_percent.get() if self.cpu_profile.startswith('percent:') else round(used/self.device['logical']*100,1)
            self.cpu_allocation.set(self.t('cpu_allocation').format(percent=percent,used=used,logical=self.device['logical']))
        except (tk.TclError,ValueError):
            pass

    def apply_cpu_percent(self):
        try:
            value=max(1,min(100,self.cpu_percent.get()))
            self.set_cpu_profile('percent:'+str(value))
        except tk.TclError:
            self.cpu_percent.set(100)

    def cooldown_remaining(self,endpoint):
        return max(0,self.pool_cooldowns.get(cooldown_key(endpoint),0)-time.time())

    def handle_pool_suspension(self,line):
        if not self.proc or 'new connections from this ip address are temporarily suspended' not in line.lower():
            return False
        endpoint=self.run['endpoint']
        if endpoint.lower() not in line.lower(): return False
        self.pool_cooldowns[cooldown_key(endpoint)]=time.time()+600
        previous=None
        self.pending_pool=None
        if previous and not self.cooldown_remaining(previous['endpoint']):
            self.run=previous
            self.write_config()
            self.switch_message='pool_paused_restored'
        else:
            self.stop()
            self.switch_message='pool_paused'
        self.switch_label.configure(text=self.t(self.switch_message))
        self.save()
        return True

    def switch_running_pool(self):
        if not self.proc and not self.checking:
            messagebox.showinfo(self.t('warn'),self.t('start_first'))
            return
        target=self.endpoint.get().strip()
        if self.mode.get()!='pool' or not provider_for(target): return
        if self.cooldown_remaining(target):
            messagebox.showinfo(self.t('warn'),self.t('pool_cooldown').format(minutes=math.ceil(self.cooldown_remaining(target)/60)))
            return
        try:
            # stop() waits for the owned child process to exit before start().
            self.stop()
            self.invalidate_pool()
            self.pool_query_address.set(self.wallet.get().strip())
            self.start()
            if self.checking:
                self.pending_pool={'target':target,'deadline':time.monotonic()+60}
                self.switch_message='switching'
                self.switch_label.configure(text=self.t(self.switch_message))
            self.update_pool_view()
        except Exception as exc:
            self.pending_pool=None
            messagebox.showerror(self.t('warn'),self.error_text(exc))

    def render_energy(self,parent):
        self.label(parent,self.t('automatic_power_note'),wraplength=900,justify='left',size=10).pack(anchor='w',pady=10)
        controls=tk.Frame(parent,bg='#141f33'); controls.pack(fill='x',pady=10)
        self.label(controls,self.t('tariff'),size=9).pack(side='left')
        entry=ttk.Entry(controls,textvariable=self.electric_tariff,width=18)
        entry.pack(side='left',padx=8)
        entry.bind('<KeyRelease>',lambda event:self.update_energy())
        ttk.Button(parent,text=self.t('power_refresh'),command=self.refresh_power).pack(anchor='w',pady=8)
        self.energy_label=self.label(parent,'',wraplength=900,justify='left',fg='#70dbbc',size=11)
        self.energy_label.pack(anchor='w',pady=8)
        self.update_energy()

    def refresh_power(self):
        if self.power_busy: return
        self.power_busy=True
        self.last_power_poll=time.monotonic()
        self.update_energy()
        def read():
            try:
                value=read_power_sensor()
            except Exception:
                value={'watts':None,'source':'','scope':'cpu','time':time.monotonic(),'request_status':'failed'}
            self.events.put(('power',value))
        threading.Thread(target=read,daemon=True).start()

    def update_energy(self):
        if not hasattr(self,'energy_label'): return
        sample=self.power_sample
        whole=sample and time.monotonic()-sample['time']<=30 and sample['watts'] is not None and sample.get('scope')=='whole'
        request_state=('power_request_loading' if self.power_busy else 'power_request_ok' if whole else 'power_request_denied' if sample and sample.get('request_status')=='access_denied' else 'power_request_failed' if sample and sample.get('request_status')=='failed' else 'power_request_invalid')
        lines=[self.t(request_state),self.t('whole_power')+': '+(f"{sample['watts']:.2f} W" if whole else self.t('unavailable'))]
        recorded=self.energy_whole_seconds>0
        lines.append(self.t('whole_energy')+': '+(f'{self.energy_whole_kwh:.6f}' if recorded else self.t('unavailable')))
        lines.append(self.t('whole_time').format(seconds=int(self.energy_whole_seconds)))
        if whole: lines.append(self.t('power_source')+': '+sample['source'])
        else: lines.append(self.t('whole_unavailable'))
        try:
            price=float(self.electric_tariff.get())
            if not math.isfinite(price) or price<0: raise ValueError()
            lines.append(self.t('whole_cost')+': '+(f'{self.energy_whole_kwh*price:.4f}' if recorded else self.t('unavailable')))
        except ValueError:
            lines.append(self.t('whole_cost')+': '+self.t('not_provided'))
        self.energy_label.configure(text='\n'.join(lines))

    def sync_desktop_language(self):
        threading.Thread(target=sync_owned_desktop_shortcuts,args=(self.t('title'),self.t('tag')),daemon=True).start()

    def choose_language(self,name):
        self.language_manual=name is not None
        self.lang.set(name if name in LANGUAGES else system_language_name())
        self.save()
        self.build()
        self.sync_desktop_language()

    def select_pool(self,index):
        if not 0<=index<len(POOL_PRESETS):
            return
        was_active=bool(self.proc or self.checking)
        pool=POOL_PRESETS[index]
        self.endpoint_var().set(self.endpoint.get())
        self.pool.set(pool['endpoint'])
        self.mode.set('pool')
        self.endpoint.set(pool['endpoint'])
        self.tls.set(pool['tls'])
        self.pool_fee.set(pool['fee'])
        if not self.pending_pool:
            self.switch_message='pool_paused' if self.cooldown_remaining(pool['endpoint']) else ''
        self.invalidate_pool()
        self.pool_query_address.set(self.wallet.get().strip())
        self.save()
        self.build()
        if was_active:
            self.switch_running_pool()

    def change_mode(self,event=None):
        self.endpoint_var().set(self.endpoint.get())
        self.mode.set(('solo','pool','remote')[self.modebox.current()])
        self.endpoint.set(self.endpoint_var().get())
        self.build()

    def append(self,line):
        self.loglines.append(line)
        try:
            DATA.mkdir(exist_ok=True)
            log_file=DATA/'activity.log'
            if log_file.exists() and log_file.stat().st_size>2*1024*1024:
                tail=log_file.read_bytes()[-1024*1024:]
                log_file.write_bytes(tail)
            with log_file.open('a',encoding='utf-8') as output:
                output.write(line+'\n')
        except OSError:
            pass
        self.loglines = self.loglines[-500:]
        self.log.configure(state='normal')
        self.log.insert('end',line+'\n')
        if int(self.log.index('end-1c').split('.')[0]) > 550:
            self.log.delete('1.0','100.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def backend_toggle(self,parent,variable,key):
        button=tk.Button(parent,bg='#23394c',fg='#8ce8cb',activebackground='#2e5061',activeforeground='white',relief='flat',font=('Microsoft YaHei UI',10),padx=10,pady=7)
        def redraw():
            button.configure(text=('✓ ' if variable.get() else '□ ')+self.t(key))
        def toggle():
            variable.set(not variable.get())
            redraw()
        button.configure(command=toggle)
        button.pack(side='left',padx=6)
        redraw()
        return button

    def reset_backend_rates(self):
        self.backend_rates={}
        self.update_backend_rates()

    def update_backend_rates(self):
        run=getattr(self,'run',{})
        running=bool(self.proc)
        def display(keys,enabled):
            if not running: return self.t('stopped')
            if not enabled: return self.t('backend_off')
            rates=[self.backend_rates.get(key) for key in keys]
            if any(rate is None for rate in rates): return '— H/s'
            return f'{sum(rates):,.1f} H/s'
        self.cpu_hashrate.set(display(['cpu'],run.get('cpu_enabled',True)))
        backend=run.get('gpu_backend','off')
        self.gpu_hashrate.set(display(['cuda' if backend=='NVIDIA CUDA' else 'opencl'],backend!='off'))

    def save(self):
        self.endpoint_var().set(self.endpoint.get())
        DATA.mkdir(exist_ok=True)
        saved = {name:getattr(self,name).get() for name in ('lang','wallet','mode','node','remote','pool','threads','tls','share','gpu_backend','cpu_enabled')}
        saved['gpu_enabled']=self.gpu_enabled.get()
        saved['mining_default_version']=2
        saved['pool_cooldowns']=self.pool_cooldowns
        saved['energy_whole_kwh']=self.energy_whole_kwh
        saved['energy_whole_seconds']=self.energy_whole_seconds
        saved['language_manual'] = self.language_manual
        saved.update(manual_watts=self.manual_watts.get(),electric_tariff=self.electric_tariff.get(),energy_cpu_kwh=self.energy_cpu_kwh,energy_estimated_kwh=self.energy_estimated_kwh,energy_measured_seconds=self.energy_measured_seconds)
        saved['cpu_mode_version'] = 1
        saved['cpu_profile'] = self.cpu_profile if self.threads.get()==detected_threads(self.device,self.cpu_profile,self.threads.get()) else 'custom'
        saved['allocation_policy']='100min-minute20-v2'
        saved['allocation_elapsed']=self.allocation_elapsed
        saved['total'] = self.total
        saved['last_hps'] = self.last_hps
        temp = DATA/'settings.tmp'
        temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(DATA/'settings.json')

    def verify_engine(self):
        manifest = json.loads((BASE/'engine'/'manifest.json').read_text(encoding='utf-8'))
        validate_native_manifest(manifest)
        exe = BASE/'engine'/engine_name()
        if manifest.get('developer_donation') != 0 or hashlib.sha256(exe.read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError('挖矿引擎校验失败 / Engine integrity check failed')
        return exe

    def start(self):
        if self.proc or self.checking:
            return
        try:
            exe = self.verify_engine()
            wallet = self.wallet.get().strip()
            if not valid_wallet(wallet):
                raise ValueError('主钱包地址无效（主网 95 位地址，含校验和）。 / Invalid mainnet wallet checksum.')
            if self.mode.get() in ('solo','remote') and wallet.startswith('8'):
                raise ValueError('本地独挖仅支持 4 开头主地址。 / Local solo requires a standard address starting with 4.')
            endpoint = self.endpoint.get().strip()
            if self.cooldown_remaining(endpoint):
                raise ValueError(self.t('pool_cooldown').format(minutes=math.ceil(self.cooldown_remaining(endpoint)/60)))
            if not re.fullmatch(r'[A-Za-z0-9.-]+:\d{1,5}',endpoint) or not 1<=int(endpoint.rsplit(':',1)[1])<=65535:
                raise ValueError('地址格式应为 host:port / Expected host:port')
            threads = self.threads.get()
            if not 1<=threads<=self.device['logical']:
                raise ValueError('线程数超出设备范围 / Thread count out of range')
            if psutil.virtual_memory().available < 3*1024**3:
                raise ValueError('可用内存不足 3 GB，请先关闭其他程序。 / Less than 3 GB RAM available.')
            if not self.consent.get():
                raise ValueError('请先阅读并勾选说明 / Read and acknowledge the disclosure')
            gpu_backend=self.gpu_backend.get() if self.gpu_enabled.get() else 'off'
            if gpu_backend not in ('off','NVIDIA CUDA','AMD OpenCL'):
                raise ValueError(self.t('gpu_invalid'))
            if not self.cpu_enabled.get() and gpu_backend=='off':
                raise ValueError(self.t('gpu_no_backend'))
            if gpu_backend=='NVIDIA CUDA':
                verify_gpu_bundle(BASE/'engine')
            self.run = dict(cpu_enabled=self.cpu_enabled.get(),gpu_backend=gpu_backend,mode=self.mode.get(),endpoint=endpoint,wallet=wallet,threads=threads,tls=self.tls.get(),share=self.share.get(),exe=str(exe))
            self.save()
            self.checking = True
            self.generation += 1
            generation = self.generation
            run = self.run.copy()
            self.startbutton.configure(state='disabled')
            self.statekey = 'checking'
            self.status.configure(text=self.t(self.statekey))
            def check():
                try:
                    if run['mode'] == 'solo':
                        check_local_node(run['endpoint'])
                    elif run['mode'] == 'remote':
                        check_remote_mining(run['endpoint'],run['tls'],run['wallet'])
                    elif run['mode'] == 'pool':
                        check_pool_transport(run['endpoint'],run['tls'])
                    self.events.put(('ready',generation))
                except Exception as exc:
                    self.events.put(('error',(generation,str(exc))))
            threading.Thread(target=check,daemon=True).start()
        except Exception as exc:
            messagebox.showerror(self.t('warn'),self.error_text(exc))

    def config_payload(self):
        wallet = BENEFICIARY if self.phase else self.run['wallet']
        cfg = make_config(self.run['mode'],self.run['endpoint'],wallet,self.run['threads'],self.run['tls'],self.run.get('gpu_backend','off'),self.run.get('cpu_enabled',True))
        if self.run['threads'] >= self.device['logical']:
            cfg['cpu']['priority'] = 2
            cfg['cpu']['yield'] = False
        return cfg

    def write_config(self):
        """Send public payout settings to the bridge; its temporary XMRig config is deleted on exit."""
        proc=self.proc
        if not proc or proc.stdin is None or proc.stdin.closed:
            raise RuntimeError('Miner configuration channel is unavailable')
        payload=json.dumps(self.config_payload(),separators=(',',':')).encode('utf-8')+b'\n'
        proc.stdin.write(payload)
        proc.stdin.flush()

    def launch(self):
        self.phase = bool(self.run['share'] and allocation_active(self.allocation_elapsed))
        command=[self.run['exe'],'--config-stdin']
        if not IS_WINDOWS:
            command=[sys.executable,str(BASE/'portable_support.py'),str(os.getpid())]+command
        proc = subprocess.Popen(command,cwd=str(BASE/'engine'),stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=NO_WINDOW)
        try:
            proc.stdin.write(json.dumps(self.config_payload(),separators=(',',':')).encode('utf-8')+b'\n')
            proc.stdin.flush()
            self.job = MinerJob(proc) if IS_WINDOWS else LinuxMinerJob(proc)
        except Exception:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            proc.wait()
            proc.stdout.close()
            raise
        self.proc = proc
        self.session_started = time.strftime('%Y-%m-%d %H:%M:%S')
        self.power_previous=None
        self.last = time.monotonic()
        self.elapsed = 0
        self.accepted.set('0')
        self.reset_backend_rates()
        self.hashrate.set('— H/s')
        self.statekey = 'connecting_pool'
        self.append('START | '+self.run['mode']+' | developer donation 0% | allocation '+('1 minute/100 minutes at minute 20 (1%)' if self.run['share'] else '0%'))
        run_generation=self.generation
        run_pid=proc.pid
        if self.pending_pool:
            self.invalidate_pool()
            self.pool_query_address.set(self.pool_account_address())
            self.query_pool()
        def read():
            for raw in iter(proc.stdout.readline,b''):
                self.events.put(('log',(run_generation,run_pid,raw.decode('utf-8',errors='replace').rstrip())))
            proc.stdout.close()
        threading.Thread(target=read,daemon=True).start()

    def stop(self):
        self.generation += 1
        self.checking = False
        proc,self.proc = self.proc,None
        self.last = None
        self.power_previous=None
        self.pending_pool=None
        if proc and proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.close()
            except OSError:
                pass
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if self.job:
            self.job.close()
            self.job = None
        if proc and self.session_started:
            session = {'started':self.session_started,'ended':time.strftime('%Y-%m-%d %H:%M:%S'),
                       'mode':self.run['mode'],'endpoint':self.run['endpoint'],'seconds':round(self.elapsed,1),
                       'accepted':int(self.accepted.get()),'hps':self.last_hps}
            self.session_history.append(session)
            self.session_started = None
            try:
                DATA.mkdir(exist_ok=True)
                with (DATA/'sessions.jsonl').open('a',encoding='utf-8') as history:
                    history.write(json.dumps(session,ensure_ascii=False)+'\n')
            except OSError as exc:
                self.append(str(exc))
            self.populate_stats_tables()
        self.reset_backend_rates()
        self.hashrate.set('— H/s')
        self.statekey = 'stopped'
        self.status.configure(text=self.t('stopped'))
        self.startbutton.configure(state='normal')
        try:
            self.save()
        except (OSError,tk.TclError) as exc:
            self.append(str(exc))

    def tick(self):
        for _ in range(150):
            try:
                kind,payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'ready' and self.checking and payload == self.generation:
                self.checking = False
                try:
                    self.launch()
                except Exception as exc:
                    self.append(str(exc))
                    self.stop()
            elif kind == 'error' and self.checking and payload[0] == self.generation:
                self.append(payload[1])
                failed_switch=bool(self.pending_pool)
                self.stop()
                self.statekey='engine_failed'
                if failed_switch:
                    self.switch_message='switch_failed'
                    self.switch_label.configure(text=self.t(self.switch_message))
                messagebox.showerror(self.t('warn'),payload[1])
            elif kind == 'log':
                if isinstance(payload,tuple):
                    log_generation,log_pid,payload=payload
                    if log_generation!=self.generation or not self.proc or log_pid!=self.proc.pid:
                        continue
                self.append(payload)
                if self.proc and payload.startswith('XMR | '):
                    try:
                        transport=json.loads(payload[6:])
                        if transport.get('event')=='connection_phase':
                            stage=transport.get('stage','').lower()
                            if stage in ('dns','tcp','tls'):
                                self.statekey='connecting_'+stage
                                self.connection_detail=', '.join(transport.get('addresses',[])) if stage=='tcp' else str(transport.get('address',''))
                            elif stage=='proxy':
                                self.statekey='connecting_proxy'
                                self.connection_detail=str(transport.get('proxy_host',''))+':'+str(transport.get('proxy_port',''))
                        elif transport.get('event')=='reconnecting':
                            self.statekey='reconnecting'
                            self.connection_detail=''
                            self.hashrate.set('— H/s')
                            self.reset_backend_rates()
                            if self.pending_pool:self.pending_pool['deadline']=time.monotonic()+float(transport.get('delay_seconds',60))+30
                        elif transport.get('event')=='connection_warning':
                            self.statekey='connection_warning'
                        elif transport.get('event')=='connection_retry':
                            self.statekey='connection_retry'
                            self.connection_detail=''
                        elif transport.get('event')=='tls_verified' and type(transport.get('port')) is int:
                            actual=str(transport['host'])+':'+str(transport['port'])
                            if provider_for(actual)==provider_for(self.run['endpoint']):
                                self.run['endpoint']=actual
                                self.endpoint.set(actual)
                                self.endpoint_var().set(actual)
                                if self.pending_pool:self.pending_pool['target']=actual
                    except (ValueError,KeyError,TypeError):pass
                if self.proc:
                    lower=payload.lower()
                    if '\"event\": \"preparing\"' in lower:
                        self.statekey='preparing_dataset'
                    elif '\"event\": \"tls_verified\"' in lower:
                        self.statekey='tls_connected'
                    elif 'new job from ' in lower:
                        self.statekey='waiting_shares'
                    elif 'no active pools' in lower or 'connect error' in lower or 'read error:' in lower:
                        self.statekey='reconnecting_pool'
                        self.reset_backend_rates()
                        self.hashrate.set('— H/s')
                if self.handle_pool_suspension(payload):
                    continue
                if self.pending_pool and ('new job from '+self.pending_pool['target']).lower() in payload.lower():
                    self.pending_pool=None
                    self.switch_message='switched'
                    self.switch_label.configure(text=self.t(self.switch_message))
                backend_rate=parse_backend_rate(payload)
                if backend_rate:
                    self.backend_rates[backend_rate[0]]=backend_rate[1]
                    self.update_backend_rates()
                match = re.search(r'speed (?:1s|10s)/60s/15m\s+([\d.]+)',payload)
                if match:
                    self.hashrate.set(match[1]+' H/s')
                    self.last_hps = float(match[1])
                match = re.search(r'accepted\s*\((\d+)/',payload)
                if match:
                    self.accepted.set(match[1])
                    if self.proc: self.statekey='accepted_live'
            elif kind == 'power':
                self.power_busy=False
                self.power_sample=payload
                kwh,seconds=integrate_power(self.power_previous,payload)
                if payload.get('scope')=='whole':
                    self.energy_whole_kwh+=kwh
                    self.energy_whole_seconds+=seconds
                else:
                    self.energy_cpu_kwh+=kwh
                    self.energy_measured_seconds+=seconds
                self.power_previous=payload
                self.update_energy()
            elif kind == 'node_result':
                index,result = payload
                self.node_checks[index] = result
                self.probing.discard(index)
                self.update_node_rows()
                if 'error' in result:
                    self.append(PUBLIC_NODES[index]['name']+' | '+result['error'])
            elif kind == 'money':
                source,result,error = payload
                self.money_busy.discard(source)
                if error:
                    self.money_error = self.t('price_failed' if source=='price' else 'wallet_failed')+': '+self.error_text(error)
                    self.append(self.money_error)
                elif source=='price':
                    self.market = result
                else:
                    self.wallet_snapshot = result
                self.update_money()
                if source=='price' and self.chain and self.stats_hash.get().strip(): self.calculate_stats()
            elif kind == 'chain':
                result,error = payload
                self.chain_busy = False
                if error:
                    self.chain_message = self.t('failure')+': '+self.error_text(error)
                else:
                    self.chain = result
                    self.chain_message = f"{result['endpoint']} · height {result['height']} · {result['checked']} · sync={result['synchronized']}"
                    self.populate_stats_tables()
                    self.calculate_stats()
                self.chain_meta.configure(text=self.chain_message)
            elif kind == 'pool_overview':
                request,address,values=payload
                if request!=self.overview_request: continue
                self.overview_busy=False
                if address!=self.pool_account_address():
                    self.overview_results={}; self.overview_address=''
                else:
                    self.overview_results=values; self.overview_address=address; self.overview_checked=time.monotonic()
                self.update_pool_overview()
            elif kind == 'payout_settings':
                token,provider,address,result,error=payload
                self.receive_payout_settings(token,provider,address,result,error)
            elif kind == 'payout_saved':
                token,provider,address,result,error=payload
                self.receive_payout_saved(token,provider,address,result,error)
            elif kind == 'pool_live':
                if len(payload)==6:
                    request_id,provider,address,scope,result,error=payload
                    if request_id!=self.pool_request_id or provider!=self.selected_pool() or address!=self.pool_query_address.get().strip() or scope!=self.pool_query_scope.get():
                        continue
                else:
                    result,error=payload
                self.pool_query_busy = False
                self.pool_snapshot = result
                self.pool_query_error = error or ''
                self.update_pool_view()
        if getattr(self,'page_index',0)==3 and valid_wallet(self.pool_account_address()) and not self.overview_busy and (self.overview_address!=self.pool_account_address() or time.monotonic()-self.overview_checked>60):
            self.refresh_pool_overview()
        if time.monotonic()-self.last_power_poll>=15 and not self.power_busy:
            self.refresh_power()
        if self.proc:
            if self.proc.poll() is not None:
                exit_code=self.proc.returncode
                failed_switch=bool(self.pending_pool)
                self.append('EXIT | '+str(exit_code))
                self.stop()
                if exit_code:
                    self.statekey='engine_failed'
                    if failed_switch:
                        self.switch_message='switch_failed'
                        self.switch_label.configure(text=self.t(self.switch_message))
            else:
                now = time.monotonic()
                delta = now-self.last
                if self.pending_pool and now>self.pending_pool['deadline']:
                    self.stop()
                    self.invalidate_pool()
                    self.switch_message='switch_failed'
                    self.switch_label.configure(text=self.t(self.switch_message))
                    self.update_pool_view()
                    self.root.after(500,self.tick)
                    return
                if now-self.last_power_poll>=15 and not self.power_busy:
                    self.refresh_power()
                self.update_energy()
                self.allocation_elapsed += delta
                self.total += delta
                self.elapsed += delta
                self.last = now
                seconds = int(self.elapsed)
                self.runtime.set(f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}')
                phase = bool(self.run['share'] and allocation_active(self.allocation_elapsed))
                try:
                    if phase != self.phase:
                        self.phase = phase
                        self.write_config()
                        self.append('ALLOCATION | '+('specified beneficiary' if phase else 'main wallet')+' | hot reload')
                    if now-self.lastsave>15:
                        self.save()
                        self.lastsave = now
                except Exception as exc:
                    self.append(str(exc))
                    self.stop()
        self.update_author_label()
        state_text = self.t(self.statekey)
        if self.statekey in ('connecting_dns','connecting_tcp','connecting_tls','connecting_proxy') and getattr(self,'connection_detail',''):
            state_text+=' · '+self.connection_detail
        if self.switch_message=='pool_paused' and self.cooldown_remaining(self.endpoint.get()):
            state_text+=' · '+self.t('pool_cooldown').format(minutes=math.ceil(self.cooldown_remaining(self.endpoint.get())/60))
        if self.proc:
            state_text += ' · '+self.t({'solo':'solo','remote':'remote','pool':'pool'}[self.run['mode']])
        self.status.configure(text=state_text)
        actual_mode = self.run['mode'] if self.proc else self.mode.get()
        self.money_mode.configure(text=((self.t('running_mode') if self.proc else self.t('mode_now'))+': ')+self.t(actual_mode))
        self.root.after(500,self.tick)

    def close(self):
        self.stop()
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
