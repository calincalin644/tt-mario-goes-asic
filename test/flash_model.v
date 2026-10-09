`timescale 1ns/1ps
module flash_model(input wire cs,sck,input wire [7:0] host,oe,output wire [7:0] pins);
 reg [7:0] memory[0:16777215];
 reg [7:0] command,modebits;
 reg [23:0] address;
 reg [3:0] data;
 reg drive;
 integer clocks,offset,f,n;
 wire [3:0] outgoing={host[5:4],host[2:1]};
 function [7:0] read_byte(input integer addr);
  begin
   if(addr[23:16]==8'h08 || addr[23:16]==8'h11 || addr[23:16]==8'h1b ||
      addr[23:16]==8'h20 || addr[23:16]==8'h2e || addr[23:16]==8'h5f ||
      addr[23:16]==8'h82 || addr[23:16]==8'had || addr[23:16]==8'hb1 || addr[23:16]==8'hff)
      $fatal(1,"Read of unrelated physical block %h",addr);
   read_byte=memory[addr];
  end
 endfunction
 task load_asset(input [1023:0] filename,input integer base,size);
  begin
   f=$fopen(filename,"rb");if(!f) $fatal(1,"Missing asset %s",filename);
   n=$fread(memory,f,base,size);$fclose(f);
   if(n!=size) $fatal(1,"asset size %s %0d != %0d",filename,n,size);
  end
 endtask
 integer i;
 initial begin
  for(i=0;i<16777216;i=i+1) memory[i]=8'hff;
  `include "build/flash-load.vh"
  drive=0;data=0;clocks=0;
 end
 assign pins=drive ? {2'b00,data[3:2],1'b0,data[1:0],1'b0}:0;
 always @(negedge cs) begin clocks=0;command=0;address=0;modebits=0;drive=0;end
 always @(posedge cs) drive=0;
 always @(posedge sck) if(!cs) begin
  if(host[7:6]!==2'b11) $fatal(1,"RAM selected");
  if(clocks<8) begin
   if(oe!==8'hfb) $fatal(1,"serial directions");
   command={command[6:0],host[1]};
   if(clocks==7 && command!=8'heb) $fatal(1,"wrong opcode %h",command);
  end else if(clocks<14) begin
   if(oe!==8'hff) $fatal(1,"quad address directions");
   address={address[19:0],outgoing};
  end else if(clocks<16) begin
   if(oe!==8'hff) $fatal(1,"mode directions");
   modebits={modebits[3:0],outgoing};
   if(clocks==15 && modebits!=8'hff) $fatal(1,"unexpected continuous mode");
  end else if(oe!==8'hc9) $fatal(1,"read bus contention");
  clocks=clocks+1;
 end
 reg [7:0] byte_value;
 always @(negedge sck) if(!cs && clocks>=20) begin
  offset=address+(clocks-20)/2;
  byte_value=read_byte(offset);
  data<=#5 (clocks%2==0 ? byte_value[7:4]:byte_value[3:0]);
  drive<=#5 1;
 end
endmodule
