# This is the only program of the lot that worked perfectly first try! I'm not even joking. Even I'm surprised.

import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Appends one sample onto the end of another")
parser.add_argument("first_file", type=argparse.FileType("r"),help="The name of the first file")
parser.add_argument("second_file", type=argparse.FileType("r"),help="The name of the second file")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the spliced file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("-m", "--mix", action="store_true", help="Mixes the samples together instead of joining")

args=parser.parse_args()

first_file=args.first_file.name
second_file=args.second_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
mix=args.mix
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Join v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    
    start_time=time.perf_counter()

    with open(first_file, "rb") as file:
        first_file_bytes=file.read()
    with open(second_file, "rb") as file:
        second_file_bytes=file.read()

    if len(first_file_bytes)==0:
        print("Error: file \"" + first_file + "\" is empty!")
    elif len(second_file)==0:
        print("Error: file \"" + second_file + "\" is empty!")
    else:
        print("Rendering file...")

        file_finished=[]
        
        if mix:
            for position in range(0,max(len(first_file_bytes),len(second_file_bytes))):
                sample_sum=0
                if position<len(first_file_bytes):
                    sample_sum+=first_file_bytes[position]
                else:
                    sample_sum+=first_file_bytes[-1]
                if position<len(second_file_bytes):
                    sample_sum+=second_file_bytes[position]
                else:
                    sample_sum+=second_file_bytes[-1]
                sample_sum=sample_sum//2
                file_finished.append(sample_sum)
        else:
            file_finished=first_file_bytes+second_file_bytes # this couldn't be simpler
        
        end_time=time.perf_counter()
            
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
