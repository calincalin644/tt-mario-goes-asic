`default_nettype none
module top(input wire clk, rst_n, input wire [7:0] ui_in,
           output wire [7:0] uo_out, inout wire [7:0] uio);
    wire [7:0] pin_out, pin_oe;
    genvar i;
    generate for(i=0;i<8;i=i+1) begin: bidir
        assign uio[i]=pin_oe[i] ? pin_out[i]:1'bz;
    end endgenerate
    tt_um_mario_levels game(.clk(clk), .rst_n(rst_n), .ena(1'b1),
        .ui_in(ui_in), .uo_out(uo_out), .uio_in(uio),
        .uio_out(pin_out), .uio_oe(pin_oe));
endmodule
`default_nettype wire
