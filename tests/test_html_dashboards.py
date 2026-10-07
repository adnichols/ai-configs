import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

dashboard = module('dashboard', ROOT / 'skills/orchestrate/scripts/dashboard.py')
installer = module('installer', ROOT / '_codex/install-skills.py')

class Dashboards(unittest.TestCase):
    def test_current_priorities_legacy_unknowns_and_history(self):
        ledger = '''# Demo
Tracker: test-run
Mode: INTAKE
## Status
| ID | Title | State | Priority | Owner | Impact | Confidence | Evidence | Next action |
|---|---|---|---|---|---|---|---|---|
| WI-1 | Minor | BUILDING | P3 | Lee | Delay | suspected | https://example.test/a | Measure |
| WI-2 | Access | BLOCKED | P0 | Sam | Cannot sign in | confirmed | https://example.test/b | Recover |
| WI-3 | Old | DONE | P0 | Lee | Fixed | confirmed | | |
| WI-4 | Legacy | QUEUED | | | | | | |
## Operator decisions
- Earlier choice
'''
        out = dashboard.render(ledger, 'Demo', dashboard.TEMPLATE.read_text(), '2026-10-07')
        self.assertLess(out.index('WI-2'), out.index('WI-1'))
        self.assertLess(out.index('Completed items'), out.index('WI-3'))
        for text in ['test-run', '2026-10-07', 'Unassigned', 'Unclassified', 'Cannot sign in', 'Recover', 'https://example.test/b', 'Decision history']:
            self.assertIn(text, out)
        self.assertNotIn('{{', out)
        self.assertNotIn('prefers-color-scheme', out)
        self.assertNotIn('display:none', out)

    def test_saved_render_contract_rejects_content_loss_warning_and_stale_revision(self):
        source = '<style>p{color:var(--ava-fg,#222)}</style><p>Confirmed issue <a href="https://e.test/x">evidence</a></p>'
        saved = {'source': source, 'revision_id': 'r1'}
        rendered = {'html': source, 'warnings': [], 'revision_id': 'r1'}
        status = {'source_format': 'html', 'revision_id': 'r1'}
        dashboard.verify_html(source, saved, rendered, status, 'r1')
        for bad in [dict(rendered, html='<p>Confirmed issue</p>'), dict(rendered, warnings=[{'code': 'removed'}]), dict(rendered, revision_id='r2')]:
            with self.assertRaises(dashboard.Fail):
                dashboard.verify_html(source, saved, bad, status, 'r1')
        with self.assertRaises(dashboard.Fail):
            dashboard.verify_html(source, saved, rendered, dict(status, source_format='markdoc'), 'r1')

    def test_failed_render_never_marks_dashboard_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)/'dashboard.json'; ledger=Path(tmp)/'ledger.md'; ledger.write_text('# Demo')
            state.write_text(json.dumps({'plan_id':'doc', 'revision_id':'r0', 'web_url':'https://e.test/d'}))
            calls=[]
            def ava(*args, **kwargs):
                calls.append((args,kwargs))
                if args[1]=='status': return {'revision_id':'r0' if len(calls)<4 else 'r1', 'source_format':'html'}
                if args[1]=='plan-source': return {'source':'old' if len(calls)<4 else '<p>New</p>', 'revision_id':'r0' if len(calls)<4 else 'r1'}
                if args[1]=='edit': return {'revision_id':'r1'}
                if args[1]=='render': return {'revision_id':'r1','html':'<p>New</p>','warnings':[{'code':'removed'}]}
                raise AssertionError(args)
            with patch.object(dashboard,'ava',ava), patch.object(dashboard,'resolve_folder',return_value='folder'):
                with self.assertRaises(dashboard.Fail):
                    dashboard.publish('<p>New</p>', 'digest', 'Demo', 'space', state, ledger, '# Demo', True, ('Coding Work',))
            self.assertNotIn('digest',json.loads(state.read_text()))
            edit=next(x for x in calls if x[0][1]=='edit')
            self.assertIn('--expected-revision',edit[0])

    def test_lost_edit_reply_reconciles_without_duplicate_write_or_external_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'dashboard.json'; ledger=Path(tmp)/'ledger.md'; ledger.write_text('# Demo')
            state.write_text(json.dumps({'plan_id':'doc','revision_id':'r0','web_url':'https://e.test/d','source_digest':dashboard.digest('old')}))
            remote={'source':'old','revision_id':'r0'}; edits=[]
            def ava(*args, **kwargs):
                verb=args[1]
                if verb=='status': return {'revision_id':remote['revision_id'],'source_format':'html'}
                if verb=='plan-source': return dict(remote)
                if verb=='render': return {'html':remote['source'],'revision_id':remote['revision_id'],'warnings':[]}
                if verb=='edit':
                    edits.append((args,kwargs)); remote.update(source=kwargs['data']['source'],revision_id='r1')
                    raise dashboard.Fail(3,'reply lost')
                raise AssertionError(args)
            with patch.object(dashboard,'ava',ava), patch.object(dashboard,'resolve_folder',return_value='folder'), patch.object(dashboard,'place'):
                with self.assertRaises(dashboard.Fail): dashboard.publish('<p>New</p>','new','Demo','space',state,ledger,'# Demo',True,('Coding Work',))
                self.assertIn('pending_edit',json.loads(state.read_text()))
                dashboard.publish('<p>New</p>','new','Demo','space',state,ledger,'# Demo',True,('Coding Work',))
                self.assertEqual(len(edits),1)
                self.assertEqual(json.loads(state.read_text())['digest'],'new')
                remote.update(source='<p>Someone else</p>',revision_id='r2')
                with self.assertRaises(dashboard.Fail): dashboard.publish('<p>Next</p>','next','Demo','space',state,ledger,'# Demo',True,('Coding Work',))
                self.assertEqual(len(edits),1)


