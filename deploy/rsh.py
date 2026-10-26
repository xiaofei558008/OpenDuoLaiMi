#!/usr/bin/env python3
# usage: rsh.py run "cmd" | rsh.py put local remote | rsh.py puttree localdir remotedir
import sys,os,paramiko
H=os.environ.get('OCI_HOST','129.158.235.58'); K=os.path.join(os.path.dirname(os.path.abspath(__file__)),'oci_key')
def conn():
    c=paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(H,username='ubuntu',key_filename=K,timeout=20); return c
c=conn(); a=sys.argv
if a[1]=='run':
    i,o,e=c.exec_command(a[2],get_pty=True); 
    for l in o: print(l,end='')
    sys.exit(o.channel.recv_exit_status())
s=c.open_sftp()
def mk(p):
    try: s.stat(p)
    except IOError: mk(os.path.dirname(p)); s.mkdir(p)
if a[1]=='put': mk(os.path.dirname(a[3])); s.put(a[2],a[3])
if a[1]=='puttree':
    for r,d,f in os.walk(a[2]):
        rr=os.path.join(a[3],os.path.relpath(r,a[2])).rstrip('/.') or a[3]; mk(rr)
        for x in f:
            lp=os.path.join(r,x); rp=rr+'/'+x
            try:
                if s.stat(rp).st_size==os.path.getsize(lp) and not x.endswith(('.json','.html','.txt','.lrc')): continue
            except IOError: pass
            s.put(lp,rp); print('up',rp)
