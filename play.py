import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Plays a raw sample")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to play")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file")
parser.add_argument("-l","--loops",type=int,help="Number of additional times to play the file",default=0)

args=parser.parse_args()

file_name=args.input_file.name
sample_rate=args.sample_rate
loops=args.loops
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

if loops>128:
    print("Error: Number of loops must be 128 or below!")
elif loops<0:
    print("Error: Number of loops can't be negative!")
elif sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    print("Playing...")

    pya=pyaudio.PyAudio()
    stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

    for a in range(0,loops+1):
        with open(file_name, "rb") as file:
            data=file.read(1)
            while len(data)>0:
                stream.write(data)
                data=file.read(1)
            
    stream.stop_stream()
    stream.close()
    pya.terminate()
