`timescale 1ns/1ps
module audio_test;
 reg clk=0; always #20 clk=!clk;
 reg rst=0;
 wire [7:0] video,out,oe;
 tt_um_mario_levels dut(8'b0,video,8'hf7,out,oe,1'b1,clk,rst);
 integer n,highs,phase,load;
 task carrier(input integer expected);
  begin
   @(negedge clk);dut.h=0;
   highs=0;
   for(n=0;n<32;n=n+1) begin
    #1;
    if(out[7]===1'b1) highs=highs+1;
    else if(out[7]!==1'b0) $fatal(1,"Unknown audio output");
    if(out[6]!==1 || oe[7]!==1) $fatal(1,"Audio enable / PSRAM A select");
    @(negedge clk);
   end
   if(highs!=expected) $fatal(1,"PWM duty: got %0d/32 expected %0d/32",highs,expected);
  end
 endtask
 initial begin
  repeat(4) @(negedge clk);rst=1;
  repeat(4) @(negedge clk);
  force dut.jump_beep=0;force dut.music_playing=0;carrier(16);
  force dut.music_playing=1;
  force dut.music_tone=0;carrier(8);
  force dut.music_tone=1;carrier(24);
  // The opposite music polarity must not affect the jump-beep waveform.
  force dut.jump_beep=1;
  for(load=0;load<2;load=load+1) begin
   force dut.level_load=load;
   for(phase=0;phase<2;phase=phase+1) begin
    @(negedge clk);dut.v=phase*16;
    carrier(load ? 16:phase ? 24:8);
   end
  end
  // Four full presentation frames per game update; holding jump does not
  // retrigger, as checked using real controller packets in controls.v.
  force dut.level_load=0;
  release dut.jump_beep;release dut.music_tone;release dut.music_playing;
  @(negedge clk);dut.h=1;dut.v=480;dut.frame_phase=0;dut.jump_beep=1;
  repeat(4*800*525-1) begin
   @(negedge clk);
   if(dut.jump_beep!==1) $fatal(1,"Jump beep ended before four frames");
  end
  @(negedge clk);
  if(dut.jump_beep!==0) $fatal(1,"Jump beep did not end after four frames");
  if(dut.music.position==0) $fatal(1,"Melody did not advance under jump beep");
  rst=0;repeat(4) @(negedge clk);
  if(oe!==0) $fatal(1,"Reset must release audio and flash pins");
  $display("PASS: music PWM, jump priority, idle, DIP mute, four-frame duration and reset release");
  $finish;
 end
endmodule
