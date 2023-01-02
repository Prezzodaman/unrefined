import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Speeds up or slows down a sample by repeating/skipping bytes")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to affect")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the affected file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("bytes",type=int,help="How many bytes to repeat/skip")
parser.add_argument("-s","--skip",action="store_true",help="Skips bytes instead of repeating them")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
bytes_to_skip=args.bytes
skip=args.skip
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Speed v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif bytes_to_skip>32:
    print("Error: Can't skip more than 8 bytes!")
elif bytes_to_skip<1:
    print("Error: Amount of bytes to skip must be 1 or above!")
else:
    file_orig=[]
    with open(file_name, "rb") as file:
        file_orig=file.read()

    file_finished=[]
    if skip:
        for a in range(0,len(file_orig),bytes_to_skip):
            file_finished.append(file_orig[a])
    else:
        for a in range(0,len(file_orig)):
            for b in range(0,bytes_to_skip+1):
                file_finished.append(file_orig[a])

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
