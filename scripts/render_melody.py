"""Render the RTL divider's audible baseband, without the 787.5 kHz PWM carrier.
Uses the same 31.5 kHz line ticks and 60 Hz frame slots as mario_melody.
A real PMOD's analog filtering and speaker response are not simulated.
"""
import argparse,json,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def render(output,repeats=2):
 a=json.loads((ROOT/'assets/melody.json').read_text())
 # Derive timing independently from the compact score, check exported slots.
 slots=[]
 for i,note in enumerate(a['step_notes']):
  slots += [a['note_divisors'][note]]*(6+(i&1))+[0]
 assert slots==a['frame_divisors']
 levels=[];count=0;polarity=0
 for divisor in slots*repeats:
  for _ in range(525):
   if not divisor:count=0;polarity=0;level=0
   else:
    if count==0:count=divisor-1;polarity=1-polarity
    else:count-=1
    level=1 if polarity else -1
   levels.append(level)
 # Sample the piecewise constant divider output at the WAV sample times.
 rate=44100
 indexes=np.arange(len(slots)*repeats*rate//60,dtype=np.int64)*31500//rate
 pcm=(np.asarray(levels,dtype=np.int16)[indexes]*8192).astype('<i2')
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
 with wave.open(str(output),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())
 print(f'{output}: {len(pcm)/rate:.3f}s, {repeats} loops, hardware pitches/timing, no decay envelope')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--repeats',type=int,default=2)
 args=p.parse_args();assert args.repeats>0;render(args.output,args.repeats)
