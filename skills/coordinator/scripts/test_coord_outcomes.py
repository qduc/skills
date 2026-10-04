"""Exercise outcome invariants through owner-fenced state and real processes."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import coord_outcomes as outcomes
import coord_runtime as runtime
import coord_state as tasks


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.workspace = self.project / 'work'
        self.workspace.mkdir()
        created = tasks.create(argparse.Namespace(title='Configuration compatibility', objective='Old and new configuration work',
                                                   project=str(self.project), conversation=None, owner='coordinator'), self.root)
        self.task_dir = Path(created['state_path']).parent
        self.route = {'harness': 'fixture', 'model': 'controlled'}
        state = tasks.load(self.task_dir)
        state['selection'] = [self.route]
        state['details']['authority'] = 'Write config artifacts inside the assigned workspace; no publication'
        state['details']['acceptance_criteria'] = ['Both old and new configuration are usable together']
        tasks.save(self.task_dir, state)
        self.spec = {'outcomes': [self.spec_for('config')], 'goal_checks': [self.check('compatibility',
                     "import json,pathlib; p=pathlib.Path('integrated.json'); assert json.loads(p.read_text()) == {'version': 2}")]}
        self.call(lambda s,p: outcomes.initialize(s, self.spec))

    def check(self, cid, script):
        return {'id': cid, 'argv': [sys.executable, '-c', script]}

    def spec_for(self, oid, needs=None):
        return {'id': oid, 'objective': 'Produce configuration version 2', 'rationale': 'Enable the new consumer',
                'scope': 'One configuration file in the assigned workspace', 'authority': 'Write local artifacts only',
                'cwd': str(self.workspace), 'needs': needs or [],
                'checks': [self.check('format', "import json,pathlib; assert json.loads(pathlib.Path('result.json').read_text()) == {'version': 2}")]}

    def call(self, action, owner='coordinator', revision='latest'):
        return outcomes.mutate(self.task_dir, owner, revision, action)['result']

    def state(self):
        return tasks.load(self.task_dir)

    def native(self, oid='config', method='bounded_worker', catalogs=None):
        response = self.call(lambda s,p: runtime.start(s,p,oid,'native',self.route,method,catalogs or []))
        self.call(lambda s,p: runtime.bind_native(s,oid,response['attempt_id'],'host-'+oid))
        return Path(response['assignment_file'])

    def candidate(self, content='{"version":2}', oid='config', claim=False):
        assignment = self.native(oid)
        artifact = self.workspace / 'result.json'
        artifact.write_text(content)
        report = Path(outcomes.report(assignment, artifact)['report'])
        if claim:
            payload = json.loads(report.read_text())
            payload.update(accepted=True, status='completed', tests_passed=True)
            report.write_text(json.dumps(payload))
        self.call(lambda s,p: runtime.observe(s,oid,{'handle':'host-'+oid,'status':'finished'}))
        return artifact, report

    def accept_and_integrate(self):
        artifact, report = self.candidate()
        self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        self.call(lambda s,p: outcomes.accept(s,'config','Inspected config bytes and independent format check'))
        target = self.project/'integrated.json'
        shutil.copyfile(artifact,target)
        self.call(lambda s,p: outcomes.integrate(s,'config',target))
        return artifact, report, target

    def test_full_loop_requires_separate_acceptance_and_goal_verification(self):
        self.accept_and_integrate()
        with self.assertRaisesRegex(tasks.StateError,'goal verification'):
            tasks.apply_patch(self.state(), {'status':'completed'})
        gate = self.call(lambda s,p: outcomes.verify_goal(s,5))
        self.assertEqual(gate['checks'][0]['exit_code'],0)
        state=self.state()
        tasks.apply_patch(state,{'status':'completed'})
        self.assertEqual(state['status'],'completed')

    def test_worker_claim_does_not_accept_broken_result(self):
        artifact, report = self.candidate('{"version":1}',claim=True)
        verification=self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        self.assertNotEqual(verification['checks'][0]['exit_code'],0)
        with self.assertRaisesRegex(tasks.StateError,'verification failed'):
            self.call(lambda s,p: outcomes.accept(s,'config','Worker says tests passed'))
        self.assertNotIn('acceptance',self.state()['outcome_plan']['outcomes']['config'])

    def test_finished_and_verified_are_not_accepted(self):
        artifact,report=self.candidate()
        self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        with self.assertRaisesRegex(tasks.StateError,'not accepted'):
            self.call(lambda s,p: outcomes.integrate(s,'config',artifact))

    def test_changed_artifact_blocks_acceptance(self):
        artifact,report=self.candidate()
        self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        artifact.write_text('{"version":3}')
        with self.assertRaisesRegex(tasks.StateError,'evidence changed'):
            self.call(lambda s,p: outcomes.accept(s,'config','Inspected'))

    def test_changed_report_blocks_acceptance(self):
        artifact,report=self.candidate()
        self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        report.write_text('{}')
        with self.assertRaisesRegex(tasks.StateError,'evidence changed'):
            self.call(lambda s,p: outcomes.accept(s,'config','Inspected'))

    def test_verification_rejects_live_worker(self):
        assignment=self.native()
        artifact=self.workspace/'result.json'; artifact.write_text('{"version":2}')
        report=outcomes.report(assignment,artifact)['report']
        with self.assertRaisesRegex(tasks.StateError,'settle'):
            self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))

    def test_unrelated_checkpoint_preserves_acceptance(self):
        self.accept_and_integrate()
        self.call(lambda s,p: tasks.apply_patch(s,{'details':{'next_action':'Inspect combined behavior'}}))
        self.assertTrue(outcomes.accepted(self.state(),'config'))

    def test_obsolete_assignment_report_rejected_after_revision(self):
        artifact,report=self.candidate()
        self.call(lambda s,p: outcomes.revise(s,'config',self.spec_for('config')))
        self.native()
        with self.assertRaisesRegex(tasks.StateError,'assignment_id'):
            self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))

    def test_revision_invalidates_transitive_dependents_only(self):
        state=self.state()
        state.pop('outcome_plan'); state['details']['work_items']=[]
        spec={'outcomes':[self.spec_for('config'),self.spec_for('consumer',['config']),
                          self.spec_for('docs',['consumer']),self.spec_for('independent')],
              'goal_checks':self.spec['goal_checks']}
        outcomes.initialize(state,spec); tasks.save(self.task_dir,state)
        original={k:v['assignment_id'] for k,v in state['outcome_plan']['outcomes'].items()}
        result=self.call(lambda s,p: outcomes.revise(s,'config',self.spec_for('config')))
        self.assertEqual(result['invalidated'],['config','consumer','docs'])
        after=self.state()['outcome_plan']['outcomes']
        self.assertEqual(after['independent']['assignment_id'],original['independent'])
        self.assertNotEqual(after['docs']['assignment_id'],original['docs'])

    def test_dependency_must_be_integrated_before_dispatch(self):
        state=self.state(); state.pop('outcome_plan'); state['details']['work_items']=[]
        outcomes.initialize(state,{'outcomes':[self.spec_for('config'),self.spec_for('consumer',['config'])],
                                   'goal_checks':self.spec['goal_checks']}); tasks.save(self.task_dir,state)
        with self.assertRaisesRegex(tasks.StateError,'integration'):
            self.native('consumer')
        self.assertNotIn('attempt',self.state()['outcome_plan']['outcomes']['consumer'])

    def test_wrong_integrated_bytes_rejected(self):
        artifact,report=self.candidate()
        self.call(lambda s,p: outcomes.verify_result(s,'config',report,5))
        self.call(lambda s,p: outcomes.accept(s,'config','Inspected'))
        target=self.project/'integrated.json'; target.write_text('{"version":1}')
        with self.assertRaisesRegex(tasks.StateError,'bytes differ'):
            self.call(lambda s,p: outcomes.integrate(s,'config',target))

    def test_goal_failure_prevents_completion_when_local_checks_pass(self):
        self.accept_and_integrate()
        # A separate behavioral gate fails despite structurally valid artifacts.
        self.call(lambda s,p:s['outcome_plan'].update(goal_checks=[self.check('compatibility','raise SystemExit(1)')]))
        gate=self.call(lambda s,p:outcomes.verify_goal(s,5))
        self.assertEqual(gate['checks'][0]['exit_code'],1)
        with self.assertRaisesRegex(tasks.StateError,'goal verification'):
            tasks.apply_patch(self.state(),{'status':'completed'})

    def test_integration_before_checkpoint_is_reconciled_in_fresh_process(self):
        artifact,report=self.candidate()
        self.call(lambda s,p:outcomes.verify_result(s,'config',report,5))
        self.call(lambda s,p:outcomes.accept(s,'config','Inspected'))
        target=self.project/'integrated.json'; shutil.copyfile(artifact,target)
        self.assertNotIn('integration',self.state()['outcome_plan']['outcomes']['config'])
        result=subprocess.run([sys.executable,str(Path(outcomes.__file__)),'integrate','--task-dir',str(self.task_dir),
                              '--owner','coordinator','--revision','latest','--outcome','config','--artifact',str(target)],
                              capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(outcomes.integrated(self.state(),'config')['artifact'],outcomes.file_ref(target))

    def test_takeover_fences_old_owner_before_any_launch(self):
        self.call(lambda s,p:s.update(owner='replacement'))
        with patch.object(runtime.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(tasks.StateError,'not owned'):
                self.call(lambda s,p:runtime.start(s,p,'config','process',self.route,'bounded_worker',[],[sys.executable,'-c','pass']))
            launch.assert_not_called()

    def test_stale_revision_cannot_start_worker(self):
        revision=self.state()['revision']; self.call(lambda s,p:s['details'].update(next_action='Continue'))
        with self.assertRaisesRegex(tasks.StateError,'stale revision'):
            self.call(lambda s,p:runtime.start(s,p,'config','native',self.route,'bounded_worker',[]),revision=revision)

    def test_native_uncertain_delivery_does_not_redispatch(self):
        self.call(lambda s,p:runtime.start(s,p,'config','native',self.route,'bounded_worker',[]))
        self.assertEqual(self.call(lambda s,p:runtime.observe(s,'config'))['status'],'unknown')
        with self.assertRaisesRegex(tasks.StateError,'already recorded'):
            self.native()
        with self.assertRaisesRegex(tasks.StateError,'settle'):
            self.call(lambda s,p:outcomes.revise(s,'config',self.spec_for('config')))

    def test_native_non_delivery_requires_explicit_evidenced_reconciliation(self):
        started=self.call(lambda s,p:runtime.start(s,p,'config','native',self.route,'bounded_worker',[]))
        evidence=self.root/'host-inspection.json'
        evidence.write_text(json.dumps({'attempt_id':started['attempt_id'],'status':'not_started',
                                       'basis':'Host inventory inspected: this saved request was never delivered'}))
        with self.assertRaisesRegex(tasks.StateError,'current attempt'):
            self.call(lambda s,p:runtime.reconcile(s,'config','stale',evidence,'Inspected host'))
        self.call(lambda s,p:runtime.reconcile(s,'config',started['attempt_id'],evidence,'Confirmed non-delivery via host inventory'))
        self.assertEqual(self.state()['outcome_plan']['outcomes']['config']['attempt']['status'],'stopped')
        self.call(lambda s,p:outcomes.revise(s,'config',self.spec_for('config')))
        self.native()

    def test_lost_launcher_requires_explicit_reconciliation_after_actual_exit(self):
        started=self.call(lambda s,p:runtime.start(s,p,'config','process',self.route,'bounded_worker',[],
                                                  [sys.executable,'-c','import time;time.sleep(0.4)']))
        receipt_path=Path(started['receipt']); deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if receipt_path.exists():
                receipt=json.loads(receipt_path.read_text())
                if receipt['status']=='working': break
            time.sleep(0.01)
        self.assertEqual(receipt['status'],'working')
        launcher=runtime._LAUNCHERS.pop(started['attempt_id'])
        launcher.kill(); launcher.wait(timeout=3)
        evidence=self.root/'process-inspection.json'
        evidence.write_text(json.dumps({'attempt_id':started['attempt_id'],'status':'stopped','basis':'Inspected known launcher and worker process identities'}))
        with self.assertRaisesRegex(tasks.StateError,'remain live'):
            self.call(lambda s,p:runtime.reconcile(s,'config',started['attempt_id'],evidence,'Inspect known resources'))
        while runtime.process_identity(receipt['pid']) and time.monotonic()<deadline: time.sleep(0.01)
        self.assertIsNone(runtime.process_identity(receipt['pid']))
        self.assertEqual(self.call(lambda s,p:runtime.observe(s,'config'))['status'],'unknown')
        self.call(lambda s,p:runtime.reconcile(s,'config',started['attempt_id'],evidence,'Confirmed stopped resources after launcher loss'))
        self.call(lambda s,p:outcomes.revise(s,'config',self.spec_for('config')))

    def test_changed_report_after_acceptance_blocks_goal_completion(self):
        artifact,report,target=self.accept_and_integrate()
        self.call(lambda s,p:outcomes.verify_goal(s,5))
        report.write_text('{}')
        with self.assertRaisesRegex(tasks.StateError,'evidence changed'):
            tasks.apply_patch(self.state(),{'status':'completed'})

    def test_missing_protocol_falls_back_and_installed_protocol_is_pinned(self):
        catalog=self.root/'catalog'; skill=catalog/'architect'/'SKILL.md'; skill.parent.mkdir(parents=True)
        skill.write_text('---\nname: architect\ndescription: engineering method\n---\nInspect configuration compatibility.\n')
        assignment=self.native(method='architect',catalogs=[catalog])
        payload=json.loads(assignment.read_text())
        self.assertEqual(payload['method']['event'],'protocol_selected')
        skill.write_text('changed after dispatch')
        self.assertIn('Inspect configuration',Path(payload['method']['skill']).read_text())

    def test_native_host_observation_requires_matching_handle(self):
        self.native()
        with self.assertRaisesRegex(tasks.StateError,'bound native handle'):
            self.call(lambda s,p:runtime.observe(s,'config',{'handle':'another-worker','status':'finished'}))

    def test_scope_and_confirmed_route_enforced(self):
        assignment=self.native()
        outside=self.root/'outside.json'; outside.write_text('{}')
        with self.assertRaisesRegex(tasks.StateError,'outside'):
            outcomes.report(assignment,outside)
        self.call(lambda s,p:runtime.observe(s,'config',{'handle':'host-config','status':'finished'}))
        self.call(lambda s,p:outcomes.revise(s,'config',self.spec_for('config')))
        with self.assertRaisesRegex(tasks.StateError,'confirmed selection'):
            self.call(lambda s,p:runtime.start(s,p,'config','native',{'harness':'other','model':'other'},'bounded_worker',[]))

    def test_goal_or_authority_change_requires_replanning(self):
        self.call(lambda s,p:s['details'].update(authority='Different authority'))
        with self.assertRaisesRegex(tasks.StateError,'explicitly replan'):
            self.native()

    def test_timeout_is_failed_evidence(self):
        evidence=outcomes.run_checks([self.check('slow','import time; time.sleep(1)')],self.workspace,0.01)
        self.assertIsNone(evidence[0]['exit_code'])
        self.assertFalse(outcomes.passed(evidence,[self.check('slow','import time; time.sleep(1)')]))

    def test_changed_goal_allows_settlement_before_replanning(self):
        self.native()
        self.call(lambda s,p:tasks.apply_patch(s,{'details':{'authority':'Updated local authority'}}))
        self.assertEqual(self.call(lambda s,p:runtime.control(s,'config','stop'))['request']['action'],'stop')
        self.call(lambda s,p:runtime.observe(s,'config',{'handle':'host-config','status':'finished'}))
        self.call(lambda s,p:outcomes.replan(s,self.spec,'User changed authority; old attempt settled'))
        self.assertEqual(self.state()['outcome_plan']['goal']['authority'],'Updated local authority')
        self.assertEqual(len(self.state()['outcome_history']),1)

    def test_failed_receipt_publication_never_settles_a_live_worker(self):
        directory=self.root/'launch'; directory.mkdir()
        (directory/'launch.json').write_text(json.dumps({'attempt_id':'fault','argv':[sys.executable,'-c','import time;time.sleep(30)'],'cwd':str(self.workspace)}))
        original=tasks.atomic_write; calls=[]; processes=[]; popen=subprocess.Popen
        def write(path,data):
            calls.append(path)
            if len(calls)==2: raise OSError('injected receipt publication failure')
            return original(path,data)
        def spawn(*args,**kwargs):
            process=popen(*args,**kwargs); processes.append(process); return process
        try:
            with patch.object(tasks,'atomic_write',side_effect=write), patch.object(runtime.subprocess,'Popen',side_effect=spawn):
                runtime.launch(directory)
            receipt=json.loads((directory/'receipt.json').read_text())
            self.assertEqual(receipt['status'],'failed')
            self.assertIsNotNone(processes[0].poll(),'terminal receipt requires settled worker')
        finally:
            for process in processes:
                if process.poll() is None: process.kill(); process.wait()

    def test_non_utf8_check_output_preserves_exit_status(self):
        evidence=outcomes.run_checks([self.check('binary','import os;os.write(1,bytes([255]))')],self.workspace,5)
        self.assertEqual(evidence[0]['exit_code'],0)

    def test_check_timeout_settles_subprocess_descendants(self):
        marker=self.root/'late-check-write'
        child=f"import time,pathlib;time.sleep(0.3);pathlib.Path({str(marker)!r}).write_text('late')"
        code=f"import subprocess,sys;subprocess.run([sys.executable,'-c',{child!r}])"
        evidence=outcomes.run_checks([self.check('spawn',code)],self.workspace,0.05)
        self.assertIsNone(evidence[0]['exit_code'])
        time.sleep(0.4)
        self.assertFalse(marker.exists(),'timed-out check left a writing descendant')

    def test_process_receipt_waits_for_descendant_settlement(self):
        marker=self.root/'late-worker-write'
        child=f"import time,pathlib;time.sleep(0.3);pathlib.Path({str(marker)!r}).write_text('late')"
        code=f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}])"
        directory=self.root/'descendant'; directory.mkdir()
        (directory/'launch.json').write_text(json.dumps({'attempt_id':'child','argv':[sys.executable,'-c',code],'cwd':str(self.workspace)}))
        runtime.launch(directory)
        self.assertEqual(json.loads((directory/'receipt.json').read_text())['status'],'finished')
        time.sleep(0.4)
        self.assertFalse(marker.exists(),'finished receipt left a writing descendant')

    def test_process_runtime_executes_and_recovers_without_coordinator(self):
        reporter=Path(outcomes.__file__).resolve()
        worker=self.root/'worker.py'
        worker.write_text("import pathlib, subprocess, sys\npathlib.Path('result.json').write_text('{\"version\":2}')\n"
                          f"subprocess.run([sys.executable,{str(reporter)!r},'report','--assignment-file',sys.argv[1],"
                          "'--artifact',str(pathlib.Path('result.json').resolve())],check=True)\n")
        started=self.call(lambda s,p:runtime.start(s,p,'config','process',self.route,'bounded_worker',[],
                                                  [sys.executable,str(worker),'{assignment}']))
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                observation=self.call(lambda s,p:runtime.observe(s,'config'))
            except tasks.StateError as error:
                if 'busy' not in str(error): raise
                time.sleep(0.02)
                continue
            if observation['status']=='finished': break
            time.sleep(0.02)
        self.assertEqual(observation['status'],'finished')
        self.assertEqual(len(observation['reports']),1)
        self.call(lambda s,p:outcomes.verify_result(s,'config',observation['reports'][0],5))
        self.call(lambda s,p:outcomes.accept(s,'config','Inspected process-produced artifact'))
        self.assertEqual(self.state()['outcome_plan']['outcomes']['config']['attempt']['receipt']['exit_code'],0)
        with self.assertRaisesRegex(tasks.StateError,'already recorded'):
            self.call(lambda s,p:runtime.start(s,p,'config','process',self.route,'bounded_worker',[],[sys.executable,'-c','pass']))

    def test_process_capabilities_refuse_correction(self):
        self.assertFalse(runtime.capabilities('process')['correct'])
        state=self.state()
        state['outcome_plan']['outcomes']['config']['attempt']={'runtime':'process','id':'x','status':'working'}
        with self.assertRaisesRegex(tasks.StateError,'cannot accept'):
            runtime.control(state,'config','correct','new brief')

    def test_missing_process_identity_is_unknown_not_live(self):
        self.native()
        directory=self.root/'fast-worker'; directory.mkdir()
        (directory/'launch.json').write_text(json.dumps({'attempt_id':'fast','argv':['/usr/bin/true'],'cwd':str(self.workspace)}))
        original=tasks.atomic_write
        def write(path,data):
            if Path(path).name=='receipt.json' and json.loads(data)['status'] in {'finished','failed'}:
                raise OSError('injected terminal receipt publication failure')
            return original(path,data)
        with patch.object(runtime,'process_identity',return_value=None), patch.object(tasks,'atomic_write',side_effect=write):
            with self.assertRaises(OSError): runtime.launch(directory)
        receipt=json.loads((directory/'receipt.json').read_text())
        self.assertIsNone(receipt['identity'])
        self.assertFalse(runtime.coord_process.live_group(receipt['pid']))
        def fixture(state,path):
            attempt=state['outcome_plan']['outcomes']['config']['attempt']
            attempt.update(id='fast',runtime='process',run_dir=str(directory),status='unknown')
        self.call(fixture)
        self.assertEqual(self.call(lambda s,p:runtime.observe(s,'config'))['status'],'unknown')
        evidence=self.root/'fast-inspection.json'
        evidence.write_text(json.dumps({'attempt_id':'fast','status':'stopped','basis':'Known worker and group have exited; terminal receipt lost'}))
        self.call(lambda s,p:runtime.reconcile(s,'config','fast',evidence,'Confirmed actual exit'))

    def test_legacy_task_remains_readable_without_outcome_plan(self):
        fixture=Path(__file__).with_name('fixtures')/'v1-task-state.json'
        state=json.loads(fixture.read_text()); directory=self.root/'tasks'/state['id']; directory.mkdir()
        (directory/'state.json').write_text(json.dumps(state))
        self.assertEqual(tasks.load(directory),state)


if __name__=='__main__':
    unittest.main()
