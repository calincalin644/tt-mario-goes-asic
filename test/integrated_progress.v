`timescale 1ns/1ps
module progress_test;
 reg clk=0;always #20 clk=!clk;
 reg rst=0;reg [7:0] host=8'hf7;
 wire [7:0] video,out,oe,pins,memory;
 assign pins=rst ? memory:host;
 tt_um_mario_levels dut(8'b0,video,pins,out,oe,1'b1,clk,rst);
 flash_model flash(rst ? out[0]:1'b1,out[3],out,oe,memory);
 integer x,y,f;reg [5:0] rgb,expected;reg [6:0] saved;
 always @(negedge clk) #1 if(!rst && oe!==0) $fatal(1,"ASIC must release all flash/PSRAM pins in maintenance");
 task nibble(input [3:0] data);
  begin
   host={2'b11,data[3:2],1'b0,data[1:0],1'b1};repeat(8) @(negedge clk);
   host[3]=1;repeat(8) @(negedge clk);host[3]=0;repeat(8) @(negedge clk);
  end
 endtask
 task arm;
  begin host=8'hf6;repeat(8) @(negedge clk);host[0]=1;repeat(8) @(negedge clk);end
 endtask
 task send(input [7:0] word);
  begin
   arm;nibble(word[7:4]);nibble(word[3:0]);
   if(dut.upload_status!=={&word[7:6],word[5:0]}) $fatal(1,"quad packet mismatch");
  end
 endtask
 task check(input [7:0] word);
  begin
   while(!(dut.h==0 && dut.v==240)) @(negedge clk);
   @(negedge clk);
   for(x=0;x<640;x=x+1) begin
    @(negedge clk);rgb={video[0],video[4],video[1],video[5],video[2],video[6]};
    expected=6'b000001;
    if(x>=64 && x<576) begin
     if(word[7:6]==3) expected=6'b110000;
     else if((x-64)/16<word[5:0]) expected=word[5] ? 6'b001100:6'b001111;
     else expected=6'b010101;
    end
    if(rgb!==expected) $fatal(1,"bar pixel x=%d word=%h got=%h expected=%h",x,word,rgb,expected);
   end
  end
 endtask
 initial begin
  repeat(3) @(negedge clk);rst=1;repeat(10) @(negedge clk);
  rst=0;repeat(10) @(negedge clk);
  send(8'h00);check(8'h00);
  send(8'h01);check(8'h01);
  send(8'h50);check(8'h50);
  // Full VGA frame while reset remains asserted and the RP owns flash.
  while(!(dut.h==0 && dut.v==0)) @(negedge clk);
  @(negedge clk);
  f=$fopen("build/progress-50.ppm","w");$fwrite(f,"P3\n640 480\n255\n");
  for(y=0;y<525;y=y+1) for(x=0;x<800;x=x+1) begin
   @(negedge clk);
   if(video[7]!==!(x>=656 && x<752) || video[3]!==!(y>=490 && y<492)) $fatal(1,"sync during held reset");
   rgb={video[0],video[4],video[1],video[5],video[2],video[6]};
   if(x<640 && y<480) $fwrite(f,"%d %d %d\n",rgb[5:4]*85,rgb[3:2]*85,rgb[1:0]*85);
   else if(rgb!==0) $fatal(1,"blanking");
  end
  $fclose(f);
  saved=dut.upload_status;
  // Ordinary SPI traffic and an incomplete progress packet cannot change the bar.
  host[0]=0;
  repeat(32) begin host[3]=1;repeat(8) @(negedge clk);host[3]=0;repeat(8) @(negedge clk);end
  host[0]=1;repeat(8) @(negedge clk);
  if(dut.upload_status!==saved) $fatal(1,"ordinary flash traffic altered progress");
  arm;nibble(4'hf);if(dut.upload_status!==saved) $fatal(1,"partial packet changed progress");
  send(8'h90);check(8'h90); // framing recovers; write/readback yellow
  send(8'h5f);check(8'h5f); // 31/32 full until checks finish
  send(8'h60);check(8'h60); // complete, green
  send(8'hcb);check(8'hcb); // partial error, red
  send(8'hc0);check(8'hc0); // zero-progress error turns the whole bar red
  rst=1;repeat(1000) @(negedge clk);
  if(dut.upload_status!==0 || oe===0) $fatal(1,"game did not regain bus after release");
  if(dut.player!==41'h1000001eb00) $fatal(1,"game state not restarted");
  $display("PASS: integrated 0/1/16/31/32-step bars, simple cyan/green/red colors, visible zero-progress errors, framed quad updates, SPI isolation, held-reset VGA, released BIDIR and game restart");$finish;
 end
 initial begin #1000000000;$fatal(1,"timeout");end
endmodule
