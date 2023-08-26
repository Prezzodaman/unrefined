import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Cuts the sound volume at a certain rate")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to gargle")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the gargled file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("wait_length",type=int,help="The amount of bytes between cuts")
parser.add_argument("cut_length",type=int,help="The amount of bytes to cut")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
width=args.wait_length
cuts=args.cut_length
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Gargle v1.0.0")
print("by Presley Peters, 2023")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif width<1:
    print("Error: Must skip 1 byte or more!")
elif cuts<1:
    print("Error: Must cut more than 1 byte!")
else:
    file_orig=[]
    with open(file_name, "rb") as file:
        file_orig=file.read()

    file_finished=[]

    bytes_waited=0
    bytes_cut=0
    for a in file_orig:
        if bytes_waited<width:
            bytes_waited+=1
        else:
            bytes_cut+=1
            if bytes_cut>cuts:
                bytes_cut=0
                bytes_waited=0
        if bytes_cut==0:
            file_finished.append(a)
        else:
            file_finished.append(127)

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
