// SPDX-License-Identifier: Apache-2.0
`default_nettype none
module tt_um_mario_levels(input wire [7:0] ui_in,output wire [7:0] uo_out,
 input wire [7:0] uio_in,output wire [7:0] uio_out,uio_oe,
 input wire ena,clk,rst_n);
 // Reset transitions initialize the raster; a sustained low reset keeps VGA alive.
 // A normal low-then-high power-on reset initializes all game/video state.
 reg reset_previous;
 always @(posedge clk) reset_previous<=rst_n;
 wire raster_reset=rst_n!=reset_previous;
 reg [9:0] h,v;
 reg [1:0] frame_phase;
 wire frame=h==0 && v==480;
 always @(posedge clk) begin
  if(raster_reset) begin h<=0;v<=0;frame_phase<=0;end
  else begin
   if(h==799) begin h<=0;v<=v==524 ? 10'd0:v+1'b1;end
   else h<=h+1'b1;
   if(frame) frame_phase<=frame_phase+1'b1;
  end
 end
 // Maintenance packets use two quad nibbles with flash CS HIGH. Only the
 // error flag and six progress bits are retained by the plain bar. A preceding
 // empty CS-low interval resets framing. Real SPI traffic (CS low) is ignored.
 reg [1:0] upload_clock;
 reg upload_previous,upload_half;
 reg [2:0] upload_high;
 reg [6:0] upload_status;
 wire [3:0] upload_quad={uio_in[5:4],uio_in[2:1]};
 always @(posedge clk) begin
  if(rst_n) begin
   upload_clock<=0;upload_previous<=0;upload_half<=0;upload_high<=0;upload_status<=0;
  end else begin
   upload_clock<={upload_clock[0],uio_in[3]};upload_previous<=upload_clock[1];
   if(!uio_in[0]) upload_half<=0;
   else if(upload_clock[1] && !upload_previous) begin
    upload_half<=!upload_half;
    if(!upload_half) upload_high<={&upload_quad[3:2],upload_quad[1:0]};
    else upload_status<={upload_high,upload_quad};
   end
  end
 end
 wire [5:0] bar_column=h[9:4]-6'd4;
 reg bar_d,fill_d;
 always @(posedge clk) begin
  bar_d<=!bar_column[5] && v[9:5]==7;
  fill_d<=bar_column<upload_status[5:0];
 end
 wire left,right,jump;
 wire [3:0] level_request;
 mario_controls controls(clk,rst_n,frame,ui_in,left,right,jump,level_request);
 reg jump_previous,facing,level_load;
 reg [2:0] action;
 always @(posedge clk) begin
  if(!rst_n) begin action<=0;jump_previous<=0;facing<=1;level_load<=0;end
  else if(frame && frame_phase==3) begin
   action<=level_request[3] ? level_request[2:0]:{jump && !jump_previous,right,left};
   level_load<=level_request[3];jump_previous<=jump;
   if(left!=right) facing<=right;
  end
 end
 // Flash result: physical node pointer(18), x(8), feet(5), picture bank(6), motion(4).
 wire [40:0] player;
 wire [7:0] px=player[22:15];

 wire [4:0] feet=player[14:10];
 // Flash supplies interpolation metadata as well as the next node. There
 // is no previous-position register or delta calculation on the ASIC.
 wire [1:0] remaining=ena ? ~frame_phase:2'd0;
 wire moving_x=player[0];
 wire [7:0] render_cell_x=px-{{7{1'b0}},moving_x && facing && |remaining};
 wire [1:0] fraction_x=!moving_x ? 2'd0:facing ? -remaining:remaining;
 wire [9:0] draw_x={render_cell_x,fraction_x};
 wire [2:0] motion=player[3:1];
 wire [3:0] distance_y=motion==3 ? 4'd0:motion[0] ? {2'b00,remaining}:
                       motion[1] ? {1'b0,remaining,1'b0}:4'd0;
 wire [3:0] correction_y=motion[2] ? distance_y:-distance_y;
 wire [6:0] draw_y={feet,2'b00}+{{3{correction_y[3]}},correction_y};
 wire [9:0] camera=draw_x>48 ? draw_x-10'd48:10'd0;
 wire [5:0] screen_x=draw_x>48 ? 6'd48:draw_x[5:0];
 wire dead=motion==3,won=motion==4;
 wire [9:0] next_v=v==524 ? 10'd0:v+1'b1;
 wire [3:0] sprite_line=next_v[4:1]-{draw_y[2:0],1'b0};
 wire game_slot=v==480 && frame_phase==0 && ena;
 wire [31:0] sprite;
 wire [3:0] background;
 mario_stream_flash flash(clk,rst_n,h,game_slot,action,level_load,
  {player[9:4],next_v[8:1],camera}, {px[0],sprite_line},uio_in,uio_out,uio_oe,
  player,sprite,background);
 // All coordinate calculations precede pixel lookup by one clock.
 reg [8:0] sx;
 reg [7:0] sy;
 reg [3:0] bg;
 reg hs_d,vs_d,active_d,border;
 always @(posedge clk) begin
  if(raster_reset) begin sx<=0;sy<=0;bg<=0;hs_d<=1;vs_d<=1;active_d<=0;border<=0;end
  else begin
   sx<=h[9:1]-{screen_x,1'b0};
   sy<=v[8:1]-{draw_y,1'b0}+8'd16;
   bg<=background;
   hs_d<=!(h>=656 && h<752);vs_d<=!(v>=490 && v<492);
   active_d<=h<640 && v<480;
   border<=h<4 || h>=636 || v<4 || v>=476;
  end
 end
 wire [3:0] col=facing ? sx[3:0]:~sx[3:0];
 wire [1:0] ink=(sprite >> {col,1'b0}) & 2'b11;
 reg [5:0] rgb;
 always @* begin
  case(bg)
   0:rgb=6'b011011; 1:rgb=6'b100100; 2:rgb=6'b001100; 3:rgb=6'b111111;
   4:rgb=6'b111000; 5:rgb=6'b110100; 6:rgb=6'b000001; 7:rgb=6'b101010;
   8:rgb=6'b100110; 9:rgb=6'b000010; 10:rgb=6'b010101; 11:rgb=6'b101011;
   12:rgb=6'b010000; 13:rgb=6'b001000; 14:rgb=6'b111001; 15:rgb=6'b000011;
  endcase
  if(sx<16 && sy<16 && ink!=0) begin
   case(ink)
    1:rgb=6'b110000;2:rgb=6'b111001;3:rgb=6'b000011;
   endcase
  end
  if(border && (dead || won)) rgb=won ? 6'b001100:6'b110000;
  if(!rst_n) begin
   rgb=6'b000001;
   if(bar_d) begin
    if(upload_status[6]) rgb=6'b110000;
    else if(fill_d) rgb=upload_status[5] ? 6'b001100:6'b001111;
    else rgb=6'b010101;
   end
  end
  if(!active_d) rgb=0;
 end
 reg [7:0] video;
 always @(posedge clk) begin
  if(raster_reset) video<=8'h88;
  else video<={hs_d,rgb[0],rgb[2],rgb[4],vs_d,rgb[1],rgb[3],rgb[5]};
 end
 assign uo_out=video;
 wire unused=&{1'b0,ui_in[7]};
endmodule

// Two reads per scanline: small sprite (or one state transition in vblank),
// then a streaming background row. 0xEB, 24-bit quad address, FF mode, 4 dummy.
module mario_stream_flash(input wire clk,rst_n,input wire [9:0] h,
 input wire game_slot,input wire [2:0] action,input wire level_load,
 input wire [23:0] background_row,
 input wire [4:0] sprite_index,input wire [7:0] pins_in,
 output wire [7:0] pins_out,pins_oe,output reg [40:0] player,
 output reg [31:0] sprite,output reg [3:0] background);
 localparam IDLE=0,SPRITE=1,GAME=2,BG=3;
 reg [1:0] mode;
 reg [4:0] count;
 // Address sources remain stable until all six address nibbles are sent.
 // Select nibbles directly instead of storing and shifting 24 address bits.
 // The final unused node of level 1 contains eight level-entry records.
 wire [17:0] rule_pointer=level_load ? 18'h20fff:player[40:23];
 wire [23:0] rule_address={rule_pointer,action,3'b000};
 wire [23:0] address=mode==GAME ? rule_address:
                      mode==BG ? background_row:
                      {16'he000,1'b0,sprite_index,2'b00};
 reg [3:0] address_nibble;
 always @* case(count[2:0])
  0:address_nibble=address[23:20];1:address_nibble=address[19:16];
  2:address_nibble=address[15:12];3:address_nibble=address[11:8];
  4:address_nibble=address[7:4];default:address_nibble=address[3:0];
 endcase
 reg sck;
 reg streaming;
 reg [3:0] prefetch;
 wire [3:0] quad_in={pins_in[5:4],pins_in[2:1]};
 wire serial_bit=(8'heb >> (3'd7-count[2:0])) & 1'b1;
 wire [3:0] quad_out=count<8 ? {2'b11,1'b0,serial_bit} : count<14 ? address_nibble:4'hf;
 assign pins_out={2'b11,quad_out[3:2],sck,quad_out[1:0],mode==IDLE};
 assign pins_oe=!rst_n ? 8'h00 : mode==IDLE || count<8 ? 8'hfb : count<16 ? 8'hff:8'hc9;
 always @(posedge clk) begin
  if(!rst_n) begin
   player<=41'h1000001eb00;sprite<=0;background<=0;
   mode<=IDLE;count<=0;sck<=0;streaming<=0;prefetch<=0;
  end else begin
   if(h==640) begin mode<=IDLE;sck<=0;streaming<=0;end
   else if(h==644) begin
    mode<=game_slot ? GAME:SPRITE;count<=0;sck<=0;streaming<=0;
   end else if(h==708) begin
    mode<=BG;count<=0;sck<=0;streaming<=0;
   end else if(mode!=IDLE) begin
    if(streaming) begin
     if(h==799) background<=prefetch;
     if(h<640) begin
      if(!h[0]) begin sck<=1;prefetch<=quad_in;end
      else begin sck<=0;background<=prefetch;end
     end
    end else if(!sck) begin
     sck<=1;
     if(count>=20) begin
      case(mode)
       SPRITE:sprite<={sprite[27:0],quad_in};
       GAME:player<={player[36:0],quad_in};
       BG:prefetch<=quad_in;
      endcase
     end
    end else begin
     sck<=0;
     if(mode==BG && count==20) streaming<=1;
     else if((mode==SPRITE && count==27)||(mode==GAME && count==30)) mode<=IDLE;
     else count<=count+1'b1;
    end
   end
  end
 end
endmodule
`default_nettype wire
