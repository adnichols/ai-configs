import hashlib,json,os,stat,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def manifest(root):
    result={}
    for p in sorted(root.rglob('*')):
        rel=str(p.relative_to(root)); mode=stat.S_IMODE(p.lstat().st_mode)
        result[rel]=(mode,'L:'+os.readlink(p) if p.is_symlink() else 'D' if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
    return result
class InstallTransactionTest(unittest.TestCase):
    def assert_exact_installed_agents(self, home):
        source={path.name for path in (ROOT/'_pi/agents').iterdir()}
        installed={path.name for path in (home/'.pi/agent/agents').iterdir()}
        self.assertEqual(source,installed)
        self.assertEqual({'Explore.md','developer-mid.md','planner.md','reviewer.md','scout.md'},installed)
    def metadata(self,path):
        value=path.stat();return (stat.S_IMODE(value.st_mode),value.st_atime_ns,value.st_mtime_ns)
    def symlinked_parents(self, home, kind):
        external=Path(tempfile.mkdtemp(prefix='pi-review-skills-'))
        self.addCleanup(lambda: __import__('shutil').rmtree(external,ignore_errors=True))
        if kind=='agents':
            (external/'skills').mkdir();(home/'.agents').symlink_to(external,target_is_directory=True)
        else:
            (home/'.agents').mkdir();(home/'.agents/skills').symlink_to(external,target_is_directory=True)
        return external
    def path_snapshot(self,path):
        currents=[path] if path.is_symlink() else [path,*sorted(path.rglob('*'))];payloads={}
        for current in currents:
            kind='L' if current.is_symlink() else 'D' if current.is_dir() else 'F';payloads[current]=(kind,os.readlink(current) if kind=='L' else hashlib.sha256(current.read_bytes()).hexdigest() if kind=='F' else '')
        result=[]
        for current in currents:
            value=current.lstat();kind,payload=payloads[current]
            # Reading a symlink may update its access time on Linux even when
            # the installer rejects it without mutating the link or target.
            # Keep exact content/ownership/mode/mtime/ctime checks, but do not
            # mistake that read-only access-time update for an install write.
            atime=None if kind=='L' else value.st_atime_ns
            result.append((str(current.relative_to(path.parent)),kind,stat.S_IMODE(value.st_mode),value.st_uid,value.st_gid,atime,value.st_mtime_ns,value.st_ctime_ns,payload))
        return result
    def test_bounded_install_and_scoped_check_only(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); foreign=home/'foreign';foreign.write_text('keep');models=home/'.pi/agent/models.json';models.parent.mkdir(parents=True);models.write_text(json.dumps({'providers':{'caller-owned':{'apiKey':'secret','models':[{'id':'local'}]}}}));env={**os.environ,'HOME':d}
            subprocess.run(['bash','-c','umask 022; exec bash install.sh --pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(stat.S_IMODE((home/'.pi/agent/agents').stat().st_mode),0o700)
            self.assertEqual(foreign.read_text(),'keep');self.assert_exact_installed_agents(home);installed=json.loads(models.read_text());self.assertEqual(installed['providers']['caller-owned']['apiKey'],'secret');self.assertIn('openai-codex',installed['providers']);self.assertTrue((home/'.agents/skills/autoreview/SKILL.md').is_file());self.assertTrue((home/'.agents/skills/claude-code-review/SKILL.md').is_file());scripts=home/'.agents/skills/codex-review-partner/scripts';self.assertEqual(stat.S_IMODE((scripts/'process_identity.py').stat().st_mode)&0o500,0o500);self.assertEqual(stat.S_IMODE((scripts/'review_supervisor.py').stat().st_mode)&0o500,0o500);append=(home/'.pi/agent/APPEND_SYSTEM.md').read_text();self.assertNotIn('{{AI_CONFIGS_VERSION}}',append);self.assertRegex(append,r'Doctrine-Version: \d{4}-\d{2}-\d{2}\+[0-9a-f]{8}(?:-dirty)?');before=manifest(home)
            subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(before,manifest(home))
            helper=scripts/'process_identity.py';helper.chmod(0o050)
            result=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('owner-readable and executable',result.stderr)
    def test_retired_pi_models_are_pruned_without_claiming_custom_entries(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);agent=home/'.pi/agent';agents=agent/'agents';agents.mkdir(parents=True);stale=agents/'stale-installed-agent.md';stale.write_text('P4 will replace this directory exactly')
            models=agent/'models.json';models.write_text(json.dumps({'providers':{
                'openai-codex':{'localField':'keep','models':[
                    {'id':'gpt-5.4','name':'GPT-5.4 (CLI Proxy API)'},
                    {'id':'gpt-5.4-mini','name':'GPT-5.4 mini (CLI Proxy API)'},
                    {'id':'caller-custom','name':'Caller Custom (CLI Proxy API)','customField':'keep'},
                ]},
                'caller-owned':{'baseUrl':'https://caller.invalid/v1','api':'custom-api','apiKey':'secret','models':[{'id':'gpt-5.4','name':'Unrelated same ID'}]},
            }}))
            settings=agent/'settings.json';settings.write_text(json.dumps({'callerSetting':'keep','enabledModels':[
                'gpt-5.4','gpt-5.4-mini','openai-codex/gpt-5.4','openai-codex/gpt-5.4-mini',
                'openai-codex-old/gpt-5.4','openai-codex-history/gpt-5.4-mini',
                'openai-codex-/gpt-5.4','caller-owned/gpt-5.4','openai-codex/caller-custom',42,
            ]}))
            env={**os.environ,'HOME':d}
            subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            installed=json.loads(models.read_text());providers=installed['providers'];codex=providers['openai-codex'];ids={model['id'] for model in codex['models']}
            self.assertNotIn('gpt-5.4',ids);self.assertNotIn('gpt-5.4-mini',ids);self.assertIn('caller-custom',ids);custom=next(model for model in codex['models'] if model['id']=='caller-custom');self.assertEqual(custom['name'],'Caller Custom (CLI Proxy API)');self.assertEqual(custom['customField'],'keep');self.assertEqual(codex['localField'],'keep')
            self.assertEqual(providers['caller-owned'],{'baseUrl':'https://caller.invalid/v1','api':'custom-api','apiKey':'secret','models':[{'id':'gpt-5.4','name':'Unrelated same ID'}]})
            configured=json.loads(settings.read_text());self.assertEqual(configured['callerSetting'],'keep');self.assertEqual(configured['enabledModels'],['caller-owned/gpt-5.4','openai-codex/caller-custom',42])
            self.assertFalse(stale.exists());self.assert_exact_installed_agents(home)
            configured['enabledModels'].append('openai-codex-/gpt-5.4');settings.write_text(json.dumps(configured))
            scoped=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(scoped.returncode,0);self.assertIn('installed merged model contract',scoped.stderr)
            full=subprocess.run(['bash','scripts/verify-pi-install.sh','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(full.returncode,0);self.assertIn('enabledModels still contains retired GPT-5.4 Pi routes',full.stdout)

    def test_malformed_settings_fail_before_any_bounded_install_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);agent=home/'.pi/agent';(agent/'agents').mkdir(parents=True);(agent/'prompts').mkdir();(agent/'agents/local.md').write_text('keep agent');(agent/'prompts/local.md').write_text('keep prompt');(agent/'README.md').write_text('keep readme');(agent/'models.json').write_text(json.dumps({'providers':{'caller-owned':{'models':[{'id':'local'}]}}}));(agent/'settings.json').write_text('[]');before=manifest(agent);env={**os.environ,'HOME':d}
            result=subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('settings.json must be a JSON object',result.stderr);self.assertEqual(before,manifest(agent))

    def test_preexisting_agents_parent_metadata_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);parents=[home/'.agents',home/'.agents/skills'];parents[1].mkdir(parents=True);os.chmod(parents[0],0o751);os.chmod(parents[1],0o753);before=[(stat.S_IMODE(p.stat().st_mode),p.stat().st_mtime_ns) for p in parents];env={**os.environ,'HOME':d}
            subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(before,[(stat.S_IMODE(p.stat().st_mode),p.stat().st_mtime_ns) for p in parents])
    def test_symlinked_agents_or_skills_parents_install_successfully(self):
        for kind in ('agents','skills'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                home=Path(d);external=self.symlinked_parents(home,kind);(external/'foreign').write_text('keep');targets=[external,external/'skills'] if kind=='agents' else [external];stamp=1_577_934_245_123_456_789
                for index,target in enumerate(targets): os.utime(target,ns=(stamp+index,stamp+index+10))
                before=[self.metadata(target) for target in targets];env={**os.environ,'HOME':d}
                subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
                self.assertEqual(before,[self.metadata(target) for target in targets])
                self.assertTrue((home/'.agents').is_symlink() if kind=='agents' else (home/'.agents/skills').is_symlink());self.assertEqual((external/'foreign').read_text(),'keep');self.assertTrue((home/'.agents/skills/codex-review-partner/SKILL.md').is_file())
    def test_transaction_rolls_back_every_structural_failpoint(self):
        for point in ('after-install','after-verify','after-parity','after-preflight','after-host'):
            with self.subTest(point=point),tempfile.TemporaryDirectory() as d:
                home=Path(d);(home/'.pi').mkdir();(home/'.pi/foreign').write_text('old');before=manifest(home);env={**os.environ,'HOME':d,'PI_REVIEW_STACK_FAILPOINT':point}
                r=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.assertNotEqual(r.returncode,0);self.assertEqual(before,manifest(home))
    def test_installed_preflight_precedes_fake_launcher_substitution(self):
        text=(ROOT/'scripts/install-pi-transactionally.sh').read_text()
        parity=text.index('failpoint after-parity')
        helper=text.index('python3 "$helper" snapshot --pid $$')
        supervisor=text.index('python3 "$supervisor" --preflight')
        fake=text.index('fake_launcher.py')
        self.assertLess(parity,helper);self.assertLess(helper,supervisor);self.assertLess(supervisor,fake)
    def test_symlinked_pi_is_rejected_without_touching_link_or_external_tree(self):
        for command,failpoint in ((['bash','install.sh','--pi-review-stack'],None),(['bash','scripts/install-pi-transactionally.sh'],'after-install')):
            with self.subTest(command=command[-1]),tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
                home=Path(d);external=Path(external_d);nested=external/'nested';nested.mkdir();payload=nested/'payload.bin';payload.write_bytes(b'\x00external\xffcontent\n');os.chmod(external,0o751);os.chmod(nested,0o753);os.chmod(payload,0o640);stamp=1_577_934_245_123_456_789
                for index,target in enumerate((external,nested,payload)): os.utime(target,ns=(stamp+index,stamp+index+10))
                link=home/'.pi';link.symlink_to(external,target_is_directory=True);before_link=self.path_snapshot(link);before_external=self.path_snapshot(external);env={**os.environ,'HOME':d}
                if failpoint: env['PI_REVIEW_STACK_FAILPOINT']=failpoint
                result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('requires ~/.pi to be a real directory, not a symlink',result.stderr);self.assertEqual(before_link,self.path_snapshot(link));self.assertEqual(before_external,self.path_snapshot(external))
    def test_nested_pi_symlink_is_rejected_without_touching_external_tree(self):
        for command in (['bash','install.sh','--pi-review-stack'],['bash','scripts/install-pi-transactionally.sh']):
            with self.subTest(command=command[-1]),tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
                home=Path(d);external=Path(external_d);(home/'.pi').mkdir();(home/'.pi/agent').symlink_to(external,target_is_directory=True);payload=external/'payload';payload.write_text('external');before_home=self.path_snapshot(home/'.pi');before_external=self.path_snapshot(external);env={**os.environ,'HOME':d}
                result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('symlinks at managed ~/.pi paths',result.stderr);self.assertEqual(before_home,self.path_snapshot(home/'.pi'));self.assertEqual(before_external,self.path_snapshot(external))
    def test_transaction_rollback_preserves_preexisting_parent_modes(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);skills=home/'.agents/skills';skills.mkdir(parents=True);os.chmod(home/'.agents',0o751);os.chmod(skills,0o753);before=(stat.S_IMODE((home/'.agents').stat().st_mode),stat.S_IMODE(skills.stat().st_mode));env={**os.environ,'HOME':d,'PI_REVIEW_STACK_FAILPOINT':'after-install'}
            result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode,0);self.assertEqual(before,(stat.S_IMODE((home/'.agents').stat().st_mode),stat.S_IMODE(skills.stat().st_mode)))
    def test_transaction_rollback_with_symlinked_parents_is_exact(self):
        for kind in ('agents','skills'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                home=Path(d);external=self.symlinked_parents(home,kind);(external/'foreign').write_text('keep');targets=[external,external/'skills'] if kind=='agents' else [external];stamp=1_577_934_245_123_456_789
                for index,target in enumerate(targets): os.utime(target,ns=(stamp+index,stamp+index+10))
                before_home=manifest(home);before_external=manifest(external);before_metadata=[self.metadata(target) for target in targets];env={**os.environ,'HOME':d,'PI_REVIEW_STACK_FAILPOINT':'after-install'}
                result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.assertNotEqual(result.returncode,0);self.assertEqual(before_metadata,[self.metadata(target) for target in targets]);self.assertEqual(before_home,manifest(home));self.assertEqual(before_external,manifest(external))
    def test_transaction_signals_restore_and_return_shell_signal_codes(self):
        for signal_name,expected in (('SIGINT',130),('SIGTERM',143)):
            with self.subTest(signal=signal_name),tempfile.TemporaryDirectory() as d:
                home=Path(d);(home/'.pi').mkdir();(home/'.pi/foreign').write_text('old');before=manifest(home);marker=home/'paused';env={**os.environ,'HOME':d,'PI_REVIEW_STACK_TEST_PAUSE_MARKER':str(marker)}
                process=subprocess.Popen(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for _ in range(500):
                    if marker.exists(): break
                    __import__('time').sleep(.02)
                else: process.kill();self.fail('transaction did not reach signal failpoint')
                process.send_signal(getattr(__import__('signal'),signal_name));self.assertEqual(process.wait(timeout=30),expected);marker.unlink();self.assertEqual(before,manifest(home))
    def test_full_check_only_does_not_repair_settings_or_web_search(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);agent=home/'.pi/agent';agent.mkdir(parents=True);(agent/'settings.json').write_text(json.dumps({'defaultProvider':'foreign','defaultModel':'foreign','enabledModels':['foreign/model']}));(home/'.pi/web-search.json').write_text(json.dumps({'summaryModel':'foreign/model'}));bin_dir=home/'bin';bin_dir.mkdir();pi=bin_dir/'pi';pi.write_text('#!/bin/sh\nexit 1\n');pi.chmod(0o755);before=manifest(home);env={**os.environ,'HOME':d,'PATH':f'{bin_dir}:{os.environ["PATH"]}'}
            subprocess.run(['bash','scripts/verify-pi-install.sh','--check-only'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertEqual(before,manifest(home))
if __name__=='__main__':unittest.main()
