`timescale 1ns/1ps
module core_controls_test;
 reg clk=0;always #20 clk=!clk;
 reg rst=0,ena=1;reg [7:0] ui=0;
 wire [7:0] video,out,oe,pins;
 tt_um_mario_levels dut(ui,video,pins,out,oe,ena,clk,rst);
 flash_model flash(out[0],out[3],out,oe,pins);
 reg [40:0] saved;
 integer level;
 reg [17:0] expected_pointer;
 task packet(input [2:0] buttons);
  reg [11:0] bits;integer i;
  begin
   bits=0;bits[5]=buttons[0];bits[4]=buttons[1];bits[11]=buttons[2];
   for(i=11;i>=0;i=i-1) begin
    ui[6]=bits[i];ui[5]=0;repeat(6) @(negedge clk);
    ui[5]=1;repeat(6) @(negedge clk);
   end
   ui[5]=0;ui[4]=1;repeat(6) @(negedge clk);
   ui[4]=0;repeat(6) @(negedge clk);
  end
 endtask
 task game_update;
  begin
   @(negedge clk);dut.h=0;dut.v=480;dut.frame_phase=3;
   repeat(708) @(negedge clk);
  end
 endtask
 initial begin
  repeat(3) @(negedge clk);rst=1;
  packet(4);game_update;
  if(dut.action!==3'b100 || dut.player[14:10]!=24) $fatal(1,"gamepad jump edge or table response");
  game_update;if(dut.action!==0 || dut.player[14:10]!=22) $fatal(1,"held jump repeated");
  saved=dut.player;ena=0;game_update;
  if(dut.player!==saved) $fatal(1,"ena pause");
  ena=1;packet(0);game_update;
  packet(4);game_update;
  if(dut.action!==4) $fatal(1,"new jump edge missing");
  packet(2);
  for(level=0;level<8;level=level+1) begin
   ui[3:0]={1'b1,level[2:0]};repeat(10) @(negedge clk);game_update;
   expected_pointer=level<5 ? 18'h20000+level*18'h1000:level==5 ? 18'h28000:level==6 ? 18'h2c000:18'h14000;
   if(dut.player[40:23]!==expected_pointer || dut.player[22:15]!=3 || dut.player[14:10]!=26)
    $fatal(1,"DIP selection %0d failed: %h",level,dut.player);
   saved=dut.player;game_update;if(dut.player!==saved) $fatal(1,"DIP load not held");
   ui[3]=0;repeat(10) @(negedge clk);game_update;
   if(dut.player[22:15]!=4) $fatal(1,"gamepad movement after DIP release %0d",level);
  end
  // Changing a switch while an address is being sent must affect only the
  // following transaction, not corrupt the current flash address.
  ui[3:0]=4'hd;repeat(10) @(negedge clk);
  dut.h=0;dut.v=480;dut.frame_phase=3;
  repeat(660) @(negedge clk);ui[3:0]=4'he;
  repeat(48) @(negedge clk);
  if(dut.player[40:23]!=18'h28000) $fatal(1,"DIP change corrupted in-flight lookup");
  game_update;
  if(dut.player[40:23]!=18'h2c000) $fatal(1,"DIP change missed next lookup");
  $display("PASS: real serial gamepad, jump edges, held jump, ena pause, all eight DIP selections, load hold and release");$finish;
 end
endmodule
