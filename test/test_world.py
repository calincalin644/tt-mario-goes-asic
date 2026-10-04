"""Cross-check dense tables and find controller routes through every checkpoint."""
import sys,json
from pathlib import Path
from collections import deque
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from world import *
from compile_rules import graph
rules=[(ROOT/f'build/rules-{level}.bin').read_bytes() for level in range(8)]
graphs=[graph(level) for level in range(8)]
def lookup(word,action):
    level,node,*_=decode_word(word)
    at=(node*8+action)*8
    return int.from_bytes(rules[level][at:at+6],'big')>>4
def initial(level,checkpoint=0):
    state=spawn(level,checkpoint)
    return render_word(level,graphs[level][1][state],state)
def route(level,checkpoint=0):
    start=initial(level,checkpoint)
    todo=deque([(start,False)]);parent={(start,False):None};finish=None
    while todo:
        node=todo.popleft();word,pressed=node
        if decode_word(word)[0]!=level or decode_word(word)[4]==2:finish=node;break
        for buttons in (2,6,0,4,1,5):
            held=bool(buttons&4);action=buttons if not held or not pressed else buttons&3
            nxt=lookup(word,action)
            if decode_word(nxt)[4]==1:continue
            old_level,old_node,old_x,*_=decode_word(word)
            nl,nn,nx,*_=decode_word(nxt)
            if enemy_for(level,old_x) and not enemy_state(graphs[level][0][old_node])[1]:
                if nl!=level or nx//64>old_x//64 or decode_word(nxt)[4]==2:continue
            item=(nxt,held)
            if item not in parent:parent[item]=(node,buttons,action);todo.append(item)
    assert finish is not None,('unreachable finish',level,checkpoint,len(parent))
    moves=[];node=finish
    while parent[node]:
        prev,buttons,action=parent[node];moves.append((buttons,action,node[0]));node=prev
    return moves[::-1]
assert not LEVELS[0]['spikes'] and not LEVELS[0]['pits']
assert not LEVELS[1]['pits'] and not LEVELS[1]['platforms']
assert not LEVELS[2]['spikes'] and not LEVELS[2]['platforms']
# Directed geometry checks independently of table generation.
assert unpack(transition(0,spawn(0),4))[1:]==(24,2)
assert unpack(transition(0,pack(16,26,0),2))[0]==16
landed=transition(0,transition(0,pack(18,23,8),0),0)
assert unpack(landed)[1:]==(25,0)
assert transition(1,pack(23,26,0),0)&15==DEAD
fall=pack(24,26,0)
for _ in range(3):fall=transition(2,fall,0)
assert fall&15==DEAD
for level in (5,6,7):
    for enemy in LEVELS[level]['enemies']:
        x,feet=enemy['x'],enemy['feet']
        side=transition(level,pack(x,feet,0),0)
        assert unpack(side)[2]==DEAD, ('enemy side contact',level,enemy)
        stomp=transition(level,pack(x,feet-2,8),0)
        assert enemy_state(stomp)==(0,True) and unpack(stomp)[2]==1, ('stomp/bounce',level,enemy)
        assert enemy_visual(level,stomp)==0
        continued=transition(level,stomp,0)
        assert enemy_state(continued)[1] and unpack(continued)[2]!=DEAD
        patrol=transition(level,pack(x-8,feet,0),0)
        if level!=7:
            assert enemy_state(patrol)[0]==1 and enemy_visual(level,patrol)==9
# The wide-water lesson must require the high platforms, rather than allowing
# a ground-level jump across every gap.
platforms=LEVELS[4]['platforms']
try:
    LEVELS[4]['platforms']=[]
    solid.cache_clear();blocked.cache_clear()
    assert not any(unpack(state)[2]==WON for state in graph(4)[0])
finally:
    LEVELS[4]['platforms']=platforms
    solid.cache_clear();blocked.cache_clear()
for level in range(8):
    assert unpack(transition(level,pack(0,26,0),1))[0]==0
    assert unpack(transition(level,pack(63,26,0),2))==(64,26,0)
    assert unpack(transition(level,pack(64,26,0),1))==(63,26,0)
for level,(nodes,ids) in enumerate(graphs):
    for node,state in enumerate(nodes):
        word=render_word(level,node,state)
        for action in range(8):
            nl,nxt=campaign_step(level,state,action)
            expected=render_word(nl,graphs[nl][1][nxt],nxt,state,level)
            assert lookup(word,action)==expected,(level,node,action)
            nx,ny,np=unpack(nxt);ox,oy,op=unpack(state)
            moving,vertical=decode_motion(expected)
            interpolate=nl==level and np not in (DEAD,WON) and op not in (DEAD,WON) and abs(nx-ox)<=1 and abs(ny-oy)<=2
            assert moving==(interpolate and nx!=ox)
            assert vertical==(ny-oy if interpolate else 0)
            if moving:assert nx-ox==(1 if action&2 else -1)
        if state&15==DEAD:assert lookup(word,4)==initial(level,min(unpack(state)[0]>>6,3))
    for node in range(len(nodes),NODE_CAPS[level]):
        for action in range(8):
            expected=initial(action) if level==0 and node==SELECTOR_NODE else initial(level)
            assert lookup(render_word(level,node,spawn(level)),action)==expected
    for checkpoint in range(4):
        moves=route(level,checkpoint)
        print('Level',level+1,'checkpoint',checkpoint+1,'route',len(moves),'updates',flush=True)
moves=[]
for level in range(8):
    # Release jump at each new spawn, matching real controller edge detection.
    word=initial(level);assert lookup(word,0)==word
    moves.append((0,0,word));moves.extend(route(level))
assert decode_word(moves[-1][2])[4]==2
assert lookup(moves[-1][2],0)==moves[-1][2]
assert lookup(moves[-1][2],4)==initial(0)
(ROOT/'build/route.json').write_text(json.dumps(moves)+'\n')
(ROOT/'build/route.hex').write_text(''.join(f'{(action<<41)|word:011x}\n' for _,action,word in moves))
(ROOT/'build/route-count.vh').write_text(f'`define ROUTE_COUNT {len(moves)}\n')
print('PASS: all dense entries, eight levels, 32 checkpoint routes, final victory/restart;',len(moves),'campaign updates')
