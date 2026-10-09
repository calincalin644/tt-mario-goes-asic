"""Offline geometry and physics for eight progressively harder scrolling levels."""
import json
from pathlib import Path
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[1]
LEVELS=json.loads((ROOT/'assets/levels.json').read_text())
DEAD,WON=14,15
DY=(2,-2,-2,-1,-1,0,1,1,2)
NODE_BITS=12
NODES_PER_LEVEL=1<<NODE_BITS
ENEMY_OFFSETS=(0,4,8,12,16,12,8,4)
RULE_BASES=(0x800000,0x840000,0x880000,0x8c0000,0x900000,0xa00000,0xb00000,0x500000)
NODE_CAPS=(4096, 3072, 3072, 3072, 5120, 14336, 14336, 15360)
ENEMY_BANKS={5:(0,1,3,5,7,9,10,12),6:(13,14,15,24,25,26,27,28),7:(29,30,31,57,58,59,60,61)}
COIN_BANKS={0:(62,33),1:(34,35),2:(36,38),3:(39,40),4:(41,42)}
SHELL_BANKS={6:19,7:37}
SHELL_TICKS=3  # 200 ms at the 15 Hz gameplay rate
RELOCATIONS={129: 10, 130: 11, 132: 18, 133: 19, 134: 24, 136: 25, 137: 26, 138: 33, 140: 34, 141: 35, 142: 44, 144: 45, 145: 47, 146: 69, 147: 70, 148: 71, 160: 72, 161: 73, 162: 74, 163: 75, 164: 94, 165: 174, 166: 175, 167: 190, 168: 191, 169: 225, 170: 226, 171: 227, 173: 9, 177: 129, 94: 16}
SELECTOR_NODE=4095

def physical(address):return (RELOCATIONS.get(address>>16,address>>16)<<16)|(address&65535)

def logical(address):
    inverse={v:k for k,v in RELOCATIONS.items()}
    return (inverse.get(address>>16,address>>16)<<16)|(address&65535)

def record_bytes(word):return (word<<4).to_bytes(6,'big')+b'\xff'*2

def pack(x,y,phase,enemy_phase=0,enemy_dead=False):
    return (x<<9)|(y<<4)|phase|(enemy_phase<<17)|(int(enemy_dead)<<20)

def unpack(state):return (state>>9)&255,(state>>4)&31,state&15

def spawn(level,checkpoint=0):return pack(LEVELS[level]['checkpoints'][checkpoint],26,0)

def camera(x):return max(0,x-12)

@lru_cache(None)
def ground(level,x):
    world=LEVELS[level]
    if any(a<=x<b for a,b in world['pits']):return 30
    for a,b,top in world['ground']:
        if a<=x<b:return top
    return 26

@lru_cache(None)
def solid(level,x,y):
    if x<0 or x>=256 or y<0:return True
    if y>=30:return False
    return y>=ground(level,x) or any(a<=x<b and y==top for a,b,top in LEVELS[level]['platforms'])

@lru_cache(None)
def blocked(level,x,y):
    return any(solid(level,c,r) for c in (x,x+1) for r in (y-2,y-1))

def player_transition(level,state,action):
    x,y,phase=unpack(state);finish=LEVELS[level]['finish'];jump=bool(action&4)
    if phase==DEAD:return spawn(level,min(x>>6,3)) if jump else state
    if phase==WON:return spawn(level) if jump else state
    if phase>8 or x>finish or y<2 or y>=30 or blocked(level,x,y):return pack(min(x,finish),min(max(y,2),30),DEAD)
    dx=(1 if action&2 else 0)-(1 if action&1 else 0)
    if dx and 0<=x+dx<=finish and not blocked(level,x+dx,y):x+=dx
    supported=blocked(level,x,y+1)
    if jump and phase==0 and supported:phase=1
    dy=DY[phase]
    # All subsequent falling phases have identical behaviour; share one state.
    next_phase=min(phase+1,8) if phase else 0
    if dy:
        direction=1 if dy>0 else -1
        for _ in range(abs(dy)):
            if blocked(level,x,y+direction):
                next_phase=0 if direction>0 else 6
                break
            y+=direction
            if y>=30:return pack(x,30,DEAD)
    if any(x+2>a and x<b and y>25 for a,b in LEVELS[level]['spikes']):return pack(x,y,DEAD)
    if x>=finish and y==26:return pack(x,y,WON)
    return pack(x,y,next_phase)

