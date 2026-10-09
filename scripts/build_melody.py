"""Compile the auditioned frame sequence into compact hardwired repeated runs.
The musical input remains fixed VGA-frame slots, with no flash reads.
"""
from pathlib import Path
from itertools import groupby
import json
ROOT=Path(__file__).resolve().parents[1]
START='// BEGIN GENERATED MELODY\n'
END='// END GENERATED MELODY\n'
def generate():
 slots=json.loads((ROOT/'assets/melody.json').read_text())['frame_divisors']
 assert len(slots)==661 and all(0<=n<64 for n in slots)
 runs=[(n,len(list(g))) for n,g in groupby(slots)]
 assert len(runs)==82 and max(t for _,t in runs)<=32
 lines=[START.rstrip(),'// Generated from assets/melody.json: 661 frames, 82 repeated-value runs.',
 'module mario_melody(input wire clk,rst_n,enable,line_tick,frame_tick,',
 ' output reg tone,output wire playing);',
 ' reg [6:0] position;', ' reg [4:0] elapsed;', ' reg [5:0] counter;',
 ' reg [5:0] reload;', ' reg [4:0] last_frame;',
 ' always @* begin',"  reload=0;last_frame=0;",'  case(position)']
 for i,(n,duration) in enumerate(runs):
  lines.append(f"   7'd{i}: begin reload=6'd{max(n-1,0)};last_frame=5'd{duration-1};end")
 lines += ['   default: begin end','  endcase',' end',
 ' assign playing=enable && |reload;',
 ' always @(posedge clk) begin',
 '  if(!rst_n) begin position<=0;elapsed<=0;counter<=0;tone<=0;end',
 '  else begin',
 '   if(enable && frame_tick) begin',
 '    if(elapsed==last_frame) begin',
 "     elapsed<=0;position<=position==7'd81 ? 7'd0:position+1'b1;",
 "    end else elapsed<=elapsed+1'b1;",'   end',
 '   if(!playing) begin counter<=0;tone<=0;end',
 '   else if(line_tick) begin',
 '    if(counter==0) begin counter<=reload;tone<=!tone;end',
 "    else counter<=counter-1'b1;",'   end','  end',' end','endmodule',END.rstrip()]
 return '\n'.join(lines)+'\n'
if __name__=='__main__':
 p=ROOT/'src/tt_um_mario_levels.v';s=p.read_text();g=generate()
 a=s.index(START);b=s.index(END,a)+len(END);p.write_text(s[:a]+g+s[b:])
 print('Generated 661 fixed frame slots as 82 runs; no flash allocation')
