import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Trims a sample")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to trim")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the trimmed file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file")
parser.add_argument("start_point",type=int,help="Start point * 255")
parser.add_argument("end_point",type=int,help="End point * 255")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
start_point=args.start_point
end_point=args.end_point
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Truncate v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif start_point*255<0:
    print("Error: Start point cannot be negative!")
elif end_point*255==0:
    print("Error: End point must be 1 or greater!")
else:
    with open(file_name, "rb") as file:
        file_orig=file.read()
        
    if end_point*255>len(file_orig):
        print("Error: End point out of range! Must be between 1 and " + str(len(file_orig)//255) + ".")
    else:
        file_finished=file_orig[start_point*255:end_point*255] # It's That Easy! (tm)

        print("Playing...")

        pya=pyaudio.PyAudio()
        stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

        with open(output_file, "wb") as file:
            file.write(bytearray(file_finished))

        for byte in file_finished:
            stream.write(int.to_bytes(byte,1,"little"))
                
        stream.stop_stream()
        stream.close()
        pya.terminate()
