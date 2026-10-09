"""Coin encounters use only existing enemy state and background selection."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from world import *
from compile_rules import graph
coins=[]
for level,world in enumerate(LEVELS):
    for coin in world.get('enemies',[]):
        if coin['kind']!='coin':continue
        coins.append(level)
        assert sum(e['x']//64==coin['x']//64 for e in world['enemies'])==1
        x,feet=coin['x'],coin['feet']
        before=pack(x,feet+1,0)
        after=transition(level,before,0)
        assert unpack(after)==unpack(player_transition(level,before,0)), 'coin damaged or bounced player'
        assert enemy_state(after)[1] and enemy_visual(level,after)==0
        assert enemy_state(transition(level,after,0))[1]
        nodes,_=graph(level)
        assert any(enemy_state(n)[1] and unpack(n)[0]//64==x//64 for n in nodes), 'unreachable coin'
        animation={enemy_visual(level,n)&7 for n in nodes if enemy_visual(level,n) and unpack(n)[0]//64==x//64}
        assert animation=={0,1}, animation
        assert enemy_state(spawn(level,x//64))==(0,False)
assert coins==[0,1,2,3,4,7]
assert [e['kind'] for e in LEVELS[5]['enemies']]==['mushroom']*4
assert [e['kind'] for e in LEVELS[6]['enemies']]==['tortoise']*4
print('PASS: six reachable collectible rotating coins, no damage/bounce, encounter reset, all enemies preserved')
