"""Generate synthetic EV queue inputs. No third-party libraries are needed."""
import argparse, csv, json, random
from pathlib import Path

def write_csv(path, rows, fields=None):
    fields = fields or list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def generate(out, seed=20261104, urgent_prior=0.30):
    out.mkdir(parents=True, exist_ok=True)
    if not 0 <= urgent_prior <= 1: raise ValueError('urgent_prior must be between 0 and 1')
    ids = [f'D{i:03}' for i in range(1,41)]
    type_rng, session_rng, strategy_rng = [random.Random(seed+k) for k in (101,202,303)]
    labels = ['release']*10 + ['hold']*10 + ['reciprocal']*10 + ['fee_aware']*10
    strategy_rng.shuffle(labels)
    drivers=[]
    for ident, strategy in zip(ids,labels):
        urgent = type_rng.random() < urgent_prior
        drivers.append(dict(driver_id=ident, private_type='urgent' if urgent else 'flexible',
            value_per_kwh=3 if urgent else 2, wait_cost_per_slot=3 if urgent else 1,
            idle_benefit_per_slot=1 if urgent else 2, private_strategy=strategy))
    sessions=[]
    for day in range(1,61):
        active=session_rng.sample(ids,36)
        requests=[]
        for ident in active:
            arrival=session_rng.randint(0,4) if session_rng.random()<.7 else session_rng.randint(5,8)
            needed=session_rng.choice([2,3,4,5,6])
            departure=min(16,arrival+needed+session_rng.randint(0,7))
            requests.append(dict(day=day,driver_id=ident,arrival_slot=arrival,
                                 departure_slot=departure,requested_kwh=3*needed))
        for case,count in [('low',12),('medium',24),('high',36)]:
            for r in requests[:count]:
                sessions.append(dict(scenario=case,request_id=f'{case}-{day:02}-{r["driver_id"]}',**r))
    write_csv(out/'sessions_public.csv',sessions)
    write_csv(out/'drivers_private.csv',drivers)
    write_csv(out/'chargers.csv',[dict(charger_id=f'C{i:02}',power_kw=6) for i in range(1,7)])
    write_csv(out/'policies.csv',[
        dict(policy_id='P0',name='First come first served',fee_per_idle_slot=0,use_history=0),
        dict(policy_id='P1',name='Idle penalty only',fee_per_idle_slot=2,use_history=0),
        dict(policy_id='P2',name='History only',fee_per_idle_slot=0,use_history=1),
        dict(policy_id='P3',name='History and penalty',fee_per_idle_slot=2,use_history=1)])
    write_csv(out/'benchmark_game.csv',[
        dict(p1_action='C',p2_action='C',p1_payoff=4,p2_payoff=4),
        dict(p1_action='C',p2_action='H',p1_payoff=0,p2_payoff=6),
        dict(p1_action='H',p2_action='C',p1_payoff=6,p2_payoff=0),
        dict(p1_action='H',p2_action='H',p1_payoff=1,p2_payoff=1)])
    write_csv(out/'bayesian_types.csv',[
        dict(private_type='urgent',probability=urgent_prior,extra_hold_payoff=0),
        dict(private_type='flexible',probability=1-urgent_prior,extra_hold_payoff=1)])
    leaves=[('L','L','L',1,3),('L','L','R',8,4),('L','R','L',6,1),('L','R','R',0,2),
            ('R','L','L',6,5),('R','L','R',2,2),('R','R','L',3,4),('R','R','R',1,1)]
    write_csv(out/'memory_tree.csv',[dict(p1_first=a,p2_action=b,p1_second=c,p1_payoff=u,p2_payoff=v) for a,b,c,u,v in leaves])
    write_csv(out/'mini_case_public.csv',[
        dict(request_id='mini-A',driver_id='A',arrival_slot=0,departure_slot=4,requested_kwh=6),
        dict(request_id='mini-B',driver_id='B',arrival_slot=0,departure_slot=5,requested_kwh=3),
        dict(request_id='mini-C',driver_id='C',arrival_slot=1,departure_slot=6,requested_kwh=6)])
    write_csv(out/'mini_case_private.csv',[
        dict(driver_id='A',private_type='flexible',value_per_kwh=2,wait_cost_per_slot=1,idle_benefit_per_slot=2),
        dict(driver_id='B',private_type='urgent',value_per_kwh=3,wait_cost_per_slot=3,idle_benefit_per_slot=1),
        dict(driver_id='C',private_type='flexible',value_per_kwh=2,wait_cost_per_slot=1,idle_benefit_per_slot=2)])
    expected={
      'conditions':{'chargers':1,'power_kw':6,'slot_minutes':30,'end_boundary':6,'policy':'P0','fee':0,'tie_break':'driver_id ascending'},
      'all_release':{'A':{'start':0,'finish':2,'release':2,'wait_slots':0,'utility':12},'B':{'start':2,'finish':3,'release':3,'wait_slots':2,'utility':3},'C':{'start':3,'finish':5,'release':5,'wait_slots':2,'utility':10},'total_utility':25,'total_wait_slots':4,'delivered_kwh':15},
      'A_holds_one_slot':{'A':{'start':0,'finish':2,'release':3,'wait_slots':0,'utility':14},'B':{'start':3,'finish':4,'release':4,'wait_slots':3,'utility':0},'C':{'start':4,'finish':6,'release':6,'wait_slots':3,'utility':9},'total_utility':23,'total_wait_slots':6,'delivered_kwh':15},
      'note':'These are arithmetic checks with fixed actions, not research findings.'}
    (out/'mini_case_expected.json').write_text(json.dumps(expected,indent=2)+'\n')
    config={'data_kind':'synthetic teaching data; not measured or fitted to ACN-Data',
      'seed':seed,'urgent_prior':urgent_prior,'days':60,'driver_pool':40,'slot_minutes':30,'day_slots':16,
      'day_start':'08:00','day_end':'16:00','charger_count':6,'charger_power_kw':6,
      'loads_per_day':{'low':12,'medium':24,'high':36},'default_delta':0.8,
      'history_initial':0,'history_min':-3,'history_max':3,'history_release_change':1,'history_hold_change':-1,
      'long_wait_priority_slots':4,'max_idle_slots':2,
      'benchmark_fee_grid':[0,1.5,3],'queue_fee_grid':[0,1,2,3],
      'bayesian_prior_grid':[0.25,0.5,0.75],'replicator_step':0.05,'replicator_generations':100,
      'public_input_policy':'Only expose an arrival at its arrival boundary; never give agents future rows.',
      'private_input_policy':'Give a driver its own type and rule only. Full private table belongs to the evaluator.'}
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    summary={'seed':seed,'sessions':len(sessions),'scenarios':{s:sum(r['scenario']==s for r in sessions) for s in ['low','medium','high']},
      'driver_count':40,'realized_urgent_count':sum(x['private_type']=='urgent' for x in drivers),'days_per_scenario':60,
      'source':'All rows generated by this script; no records describe real people or a real campus.'}
    (out/'data_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    assert len(sessions)==4320 and len({r['request_id'] for r in sessions})==4320
    for r in sessions:
        assert 0<=r['arrival_slot']<r['departure_slot']<=16
        assert r['requested_kwh']>0 and r['requested_kwh']%3==0
        assert r['requested_kwh']<=3*(r['departure_slot']-r['arrival_slot'])
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--seed',type=int,default=20261104)
    ap.add_argument('--urgent-prior',type=float,default=.30)
    a=ap.parse_args();print(json.dumps(generate(a.output,a.seed,a.urgent_prior),indent=2))
