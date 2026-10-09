`timescale 1ns/1ps
module music_flash_test;
 reg clk=0;always #20 clk=!clk;
 reg rst=0;reg [9:0] h=0;
 always @(posedge clk) if(!rst) h<=0;else h<=h==799 ? 10'd0:h+1'b1;
 reg music_slot=1;reg [9:0] position=0;
 reg [23:0] picture=24'hc00000;
 wire [7:0] pins,out,oe;wire [40:0] player;
 wire [31:0] sprite;wire [3:0] bg;wire [5:0] pitch;
 mario_stream_flash dut(clk,rst,h,1'b0,3'd0,1'b0,picture,5'd0,pins,out,oe,player,sprite,bg,music_slot,position,pitch);
 flash_model flash(out[0],out[3],out,oe,pins);
 integer i,j;reg [5:0] held;
 initial begin
  repeat(3) @(negedge clk);rst=1;
  for(i=0;i<661;i=i+1) begin
   while(h!=640) @(negedge clk);
   position=i;picture=24'hc00000+((i%8)<<18)+((i*977)%245760);
   while(h!=688) @(negedge clk);
   if(flash.address!==24'hc3c000+i) $fatal(1,"Music address follows graphics: %h",flash.address);
   while(h!=704) @(negedge clk);
   if(pitch!==flash.memory[24'hc3c000+i][5:0]) $fatal(1,"Wrong flash pitch at %0d",i);
   if(player!==41'h1000001eb00) $fatal(1,"Music changed game state");
   held=pitch;
   while(h!=752) @(negedge clk);
   if(flash.address!==picture) $fatal(1,"Background read not restored");
   if(pitch!==held) $fatal(1,"Background overwrote pitch");
  end
  music_slot=0;
  for(j=0;j<3;j=j+1) begin
   while(h!=640) @(negedge clk);
   while(h!=704) @(negedge clk);
   if(flash.address!==24'he00000) $fatal(1,"Sprite address not restored");
   if(sprite!=={flash.memory[24'he00000],flash.memory[24'he00001],flash.memory[24'he00002],flash.memory[24'he00003]}) $fatal(1,"Sprite data corrupt");
   if(pitch!==held) $fatal(1,"Sprite overwrote pitch");
  end
  rst=0;repeat(3) @(negedge clk);
  if(pitch!==0 || oe!==0) $fatal(1,"Reset failed");
  $display("PASS: 661 real QSPI music reads independent of camera/bank; background and sprite resume; pitch held; reset");$finish;
 end
 initial begin #30000000;$fatal(1,"timeout");end
endmodule
