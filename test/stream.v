`timescale 1ns/1ps
`include "build/route-count.vh"
module stream_test;
 reg clk=0;always #20 clk=!clk;
 reg rst=0;reg [9:0] h=0;
 always @(posedge clk) if(!rst) h<=0;else h<=h==799 ? 10'd0:h+1'b1;
 reg game_slot=0;reg [2:0] action=0;
 wire [7:0] pins,out,oe;wire [40:0] player;wire [31:0] sprite;wire [3:0] bg;
 mario_stream_flash dut(clk,rst,h,game_slot,action,1'b0,24'hc00000,5'd0,pins,out,oe,player,sprite,bg,1'b0,10'd0,);
 flash_model flash(out[0],out[3],out,oe,pins);
 reg [43:0] route[0:`ROUTE_COUNT-1];integer i;
 task advance(input [2:0] a);
  begin
   while(h!=640) @(negedge clk);
   action=a;game_slot=1;
   while(h!=708) @(negedge clk);
   game_slot=0;
  end
 endtask
 initial begin
  $readmemh("build/route.hex",route);
  repeat(3) @(negedge clk);if(oe!==0) $fatal(1,"bus not released in reset");rst=1;
  for(i=0;i<`ROUTE_COUNT;i=i+1) begin
   advance(route[i][43:41]);
   if(player!==route[i][40:0]) $fatal(1,"route step %d got=%h expected=%h",i,player,route[i][40:0]);
  end
  if(player[3:1]!=4) $fatal(1,"final victory missing");
  advance(0);if(player[3:1]!=4) $fatal(1,"win not latched");
  advance(4);if(player!=route[0][40:0]) $fatal(1,"restart");
  $display("PASS: continuous scrolling-world playthrough and restart using actual SPI transactions and flash table");$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
