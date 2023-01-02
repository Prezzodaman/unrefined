# This entire program worked first try without any errors or adjustments needed. I can't believe it.

import pyaudio
import time
import argparse
import wave
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Converts a 16-bit signed wave file to a 8-bit unsigned raw file.")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to convert")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the converted file")
parser.add_argument("sample_rate", type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("-r","--right_channel", action="store_true", help="If the sample is stereo, use the right channel instead",default=False)

args=parser.parse_args()

input_file=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
right_channel=args.right_channel
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("16to8 v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>48000:
    print("Error: Sample rate cannot be above 48000!")
else:
    file_step=0
    file_start=0
    
    with wave.open(input_file,"rb") as file:
        file_orig=file.readframes(file.getnframes())
        file_step=file.getnchannels()*2
    
    if right_channel:
        file_start=1 # well that was hard to implement :kekw:
        
    file_quantized=[]
    for a in range(file_start,len(file_orig),file_step):
        if file_step>=4:
            byte=file_orig[a+1]
        else:
            byte=file_orig[a]
        if byte>127:
            byte-=127
        else:
            byte+=127
        file_quantized.append(byte)
        
    with open(output_file, "wb") as file:
        file.write(bytearray(file_quantized))
         
    pya=pyaudio.PyAudio()           
    stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

    print("Playing...")
    for byte in file_quantized:
        stream.write(int.to_bytes(byte,1,"little"))

    stream.stop_stream()
    stream.close()
    pya.terminate()
