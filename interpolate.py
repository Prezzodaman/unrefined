import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Linearly interpolates a sample, resulting in a smoother sound at half speed")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to interpolate")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the interpolated file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("-d","--double_speed", action="store_true", help="Plays the result at double speed",default=False)
parser.add_argument("-lp","--lowpass", action="store_true", help="Adds a low-pass filter for extra smoothness",default=False)

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
double_speed=args.double_speed
lowpass=args.lowpass
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Interpolate v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    if double_speed:
        sample_rate*=2
    print("Rendering file...")

    start_time=time.perf_counter()
    file_orig=[]
    with open(file_name, "rb") as file:
        file_orig=file.read()

    byte_previous=0
    file_finished=[]

    for byte in file_orig:
        file_finished.append(byte_previous)
        file_finished.append((byte+byte_previous)//2)
        byte_previous=byte
        
    if lowpass:
        file_finished_filtered=[]
        previous_byte=0
        for byte in file_finished:
            filtered_byte=(byte+previous_byte)//2
            file_finished_filtered.append(filtered_byte)
            previous_byte=byte
        file_finished=file_finished_filtered.copy()

    with open(output_file,"wb") as file:
        file.write(bytearray(file_finished))

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
