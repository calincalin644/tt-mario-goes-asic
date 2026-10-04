"""Compile reachable player/enemy states into physical-pointer action tables."""
import json
from collections import deque
from world import *

def graph(level):
    nodes=list(dict.fromkeys(spawn(level,c) for c in range(4)))
    ids={state:i for i,state in enumerate(nodes)}
    todo=deque(nodes)
    while todo:
        state=todo.popleft()
        for action in range(8):
            nxt=transition(level,state,action)
            if nxt not in ids:
                ids[nxt]=len(nodes);nodes.append(nxt);todo.append(nxt)
    assert len(nodes)<=NODE_CAPS[level], (level,len(nodes),'state-bank overflow')
    return nodes,ids

def build_rules():
    graphs=[graph(level) for level in range(len(LEVELS))]
    rules=bytearray()
    metadata=[]
    for level,(nodes,ids) in enumerate(graphs):
        bank=bytearray(record_bytes(render_word(level,0,spawn(level)))*(NODE_CAPS[level]*8))
        for node,state in enumerate(nodes):
            for action in range(8):
                next_level,nxt=campaign_step(level,state,action)
                next_node=graphs[next_level][1][nxt]
                at=(node*8+action)*8
                bank[at:at+8]=record_bytes(render_word(next_level,next_node,nxt,state,level))
        if level==0:
            assert len(nodes)<SELECTOR_NODE
            for selected in range(8):
                at=(SELECTOR_NODE*8+selected)*8
                bank[at:at+8]=record_bytes(render_word(selected,0,spawn(selected)))
        rules.extend(bank)
        (ROOT/f'build/rules-{level}.bin').write_bytes(bank)
        metadata.append(dict(name=LEVELS[level]['name'],nodes=nodes,count=len(nodes)))
        print('Level',level+1,LEVELS[level]['name'],len(nodes),'reachable states')
    assert len(rules)==0x440000
    (ROOT/'build/rules.bin').write_bytes(rules)
    (ROOT/'build/nodes.json').write_text(json.dumps(metadata)+'\n')
    return graphs
if __name__=='__main__':build_rules()