class ScopedInstall(unittest.TestCase):
    def test_codex_selected_repeat_and_preserve_local_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source'; codex=Path(tmp)/'codex'; home=Path(tmp)/'home'
            (root/'skills/one').mkdir(parents=True); (root/'skills/one/SKILL.md').write_text('new')
            (root/'skill-overrides.json').write_text(json.dumps({'skills':{'one':{'profile':'default'}}}))
            (codex/'skills/one').mkdir(parents=True); (codex/'skills/one/SKILL.md').write_text('old')
            (codex/'config.toml').write_text('preserve'); (codex/'unrelated').write_text('local')
            import hashlib
            (codex/'ai-configs-skills.json').write_text(json.dumps({'skills':['one'],'files':{'skills/one/SKILL.md':hashlib.sha256(b'old').hexdigest()}}))
            with patch.object(installer,'ROOT',root):
                installer.refresh_only(home,codex,['one']); installer.refresh_only(home,codex,['one'])
                self.assertEqual((codex/'skills/one/SKILL.md').read_text(),'new')
                (codex/'skills/one/SKILL.md').write_text('user edit')
                with self.assertRaises(ValueError): installer.refresh_only(home,codex,['one'])
            self.assertEqual((codex/'config.toml').read_text(),'preserve')
            self.assertEqual((codex/'unrelated').read_text(),'local')

    def test_shared_selected_repeat_and_preserve_local_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); dest=home/'.agents/skills/orchestrate';dest.mkdir(parents=True)
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            paths=subprocess.check_output(['git','ls-tree','-r','--name-only',commit,'--','skills/orchestrate'],cwd=ROOT,text=True).splitlines()
            for name in paths:
                p=dest/Path(name).relative_to('skills/orchestrate');p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT))
            (dest/'.ai-configs-managed.json').write_text(json.dumps({'repo':'ai-configs','source':'skills/orchestrate','managed':True,'commit':commit}))
            sentinel=home/'.agents/skills/untouched/SKILL.md';sentinel.parent.mkdir();sentinel.write_text('custom')
            env={**os.environ,'HOME':str(home)}
            for _ in range(2):
                result=subprocess.run(['bash','install.sh','--repo-skill','orchestrate'],cwd=ROOT,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr+result.stdout)
            (dest/'SKILL.md').write_text('local change')
            result=subprocess.run(['bash','install.sh','--repo-skill','orchestrate'],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual((dest/'SKILL.md').read_text(),'local change');self.assertEqual(sentinel.read_text(),'custom')

if __name__=='__main__': unittest.main()
