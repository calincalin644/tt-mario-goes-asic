`default_nettype none
// Psychogenic PMOD: last 12 serial bits describe controller 1, active high.
module mario_controls(input wire clk, rst_n, frame, input wire [7:0] ui,
                       output wire left, right, jump, output wire [3:0] level_request);
    reg [6:0] meta, sync;
    reg last_clock, last_latch;
    reg [11:0] shift;
    reg [2:0] buttons;
    reg [6:0] age;
    always @(posedge clk) begin
        if (!rst_n) begin
            meta <= 0; sync <= 0; last_clock <= 0; last_latch <= 0;
            shift <= 12'hfff; buttons <= 0; age <= 7'd127;
        end else begin
            meta <= ui[6:0]; sync <= meta;
            last_clock <= sync[5]; last_latch <= sync[4];
            if (sync[5] && !last_clock) shift <= {shift[10:0],sync[6]};
            if (frame) begin
                if (age != 7'd127) age <= age+1'b1;
                if (age == 7'd127) buttons <= 0;
            end
            if (sync[4] && !last_latch) begin
                buttons <= shift == 12'hfff ? 3'b0 :
                           {shift[11] | shift[3],shift[4],shift[5]};
                age <= 7'd0;
            end
        end
    end
    assign left = buttons[0];
    assign right = buttons[1];
    assign jump = buttons[2];
    assign level_request = sync[3:0];
endmodule

`default_nettype wire
