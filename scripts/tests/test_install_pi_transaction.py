import hashlib,json,os,stat,subprocess,tempfile,unittest
from pathlib import Path
from scripts.tests.workflow_fixture_axes import workflow_fixture_env
ROOT=Path(__file__).resolve().parents[2]
def manifest(root):
    result={}
    for p in sorted(root.rglob('*')):
        rel=str(p.relative_to(root)); mode=stat.S_IMODE(p.lstat().st_mode)
        result[rel]=(mode,'L:'+os.readlink(p) if p.is_symlink() else 'D' if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
    return result
class InstallTransactionTest(unittest.TestCase):
    def review_env(self, home, **extra):
        package = home / '.pi/agent/npm/node_modules/@tintinweb/pi-subagents'
        files = {
            'src/types.ts': 'export type IsolationMode = "worktree";\n',
            'dist/types.d.ts': 'export type IsolationMode = "worktree";\n',
            'src/custom-agents.ts': 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
            'dist/custom-agents.js': 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,\n',
            'src/invocation-config.ts': 'isolation: agentConfig?.isolation ?? params.isolation,\n',
            'dist/invocation-config.js': 'isolation: agentConfig?.isolation ?? params.isolation,\n',
        }
        for relative, content in files.items():
            target = package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        env=workflow_fixture_env(home=home,hub_state='unavailable',profile_root=home/'.config',transport_result='pass')
        env.update(extra)
        return env

    def assert_exact_installed_agents(self, home):
        source={path.name for path in (ROOT/'_pi/agents').iterdir()}
        installed={path.name for path in (home/'.pi/agent/agents').iterdir()}
        self.assertEqual(source,installed)
        self.assertEqual({'Explore.md','imaging.md','oracle.md','planner.md','reviewer.md','scout.md'},installed)
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
            home=Path(d); foreign=home/'foreign';foreign.write_text('keep');foreign_scripts=home/'.agents/scripts';foreign_scripts.mkdir(parents=True);foreign_script=foreign_scripts/'caller-owned.py';foreign_script.write_text('keep sibling\n');models=home/'.pi/agent/models.json';models.parent.mkdir(parents=True);models.write_text(json.dumps({'providers':{'caller-owned':{'apiKey':'secret','models':[{'id':'local'}]}}}));settings=home/'.pi/agent/settings.json';settings.write_text(json.dumps({'extensions':['.pi/agent/extensions/claude-review',{'source':str(home/'.pi/agent/extensions/codex-review')},'npm:caller-owned']}));env=self.review_env(home)
            subprocess.run(['bash','-c','umask 022; exec bash install.sh --pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(json.loads(settings.read_text())['extensions'],['npm:caller-owned'])
            self.assertEqual(stat.S_IMODE((home/'.pi/agent/agents').stat().st_mode),0o700)
            self.assertEqual(foreign.read_text(),'keep');self.assertEqual(foreign_script.read_text(),'keep sibling\n');self.assert_exact_installed_agents(home);installed=json.loads(models.read_text());self.assertEqual(installed['providers']['caller-owned']['apiKey'],'secret');self.assertIn('openai-codex',installed['providers']);self.assertTrue((home/'.agents/skills/autoreview/SKILL.md').is_file());self.assertTrue((home/'.agents/skills/claude-code-review/SKILL.md').is_file());self.assertFalse((home/'.agents/skills/herdr-reviewers').exists());self.assertFalse((home/'.pi/agent/extensions/claude-review').exists());self.assertFalse((home/'.pi/agent/extensions/codex-review').exists());runtime=home/'.agents/scripts/review_orchestration.py';self.assertEqual(runtime.read_bytes(),(ROOT/'scripts/review_orchestration.py').read_bytes());self.assertEqual(stat.S_IMODE(runtime.stat().st_mode),0o755);scripts=home/'.agents/skills/codex-review-partner/scripts';self.assertEqual(stat.S_IMODE((scripts/'process_identity.py').stat().st_mode)&0o500,0o500);self.assertEqual(stat.S_IMODE((scripts/'review_supervisor.py').stat().st_mode)&0o500,0o500);append=(home/'.pi/agent/APPEND_SYSTEM.md').read_text();self.assertNotIn('{{AI_CONFIGS_VERSION}}',append);self.assertRegex(append,r'Doctrine-Version: \d{4}-\d{2}-\d{2}\+[0-9a-f]{8}(?:-dirty)?');before=manifest(home)
            subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(before,manifest(home))
            stale_extension=home/'.pi/agent/extensions/claude-review';stale_extension.mkdir()
            full=subprocess.run(['bash','scripts/verify-pi-install.sh','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(full.returncode,0);self.assertIn('disabled Pi extension is still installed: claude-review',full.stdout)
            stale_extension.rmdir()
            settings.write_text(json.dumps({'extensions':['.pi/agent/extensions/codex-review','npm:caller-owned']}))
            scoped=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(scoped.returncode,0);self.assertIn('disabled Pi extension remains explicitly registered',scoped.stderr)
            settings.write_text(json.dumps({'extensions':['npm:caller-owned']}))
            runtime.write_text('tampered\n')
            result=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('review runtime parity',result.stderr)
            runtime.write_bytes((ROOT/'scripts/review_orchestration.py').read_bytes());runtime.chmod(0o700)
            result=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('exact mode 0755',result.stderr)
            runtime.chmod(0o755)
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
                'opencode':{'modelOverrides':{'glm-5.2':{'reasoning':True}}},
                'opencode-go':{'modelOverrides':{'glm-5.2':{'reasoning':True}}},
            }}))
            settings=agent/'settings.json';settings.write_text(json.dumps({'callerSetting':'keep','enabledModels':[
                'gpt-5.4','gpt-5.4-mini','openai-codex/gpt-5.4','openai-codex/gpt-5.4-mini',
                'opencode/glm-5.2','glm-5.2',
                'openai-codex-old/gpt-5.4','openai-codex-history/gpt-5.4-mini',
                'openai-codex-/gpt-5.4','caller-owned/gpt-5.4','openai-codex/caller-custom',42,
            ]}))
            env=self.review_env(home)
            subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            installed=json.loads(models.read_text());providers=installed['providers'];codex=providers['openai-codex'];ids={model['id'] for model in codex['models']}
            self.assertNotIn('gpt-5.4',ids);self.assertNotIn('gpt-5.4-mini',ids);self.assertIn('caller-custom',ids);custom=next(model for model in codex['models'] if model['id']=='caller-custom');self.assertEqual(custom['name'],'Caller Custom (CLI Proxy API)');self.assertEqual(custom['customField'],'keep');self.assertEqual(codex['localField'],'keep')
            self.assertEqual(providers['caller-owned'],{'baseUrl':'https://caller.invalid/v1','api':'custom-api','apiKey':'secret','models':[{'id':'gpt-5.4','name':'Unrelated same ID'}]})
            self.assertNotIn('glm-5.2',providers.get('opencode',{}).get('modelOverrides',{}));self.assertNotIn('opencode-go',providers)
            configured=json.loads(settings.read_text());self.assertEqual(configured['callerSetting'],'keep');self.assertEqual(configured['enabledModels'],['caller-owned/gpt-5.4','openai-codex/caller-custom',42])
            self.assertFalse(stale.exists());self.assert_exact_installed_agents(home)
            configured['enabledModels'].append('openai-codex-/gpt-5.4');settings.write_text(json.dumps(configured))
            scoped=subprocess.run(['bash','scripts/verify-pi-install.sh','--scope','pi-review-stack','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(scoped.returncode,0);self.assertIn('installed merged model contract',scoped.stderr)
            full=subprocess.run(['bash','scripts/verify-pi-install.sh','--check-only'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(full.returncode,0);self.assertIn('enabledModels still contains retired GPT-5.4 Pi routes',full.stdout)

    def test_managed_grok_proxy_routes_migrate_to_native_xai(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            agent = home / '.pi/agent'
            (agent / 'agents').mkdir(parents=True)
            bin_dir = home / 'bin'
            bin_dir.mkdir()
            pi = bin_dir / 'pi'
            pi.write_text('#!/bin/sh\nexit 0\n')
            pi.chmod(0o755)
            models = agent / 'models.json'
            managed_xai_ids = [
                'grok-4.5', 'grok-4.3', 'grok-build-0.1',
                'grok-4.20-0309-reasoning', 'grok-4.20-0309-non-reasoning',
                'grok-4.20-multi-agent-0309', 'grok-3-mini', 'grok-3-mini-fast',
                'grok-composer-2.5-fast', 'grok-imagine-image',
                'grok-imagine-image-quality', 'grok-imagine-video',
                'grok-imagine-video-1.5-preview',
            ]
            models.write_text(json.dumps({'providers': {
                'caller-owned': {'models': [{'id': 'local'}]},
                'xai': {
                    'baseUrl': 'http://127.0.0.1:8318/v1',
                    'api': 'openai-responses',
                    'apiKey': 'local-cliproxyapi',
                    'headers': {
                        'User-Agent': 'codex-tui/0.142.5 (Linux; x86_64)',
                        'Originator': 'codex-tui',
                    },
                    'models': [{'id': model_id} for model_id in managed_xai_ids],
                },
                'opencode': {'modelOverrides': {'grok-4.5': {'contextWindow': 500000}}},
                'cursor': {'modelOverrides': {'grok-4.5': {'contextWindow': 256000}}},
            }}))
            settings = agent / 'settings.json'
            settings.write_text(json.dumps({'enabledModels': [
                'grok/grok-4.5', 'grok/grok-composer-2.5-fast', 'grok-4.3', 'openai-codex/grok-4.5', 'opencode/grok-4.5', 'cursor/grok-4.5', 'openai-codex/gpt-5.6-sol',
            ]}))
            # Reproduce the deployed PR #54 layout: a non-factory helper left in
            # extensions/ must be removed before Pi's next auto-discovered launch.
            legacy_policy = agent / 'extensions/grok-context-ceiling-policy.ts'
            legacy_policy.parent.mkdir(parents=True)
            legacy_policy.write_text('export const stale = true;\n')
            env=self.review_env(home, PATH=f'{bin_dir}:{os.environ["PATH"]}')
            subprocess.run(['bash','install.sh','--pi'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            configured_data=json.loads(settings.read_text())
            configured=configured_data['enabledModels']
            self.assertEqual(configured_data['defaultProvider'],'deepinfra')
            self.assertEqual(configured_data['defaultModel'],'deepseek-ai/DeepSeek-V4-Flash-0731')
            self.assertEqual(configured,[
                'deepinfra/deepseek-ai/DeepSeek-V4-Flash-0731:high',
                'openai-codex/gpt-5.6-terra:high',
                'openai-codex/gpt-5.6-luna:xhigh',
                'openai-codex/gpt-5.6-sol:medium',
                'xai/grok-4.6:high',
                'cursor/grok-4.5:high',
                'opencode/deepseek-v4-flash:high',
            ])
            installed_models=json.loads(models.read_text())['providers']
            self.assertNotIn('xai',installed_models)
            self.assertEqual(installed_models['opencode']['modelOverrides']['grok-4.5']['contextWindow'],200000)
            self.assertEqual(
                installed_models['opencode']['modelOverrides']['deepseek-v4-flash']['thinkingLevelMap']['max'],
                'max',
            )
            self.assertEqual(
                installed_models['deepinfra']['modelOverrides']['deepseek-ai/DeepSeek-V4-Flash-0731']['thinkingLevelMap']['max'],
                'max',
            )
            self.assertEqual(installed_models['cursor']['modelOverrides']['grok-4.5']['contextWindow'],256000)
            self.assertNotIn('grok-4.5',{model['id'] for model in installed_models['openai-codex']['models']})
            native_xai = {
                'baseUrl': 'https://api.x.ai/v1',
                'api': 'xai-responses',
                'apiKey': 'caller-owned-native-xai-key',
                'models': [{'id': 'caller-owned-native-model'}],
            }
            installed_models['xai'] = native_xai
            models.write_text(json.dumps({'providers': installed_models}))
            subprocess.run(['bash','install.sh','--pi'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(json.loads(models.read_text())['providers']['xai'],native_xai)
            policy_source = ROOT / '_pi/lib/grok-context-ceiling-policy.ts'
            installed_policy = agent / 'lib/grok-context-ceiling-policy.ts'
            self.assertEqual(installed_policy.read_bytes(), policy_source.read_bytes())
            self.assertFalse((agent / 'extensions/grok-context-ceiling-policy.ts').exists())
            self.assertIn('../lib/grok-context-ceiling-policy', (agent / 'extensions/percentage-compaction.ts').read_text())

    def test_malformed_settings_fail_before_any_bounded_install_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);agent=home/'.pi/agent';(agent/'agents').mkdir(parents=True);(agent/'prompts').mkdir();(agent/'agents/local.md').write_text('keep agent');(agent/'prompts/local.md').write_text('keep prompt');(agent/'README.md').write_text('keep readme');(agent/'models.json').write_text(json.dumps({'providers':{'caller-owned':{'models':[{'id':'local'}]}}}));(agent/'settings.json').write_text('[]');before=manifest(agent);env={**os.environ,'HOME':d}
            result=subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('settings.json must be a JSON object',result.stderr);self.assertEqual(before,manifest(agent))

    def test_review_stack_rejects_missing_pi_subagents_before_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            agent = home / '.pi/agent'
            agent.mkdir(parents=True)
            (agent / 'caller-owned').write_text('keep\n')
            before = manifest(agent)
            result = subprocess.run(
                ['bash', 'install.sh', '--pi-review-stack'],
                cwd=ROOT,
                env={**os.environ, 'HOME': d},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('required package not found', result.stderr)
            self.assertEqual(before, manifest(agent))

    def test_full_pi_install_stages_transport_probe_before_managed_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);fake_bin=home/'fake-bin';fake_bin.mkdir();npm=fake_bin/'npm';npm.write_text('#!/usr/bin/env bash\nexit 9\n');npm.chmod(0o755);env={**os.environ,'HOME':d,'PATH':f'{fake_bin}:{os.environ["PATH"]}'}
            result=subprocess.run(['bash','install.sh','--pi'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('could not be staged for preflight',result.stderr)
            for managed in (home/'.pi',home/'.agents',home/'.local/bin'):
                self.assertFalse(managed.exists() or managed.is_symlink(),managed)

    def test_preexisting_agents_parent_metadata_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);parents=[home/'.agents',home/'.agents/skills',home/'.agents/scripts'];parents[1].mkdir(parents=True);parents[2].mkdir();os.chmod(parents[0],0o751);os.chmod(parents[1],0o753);os.chmod(parents[2],0o750);before=[(stat.S_IMODE(p.stat().st_mode),p.stat().st_mtime_ns) for p in parents];env=self.review_env(home)
            subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(before,[(stat.S_IMODE(p.stat().st_mode),p.stat().st_mtime_ns) for p in parents])
    def test_symlinked_agents_or_skills_parents_are_rejected_without_external_mutation(self):
        for kind in ('agents','skills'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                home=Path(d);external=self.symlinked_parents(home,kind);(external/'foreign').write_text('keep');env=self.review_env(home);link=home/'.agents' if kind=='agents' else home/'.agents/skills';before_link=self.path_snapshot(link);before_external=manifest(external)
                result=subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('managed rollback paths',result.stderr);self.assertEqual(before_link,self.path_snapshot(link));self.assertEqual(before_external,manifest(external))
    def test_transaction_rolls_back_every_structural_failpoint(self):
        for point in ('after-install','after-verify','after-parity','after-preflight','after-host'):
            with self.subTest(point=point),tempfile.TemporaryDirectory() as d:
                home=Path(d);(home/'.pi').mkdir();(home/'.pi/foreign').write_text('old');env=self.review_env(home, PI_REVIEW_STACK_FAILPOINT=point);before=manifest(home)
                r=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.assertNotEqual(r.returncode,0);self.assertEqual(before,manifest(home))
    def test_bounded_install_rejects_runtime_symlink_without_touching_external_target(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
            home=Path(d);external=Path(external_d)/'runtime.py';external.write_text('external runtime\n');scripts=home/'.agents/scripts';scripts.mkdir(parents=True);runtime=scripts/'review_orchestration.py';runtime.symlink_to(external);env=self.review_env(home)
            result=subprocess.run(['bash','install.sh','--pi-review-stack'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('managed rollback paths',result.stderr);self.assertTrue(runtime.is_symlink());self.assertEqual(external.read_text(),'external runtime\n')
    def test_managed_link_leaf_rejects_foreign_symlink_without_touching_target(self):
        for command in (['bash','install.sh','--pi-review-stack'],['bash','scripts/install-pi-transactionally.sh']):
            with self.subTest(command=command[-1]),tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
                home=Path(d);external=Path(external_d)/'foreign-delivery';external.write_text('foreign\n');bin_dir=home/'.local/bin';bin_dir.mkdir(parents=True);link=bin_dir/'delivery';link.symlink_to(external);env=self.review_env(home);before_link=self.path_snapshot(link);before_external=self.path_snapshot(external)
                result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('foreign symlinks',result.stderr);self.assertEqual(before_link,self.path_snapshot(link));self.assertEqual(before_external,self.path_snapshot(external))

    def test_transaction_rollback_restores_exact_runtime_and_preserves_foreign_sibling(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);scripts=home/'.agents/scripts';scripts.mkdir(parents=True);runtime=scripts/'review_orchestration.py';runtime.write_text('preexisting runtime\n');runtime.chmod(0o640);foreign=scripts/'caller-owned.py';foreign.write_text('keep sibling\n');env=self.review_env(home, PI_REVIEW_STACK_FAILPOINT='after-parity');before=manifest(home);before_metadata=self.metadata(scripts)
            result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode,0);self.assertEqual(before,manifest(home));self.assertEqual(before_metadata,self.metadata(scripts));self.assertEqual(foreign.read_text(),'keep sibling\n')
    def test_transaction_rollback_restores_runtime_symlink_without_touching_external_target(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
            home=Path(d);external=Path(external_d)/'runtime.py';external.write_text('external runtime\n');scripts=home/'.agents/scripts';scripts.mkdir(parents=True);runtime=scripts/'review_orchestration.py';runtime.symlink_to(external);env=self.review_env(home, PI_REVIEW_STACK_FAILPOINT='after-parity')
            result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode,0);self.assertTrue(runtime.is_symlink());self.assertEqual(runtime.resolve(),external.resolve());self.assertEqual(external.read_text(),'external runtime\n')
    def test_installed_preflight_precedes_final_host_failpoint(self):
        text=(ROOT/'scripts/install-pi-transactionally.sh').read_text()
        parity=text.index('failpoint after-parity')
        helper=text.index('python3 "$helper" snapshot --pid $$')
        supervisor=text.index('python3 "$supervisor" --preflight')
        host=text.index('failpoint after-host')
        self.assertNotIn('fake_launcher.py',text)
        self.assertLess(parity,helper);self.assertLess(helper,supervisor);self.assertLess(supervisor,host)
    def test_symlinked_pi_is_rejected_without_touching_link_or_external_tree(self):
        for command,failpoint in ((['bash','install.sh','--pi-review-stack'],None),(['bash','scripts/install-pi-transactionally.sh'],'after-install')):
            with self.subTest(command=command[-1]),tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
                home=Path(d);external=Path(external_d);nested=external/'nested';nested.mkdir();payload=nested/'payload.bin';payload.write_bytes(b'\x00external\xffcontent\n');os.chmod(external,0o751);os.chmod(nested,0o753);os.chmod(payload,0o640);stamp=1_577_934_245_123_456_789
                for index,target in enumerate((external,nested,payload)): os.utime(target,ns=(stamp+index,stamp+index+10))
                link=home/'.pi';link.symlink_to(external,target_is_directory=True);before_link=self.path_snapshot(link);before_external=self.path_snapshot(external);env={**os.environ,'HOME':d};receipt=home/'failure-receipt.json'
                if failpoint: env['PI_REVIEW_STACK_FAILPOINT']=failpoint
                result=subprocess.run([*command,'--summary-json',str(receipt)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('requires ~/.pi to be a real directory, not a symlink',result.stderr);self.assertEqual(before_link,self.path_snapshot(link));self.assertEqual(before_external,self.path_snapshot(external));summary=json.loads(receipt.read_text());self.assertEqual('failed',summary['status']);self.assertEqual('not_run',summary['transportProbe']['status']);self.assertFalse(summary['rollback']['attempted'])
    def test_nested_pi_symlink_is_rejected_without_touching_external_tree(self):
        for command in (['bash','install.sh','--pi-review-stack'],['bash','scripts/install-pi-transactionally.sh']):
            with self.subTest(command=command[-1]),tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as external_d:
                home=Path(d);external=Path(external_d);(home/'.pi').mkdir();(home/'.pi/agent').symlink_to(external,target_is_directory=True);payload=external/'payload';payload.write_text('external');before_home=self.path_snapshot(home/'.pi');before_external=self.path_snapshot(external);env={**os.environ,'HOME':d}
                result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('managed rollback paths',result.stderr);self.assertEqual(before_home,self.path_snapshot(home/'.pi'));self.assertEqual(before_external,self.path_snapshot(external))
    def test_transaction_rollback_preserves_preexisting_parent_modes(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);skills=home/'.agents/skills';skills.mkdir(parents=True);os.chmod(home/'.agents',0o751);os.chmod(skills,0o753);env=self.review_env(home, PI_REVIEW_STACK_FAILPOINT='after-install');before=(stat.S_IMODE((home/'.agents').stat().st_mode),stat.S_IMODE(skills.stat().st_mode))
            result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertNotEqual(result.returncode,0);self.assertEqual(before,(stat.S_IMODE((home/'.agents').stat().st_mode),stat.S_IMODE(skills.stat().st_mode)))
    def test_transaction_rollback_with_symlinked_parents_is_exact(self):
        for kind in ('agents','skills'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                home=Path(d);external=self.symlinked_parents(home,kind);(external/'foreign').write_text('keep');targets=[external,external/'skills'] if kind=='agents' else [external];stamp=1_577_934_245_123_456_789
                for index,target in enumerate(targets): os.utime(target,ns=(stamp+index,stamp+index+10))
                env=self.review_env(home, PI_REVIEW_STACK_FAILPOINT='after-install');before_home=manifest(home);before_external=manifest(external);before_metadata=[self.metadata(target) for target in targets]
                result=subprocess.run(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.assertNotEqual(result.returncode,0);self.assertEqual(before_metadata,[self.metadata(target) for target in targets]);self.assertEqual(before_home,manifest(home));self.assertEqual(before_external,manifest(external))
    def test_transaction_signals_restore_and_return_shell_signal_codes(self):
        for signal_name,expected in (('SIGINT',130),('SIGTERM',143)):
            with self.subTest(signal=signal_name),tempfile.TemporaryDirectory() as d:
                home=Path(d);(home/'.pi').mkdir();(home/'.pi/foreign').write_text('old');marker=home/'paused';env=self.review_env(home, PI_REVIEW_STACK_TEST_PAUSE_MARKER=str(marker));before=manifest(home)
                process=subprocess.Popen(['bash','scripts/install-pi-transactionally.sh'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for _ in range(500):
                    if marker.exists(): break
                    __import__('time').sleep(.02)
                else: process.kill();self.fail('transaction did not reach signal failpoint')
                process.send_signal(getattr(__import__('signal'),signal_name));self.assertEqual(process.wait(timeout=30),expected);marker.unlink();self.assertEqual(before,manifest(home))
    def test_transaction_receipts_cover_success_and_rollback(self):
        for failpoint,expected_status,rollback_status in ((None,'success','not_needed'),('after-install','rolled_back','succeeded')):
            with self.subTest(failpoint=failpoint),tempfile.TemporaryDirectory() as d:
                home=Path(d);receipt=home/'receipt.json';extra={'PI_REVIEW_STACK_FAILPOINT':failpoint} if failpoint else {};env=self.review_env(home,**extra)
                result=subprocess.run(['bash','scripts/install-pi-transactionally.sh','--summary-json',str(receipt)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.assertEqual(0 if failpoint is None else 1,result.returncode)
                payload=json.loads(receipt.read_text());self.assertEqual('transaction',payload['command']);self.assertEqual(expected_status,payload['status']);self.assertEqual(rollback_status,payload['rollback']['status']);self.assertEqual(failpoint is not None,payload['rollback']['attempted']);self.assertEqual('pass',payload['transportProbe']['status']);self.assertEqual('scripts/pi-review-stack-managed-surfaces.json',payload['managedSurfaceManifest']['path']);self.assertEqual(0o600,stat.S_IMODE(receipt.stat().st_mode))
    def test_full_check_only_does_not_repair_settings_or_web_search(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);agent=home/'.pi/agent';agent.mkdir(parents=True);(agent/'settings.json').write_text(json.dumps({'defaultProvider':'foreign','defaultModel':'foreign','enabledModels':['foreign/model']}));(home/'.pi/web-search.json').write_text(json.dumps({'summaryModel':'foreign/model'}));bin_dir=home/'bin';bin_dir.mkdir();pi=bin_dir/'pi';pi.write_text('#!/bin/sh\nexit 1\n');pi.chmod(0o755);before=manifest(home);env={**os.environ,'HOME':d,'PATH':f'{bin_dir}:{os.environ["PATH"]}'}
            subprocess.run(['bash','scripts/verify-pi-install.sh','--check-only'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertEqual(before,manifest(home))
if __name__=='__main__':unittest.main()
