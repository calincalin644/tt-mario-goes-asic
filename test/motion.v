`timescale 1ns/1ps
`include "build/route-count.vh"
module motion_test;
 reg clk=0;always #20 clk=!clk;
 reg rst=0,ena=1;
 wire [7:0] video,out,oe,pins;
 tt_um_mario_levels dut(8'b0,video,pins,out,oe,ena,clk,rst);
 // Audio PMOD passes bits 0..6 and pulls downstream PSRAM B CS high.
 flash_model flash(out[0],out[3],{1'b1,out[6:0]},oe,pins);
 reg [43:0] route[0:`ROUTE_COUNT-1];
 integer i,p,old_x,old_y,target_x,target_y,dx,dy,expect_x,expect_y;
 integer moving_frames=0,teleports=0;
 task check_interpolation(input [40:0] target);
  begin
   target_x=target[22:15]*4;target_y=target[14:10]*4;
   dx=target_x-old_x;dy=target_y-old_y;
   for(p=0;p<4;p=p+1) begin
    @(negedge clk);dut.h=704;dut.v=480;dut.frame_phase=p;
    @(negedge clk);
    if(dx < -4 || dx > 4 || dy < -8 || dy > 8 || target[3:1]==3 || target[3:1]==4) begin
     expect_x=target_x;expect_y=target_y;if(p==0) teleports=teleports+1;
    end else begin
     expect_x=old_x+dx*(p+1)/4;expect_y=old_y+dy*(p+1)/4;
     if(dx || dy) moving_frames=moving_frames+1;
    end
    if(dut.draw_x!==expect_x || dut.draw_y!==expect_y)
     $fatal(1,"step %0d phase %0d render=(%0d,%0d) expected=(%0d,%0d)",i,p,dut.draw_x,dut.draw_y,expect_x,expect_y);
    if(dut.camera!==(expect_x>48 ? expect_x-48:0)) $fatal(1,"camera interpolation");
    // Position must remain stable throughout active display (no tearing).
    dut.h=100;dut.v=100;repeat(10) @(negedge clk);
    if(dut.draw_x!==expect_x || dut.draw_y!==expect_y) $fatal(1,"active-display movement");
   end
  end
 endtask
 task advance(input [2:0] action,input [40:0] target);
  begin
   old_x=dut.draw_x;old_y=dut.draw_y;
   @(negedge clk);dut.h=640;dut.v=480;dut.frame_phase=0;dut.action=action;
   if(action[1:0]==1) dut.facing=0;else if(action[1:0]==2) dut.facing=1;
   while(dut.h!=707) @(negedge clk);
   if(dut.player!==target) $fatal(1,"table result at step %0d",i);
   check_interpolation(target);
  end
 endtask
 task directed(input [7:0] x,input [4:0] feet);
  reg [40:0] word;reg [2:0] motion;reg moved;integer cell_dx,cell_dy;
  begin
   old_x=dut.draw_x;old_y=dut.draw_y;
   cell_dx=x-old_x/4;cell_dy=feet-old_y/4;motion=0;moved=0;
   if(cell_dx>=-1 && cell_dx<=1 && cell_dy>=-2 && cell_dy<=2) begin
    motion=cell_dy;moved=cell_dx!=0;
   end
   word={18'h20000,x,feet,6'd48,motion,moved};
   @(negedge clk);dut.flash.player=word;
   if(moved) dut.facing=cell_dx>0;
   check_interpolation(word);
  end
 endtask
 initial begin
  $readmemh("build/route.hex",route);
  repeat(3) @(negedge clk);rst=1;repeat(2) @(negedge clk);
  for(i=0;i<`ROUTE_COUNT;i=i+1) advance(route[i][43:41],route[i][40:0]);
  advance(0,route[`ROUTE_COUNT-1][40:0]);advance(4,route[0][40:0]);
  directed(10,26);directed(11,26);directed(10,26); // Stop/reverse.
  directed(10,25);directed(10,24);directed(10,26); // Vertical 1/2-cell steps.
  directed(0,26);directed(1,26);directed(0,26); // Left world boundary.
  directed(12,26);directed(13,26);directed(12,26); // Camera threshold both ways.
  directed(228,30);directed(195,26); // Death/respawn snap, never pan across a level.
  directed(196,25);ena=0;
  for(p=0;p<4;p=p+1) begin
   @(negedge clk);dut.frame_phase=p;repeat(5) @(negedge clk);
   if(dut.draw_x!=196*4 || dut.draw_y!=25*4) $fatal(1,"paused interpolation repeated");
  end
  ena=1;
  if(moving_frames<6000 || teleports<8) $fatal(1,"insufficient campaign coverage");
  $display("PASS: %0d smooth moving frames; %0d teleports; full campaign, reversals, jumps, boundaries, restart and active-raster stability",moving_frames,teleports);
  $finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
