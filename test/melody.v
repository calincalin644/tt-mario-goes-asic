`timescale 1ns/1ps
module melody_test;
 reg clk=0;always #5 clk=!clk;
 reg rst=0,enable=1,line_tick=0,frame_tick=0;
 wire tone,playing;
 wire [9:0] position;
 reg [5:0] pitches[0:660];
 mario_melody dut(clk,rst,enable,line_tick,frame_tick,pitches[position],position,tone,playing);
 reg [5:0] expected[0:660];
 integer frame_no,line_no,divisor,count=0,polarity=0,next_div;
 initial begin
  $readmemh("build/melody-expected.hex",expected);
  $readmemh("build/melody-pitches.hex",pitches);
  repeat(3) @(negedge clk);rst=1;
  // Accelerate the input enables, preserving 525 line ticks per frame.
  for(frame_no=0;frame_no<1322;frame_no=frame_no+1) begin
   divisor=expected[frame_no%661];
   if(dut.reload!==(divisor ? divisor-1:0))
    $fatal(1,"Wrong note or loop position at frame %0d",frame_no);
   for(line_no=0;line_no<525;line_no=line_no+1) begin
    line_tick=1;frame_tick=line_no==524;
    if(divisor==0) begin count=0;polarity=0;end
    else if(count==0) begin count=divisor-1;polarity=1-polarity;end
    else count=count-1;
    @(negedge clk);
    if(tone!==polarity) $fatal(1,"Tone divider mismatch at frame/line %0d/%0d",frame_no,line_no);
   end
  end
  line_tick=0;frame_tick=0;enable=0;
  repeat(3) @(negedge clk);
  if(playing!==0 || tone!==0 || dut.position!==0) $fatal(1,"Pause/mute failed");
  frame_tick=1;line_tick=1;
  repeat(10) @(negedge clk);
  if(dut.position!==0) $fatal(1,"Disabled sequence advanced");
  rst=0;@(negedge clk);
  if(dut.position!==0 || tone!==0) $fatal(1,"Reset failed");
  $display("PASS: all 661 frame slots, two complete loops, line-divider waveform, pause and reset");
  $finish;
 end
endmodule
