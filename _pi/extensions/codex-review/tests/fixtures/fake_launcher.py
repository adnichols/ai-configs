#!/usr/bin/env python3
import argparse,json,os,pathlib,signal,subprocess,sys,time
p=argparse.ArgumentParser(); p.add_argument('--mode'); p.add_argument('--verdict-profile'); p.add_argument('--input'); p.add_argument('--cwd'); p.add_argument('--output',required=True); p.add_argument('--status-file',required=True); p.add_argument('--process-identity-file',required=True); p.add_argument('--job-nonce',required=True); p.add_argument('--owner-pid'); p.add_argument('--owner-start-identity'); p.add_argument('--owner-boot-id'); p.add_argument('--timeout-seconds'); p.add_argument('--managed-process-group',action='store_true'); a=p.parse_args()
text=pathlib.Path(a.input).read_text() if a.input else ''
mode=next((line.split('=',1)[1] for line in text.splitlines() if line.startswith('MODE=')),'success')
delay=float(next((line.split('=',1)[1] for line in text.splitlines() if line.startswith('DELAY=')),'0'))
launcher_ready=next((line.split('=',1)[1] for line in text.splitlines() if line.startswith('LAUNCHER_READY=')),os.environ.get('FAKE_LAUNCHER_READY',''))
descendant_pid=next((line.split('=',1)[1] for line in text.splitlines() if line.startswith('DESCENDANT_PID=')),os.environ.get('FAKE_DESCENDANT_PID',''))
if mode=='descendant':
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
    pathlib.Path(descendant_pid).write_text(str(child.pid)); time.sleep(60)
if mode=='launcher-death':
    code='import signal,subprocess,sys,time,pathlib,os; signal.signal(signal.SIGTERM,signal.SIG_IGN); c=subprocess.Popen([sys.executable,"-c","import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(60)"]); pathlib.Path(os.environ["FAKE_DESCENDANT_PID"]).write_text(f"{os.getpid()} {c.pid}"); time.sleep(60)'
    child_env={**os.environ,'FAKE_DESCENDANT_PID':descendant_pid}
    codex=subprocess.Popen([sys.executable,'-c',code],preexec_fn=os.setsid,env=child_env)
    helper=pathlib.Path(__file__).resolve().with_name('process_identity.py')
    if not helper.exists(): helper=pathlib.Path(__file__).resolve().parents[5]/'skills/codex-review-partner/scripts/process_identity.py'
    for _ in range(100):
        snapshot=json.loads(subprocess.check_output([sys.executable,str(helper),'snapshot','--pid',str(codex.pid)],text=True))
        if snapshot.get('process'): break
        time.sleep(.01)
    for _ in range(100):
        if pathlib.Path(descendant_pid).exists(): break
        time.sleep(.01)
    record=snapshot['process']
    evidence={'protocolVersion':2,'adapterVersion':1,'platform':snapshot['platform'],'nonce':a.job_nonce,'bootId':snapshot['bootId'],'phase':'ready','leaderPid':record['pid'],'leaderPgid':record['pgid'],'leaderSid':record['sid'],'leaderStartIdentity':record['startIdentity']}
    tmp=pathlib.Path(a.process_identity_file+'.tmp');tmp.write_text(json.dumps(evidence));os.chmod(tmp,0o600);os.replace(tmp,a.process_identity_file)
    pathlib.Path(launcher_ready).write_text('ready')
    time.sleep(60)
time.sleep(delay)
tokens={'pre-pr-implementation':'CLEAN_FOR_PR','run-plan-pm':'PASS_SCOPED','reviewed-html-plan':'PLAN_EXECUTION_READY','generic-implementation':'CLEAN_FOR_PR','generic-plan':'PLAN_EXECUTION_READY'}
if a.mode=='smoke': final='CODEX_REVIEW_SMOKE_READY\n'
else: final='Review complete.\nVERDICT: '+tokens[a.verdict_profile]+'\n'
classification='CODEX_REVIEW_SUCCEEDED'; outcome='success'; code=0
if mode=='invalid': final='I will inspect the diff.\n'
if mode!='missing': pathlib.Path(a.output).write_text(final)
status={'protocolVersion':1,'cliVersion':'codex-cli 0.144.4','outcome':outcome,'classification':classification,'matchedSource':'final-message','codexExitCode':code,'codexSignal':None,'timeout':False,'finalMessageValidation':'valid'}
if mode=='protocol-missing': pass
elif mode=='protocol-malformed': pathlib.Path(a.status_file).write_text('{')
elif mode.startswith('protocol-contradiction-'):
    field=mode.removeprefix('protocol-contradiction-')
    if field=='classification': status['classification']='CODEX_REVIEW_INNER_TIMEOUT'
    elif field=='codexExitCode': status['codexExitCode']=9
    elif field=='codexSignal': status['codexSignal']='TERM'
    elif field=='timeout': status['timeout']=True
    elif field=='matchedSource': status['matchedSource']='generic'
    elif field=='finalMessageValidation': status['finalMessageValidation']='invalid'
    pathlib.Path(a.status_file).write_text(json.dumps(status))
elif mode=='protocol-inner-timeout-signal-mismatch':
    status.update(outcome='failure',classification='CODEX_REVIEW_INNER_TIMEOUT',matchedSource='inner-timeout',codexExitCode=137,codexSignal=15,timeout=True,finalMessageValidation='not-checked')
    pathlib.Path(a.status_file).write_text(json.dumps(status));sys.exit(124)
elif mode=='protocol-inner-timeout-numeric-string':
    status.update(outcome='failure',classification='CODEX_REVIEW_INNER_TIMEOUT',matchedSource='inner-timeout',codexExitCode=137,codexSignal='9',timeout=True,finalMessageValidation='not-checked')
    pathlib.Path(a.status_file).write_text(json.dumps(status));sys.exit(124)
elif mode=='protocol-codex-signal-mismatch':
    status.update(outcome='failure',classification='CODEX_REVIEW_CODEX_SIGNAL',matchedSource='signal',codexExitCode=143,codexSignal=9,timeout=False,finalMessageValidation='not-checked')
    pathlib.Path(a.status_file).write_text(json.dumps(status));sys.exit(143)
elif mode=='protocol-outer-exit-mismatch':
    status.update(outcome='failure',classification='CODEX_REVIEW_CODEX_EXIT_NONZERO',matchedSource='generic',codexExitCode=7,codexSignal=None,timeout=False,finalMessageValidation='not-checked')
    pathlib.Path(a.status_file).write_text(json.dumps(status));sys.exit(8)
elif mode=='protocol-output-commit-failed':
    status.update(outcome='failure',classification='CODEX_REVIEW_OUTPUT_COMMIT_FAILED',matchedSource='output-commit',codexExitCode=0,codexSignal=None,timeout=False,finalMessageValidation='valid')
    pathlib.Path(a.status_file).write_text(json.dumps(status));sys.exit(23)
else: pathlib.Path(a.status_file).write_text(json.dumps(status))
print('{"type":"turn.completed","token":"Bearer secret-value"}')
