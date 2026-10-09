"""Compile fixed 16th-note slots; alternate 7/8 VGA frames at 120 BPM."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
START='// BEGIN GENERATED MELODY\n'
END='// END GENERATED MELODY\n'
def generate():
 a=json.loads((ROOT/'assets/melody.json').read_text())
 notes=a['step_notes'];div=a['note_divisors']
 assert len(notes)==80
 lines=[START.rstrip(),'// 80 fixed steps: alternating 7/8 frames, final frame silent.',
 'module mario_melody(input wire clk,rst_n,enable,line_tick,frame_tick,',
 ' output reg tone,output wire playing);',
 ' reg [6:0] position;', ' reg [2:0] elapsed;', ' reg [5:0] counter;',
 ' reg [5:0] pitch_reload;',
 " wire [2:0] last_frame={2'b11,position[0]};",
 ' wire [5:0] reload=elapsed==last_frame ? 6\'d0:pitch_reload;',
 ' always @* begin',"  pitch_reload=0;",'  case(position)']
 for n in dict.fromkeys(notes):
  if n=='REST':continue
  cases=','.join(f"7'd{i}" for i,x in enumerate(notes) if x==n)
  lines.append(f"   {cases}: pitch_reload=6'd{div[n]-1}; // {n}")
 lines += ['   default: begin end','  endcase',' end',
 ' assign playing=enable && |reload;',
 ' always @(posedge clk) begin',
 '  if(!rst_n) begin position<=0;elapsed<=0;counter<=0;tone<=0;end',
 '  else begin',
 '   if(enable && frame_tick) begin',
 '    if(elapsed==last_frame) begin',
 "     elapsed<=0;position<=position==7'd79 ? 7'd0:position+1'b1;",
 "    end else elapsed<=elapsed+1'b1;",'   end',
 '   if(!playing) begin counter<=0;tone<=0;end',
 '   else if(line_tick) begin',
 '    if(counter==0) begin counter<=reload;tone<=!tone;end',
 "    else counter<=counter-1'b1;",'   end','  end',' end','endmodule',END.rstrip()]
 return '\n'.join(lines)+'\n'
if __name__=='__main__':
 p=ROOT/'src/tt_um_mario_levels.v';s=p.read_text();g=generate()
 a=s.index(START);b=s.index(END,a)+len(END);p.write_text(s[:a]+g+s[b:])
 print('Generated 80 fixed steps, 600 frames; no flash allocation')
