import importlib.util,json,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('audit_codex',Path(__file__).resolve().parents[1]/'audit-codex-review-sessions.py');MOD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MOD);audit=MOD.audit
class AuditTest(unittest.TestCase):
    def state(self,jobs,name,**kw):
        base={'jobId':name,'jobNonce':f'nonce-{name}','action':'start','verdictProfile':'generic-implementation','status':'failed','classification':'CODEX_REVIEW_LAUNCH_FAILED','output':str(jobs/f'{name}.md'),'stdoutLog':str(jobs/f'{name}.stdout.jsonl'),'deliveryId':f'delivery-{name}','deliveryState':'delivered'};base.update(kw);(jobs/f'{name}.state.json').write_text(json.dumps(base));return base
    def delivery(self,sessions,delivery_id):
        sessions.mkdir(exist_ok=True);row={'type':'custom_message','customType':'codex-review-completion','content':'bounded status only','details':{'deliveryId':delivery_id}};with_file=sessions/f'{delivery_id.replace("/","-")}.jsonl';with_file.write_text(json.dumps(row)+'\n')
    def codex_thread(self,jobs,codex_sessions,name,thread_id=None,session_ids=None):
        thread_id=thread_id or f'feedface-{name}-1234';(jobs/f'{name}.stdout.jsonl').write_text(json.dumps({'type':'thread.started','thread_id':thread_id,'prompt':'must not be retained'})+'\n')
        codex_sessions.mkdir(exist_ok=True)
        for index,value in enumerate(session_ids if session_ids is not None else [thread_id]):
            (codex_sessions/f'{name}-{index}.jsonl').write_text(json.dumps({'type':'thread.started','thread_id':value,'output':'private'})+'\n')
    def test_truthful_passing_terminal_cases(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);jobs=root/'jobs';jobs.mkdir();sessions=root/'sessions';codex=root/'codex-sessions'
            for name,token,profile in [('clean','CLEAN_FOR_PR','generic-implementation'),('pm','PASS_SCOPED','run-plan-pm'),('plan','PLAN_EXECUTION_READY','reviewed-html-plan')]:
                (jobs/f'{name}.md').write_text(f'body\nVERDICT: {token}\n');self.state(jobs,name,status='succeeded',classification='CODEX_REVIEW_SUCCEEDED',verdict=token,verdictProfile=profile);self.delivery(sessions,f'delivery-{name}');self.codex_thread(jobs,codex,name)
            self.state(jobs,'shutdown',status='cancelled',classification='CODEX_REVIEW_CANCELLED',cancellationReason='session_shutdown',deliveryState='ineligible')
            self.assertEqual(audit(root,True,sessions,codex)[1],[])
    def test_missing_duplicate_and_profile_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);jobs=root/'jobs';jobs.mkdir();sessions=root/'sessions';sessions.mkdir()
            self.state(jobs,'missing')
            self.state(jobs,'duplicate');self.delivery(sessions,'delivery-duplicate');duplicate=sessions/'duplicate-2.jsonl';duplicate.write_text((sessions/'delivery-duplicate.jsonl').read_text())
            (jobs/'profile.md').write_text('body\nVERDICT: PASS_SCOPED\n');self.state(jobs,'profile',status='succeeded',classification='CODEX_REVIEW_SUCCEEDED',verdict='PASS_SCOPED',verdictProfile='generic-implementation');self.delivery(sessions,'delivery-profile')
            errors='\n'.join(audit(root,True,sessions)[1]);self.assertIn('delivery count is 0',errors);self.assertIn('delivery count is 2',errors);self.assertIn('selected profile',errors)
    def test_manual_cancellation_requires_delivery_but_shutdown_forbids_it(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);jobs=root/'jobs';jobs.mkdir();sessions=root/'sessions';sessions.mkdir();self.state(jobs,'manual',status='cancelled',classification='CODEX_REVIEW_CANCELLED',cancellationReason='user',deliveryState='pending');self.state(jobs,'shutdown',status='cancelled',classification='CODEX_REVIEW_CANCELLED',cancellationReason='session_shutdown',deliveryState='ineligible');self.delivery(sessions,'delivery-shutdown');errors='\n'.join(audit(root,True,sessions)[1]);self.assertIn('manual.state.json: eligible completion delivery count is 0',errors);self.assertIn('notification-ineligible completion was delivered',errors)
    def test_codex_session_missing_duplicate_and_thread_mismatch_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);jobs=root/'jobs';jobs.mkdir();sessions=root/'sessions';codex=root/'codex-sessions';sessions.mkdir();codex.mkdir()
            for name in ('missing','duplicate','mismatch'):
                self.state(jobs,name,classification='CODEX_REVIEW_CODEX_EXIT_NONZERO');self.delivery(sessions,f'delivery-{name}')
            self.codex_thread(jobs,codex,'missing',session_ids=[])
            self.codex_thread(jobs,codex,'duplicate',session_ids=['feedface-duplicate-1234','feedface-duplicate-1234'])
            self.codex_thread(jobs,codex,'mismatch',thread_id='feedface-wanted-1234',session_ids=['feedface-other-1234'])
            errors='\n'.join(audit(root,True,sessions,codex)[1]);self.assertIn('missing.state.json: Codex session count',errors);self.assertIn('duplicate.state.json: Codex session count',errors);self.assertIn('mismatch.state.json: Codex session count',errors)
    def test_job_filter_is_bounded_and_rejects_missing_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);jobs=root/'jobs';jobs.mkdir();sessions=root/'sessions';codex=root/'codex-sessions';self.state(jobs,'selected');self.delivery(sessions,'delivery-selected');self.state(jobs,'ignored')
            count,errors=audit(root,True,sessions,codex,{'selected'});self.assertEqual((count,errors),(1,[]))
            count,errors=audit(root,True,sessions,codex,{'absent'});self.assertEqual(count,0);self.assertIn('requested jobId absent',errors[0])
if __name__=='__main__':unittest.main()
