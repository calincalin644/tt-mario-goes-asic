#!/usr/bin/env bash
# Load Mario, then view VGA -> HDMI -> USB capture on the desktop.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: watch_fpga.sh [--view-only] [--list | --formats | --dry-run] [/dev/videoN]

Without a device, finds the capture node named "USB Video: USB Video".
It deliberately does not select the laptop webcam or a metadata node.

Defaults: MJPEG, 640x480, 60 fps, 960x720 window.
Loads the verified Mario bitstream already installed on the FPGA board and
sets its clock to 25.2 MHz. This restarts the game; --view-only skips loading.
Requires mpremote, found on PATH or in a nearby .venv/bin directory.
FPGA_PORT=auto selects the USB serial board; set a device path or id:SERIAL
explicitly if several MicroPython boards are connected. MPREMOTE overrides
the executable path. No flash assets are rewritten.
Overrides: CAPTURE_SIZE=1280x720 CAPTURE_FPS=60 watch_fpga.sh /dev/video2
           CAPTURE_FORMAT=yuyv422 CAPTURE_FPS=30 watch_fpga.sh /dev/video2

Keys: f = fullscreen, q or Escape = quit.
Game controls still come from the gamepad connected to the FPGA.
EOF
}

mode=view
load_game=true
device=
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --list) mode=list ;;
        --formats) mode=formats ;;
        --dry-run) mode=dry ;;
        --view-only) load_game=false ;;
        /dev/*) device=$arg ;;
        *) echo "Unknown argument: $arg" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ $mode == list ]]; then
    exec v4l2-ctl --list-devices
fi

if [[ -z $device ]]; then
    candidates=()
    for entry in /sys/class/video4linux/video*; do
        [[ -r $entry/name && -r $entry/index ]] || continue
        if [[ $(<"$entry/name") == 'USB Video: USB Video' && $(<"$entry/index") == 0 ]]; then
            candidates+=("/dev/${entry##*/}")
        fi
    done
    if (( ${#candidates[@]} != 1 )); then
        echo 'Specify the capture device explicitly; use --list to find it.' >&2
        exit 1
    fi
    device=${candidates[0]}
fi

if [[ $mode == formats ]]; then
    exec v4l2-ctl --device "$device" --list-formats-ext
fi

command -v ffplay >/dev/null || {
    echo 'ffplay is required (provided by the ffmpeg package).' >&2
    exit 1
}

command=(ffplay -hide_banner -loglevel warning
    -window_title "Mario FPGA — $device (F: fullscreen, Q: quit)"
    -f v4l2 -input_format "${CAPTURE_FORMAT:-mjpeg}"
    -video_size "${CAPTURE_SIZE:-640x480}" -framerate "${CAPTURE_FPS:-60}"
    -fflags nobuffer -flags low_delay -framedrop
    -probesize 32 -analyzeduration 0 -sync video -an
    -vf setdar=4/3 -x 960 -y 720 -i "$device")

if $load_game; then
    mpremote=${MPREMOTE:-}
    if [[ -z $mpremote ]]; then
        mpremote=$(command -v mpremote || true)
    fi
    if [[ -z $mpremote ]]; then
        search_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
        while [[ $search_dir != / ]]; do
            if [[ -x $search_dir/.venv/bin/mpremote ]]; then
                mpremote=$search_dir/.venv/bin/mpremote
                break
            fi
            search_dir=${search_dir%/*}
            [[ -n $search_dir ]] || break
        done
    fi
    [[ -n $mpremote ]] || {
        echo 'Install mpremote, set MPREMOTE=/path/to/mpremote, or use --view-only.' >&2
        exit 1
    }
    # Pinned to the board-tested eight-level enemy/DIP build. The board loader
    # checks this hash before loading and configures manual inputs and 25.2 MHz.
    load_command=("$mpremote" connect "${FPGA_PORT:-auto}" resume exec
        "import levels_board; levels_board.load('e3ce456c824bb8fb5c41ba6256f89db6a23b690bd7439a1470682ebe8407b12c')")
fi

if [[ $mode == dry ]]; then
    if $load_game; then
        printf '%q ' "${load_command[@]}"
        printf '\n'
    fi
    printf '%q ' "${command[@]}"
    printf '\n'
    exit 0
fi

[[ -c $device && -r $device && -w $device ]] || {
    echo "Cannot access capture device $device. Check its connection and permissions." >&2
    exit 1
}
if $load_game; then
    echo 'Loading Mario on the FPGA at 25.2 MHz...'
    if ! "${load_command[@]}"; then
        echo 'Mario could not be loaded. Check the board USB connection and close other serial consoles.' >&2
        echo 'The board must contain levels_board.py and the matching Mario bitstream.' >&2
        exit 1
    fi
fi
echo "Opening $device; F toggles fullscreen, Q quits."
exec "${command[@]}"
