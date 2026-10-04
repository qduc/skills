#!/usr/bin/env python3
"""Opt-in live release gate. Prepare isolated tasks; host delivers native requests.

Usage: prepare ROOT; start ROOT INDEX; bind ROOT INDEX HANDLE;
finish ROOT INDEX [HANDLE]. This does not choose a provider or spawn native agents.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import coord_outcomes as outcomes
import coord_runtime as runtime
import coord_state as tasks

OWNER = 'release-gate'
LOCAL = '''import importlib.util,sys
s=importlib.util.spec_from_file_location('candidate',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert m.load_config({'port':9000}) == {'port':9000}
assert m.load_config({'server':{'port':1234}}) == {'port':1234}
'''
GLOBAL = LOCAL + '''
assert m.load_config({}) == {'port':8080}
for port in [1,80,65535]:
 assert m.load_config({'port':port}) == {'port':port}
 assert m.load_config({'server':{'port':port}}) == {'port':port}
for bad in [None,[],{'port':True},{'port':0},{'port':65536},{'port':'80'},
            {'server':[]},{'server':{'port':-1}}, {'port':80,'server':{'port':80}}]:
 try: m.load_config(bad)
 except ValueError: pass
 else: raise AssertionError('accepted invalid config: '+repr(bad))
'''


def write(path, data):
    tasks.atomic_write(path, json.dumps(data, indent=2) + '\n')


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    settings = json.loads((Path.home()/'.local/state/term2-nodejs/settings.json').read_text())['agent']
    route = {'harness':'term2', 'model':settings['model'], 'provider':settings['provider']}
    if route['provider'] == 'openrouter':
        raise tasks.StateError('this gate does not authorize OpenRouter')
    native = {'harness':'native', 'model':'inherited-parent'}
    catalog = root/'catalog'
    skill = catalog/'architect'/'SKILL.md'; skill.parent.mkdir(parents=True)
    tasks.atomic_write(skill, '---\nname: architect\ndescription: Compatibility design evaluation protocol\n---\n'
                       'Inspect the existing loader and configuration interface. State the compatibility invariants. '
                       'Implement the smallest coherent change, and run the supplied checks. '
                       'Keep the outcome contract and authority fixed. This protocol never grants acceptance authority.\n')
    runs = []
    for engine in ('native','process'):
        for method in ('bounded_worker','architect'):
            for repeat in range(3):
                index=len(runs); project=root/f'run-{index:02d}'; project.mkdir()
                work=project/'work'; work.mkdir()
                tasks.atomic_write(work/'loader.py', "def load_config(config):\n    return {'port': config.get('port', 8080)}\n")
                tasks.atomic_write(project/'local_check.py', LOCAL)
                tasks.atomic_write(project/'goal_check.py', GLOBAL)
                created=tasks.create(argparse.Namespace(title=f'Live {engine} {method} {repeat+1}',
                    objective='Preserve legacy config and support nested config through one validated loader',
                    project=str(project),conversation=None,owner=OWNER),root/'state')
                task=Path(created['state_path']).parent
                selected=route if engine=='process' else native
                state=tasks.load(task)
                state['selection']=[selected]
                state['details']['authority']='Local isolated evaluation artifacts and reports only; no publication or child agents'
                state['details']['acceptance_criteria']=['Legacy and nested configs work; invalid ports raise ValueError; independent integrated checks pass']
                state['choice_events'].append({'id':uuid.uuid4().hex,'task_id':state['id'],'at':tasks.now(),'source':'user', 'pool':[selected],
                    'reason':'User authorized native and Term2 live gate; Term2 uses configured model'})
                tasks.save(task,state)
                spec={'outcomes':[{'id':'loader','objective':
                    'Update loader.py: load_config(config) returns {"port": int}. Support legacy {"port":N}, nested {"server":{"port":N}}, and {} default 8080. '
                    'Reject non-dicts, mixed legacy/nested forms, non-dict server, boolean/non-integer ports and ports outside 1..65535 with ValueError.',
                    'rationale':'Consumers must migrate without breaking valid legacy configurations',
                    'scope':'Edit only loader.py inside contract.cwd; read and run the supplied check files. Publish loader.py as the artifact.',
                    'authority':'Write loader.py and an attempt report only. Do not edit tests, state, descriptor or protocol snapshot.',
                    'cwd':str(work),'needs':[], 'checks':[{'id':'local-compatibility','argv':[sys.executable,str(project/'local_check.py'),str(work/'loader.py')]}]}],
                    'goal_checks':[{'id':'integrated-compatibility','argv':[sys.executable,str(project/'goal_check.py'),str(project/'integrated.py')]}]}
                outcomes.mutate(task,OWNER,'latest',lambda s,p:outcomes.initialize(s,spec))
                runs.append({'index':index,'runtime':engine,'method':method,'repeat':repeat+1,
                             'task_dir':str(task),'route':selected,'project':str(project)})
    write(root/'runs.json',runs)
    return {'runs':len(runs),'term2_route':route,'catalog':str(catalog)}


def mutate(run, action):
    return outcomes.mutate(run['task_dir'],OWNER,'latest',action)['result']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','start','bind','finish','observe'])
    parser.add_argument('root',type=Path)
    parser.add_argument('index',type=int,nargs='?')
    parser.add_argument('handle',nargs='?')
    args=parser.parse_args()
    if args.action=='prepare': result=prepare(args.root.resolve())
    else:
        run=json.loads((args.root/'runs.json').read_text())[args.index]
        if args.action=='start':
            command=None
            if run['runtime']=='process':
                command=[shutil.which('term2'),'--json','--auto-approve','--provider',run['route']['provider'],
                         '--model',run['route']['model'],'{prompt}']
            result=mutate(run,lambda s,p:runtime.start(s,p,'loader',run['runtime'],run['route'],run['method'],[args.root/'catalog'],command))
            write(args.root/f'start-{args.index:02d}.json',result)
        elif args.action=='bind':
            start=json.loads((args.root/f'start-{args.index:02d}.json').read_text())
            result=mutate(run,lambda s,p:runtime.bind_native(s,'loader',start['attempt_id'],args.handle))
        else:
            observation={'handle':args.handle,'status':'finished'} if args.handle else None
            result=mutate(run,lambda s,p:runtime.observe(s,'loader',observation))
            if args.action=='finish':
                if result['status']!='finished' or len(result['reports'])!=1 or result['blocker']:
                    raise tasks.StateError('worker must settle with exactly one report and no blocker')
                evidence=mutate(run,lambda s,p:outcomes.verify_result(s,'loader',result['reports'][0],30))
                if not outcomes.passed(evidence['checks'],tasks.load(Path(run['task_dir']))['outcome_plan']['outcomes']['loader']['contract']['checks']):
                    raise tasks.StateError('local verification failed')
                # The coordinator must additionally inspect source before finish.
                mutate(run,lambda s,p:outcomes.accept(s,'loader','Coordinator inspected loader source and independent compatibility checks'))
                target=Path(run['project'])/'integrated.py'; shutil.copyfile(evidence['artifact']['path'],target)
                mutate(run,lambda s,p:outcomes.integrate(s,'loader',target))
                gate=mutate(run,lambda s,p:outcomes.verify_goal(s,30))
                mutate(run,lambda s,p:tasks.apply_patch(s,{'status':'completed'}))
                result={'passed':True,'index':args.index,'runtime':run['runtime'],'method':run['method'],
                        'assignment':tasks.load(Path(run['task_dir']))['outcome_plan']['outcomes']['loader']['assignment_id'],
                        'artifact':outcomes.file_ref(target),'local_checks':evidence['checks'],'goal_checks':gate['checks']}
                write(args.root/f'result-{args.index:02d}.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
