# Reference:
#   I came up with the "algorithm" in my head, all by myself!

import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Performs an >extremely< crude timestretch operation on a sample")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to stretch")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the finished file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("block_size",type=int,help="How big each \"block\" should be. Similar to \"cycle length\" on Akai samplers (when compressing a sample, this is how many bytes to skip - compression gets finer as the value gets lower)")
parser.add_argument("block_repeats",type=int,help="How many times to repeat each \"block\" (when compressing a sample, this is ignored, so just put 0)")
parser.add_argument("-c","--compress",action="store_true",help="\"Compresses\" the file instead of stretching it, by removing instead of repeating sections, making it shorter in length")
args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
block_size=args.block_size
block_repeats=args.block_repeats
block_skip=block_size
compress=args.compress
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Timestretch v1.0.0")
print("by Presley Peters, 2022")
print()

if block_repeats<1 and not compress:
    print("Error: There must be more than one block repeat!")
elif block_repeats>16 and not compress:
    print("Error: Block repeats must be 16 or less!")
elif sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    error=False
    with open(file_name, "rb") as file:
        file_orig=file.read()
    sample_size=len(file_orig)
    
    if compress:
        if block_size<1:
            print("Error: Must skip one byte or more!")
            error=True
        elif block_size>len(file_orig)//2:
            print("Error: Can't skip more than " + str(len(file_orig)//2) + " bytes!")
            error=True
    else:
        if block_size<20:
            print("Error: Block size must be greater than 20!")
            error=True
        elif block_size>4096:
            print("Error: Block size must be 4096 or less!")
            error=True
            
    if not error:
        print("Rendering file...")

        start_time=time.perf_counter()

        file_finished=[]
        sample_block_offset=0
        sample_skip_counter=0
        reached_end=False
        if compress:
            for byte in file_orig:
                sample_skip_counter+=1
                if sample_skip_counter>block_size:
                    sample_skip_counter=0
                else:
                    file_finished.append(byte)
        else:
            for a in range(0,sample_size,block_skip):
                sample_block=[]
                for b in range(0,block_size): # construct the "BLOCK"
                    if not reached_end:
                        sample_block.append(file_orig[sample_block_offset])
                        sample_block_offset=b+a
                        if sample_block_offset>sample_size-1:
                            reached_end=True
                for b in range(0,block_repeats+1):
                    for byte in sample_block:
                        file_finished.append(byte)

        end_time=time.perf_counter()
            
        if compress:
            print("Speed: " + str(round(len(file_finished)/len(file_orig),2)) + "%")
        else:
            print("Speed: " + str(round(len(file_orig)/len(file_finished),2)) + "%")
        print("File rendered in " + str(round(end_time-start_time,2)) + " seconds!")

        with open(output_file, "wb") as file:
            file.write(bytearray(file_finished))

        pya=pyaudio.PyAudio()
        stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

        print("Playing...")
        for byte in file_finished:
            stream.write(int.to_bytes(byte,1,"little"))

        stream.stop_stream()
        stream.close()
        pya.terminate()