def enemy_for(level,x):
    return next((enemy for enemy in LEVELS[level].get('enemies',[]) if enemy['x']//64==x//64),None)

def enemy_state(state):return (state>>17)&7,bool(state&(1<<20))

def enemy_visual(level,state):
    x,_,phase=unpack(state)
    animation,dead=enemy_state(state)
    enemy=enemy_for(level,x)
    if enemy and dead and animation and enemy['kind']=='tortoise':return 16
    return (8|animation) if enemy and not dead else 0

def transition(level,state,action):
    old_x,old_y,old_phase=unpack(state)
    nxt=player_transition(level,state,action)
    x,y,phase=unpack(nxt)
    # Death, restart and section crossings reset the local enemy encounter.
    if phase in (DEAD,WON) or old_phase in (DEAD,WON):return nxt
    enemy=enemy_for(level,x)
    if not enemy:return nxt
    animation,dead=enemy_state(state) if x//64==old_x//64 else (0,False)
    # Start patrolling when Mario comes within 128 logical pixels. Distant
    # enemies stay visible but idle; this bounds the reachable table size.
    active=abs(x-enemy['x'])<=(3 if enemy['kind']=='coin' else 16)
    animation=max(0,animation-1) if dead else ((animation+1)&7 if active else 0)
    if enemy['kind']=='coin':
        animation=animation&1
        cx=enemy['x']*8
        if not dead and x*8<cx+8 and x*8+16>cx and (y-2)*8<enemy['feet']*8 and y*8>enemy['feet']*8-8:
            dead=True;animation=0
        return pack(x,y,phase,animation,dead)
    if not dead:
        ex=enemy['x']*8+ENEMY_OFFSETS[animation]
        bottom=enemy['feet']*8
        top=bottom-(12 if enemy['kind']=='mushroom' else 16)
        overlap=x*8+14>ex+2 and x*8+2<ex+14
        if overlap and y>=old_y and old_y*8<=top and y*8>=top:
            # Bounce upward after a stomp. Both enemy types take one stomp.
            y=enemy['feet']-2;phase=1;dead=True;animation=SHELL_TICKS if enemy['kind']=='tortoise' else 0
        elif overlap and y*8>top and (y-2)*8<bottom:
            return pack(x,y,DEAD)
    return pack(x,y,phase,animation,dead)

def campaign_step(level,state,action):
    if state&15==WON and level==len(LEVELS)-1:
        return (0,spawn(0)) if action&4 else (level,state)
    nxt=transition(level,state,action)
    if (state&15==WON or nxt&15==WON) and level<len(LEVELS)-1:
        return level+1,spawn(level+1)
    return level,nxt

def render_word(level,node,state,source=None,source_level=None):
    """Flash supplies both logical state and the visual step, avoiding ASIC history."""
    x,y,phase=unpack(state)
    motion=3 if phase==DEAD else 4 if phase==WON else 0
    moved_x=0
    if phase not in (DEAD,WON) and source is not None and source_level==level:
        old_x,old_y,old_phase=unpack(source)
        dx,dy=x-old_x,y-old_y
        if old_phase not in (DEAD,WON) and abs(dx)<=1 and abs(dy)<=2:
            motion=dy&7;moved_x=int(dx!=0)
    visual=enemy_visual(level,state)
    picture=(COIN_BANKS[level][visual&1] if level in COIN_BANKS else ENEMY_BANKS[level][visual&7]) if visual and visual!=16 else SHELL_BANKS[level] if visual==16 else 48+level
    # Send physical pointers in the result so the ASIC needs no level/bank
    # decoder or relocation logic. Each node has eight 8-byte action records.
    pointer=physical(RULE_BASES[level]+node*64)>>6
    return (pointer<<23)|(x<<15)|(y<<10)|(picture<<4)|(motion<<1)|moved_x

def decode_word(word):
    motion=(word>>1)&7
    status=1 if motion==3 else 2 if motion==4 else 0
    address=logical((word>>23)<<6)
    level=next(i for i,base in enumerate(RULE_BASES) if base<=address<base+NODE_CAPS[i]*64)
    node=(address-RULE_BASES[level])//64
    return level,node,(word>>15)&255,(word>>10)&31,status

def decode_motion(word):
    motion=(word>>1)&7
    dy=0 if motion in (3,4) else motion-8 if motion>=6 else motion
    return bool(word&1),dy
