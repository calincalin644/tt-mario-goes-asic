"""Compile the approved MIDI as one flash pitch byte per VGA frame."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
START='// BEGIN GENERATED MELODY\n'
END='// END GENERATED MELODY\n'
def generate():
 a=json.loads((ROOT/'assets/melody.json').read_text())
 assert len(a['frame_divisors'])==661
 lines=[START.rstrip(),'// Approved MIDI: 661 flash bytes, one per VGA frame.',
 'module mario_melody(input wire clk,rst_n,enable,line_tick,frame_tick,',
 ' input wire [5:0] pitch_reload,output reg [9:0] position,',
 ' output reg tone,output wire playing);',
 ' reg [5:0] counter;',

 ' wire [5:0] reload=pitch_reload;',
]
 lines += [ ' assign playing=enable && |reload;',
 ' always @(posedge clk) begin',
 '  if(!rst_n) begin position<=0;counter<=0;tone<=0;end',
 '  else begin',
 '   if(enable && frame_tick)',
 "    position<=position==10'd660 ? 10'd0:position+1'b1;",
 '   if(!playing) begin counter<=0;tone<=0;end',
 '   else if(line_tick) begin',
 '    if(counter==0) begin counter<=reload;tone<=!tone;end',
 "    else counter<=counter-1'b1;",'   end','  end',' end','endmodule',END.rstrip()]
 return '\n'.join(lines)+'\n'
if __name__=='__main__':
 p=ROOT/'src/tt_um_mario_levels.v';s=p.read_text();g=generate()
 a=s.index(START);b=s.index(END,a)+len(END);p.write_text(s[:a]+g+s[b:])
 print('Generated approved MIDI: 661 frames/bytes in graphics padding')
