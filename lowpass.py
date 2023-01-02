# Reference:
#   https://dobrian.github.io/cmp/topics/filters/lowpassfilter.html
#
# and there was me thinking you had to use some complex equation...

import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Adds a rudimentary low-pass filter to a sample")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to filter")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the finished file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("passes",type=int,help="How many times to filter the sample")
parser.add_argument("-a","--accurate", action="store_true", help="Uses 32-bit accuracy instead of 8-bit. The result will be cleaner, but contain more noise",default=False)
parser.add_argument("-b","--before", action="store_true", help="Once converted, this plays the original sample before the filtered sample",default=False)
parser.add_argument("-hp","--highpass", action="store_true", help="Add a high-pass filter instead",default=False)

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
passes=args.passes
accurate=args.accurate
before=args.before
accuracy=3
highpass=args.highpass
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Lowpass v1.0.0")
print("by Presley Peters, 2022")
print()

if passes<1:
    print("Error: Number of passes must be greater than 0!")
elif passes>1024:
    print("Error: Number of passes must be 1024 or less!")
elif sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    print("Rendering file...")

    with open(file_name, "rb") as file:
        file_orig=file.read()

    file_bloated=[]
    for a in range(0,len(file_orig)):
        if accurate:
            file_bloated.append(file_orig[a]<<accuracy)
        else:
            file_bloated.append(file_orig[a])

    start_time=time.perf_counter()

    for a in range(0,passes):
        file_finished=[]
        previous_byte=0
        for byte in file_bloated:
            filtered_byte=(byte+previous_byte)//2 # this is literally it.
            file_finished.append(filtered_byte)
            previous_byte=byte
        file_bloated=file_finished.copy()
    file_finished_actual=file_bloated.copy()

    if accurate:
        file_quantized=[] # to reduce noise
        for byte in file_finished:
            file_quantized.append(byte>>accuracy)
        file_finished_actual=file_quantized.copy()

    if highpass:
        file_highpass=[]
        for byte_orig,byte_lowpass in zip(file_orig,file_finished_actual):
            byte=(byte_orig-abs(0-byte_lowpass))+127
            if byte<0:
                byte=0
            if byte>255:
                byte=255
            file_highpass.append(byte)
        file_finished_actual=file_highpass.copy()

    end_time=time.perf_counter()
        
    print("File rendered in " + str(round(end_time-start_time,2)) + " seconds!")

    with open(output_file, "wb") as file:
        file.write(bytearray(file_finished_actual))

    pya=pyaudio.PyAudio()
    stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

    if before:
        print("Before:")
        for byte in file_orig:
            stream.write(int.to_bytes(byte,1,"little"))

    if before:
        print("After:")
    else:
        print("Playing...")
            
    if highpass:
        for byte in file_finished_actual:
            stream.write(int.to_bytes(byte,1,"little"))

    stream.stop_stream()
    stream.close()
    pya.terminate()
