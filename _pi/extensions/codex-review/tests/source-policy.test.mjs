import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';
import {isForbiddenDirectReviewToolCall} from '../runtime.ts';

const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../..');
const workflows=[
  ['skills/autoreview/SKILL.md','pre-pr-implementation'],
  ['skills/run-plan/SKILL.md','run-plan-pm'],
  ['skills/reviewed-html-plan/SKILL.md','reviewed-html-plan'],
];
const aliasRouting=/\bcodex_review\b|\bclaude_review\b|run-review\.sh|codex exec review|verdictProfile|reviewType|action\s*:\s*["']start["']/;

test('maintained Pi workflows and review skill select codex_review without Pi-wrapper contradictions',async()=>{
  for(const [file,profile] of workflows){
    const text=await readFile(path.join(repo,file),'utf8');
    assert.match(text,/codex_review/);
    assert.match(text,new RegExp(`verdictProfile[\\s\\S]{0,120}${profile}`));
    assert.doesNotMatch(text,/In Pi[^\n]*(Codex[^\n]*subprocess|wrapper|run Codex as)/i);
  }
  const alias=await readFile(path.join(repo,'skills/pre-pr-implementation-review/SKILL.md'),'utf8');
  assert.match(alias,/\/skill:autoreview/);
  assert.doesNotMatch(alias,aliasRouting);
  assert.throws(()=>assert.doesNotMatch(`${alias}\ncodex_review({reviewType:"implementation-review",verdictProfile:"generic-implementation",action:"start"})`,aliasRouting));
  const partner=await readFile(path.join(repo,'skills/codex-review-partner/SKILL.md'),'utf8');
  assert.match(partner,/In Pi, required Codex review legs must use the managed `codex_review` tool/);
  for(const contradiction of [/running from Pi[^\n]*wrapper/i,/Pi[^\n]*subprocess wrapper/i,/another runtime, such as Pi[^\n]*wrapper/i]) assert.doesNotMatch(partner,contradiction);
});

test('all blocked signatures include a valid compatible replacement',()=>{
  for(const command of ['bash run-review.sh --mode implementation-review --input p','run-review.sh --mode adversarial-implementation-review --input p','codex exec review --base main']){
    const got=isForbiddenDirectReviewToolCall('bash',{command});
    assert.equal(got.blocked,true);
    assert.match(got.reason,/action:"start"/);
    assert.match(got.reason,/reviewType:/);
    assert.match(got.reason,/verdictProfile:/);
    assert.match(got.reason,/promptFile:/);
    assert.match(got.reason,/output:/);
    assert.match(got.reason,/cwd:/);
  }
});

test('extension exposes a visible pending subprocess row without depending on overlay/process extensions',async()=>{
  for(const file of ['runtime.ts','index.ts']){
    const text=await readFile(path.join(repo,'_pi/extensions/codex-review',file),'utf8');
    assert.doesNotMatch(text,/pi-interactive-shell|pi-processes/);
    if(file==='index.ts'){
      assert.match(text,/reviewer subprocess running/);
      assert.match(text,/phase: "running"/);
      assert.match(text,/renderResult/);
      assert.doesNotMatch(text,/dispatched invisibly/);
    }
  }
});

test('completion delivery is bound to the originating Pi session',async()=>{
  const index=await readFile(path.join(repo,'_pi/extensions/codex-review/index.ts'),'utf8');
  const runtime=await readFile(path.join(repo,'_pi/extensions/codex-review/runtime.ts'),'utf8');
  assert.match(index,/sessionManager\.getSessionId\(\)/);
  assert.match(index,/originSessionId/);
  assert.match(runtime,/job\.originSessionId !== this\.activeSessionId/);
  assert.match(runtime,/if \(!job\.originSessionId\)/);
});

test('portable review paths do not reintroduce Linux-only shell or proc assumptions',async()=>{
  const runtime=await readFile(path.join(repo,'_pi/extensions/codex-review/runtime.ts'),'utf8');
  const launcher=await readFile(path.join(repo,'skills/codex-review-partner/scripts/run-review.sh'),'utf8');
  const contract=await readFile(path.join(repo,'skills/codex-review-partner/tests/test_run_review_contract.sh'),'utf8');
  assert.doesNotMatch(runtime,/\/proc\//);
  assert.doesNotMatch(launcher,/\bsetsid\s+python|\/proc\/|stat -c|prctl/);
  assert.doesNotMatch(contract,/stat -c|\/proc\//);
  assert.match(launcher,/process_identity\.py/);
  assert.match(launcher,/review_supervisor\.py/);
});
