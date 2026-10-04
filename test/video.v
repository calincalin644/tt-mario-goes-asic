`timescale 1ns/1ps
module video_test;
 parameter PLAYER_X=3;
 parameter LEVEL=0;
 parameter ENEMY=0;
 parameter PICTURE=48+LEVEL;
 parameter X_FRACTION=0;
 parameter Y_FRACTION=0;
 localparam [17:0] NODE_POINTER=LEVEL<5 ? 18'h20000+LEVEL*18'h1000:LEVEL==5 ? 18'h28000:LEVEL==6 ? 18'h2c000:18'h14000;
 reg clk=0;always #20 clk=!clk;
 reg rst=0;
 wire [7:0] video,out,oe,pins;
 tt_um_mario_levels dut(8'b0,video,pins,out,oe,1'b1,clk,rst);
 flash_model flash(out[0],out[3],out,oe,pins);
 integer x,y,f;reg [5:0] rgb;reg [1023:0] filename;
 initial begin
  repeat(3) @(negedge clk);rst=1;
  dut.flash.player={NODE_POINTER,PLAYER_X[7:0],5'd26,PICTURE[5:0],4'd0};
  force dut.draw_x=PLAYER_X*4+X_FRACTION;force dut.draw_y=26*4+Y_FRACTION;
  // Warm up one raster: line zero has no preceding flash fetch after reset.
  repeat(420002) @(negedge clk);
  if(!$value$plusargs("FRAME=%s",filename)) filename="build/frame-3.ppm";
  f=$fopen(filename,"w");$fwrite(f,"P3\n640 480\n255\n");
  for(y=0;y<525;y=y+1) begin
   for(x=0;x<800;x=x+1) begin
    @(negedge clk);
    if(video[7]!==!(x>=656 && x<752)) $fatal(1,"HSYNC %d",x);
    if(video[3]!==!(y>=490 && y<492)) $fatal(1,"VSYNC %d",y);
    rgb={video[0],video[4],video[1],video[5],video[2],video[6]};
    if(x<640 && y<480) $fwrite(f,"%0d %0d %0d\n",rgb[5:4]*85,rgb[3:2]*85,rgb[1:0]*85);
    else if(rgb!==0) $fatal(1,"blanking");
    if(out[7:6]!==2'b11) $fatal(1,"RAM selected");
   end
  end
  $fclose(f);
  $display("PASS: full VGA raster, blanking and quad flash ownership world x %d",PLAYER_X);$finish;
 end
endmodule
