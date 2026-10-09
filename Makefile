NAME := tt_um_mario_levels
YOSYS ?= yosys
IVERILOG ?= iverilog
LIBERTY ?=
RTL := src/$(NAME).v src/controls.v
.PHONY: all area assets test test-progress test-motion test-enemies routes fpga flash-image images check smoke
.NOTPARALLEL:
all: assets

fpga: build/$(NAME).bin

flash-image: assets
	python3 scripts/pack_flash.py
	python3 test/test_flash_image.py

images: assets
	python3 scripts/export_images.py

check: test test-motion test-progress test-enemies test-boot test-audio test-melody test-music-flash test-coins

.PHONY: test-boot
test-boot:
	python3 test/test_mario_boot.py

smoke:
	$(MAKE) -C test
	python3 -m cocotb_tools.check_results test/results.xml

build:
	mkdir -p build
build/$(NAME).json: $(RTL) fpga/top.v | build
	$(YOSYS) -Q -T -l build/fpga-synthesis.log -p 'read_verilog -sv $^; synth_ice40 -top top -json $@'
build/$(NAME).asc: build/$(NAME).json fpga/fabricfox.pcf
	nextpnr-ice40 --up5k --package sg48 --freq 25.2 --seed 10 --pcf fpga/fabricfox.pcf --json $< --asc $@ --log build/nextpnr.log
build/$(NAME).bin: build/$(NAME).asc
	icepack $< $@
area: | build
	@test -n "$(LIBERTY)" || (echo "Set LIBERTY to a SKY130 standard-cell liberty file"; exit 1)
	$(YOSYS) -Q -T -l build/sky130-synthesis.log -p 'read_verilog -sv $(RTL); synth -top $(NAME) -flatten; dfflibmap -liberty $(LIBERTY); abc -liberty $(LIBERTY); clean; stat -liberty $(LIBERTY)'
assets: | build
	python3 scripts/build_assets.py

routes: assets
	python3 test/test_world.py

test: routes
	python3 test/test_flash_update.py
	$(IVERILOG) -g2012 -s stream_test -o build/stream test/stream.v test/flash_model.v $(RTL)
	vvp build/stream
	for level in 0 1 2 3 4 5 6 7; do for x in 3 127 228; do $(IVERILOG) -g2012 -s video_test -Pvideo_test.PLAYER_X=$$x -Pvideo_test.LEVEL=$$level -o build/video test/video.v test/flash_model.v $(RTL) && vvp build/video +FRAME=build/frame-$$x.ppm && python3 test/check_frame.py $$x $$level || exit 1; done; done
	$(IVERILOG) -g2012 -s core_controls_test -o build/controls test/controls.v test/flash_model.v $(RTL)
	vvp build/controls

test-progress: assets
	$(IVERILOG) -g2012 -s progress_test -o build/progress-test test/integrated_progress.v test/flash_model.v $(RTL)
	vvp build/progress-test
	python3 test/test_flash_update.py
	python3 test/test_progress_driver.py
	python3 -c 'from PIL import Image; Image.open("build/progress-50.ppm").save("build/progress-50.png")'

test-motion: routes
	$(IVERILOG) -g2012 -s motion_test -o build/motion test/motion.v test/flash_model.v $(RTL)
	vvp build/motion
	for spec in '11 0 3 0' '12 0 1 -1' '12 0 2 -2' '12 0 3 -3' '127 7 3 -5' '227 7 3 1'; do set -- $$spec; $(IVERILOG) -g2012 -s video_test -Pvideo_test.PLAYER_X=$$1 -Pvideo_test.LEVEL=$$2 -Pvideo_test.X_FRACTION=$$3 -Pvideo_test.Y_FRACTION=$$4 -o build/video-fraction test/video.v test/flash_model.v $(RTL) && vvp build/video-fraction +FRAME=build/frame-$$1.ppm && python3 test/check_frame.py $$1 $$2 $$3 $$4 || exit 1; done

test-enemies: assets
	python3 test/test_enemy_video.py

.PHONY: test-audio
test-audio: | build
	$(IVERILOG) -g2012 -s audio_test -o build/audio test/audio.v $(RTL)
	vvp build/audio

.PHONY: melody test-melody
melody:
	python3 scripts/build_melody.py

test-melody: | build
	python3 test/test_melody.py

.PHONY: test-music-flash
test-music-flash: assets
	$(IVERILOG) -g2012 -s music_flash_test -o build/music-flash-test test/music_flash.v test/flash_model.v $(RTL)
	vvp build/music-flash-test

.PHONY:
test-coins: | build
	$(IVERILOG) -g2012 -s coins_test -o build/coins-test test/coins.v $(RTL)
	vvp build/coins-test

.PHONY: test-coins
test-coins:
	python3 test/test_coins.py
